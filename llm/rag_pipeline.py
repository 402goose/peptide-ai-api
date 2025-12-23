"""
Peptide AI - RAG Pipeline

Orchestrates the full retrieval-augmented generation flow:
1. Query classification
2. Context retrieval from Weaviate
3. Prompt assembly
4. Response generation
5. Safety filtering
6. Disclaimer injection
"""

import logging
from typing import Optional, List, Dict, Any
from datetime import datetime
import openai

from llm.query_classifier import QueryClassifier, QueryClassification, QueryType, RiskLevel
from llm.evidence_classifier import get_evidence_for_peptide, get_evidence_badge, enrich_context_with_evidence
from storage.weaviate_client import WeaviateClient

logger = logging.getLogger(__name__)


class RAGPipeline:
    """
    Main RAG pipeline for peptide queries

    Handles the full flow from query to response with appropriate
    context retrieval and safety measures.
    """

    def __init__(
        self,
        weaviate_client: WeaviateClient,
        openai_client: openai.AsyncOpenAI,
        model: str = "gpt-4o"
    ):
        self.weaviate = weaviate_client
        self.openai = openai_client
        self.model = model
        self.classifier = QueryClassifier(openai_client)

    async def generate_response(
        self,
        query: str,
        user_context: Optional[Dict[str, Any]] = None,
        conversation_history: Optional[List[Dict[str, str]]] = None,
        response_mode: str = "balanced"
    ) -> Dict[str, Any]:
        """
        Generate a response to a user query

        Args:
            query: User's question
            user_context: User's journey context for personalization
            conversation_history: Previous messages in conversation

        Returns:
            Dict with response, sources, disclaimers, etc.
        """
        start_time = datetime.utcnow()

        # 1. Classify the query
        classification = await self.classifier.classify(query)
        logger.info(f"Query classified as {classification.query_type.value} "
                    f"(risk: {classification.risk_level.value})")

        # 2. Handle blocked queries
        if classification.risk_level == RiskLevel.BLOCKED:
            return self._blocked_response(classification)

        # 3. Retrieve context
        context_docs = await self._retrieve_context(
            query=query,
            classification=classification,
            user_context=user_context
        )

        # 4. Build the prompt (use response_mode if provided, otherwise infer from classification)
        system_prompt = self._build_system_prompt(classification, user_context, response_mode)
        context_prompt = self._build_context_prompt(
            context_docs,
            peptides_mentioned=classification.peptides_mentioned
        )

        # 5. Build conversation messages
        messages = self._build_messages(
            system_prompt=system_prompt,
            context_prompt=context_prompt,
            query=query,
            conversation_history=conversation_history
        )

        # 6. Generate response
        response_text = await self._generate(messages)

        # 7. Apply safety filtering
        response_text = self._apply_safety_filter(response_text, classification)

        # 8. Add disclaimers
        disclaimers = self._get_disclaimers(classification)

        # 9. Format sources
        sources = self._format_sources(context_docs)

        # 10. Generate LLM-based follow-up suggestions
        follow_ups = await self._generate_followups(query, response_text)

        elapsed_ms = int((datetime.utcnow() - start_time).total_seconds() * 1000)

        return {
            "response": response_text,
            "sources": sources,
            "disclaimers": disclaimers,
            "follow_up_questions": follow_ups,
            "classification": {
                "type": classification.query_type.value,
                "risk_level": classification.risk_level.value,
                "peptides": classification.peptides_mentioned,
            },
            "metadata": {
                "model": self.model,
                "context_chunks": len(context_docs),
                "elapsed_ms": elapsed_ms
            }
        }

    async def _retrieve_context(
        self,
        query: str,
        classification: QueryClassification,
        user_context: Optional[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Retrieve relevant context from vector store"""
        # Determine search parameters based on classification
        if classification.search_strategy == "minimal":
            return []  # Sourcing queries get minimal context

        # Set alpha based on strategy
        if classification.search_strategy == "research_heavy":
            alpha = 0.6  # More semantic
            source_filter = "research"
            include_outcomes = False
        elif classification.search_strategy == "experience_heavy":
            alpha = 0.4  # More keyword
            source_filter = "user_journeys"
            include_outcomes = True
        else:
            alpha = 0.5
            source_filter = None
            include_outcomes = True

        # Perform search
        results = await self.weaviate.hybrid_search(
            query=query,
            limit=10,
            alpha=alpha,
            source_filter=source_filter,
            peptide_filter=classification.peptides_mentioned if classification.peptides_mentioned else None,
            include_outcomes=include_outcomes
        )

        return results

    def _build_system_prompt(
        self,
        classification: QueryClassification,
        user_context: Optional[Dict[str, Any]],
        response_mode: str = "balanced"
    ) -> str:
        """Build the system prompt based on query type and response mode"""
        base_prompt = """You are Peptide AI, an expert research assistant. Help users understand peptide research and protocols.

## YOUR APPROACH
- Be direct and helpful - give specific peptide recommendations
- Start with actionable information, add caveats briefly at the end
- Focus on peptides (not supplements like GABA, IP6, etc.)
- IMPORTANT: This is a CONVERSATION - remember what the user told you earlier and build on it
- Reference their specific conditions, goals, and previous questions
- Help them dig deeper into peptides discussed earlier in the conversation
- If they mentioned conditions (psoriasis, back pain, etc.), keep those in mind for all responses

## DETECT USER TYPE FROM THEIR QUESTIONS
Adapt your response based on these signals:
- **Beginner signals**: "first time", "new to", "what is", "safe?", "worried about" → More explanation, reassurance, safety focus
- **Budget signals**: "cost", "cheap", "affordable", "worth it", "price" → Include cost comparisons, budget-friendly options
- **Skeptic signals**: "evidence", "studies", "proof", "research", "scientific" → Lead with citations, acknowledge limitations
- **Advanced signals**: "stack", "cycle", "protocol", "reconstitute", specific peptide names → Skip basics, give advanced protocols
- **Anxious signals**: "side effects", "dangerous", "interactions", "worried" → Extra safety info, start-low advice, reassurance

## CRITICAL REQUIREMENTS (NEVER SKIP THESE):

1. **TIMELINE** - ALWAYS include when to expect results:
   - Initial effects: "Most notice changes in X-Y weeks"
   - Peak effects: "Full effects typically seen at X weeks"
   - Example: "For BPC-157, initial improvement often occurs within 2-4 weeks, with optimal results at 8-12 weeks"
   - If question is vague ("How long until results?"), INFER the peptide from conversation context or ask which peptide
   - NEVER give a short unhelpful response - if unclear, provide timelines for the most common healing peptides (BPC-157, TB-500)

2. **SIDE EFFECTS** - List 2-4 common ones for each peptide mentioned:
   - Common: nausea, headache, fatigue, etc.
   - Less common but important to know

3. **LEGAL STATUS** - Always mention briefly:
   - "Research use only in most countries"
   - "Not FDA approved"
   - "Check local regulations"

4. **COST CONTEXT** - For budget-conscious users, ALWAYS mention:
   - "Typical monthly cost: $30-80 for BPC-157, $50-150 for TB-500, $200-400 for GLP-1s"
   - "More affordable option: X" vs "Premium option: Y"
   - "Budget tip: Start with just BPC-157, it's effective alone and cheaper"
   - If asked about minimum doses, emphasize the COST SAVINGS of lower doses

5. **STUDY CITATIONS** - When mentioning research, cite properly:
   - Format: "Author et al. (Year), N=X subjects"
   - ALWAYS note study type: "(human RCT)", "(animal study)", "(in-vitro)", "(case report)"
   - Example: "Sikiric et al. (2018, N=24 rats, animal study) found..."
   - Example: "In a human trial, Smith et al. (2021, N=86, double-blind RCT)..."
   - If no studies exist, say so: "No peer-reviewed human studies are available for this peptide"

6. **SAFETY & DRUG INTERACTIONS** - For anxious/cautious users:
   - List known drug interactions (if any)
   - Mention contraindications
   - Suggest "start low and slow" approach
   - Recommend: "Consult your doctor if taking [common medications]"

## HANDLING SKEPTICS & EVIDENCE QUESTIONS
When users ask about evidence, studies, or express skepticism:
- BE HONEST about research limitations upfront - most peptide research is preclinical (animal studies)
- CITE SPECIFIC STUDIES when available: "Sikiric et al. (2013) found..." or "In a 2022 study with 42 participants..."
- ACKNOWLEDGE what we DON'T know: "Human clinical trials are limited" or "Long-term safety data is lacking"
- DON'T repeat dosing protocols when they're asking about evidence quality
- CRITIQUE study quality when relevant: "This was a small study (n=12) without a control group"
- VALIDATE their skepticism: "You're right to want evidence - here's what we actually know..."
- AVOID hype language like "miracle", "breakthrough", or "game-changer"
- DISTINGUISH clearly between: peer-reviewed human trials > animal studies > in-vitro > anecdotal

## RESPONSE FORMAT (CRITICAL - follow this structure)

Start with a brief 1-2 sentence intro addressing their situation.

Then for EACH peptide you recommend, use this exact format:

---

### 🧬 [Peptide Name]

**Why it helps:** One sentence explaining the mechanism relevant to their condition.

**Evidence:** Use the badge from the EVIDENCE QUALITY section (🟢 Strong, 🟡 Moderate, 🔴 Limited, ⚪ Anecdotal) + brief explanation

**Typical Protocol:**
- **Starting Dose:** X mcg (for beginners, start here)
- **Standard Dose:** X-Y mcg, frequency (e.g., "250mcg 2x daily")
- **Timing:** When to take (morning, before bed, with/without food)
- **Duration:** X weeks typical cycle
- **Administration:** SubQ injection, specific sites

**Common Side Effects:** List 2-3 most common (e.g., "mild nausea first few days, injection site redness")

**Cost Estimate:** Approximate monthly cost range

**What to expect:** Timeline with milestones:
- Week 1-2: Initial changes
- Week 4-6: Noticeable effects
- Week 8-12: Full benefits

---

After covering peptides, add:

### 💡 Getting Started
Brief practical advice on which to try first and why.

### ⚠️ Note
One sentence disclaimer about research purposes.

## FORMATTING RULES
- Use ### headers with emojis to break up sections
- Use **bold** for peptide names and key terms
- Use bullet points with **bold labels** for protocols
- Keep paragraphs SHORT (2-3 sentences max)
- Use --- dividers between peptide sections
- NO walls of text - make it scannable

"""
        # Add query-type specific instructions
        type_instructions = {
            QueryType.RESEARCH: """Focus on:
- Peer-reviewed studies with specific findings
- Human vs animal study distinctions
- Quality and size of research
""",
            QueryType.DOSING: """Focus on:
- Commonly researched protocol ranges
- Timing (morning vs evening, with/without food)
- Cycle lengths from studies
- Starting dose recommendations
""",
            QueryType.SAFETY: """Focus on:
- Known side effects (common vs rare)
- Drug interactions
- Contraindications
- What to monitor
""",
            QueryType.SOURCING: """Focus on:
- What to look for in quality (COAs, third-party testing)
- Red flags to avoid
- General sourcing best practices
""",
            QueryType.EXPERIENCE: """Focus on:
- What users commonly report
- Typical timeline for results
- Common adjustments people make
- Range of experiences (not just positive)
""",
            QueryType.STACKING: """The user is asking about COMBINING peptides. Focus on:
- Recommend a specific stack for their goals (2-3 peptides that work together)
- Explain WHY these peptides synergize
- Provide timing/protocol for the stack (e.g., "BPC-157 morning, TB-500 evening")
- Note any interactions to be aware of
- Give a "starter stack" vs "advanced stack" option if appropriate
""",
            QueryType.GENERAL: """The user needs guidance. Focus on:
- Identify the TOP peptides for their stated goals
- If they mention multiple goals (weight + energy + sleep), address EACH with specific peptides
- Suggest a practical starting point
- Be enthusiastic and helpful - they came here for peptide guidance!
""",
        }

        prompt = base_prompt + type_instructions.get(classification.query_type, "")

        # Add user context if available
        if user_context:
            prompt += f"""
USER CONTEXT:
- Expertise level: {user_context.get('expertise_level', 'unknown')}
- Primary goals: {', '.join(user_context.get('primary_goals', []))}
- Past experience: {', '.join(user_context.get('past_peptides', []))}
- Known sensitivities: {', '.join(user_context.get('reported_sensitivities', []))}

Tailor your response to their experience level and goals.
"""

        # Add response mode specific modifications
        if response_mode == "skeptic":
            prompt += """

## SKEPTIC MODE ACTIVATED
You are responding to a scientifically-minded user who wants EVIDENCE, not recommendations.

CRITICAL: For this user, you MUST:
1. LEAD with evidence quality - state upfront if evidence is limited
2. CITE specific studies: "Sikiric et al. (2013, N=24 rats, animal study)" format
3. Clearly distinguish: human RCTs > animal studies > in-vitro > anecdotal
4. ACKNOWLEDGE GAPS: "No completed human RCTs exist for BPC-157"
5. If asked about rat-to-human translation, explain dosing extrapolation challenges
6. If asked "why no FDA approval", explain: lack of commercial incentive, patent challenges, insufficient human trials
7. AVOID hype words: "promising", "powerful", "breakthrough"
8. Answer the direct question first (YES/NO), then provide context
9. Include study limitations: sample size, control groups, blinding
10. Discuss publication bias and lack of negative study publication
"""
        elif response_mode == "actionable":
            prompt += """

## ACTIONABLE MODE ACTIVATED
User wants quick, practical protocols. Be concise:
- Lead with specific doses and timing (not ranges)
- Include cost breakdown and budget tips
- Give exact stacking protocols with timing
- Mention reconstitution details if relevant
- One brief disclaimer at the end
- Format: numbered steps they can follow today
"""
        else:  # balanced mode (default)
            prompt += """

## BALANCED MODE
Provide comprehensive but digestible information:
- Include both benefits AND limitations
- Mix research evidence with practical user experiences
- Provide dosing ranges with "start here" recommendations
- Balance optimism with appropriate caution
- Include cost context when relevant
- Suggest what to try first and why
"""

        return prompt

    def _build_context_prompt(
        self,
        context_docs: List[Dict[str, Any]],
        peptides_mentioned: Optional[List[str]] = None
    ) -> str:
        """Build context section from retrieved documents"""
        sections = []

        # Add evidence quality for mentioned peptides
        if peptides_mentioned:
            sections.append("## EVIDENCE QUALITY (use these badges in your response):\n")
            for peptide in peptides_mentioned[:5]:  # Limit to top 5
                evidence = get_evidence_for_peptide(peptide)
                badge = get_evidence_badge(evidence.level)
                sections.append(f"**{peptide}**: {badge}")
                sections.append(f"  - Human studies: {evidence.human_studies}, Animal: {evidence.animal_studies}")
                sections.append(f"  - FDA: {evidence.fda_status}")
                sections.append(f"  - {evidence.summary}\n")

        if not context_docs:
            sections.append("\nNo specific research context available for this query.")
            return "\n".join(sections)

        sections.append("\n## RELEVANT RESEARCH CONTEXT:")

        for i, doc in enumerate(context_docs[:10], 1):
            props = doc.get("properties", {})
            collection = doc.get("collection", "unknown")
            source_type = props.get('source_type', 'unknown').upper()

            if collection == "PeptideChunk":
                # Research document
                sections.append(f"""
[{i}] {props.get('title', 'Untitled')}
Source: {source_type}
Citation: {props.get('citation', 'N/A')}
Content: {props.get('content', '')[:500]}...
""")
            else:
                # Journey outcome
                sections.append(f"""
[{i}] User Journey: {props.get('peptide', 'Unknown peptide')}
Duration: {props.get('duration_weeks', 'N/A')} weeks
Efficacy: {props.get('overall_efficacy', 'N/A')}/10
Summary: {props.get('outcome_narrative', '')[:300]}...
""")

        return "\n".join(sections)

    def _build_messages(
        self,
        system_prompt: str,
        context_prompt: str,
        query: str,
        conversation_history: Optional[List[Dict[str, str]]]
    ) -> List[Dict[str, str]]:
        """Build the message array for the API call"""
        messages = [
            {"role": "system", "content": system_prompt + "\n\n" + context_prompt}
        ]

        # Add conversation history
        if conversation_history:
            for msg in conversation_history[-10:]:  # Last 10 messages
                messages.append({
                    "role": msg.get("role", "user"),
                    "content": msg.get("content", "")
                })

        # Add current query
        messages.append({"role": "user", "content": query})

        return messages

    async def _generate(self, messages: List[Dict[str, str]]) -> str:
        """Generate response from LLM (OpenAI or Ollama)"""
        try:
            response = await self.openai.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=0.7,
                max_tokens=2000,
            )
            return response.choices[0].message.content or ""
        except Exception as e:
            logger.error(f"LLM generation failed ({self.model}): {e}")
            return "I apologize, but I encountered an error generating a response. Please try again."

    def _apply_safety_filter(
        self,
        response: str,
        classification: QueryClassification
    ) -> str:
        """Apply safety filtering to response"""
        # Filter out any specific vendor recommendations that slipped through
        vendor_patterns = [
            r"you can buy.*from",
            r"order from",
            r"purchase at",
            r"available at",
            r"www\.[a-z]+\.com",
        ]

        import re
        for pattern in vendor_patterns:
            response = re.sub(
                pattern,
                "[vendor information removed - please research independently]",
                response,
                flags=re.IGNORECASE
            )

        return response

    def _get_disclaimers(self, classification: QueryClassification) -> List[str]:
        """Get appropriate disclaimers based on classification"""
        disclaimer_texts = {
            "research_only": "This information is for research and educational purposes only, not medical advice.",
            "consult_professional": "Always consult a qualified healthcare professional before using any peptides.",
            "sourcing_legal": "Peptide legality varies by jurisdiction. Verify legal status in your area.",
            "verify_source": "If obtaining peptides for research, verify quality through independent testing and COAs.",
            "dosing_individual": "Dosing is highly individual. Start with the lowest effective dose and adjust based on response.",
            "side_effects": "Monitor for side effects and discontinue use if concerning symptoms occur.",
            "fda_status": "Many peptides are not FDA-approved for human use and are sold for research purposes only.",
        }

        return [
            disclaimer_texts.get(d, d)
            for d in classification.disclaimer_types
            if d in disclaimer_texts
        ]

    def _format_sources(self, context_docs: List[Dict[str, Any]]) -> List[Dict[str, str]]:
        """Format context docs as source citations"""
        sources = []

        for doc in context_docs[:5]:  # Top 5 sources
            props = doc.get("properties", {})
            sources.append({
                "title": props.get("title", "Untitled"),
                "citation": props.get("citation", ""),
                "url": props.get("url", ""),
                "type": props.get("source_type", "unknown")
            })

        return sources

    async def _generate_followups(
        self,
        query: str,
        response: str
    ) -> List[str]:
        """Generate contextual follow-up questions using LLM"""
        try:
            followup_prompt = f"""Based on this conversation about peptides, suggest 3-4 natural follow-up questions the user might want to ask next.

USER'S QUESTION: {query}

YOUR RESPONSE (summary): {response[:500]}...

Generate follow-up questions that:
1. Help them dive deeper into the specific peptides mentioned
2. Address practical concerns (dosing, timing, what to expect)
3. Explore related topics they might not have considered
4. Are conversational and specific (not generic)

Return ONLY a JSON array of 3-4 question strings. Example:
["How should I time my BPC-157 doses around meals?", "What results do most people see in the first 2 weeks?", "Should I cycle off or can I use this continuously?"]"""

            response_obj = await self.openai.chat.completions.create(
                model="gpt-4o-mini",  # Use fast model for follow-ups
                messages=[{"role": "user", "content": followup_prompt}],
                temperature=0.7,
                max_tokens=300,
            )

            import json
            content = response_obj.choices[0].message.content or "[]"
            # Clean up the response - extract JSON array
            content = content.strip()
            if content.startswith("```"):
                content = content.split("```")[1]
                if content.startswith("json"):
                    content = content[4:]

            follow_ups = json.loads(content)
            if isinstance(follow_ups, list) and len(follow_ups) > 0:
                return follow_ups[:4]
        except Exception as e:
            logger.warning(f"Failed to generate follow-ups: {e}")

        # Fallback to generic but still useful questions
        return [
            "What's the typical protocol and dosing for this?",
            "What side effects should I watch for?",
            "How long until I might see results?",
            "Can these peptides be combined with others?"
        ]

    def _blocked_response(self, classification: QueryClassification) -> Dict[str, Any]:
        """Generate response for blocked queries"""
        return {
            "response": "I'm not able to provide information on this topic. If you're experiencing a medical emergency, please contact emergency services or a healthcare provider immediately.",
            "sources": [],
            "disclaimers": ["This query cannot be answered by this platform."],
            "follow_up_questions": [],
            "classification": {
                "type": classification.query_type.value,
                "risk_level": classification.risk_level.value,
            },
            "metadata": {"blocked": True}
        }
