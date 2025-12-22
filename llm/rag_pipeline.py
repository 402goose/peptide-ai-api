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
        conversation_history: Optional[List[Dict[str, str]]] = None
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

        # 4. Build the prompt
        system_prompt = self._build_system_prompt(classification, user_context)
        context_prompt = self._build_context_prompt(context_docs)

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

        # 10. Generate follow-up suggestions
        follow_ups = self._suggest_followups(classification, context_docs)

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
        user_context: Optional[Dict[str, Any]]
    ) -> str:
        """Build the system prompt based on query type"""
        base_prompt = """You are Peptide AI, an expert research assistant for peptides. You help users understand peptide research and protocols.

CRITICAL RULES:
- ALWAYS be helpful and provide specific peptide recommendations
- NEVER say "I can't recommend" or "consult a doctor first" at the START of responses
- START with actionable peptide information, then add caveats at the end
- This is a RESEARCH PLATFORM - users expect peptide-specific answers
- Only discuss actual peptides (not supplements like GABA, IP6, etc.)

FORMATTING:
- Use **bold** for peptide names
- Structure with clear headers (##)
- Use bullet points for protocols
- Include specific dosing ranges from research (e.g., "100-300mcg daily")
- Keep responses focused and scannable

RESPONSE STRUCTURE:
1. Start with a direct answer addressing their specific question
2. Name 2-4 specific peptides most relevant to their goals
3. For each peptide: what it does, typical protocol, what users report
4. Brief safety notes inline (not as separate warning block)
5. One-line disclaimer at the very end

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

        return prompt

    def _build_context_prompt(self, context_docs: List[Dict[str, Any]]) -> str:
        """Build context section from retrieved documents"""
        if not context_docs:
            return "No specific research context available for this query."

        sections = ["RELEVANT CONTEXT:"]

        for i, doc in enumerate(context_docs[:10], 1):
            props = doc.get("properties", {})
            collection = doc.get("collection", "unknown")

            if collection == "PeptideChunk":
                # Research document
                sections.append(f"""
[{i}] {props.get('title', 'Untitled')}
Source: {props.get('source_type', 'unknown').upper()}
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

    def _suggest_followups(
        self,
        classification: QueryClassification,
        context_docs: List[Dict[str, Any]]
    ) -> List[str]:
        """Generate relevant follow-up questions"""
        # Build peptide-specific follow-ups if we know which peptides were discussed
        peptides = classification.peptides_mentioned
        conditions = classification.conditions_mentioned

        # Peptide-specific follow-ups
        if peptides:
            peptide = peptides[0]  # Use first mentioned peptide
            return [
                f"What's the typical {peptide} protocol and dosing?",
                f"What do users report experiencing with {peptide}?",
                f"What are the side effects of {peptide}?",
                f"Can {peptide} be combined with other peptides?"
            ]

        # Condition-specific follow-ups
        if conditions:
            condition = conditions[0]
            return [
                f"Which peptides are best for {condition}?",
                f"What does the research say about peptides for {condition}?",
                f"What protocols do people use for {condition}?",
                f"How long until I might see results?"
            ]

        # Query type fallbacks
        followups = {
            QueryType.RESEARCH: [
                "What clinical trials have been conducted?",
                "What are the known mechanisms of action?",
                "How does the research compare to user experiences?"
            ],
            QueryType.DOSING: [
                "What side effects should I watch for?",
                "How long does a typical cycle last?",
                "What's the best time of day to administer?",
                "How do I reconstitute and store this peptide?"
            ],
            QueryType.SAFETY: [
                "Are there any known drug interactions?",
                "What are signs that I should stop using?",
                "How do long-term users report outcomes?",
                "What bloodwork should I monitor?"
            ],
            QueryType.EXPERIENCE: [
                "What does the research say about this?",
                "What protocols do most users follow?",
                "How long until users typically see results?",
                "What's the most common starting dose?"
            ],
            QueryType.STACKING: [
                "What are the individual effects of each compound?",
                "Are there any interaction concerns?",
                "What timing works best for this stack?",
                "Should I start with one peptide first?"
            ],
            QueryType.GENERAL: [
                "What peptides would you recommend for my goals?",
                "How do I get started with peptides?",
                "What should I know before starting?",
                "What results can I realistically expect?"
            ],
        }

        return followups.get(classification.query_type, [
            "What peptides are best for my goals?",
            "How do I get started?",
            "What should I expect?",
            "What are the safety considerations?"
        ])

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
