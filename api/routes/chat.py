"""
Peptide AI - Chat Endpoints

Main conversational interface for the peptide AI assistant.
"""

from fastapi import APIRouter, Depends, Request, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from typing import Optional, List, AsyncGenerator
from datetime import datetime
from uuid import uuid4
import openai
import logging
import json

from api.deps import get_database, get_settings
from api.middleware.auth import get_current_user
from api.journey_service import JourneyService
from llm.rag_pipeline import RAGPipeline
from storage.weaviate_client import WeaviateClient

logger = logging.getLogger(__name__)

router = APIRouter()


# =============================================================================
# REQUEST/RESPONSE MODELS
# =============================================================================

class ChatMessage(BaseModel):
    """A single message in a conversation"""
    role: str = Field(..., pattern="^(user|assistant|system)$")
    content: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class ResponseMode(str):
    """Response mode for the AI"""
    BALANCED = "balanced"      # Default: recommendations with evidence context
    SKEPTIC = "skeptic"        # Evidence-first, honest limitations, then recommendations
    ACTIONABLE = "actionable"  # Quick protocols, minimal caveats


class ChatRequest(BaseModel):
    """Request to send a message to the AI"""
    message: str = Field(..., min_length=1, max_length=10000)
    conversation_id: Optional[str] = None  # None = new conversation
    context: Optional[dict] = None  # Additional context (e.g., current journey)
    history: Optional[List[ChatMessage]] = None  # Conversation history for streaming
    response_mode: Optional[str] = "balanced"  # balanced, skeptic, or actionable


class ChatResponse(BaseModel):
    """Response from the AI"""
    conversation_id: str
    message: str
    sources: List[dict] = []  # Citations from RAG
    disclaimers: List[str] = []  # Relevant disclaimers
    follow_up_questions: List[str] = []  # Suggested follow-ups
    metadata: dict = {}


class ConversationSummary(BaseModel):
    """Summary of a conversation for listing"""
    conversation_id: str
    title: str
    preview: str
    message_count: int
    created_at: datetime
    updated_at: datetime


# =============================================================================
# CHAT ENDPOINTS
# =============================================================================

@router.post("/chat", response_model=ChatResponse)
async def chat(
    request: Request,
    body: ChatRequest,
    user: dict = Depends(get_current_user)
):
    """
    Send a message to the Peptide AI assistant

    This is the main endpoint for the conversational interface.
    Handles:
    - New conversations (no conversation_id)
    - Continuing existing conversations
    - RAG retrieval and response generation
    - Disclaimer injection based on query type
    """
    db = get_database()
    settings = get_settings()
    user_id = user["user_id"]

    # Get or create conversation
    conversation_id = body.conversation_id
    if conversation_id:
        conversation = await db.conversations.find_one({
            "conversation_id": conversation_id,
            "user_id": user_id
        })
        if not conversation:
            raise HTTPException(404, "Conversation not found")
        messages = conversation.get("messages", [])
    else:
        conversation_id = str(uuid4())
        messages = []

    # Add user message
    user_message = ChatMessage(role="user", content=body.message)
    messages.append(user_message.model_dump())

    # TODO: Implement full RAG pipeline
    # 1. Classify query type
    # 2. Retrieve relevant context from Weaviate
    # 3. Build prompt with context and user history
    # 4. Generate response with OpenAI
    # 5. Apply safety checks
    # 6. Add disclaimers

    # Generate response via RAG pipeline
    rag_result = await _generate_response(
        query=body.message,
        messages=messages,
        user_id=user_id,
        context=body.context,
        db=db,
        settings=settings
    )

    response_text = rag_result.get("response", "")

    # Add assistant message
    assistant_message = ChatMessage(role="assistant", content=response_text)
    messages.append(assistant_message.model_dump())

    # Generate title if new conversation
    title = conversation.get("title") if body.conversation_id else None
    if not title:
        title = _generate_title(body.message)

    # Save conversation
    await db.conversations.update_one(
        {"conversation_id": conversation_id},
        {
            "$set": {
                "conversation_id": conversation_id,
                "user_id": user_id,
                "title": title,
                "messages": messages,
                "updated_at": datetime.utcnow()
            },
            "$setOnInsert": {
                "created_at": datetime.utcnow()
            }
        },
        upsert=True
    )

    return ChatResponse(
        conversation_id=conversation_id,
        message=response_text,
        sources=rag_result.get("sources", []),
        disclaimers=rag_result.get("disclaimers", []),
        follow_up_questions=rag_result.get("follow_up_questions", []),
        metadata=rag_result.get("metadata", {"model": settings.openai_model})
    )


@router.post("/chat/stream")
async def chat_stream(
    request: Request,
    body: ChatRequest,
    user: dict = Depends(get_current_user)
):
    """
    Stream a chat response using Server-Sent Events.
    Returns chunks of the response as they're generated.
    """
    db = get_database()
    settings = get_settings()
    user_id = user["user_id"]

    # Get or create conversation
    conversation_id = body.conversation_id
    if conversation_id:
        conversation = await db.conversations.find_one({
            "conversation_id": conversation_id,
            "user_id": user_id
        })
        if not conversation:
            raise HTTPException(404, "Conversation not found")
        messages = conversation.get("messages", [])
    else:
        conversation_id = str(uuid4())
        messages = []

    # Add user message
    user_message = ChatMessage(role="user", content=body.message)
    messages.append(user_message.model_dump())

    async def generate_stream() -> AsyncGenerator[str, None]:
        """Generate SSE stream"""
        try:
            # Send conversation ID first
            yield f"data: {json.dumps({'type': 'conversation_id', 'conversation_id': conversation_id})}\n\n"

            # Initialize clients
            if settings.llm_provider == "ollama":
                llm_client = openai.AsyncOpenAI(
                    base_url=f"{settings.ollama_url}/v1",
                    api_key="ollama"
                )
                model = settings.ollama_model
            else:
                llm_client = openai.AsyncOpenAI(api_key=settings.openai_api_key)
                model = settings.openai_model

            weaviate = WeaviateClient(
                url=settings.weaviate_url,
                api_key=settings.weaviate_api_key if settings.weaviate_api_key else None,
                openai_api_key=settings.openai_api_key
            )

            try:
                await weaviate.connect()

                # Build context using RAG pipeline components
                from llm.query_classifier import QueryClassifier
                classifier = QueryClassifier()
                classification = await classifier.classify(body.message)

                # Get context from Weaviate
                alpha = 0.5
                if classification.search_strategy == "research_heavy":
                    alpha = 0.6
                elif classification.search_strategy == "experience_heavy":
                    alpha = 0.4

                context_docs = await weaviate.hybrid_search(
                    query=body.message,
                    limit=10,
                    alpha=alpha,
                    peptide_filter=classification.peptides_mentioned if classification.peptides_mentioned else None,
                    include_outcomes=True
                )

                # Send sources
                sources = []
                for doc in context_docs[:5]:
                    props = doc.get("properties", {})
                    sources.append({
                        "title": props.get("title", "Untitled"),
                        "citation": props.get("citation", ""),
                        "url": props.get("url", ""),
                        "type": props.get("source_type", "unknown")
                    })
                yield f"data: {json.dumps({'type': 'sources', 'sources': sources})}\n\n"

                # Build mode-specific system prompt
                response_mode = body.response_mode or "balanced"
                system_prompt = _get_system_prompt_for_mode(response_mode)

                # Build context with evidence badges
                from llm.evidence_classifier import get_evidence_for_peptide, get_evidence_badge

                context_text = ""

                # Add evidence badges for mentioned peptides
                if classification.peptides_mentioned:
                    context_text += "## EVIDENCE QUALITY (include these badges in your response):\n\n"
                    for peptide in classification.peptides_mentioned[:5]:
                        evidence = get_evidence_for_peptide(peptide)
                        badge = get_evidence_badge(evidence.level)
                        context_text += f"**{peptide}**: {badge}\n"
                        context_text += f"  - Human studies: {evidence.human_studies}, Animal: {evidence.animal_studies}\n"
                        context_text += f"  - {evidence.summary}\n\n"

                context_text += "\n## RELEVANT RESEARCH:\n\n"
                for i, doc in enumerate(context_docs[:5], 1):
                    props = doc.get("properties", {})
                    context_text += f"[{i}] {props.get('title', 'Untitled')}\n"
                    context_text += f"{props.get('content', '')[:500]}\n\n"

                # Build messages with conversation history
                llm_messages = [
                    {"role": "system", "content": system_prompt + "\n\n" + context_text}
                ]

                # Add conversation history (limit to last 10 messages to avoid token limits)
                if body.history:
                    for msg in body.history[-10:]:
                        llm_messages.append({
                            "role": msg.role,
                            "content": msg.content
                        })

                # Add current message
                llm_messages.append({"role": "user", "content": body.message})

                # Stream the response
                full_response = ""
                stream = await llm_client.chat.completions.create(
                    model=model,
                    messages=llm_messages,
                    temperature=0.7,
                    max_tokens=2000,
                    stream=True
                )

                async for chunk in stream:
                    if chunk.choices[0].delta.content:
                        content = chunk.choices[0].delta.content
                        full_response += content
                        yield f"data: {json.dumps({'type': 'content', 'content': content})}\n\n"

                # Generate contextual follow-ups using LLM
                try:
                    followup_prompt = f"""Based on this conversation about peptides, suggest 3-4 natural follow-up questions.

USER'S QUESTION: {body.message}

YOUR RESPONSE (summary): {full_response[:500]}...

Generate follow-up questions that:
1. Help them dive deeper into the specific peptides mentioned
2. Address practical concerns (dosing, timing, what to expect)
3. Are conversational and specific (not generic)

Return ONLY a JSON array of 3-4 question strings."""

                    followup_response = await llm_client.chat.completions.create(
                        model="gpt-4o-mini",
                        messages=[{"role": "user", "content": followup_prompt}],
                        temperature=0.7,
                        max_tokens=300,
                    )
                    followup_content = followup_response.choices[0].message.content or "[]"
                    followup_content = followup_content.strip()
                    if followup_content.startswith("```"):
                        followup_content = followup_content.split("```")[1]
                        if followup_content.startswith("json"):
                            followup_content = followup_content[4:]
                    follow_ups = json.loads(followup_content)
                    if not isinstance(follow_ups, list):
                        follow_ups = []
                except Exception as e:
                    logger.warning(f"Failed to generate follow-ups: {e}")
                    follow_ups = [
                        "What's the typical protocol for this?",
                        "What side effects should I watch for?",
                        "How long until I might see results?"
                    ]

                # Send completion with metadata
                disclaimers = [
                    "This information is for research and educational purposes only, not medical advice.",
                    "Always consult a qualified healthcare professional before using any peptides."
                ]

                yield f"data: {json.dumps({'type': 'done', 'disclaimers': disclaimers, 'follow_up_questions': follow_ups})}\n\n"

                # Save conversation
                assistant_message = ChatMessage(role="assistant", content=full_response)
                messages.append(assistant_message.model_dump())

                title = messages[0]["content"][:50] + "..." if len(messages[0]["content"]) > 50 else messages[0]["content"]

                await db.conversations.update_one(
                    {"conversation_id": conversation_id},
                    {
                        "$set": {
                            "conversation_id": conversation_id,
                            "user_id": user_id,
                            "title": title,
                            "messages": messages,
                            "updated_at": datetime.utcnow()
                        },
                        "$setOnInsert": {"created_at": datetime.utcnow()}
                    },
                    upsert=True
                )

            finally:
                await weaviate.close()

        except Exception as e:
            logger.error(f"Streaming error: {e}")
            yield f"data: {json.dumps({'type': 'error', 'error': str(e)})}\n\n"

    return StreamingResponse(
        generate_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )


@router.get("/chat/conversations", response_model=List[ConversationSummary])
async def list_conversations(
    request: Request,
    limit: int = 20,
    offset: int = 0,
    user: dict = Depends(get_current_user)
):
    """List user's conversations"""
    db = get_database()
    user_id = user["user_id"]

    cursor = db.conversations.find(
        {"user_id": user_id}
    ).sort("updated_at", -1).skip(offset).limit(limit)

    conversations = []
    async for doc in cursor:
        messages = doc.get("messages", [])
        preview = messages[-1]["content"][:100] if messages else ""

        conversations.append(ConversationSummary(
            conversation_id=doc["conversation_id"],
            title=doc.get("title", "Untitled"),
            preview=preview,
            message_count=len(messages),
            created_at=doc.get("created_at", datetime.utcnow()),
            updated_at=doc.get("updated_at", datetime.utcnow())
        ))

    return conversations


@router.get("/chat/conversations/{conversation_id}")
async def get_conversation(
    conversation_id: str,
    user: dict = Depends(get_current_user)
):
    """Get a specific conversation with full history"""
    db = get_database()
    user_id = user["user_id"]

    conversation = await db.conversations.find_one({
        "conversation_id": conversation_id,
        "user_id": user_id
    })

    if not conversation:
        raise HTTPException(404, "Conversation not found")

    return {
        "conversation_id": conversation["conversation_id"],
        "title": conversation.get("title", "Untitled"),
        "messages": conversation.get("messages", []),
        "created_at": conversation.get("created_at"),
        "updated_at": conversation.get("updated_at")
    }


@router.delete("/chat/conversations/{conversation_id}")
async def delete_conversation(
    conversation_id: str,
    user: dict = Depends(get_current_user)
):
    """Delete a conversation"""
    db = get_database()
    user_id = user["user_id"]

    result = await db.conversations.delete_one({
        "conversation_id": conversation_id,
        "user_id": user_id
    })

    if result.deleted_count == 0:
        raise HTTPException(404, "Conversation not found")

    return {"status": "deleted"}


# =============================================================================
# HELPER FUNCTIONS (Placeholder implementations)
# =============================================================================

async def _generate_response(
    query: str,
    messages: list,
    user_id: str,
    context: Optional[dict],
    db,
    settings
) -> dict:
    """
    Generate AI response using RAG pipeline

    Returns full response dict with:
    - response: The generated text
    - sources: Citations from RAG
    - disclaimers: Relevant disclaimers
    - follow_up_questions: Suggested follow-ups
    - metadata: Generation metadata
    """
    try:
        # Initialize LLM client based on provider
        if settings.llm_provider == "ollama":
            # Use Ollama via OpenAI-compatible API
            llm_client = openai.AsyncOpenAI(
                base_url=f"{settings.ollama_url}/v1",
                api_key="ollama"  # Ollama doesn't need a real key
            )
            model = settings.ollama_model
            logger.info(f"Using Ollama at {settings.ollama_url} with model {model}")
        else:
            # Use OpenAI
            llm_client = openai.AsyncOpenAI(api_key=settings.openai_api_key)
            model = settings.openai_model
            logger.info(f"Using OpenAI with model {model}")

        # Initialize Weaviate client
        weaviate = WeaviateClient(
            url=settings.weaviate_url,
            api_key=settings.weaviate_api_key if settings.weaviate_api_key else None,
            openai_api_key=settings.openai_api_key
        )

        try:
            await weaviate.connect()

            # Get user context for personalization
            user_context = None
            if user_id and user_id != "admin":
                journey_service = JourneyService(db)
                try:
                    user_ctx = await journey_service.build_user_context(user_id)
                    user_context = user_ctx.model_dump()
                except Exception as e:
                    logger.warning(f"Could not build user context: {e}")

            # Build conversation history
            conversation_history = [
                {"role": msg.get("role"), "content": msg.get("content")}
                for msg in messages[:-1]  # Exclude current message
            ]

            # Generate response via RAG pipeline
            rag = RAGPipeline(
                weaviate_client=weaviate,
                openai_client=llm_client,
                model=model
            )

            result = await rag.generate_response(
                query=query,
                user_context=user_context,
                conversation_history=conversation_history
            )

            return result

        finally:
            await weaviate.close()

    except Exception as e:
        logger.error(f"RAG pipeline error: {e}")
        # Fallback response
        return {
            "response": (
                "I apologize, but I encountered an error processing your request. "
                "Please try again. If the issue persists, our team has been notified.\n\n"
                "*This is a research platform. Always consult healthcare professionals.*"
            ),
            "sources": [],
            "disclaimers": ["This information is for research purposes only."],
            "follow_up_questions": [],
            "metadata": {"error": str(e)}
        }


def _generate_title(message: str) -> str:
    """Generate a conversation title from the first message"""
    # Take first 50 chars or up to first newline
    title = message.split("\n")[0][:50]
    if len(message) > 50:
        title += "..."
    return title


def _get_disclaimers(query: str) -> List[str]:
    """
    Get relevant disclaimers based on query content

    TODO: Implement full disclaimer system based on:
    - Query type classification
    - Peptides mentioned
    - FDA status of peptides
    - User jurisdiction
    """
    # Default disclaimers
    disclaimers = [
        "This information is for research purposes only and not medical advice.",
        "Consult a healthcare professional before using any peptides.",
    ]

    # Add sourcing disclaimer if relevant
    sourcing_keywords = ["buy", "source", "purchase", "vendor", "supplier", "where to get"]
    if any(kw in query.lower() for kw in sourcing_keywords):
        disclaimers.append(
            "Peptide sourcing information is provided for research purposes. "
            "Verify legal status in your jurisdiction."
        )

    return disclaimers


def _suggest_followups(query: str) -> List[str]:
    """
    Suggest relevant follow-up questions

    TODO: Make this dynamic based on:
    - Query type
    - Response content
    - User's journey stage
    """
    # Generic follow-ups for now
    return [
        "What's a typical protocol for this?",
        "What side effects should I watch for?",
        "How does this compare to alternatives?"
    ]


def _get_system_prompt_for_mode(mode: str) -> str:
    """
    Get the system prompt based on response mode.

    Modes:
    - balanced: Default, recommendations with evidence context
    - skeptic: Evidence-first, honest about limitations
    - actionable: Quick protocols, minimal caveats
    """

    # Base instructions shared across modes
    base_intro = """You are Peptide AI, an expert research assistant. Help users understand peptide research and protocols.

## CONVERSATION RULES
- This is a CONVERSATION - remember what the user told you earlier and build on it
- Reference their specific conditions, goals, and previous questions
- If they mentioned conditions (psoriasis, back pain, etc.), keep those in mind
- Focus on peptides (not supplements like GABA, IP6, etc.)
"""

    # Formatting rules shared across modes
    formatting_rules = """
## FORMATTING RULES
- Use ### headers with emojis to break up sections
- Use **bold** for peptide names and key terms
- Use bullet points with **bold labels** for protocols
- Keep paragraphs SHORT (2-3 sentences max)
- Use --- dividers between peptide sections
- NO walls of text - make it scannable
"""

    if mode == "skeptic":
        return base_intro + """
## SKEPTIC MODE - EVIDENCE FIRST

Your primary job is to be HONEST about what we know and don't know. Users in this mode want the truth, not optimism.

### APPROACH:
1. START with the evidence quality - don't bury limitations at the end
2. CITE SPECIFIC STUDIES with authors and years: "Sikiric et al. (2013) found..."
3. DISTINGUISH clearly between evidence tiers:
   - 🟢 Strong: Multiple human RCTs, FDA approval
   - 🟡 Moderate: Small human studies + large animal studies
   - 🔴 Limited: Animal studies only, in-vitro only
   - ⚪ Anecdotal: User reports, forum discussions
4. CRITIQUE study quality: "This was a small study (n=12) without a control group"
5. ACKNOWLEDGE gaps: "No long-term human safety data exists"
6. AVOID hype language: no "miracle", "breakthrough", "game-changer"

### RESPONSE FORMAT:

Start by validating their desire for evidence.

For EACH peptide:

---

### 🧬 [Peptide Name]

**Evidence Quality:** [Badge] - Be specific about study limitations

**What the Research Shows:**
- Cite specific studies with (Author, Year)
- Note sample sizes and study design
- Distinguish human vs animal data

**What We DON'T Know:**
- List honest limitations and gaps

**If You Decide to Proceed:**
- **Dose:** X-Y mcg/mg based on [study]
- **Duration:** X weeks

---

End with:

### ⚠️ Bottom Line
Honest summary of whether evidence supports their interest.
""" + formatting_rules

    elif mode == "actionable":
        return base_intro + """
## ACTIONABLE MODE - GET TO THE POINT

Users want practical protocols quickly. Minimize caveats and theory.

### APPROACH:
1. LEAD with specific recommendations - peptide names, doses, timing
2. SKIP lengthy mechanism explanations
3. GIVE concrete protocols, not ranges: "250mcg" not "200-300mcg"
4. INCLUDE timing: "Morning on empty stomach" or "Before bed"
5. TELL them what to expect and when
6. ONE brief disclaimer at the end

### RESPONSE FORMAT:

### 🎯 Your Protocol

**Best Option:** [Peptide Name]
- **Dose:** Xmcg, [frequency]
- **Timing:** [specific time]
- **Duration:** X weeks
- **Expect results:** [timeline]

**Alternative:** [Second peptide if relevant]
- Same format, brief

### 📋 Quick Start
Numbered steps to begin.

### ⚡ Pro Tips
2-3 practical tips from experienced users.

*Disclaimer: Research purposes only.*
""" + formatting_rules

    else:  # balanced (default)
        return base_intro + """
## BALANCED MODE - RECOMMENDATIONS WITH CONTEXT

### APPROACH:
- Be direct and helpful - give specific peptide recommendations
- Start with actionable information, add caveats at the end
- Include evidence badges to set expectations
- Be honest about limitations without being discouraging

### HANDLING EVIDENCE QUESTIONS:
When users ask about studies or express skepticism:
- BE HONEST about research limitations - most peptide research is preclinical
- CITE SPECIFIC STUDIES when available
- ACKNOWLEDGE what we DON'T know
- VALIDATE their skepticism

### RESPONSE FORMAT:

Start with a brief 1-2 sentence intro addressing their situation.

For EACH peptide you recommend:

---

### 🧬 [Peptide Name]

**Why it helps:** One sentence explaining the mechanism.

**Evidence:** 🟢/🟡/🔴/⚪ + brief explanation

**Typical Protocol:**
- **Dose:** X-Y mcg/mg, frequency
- **Duration:** X weeks
- **Administration:** SubQ, etc.

**What to expect:** 1-2 sentences on timeline and outcomes.

---

After covering peptides:

### 💡 Getting Started
Brief practical advice on which to try first.

### ⚠️ Note
One sentence disclaimer about research purposes.
""" + formatting_rules
