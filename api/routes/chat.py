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

import re
from api.deps import get_database, get_settings
from api.middleware.auth import get_current_user
from api.journey_service import JourneyService
from llm.rag_pipeline import RAGPipeline
from storage.weaviate_client import WeaviateClient

logger = logging.getLogger(__name__)

# =============================================================================
# INTENT DETECTION
# =============================================================================

# Common peptide names to detect
PEPTIDE_NAMES = [
    "bpc-157", "bpc157", "bpc 157", "tb-500", "tb500", "tb 500",
    "semaglutide", "tirzepatide", "ozempic", "wegovy", "mounjaro",
    "ipamorelin", "cjc-1295", "cjc1295", "ghrp-6", "ghrp-2", "mk-677",
    "pt-141", "melanotan", "mt2", "aod-9604", "sermorelin", "hexarelin",
    "epithalon", "thymosin", "ll-37", "ghk-cu", "selank", "semax",
    "dihexa", "nad+", "nad", "sr9009", "sr-9009"
]

def _detect_intent(message: str) -> str:
    """
    Detect user intent from message to select appropriate response mode.

    Uses semantic understanding rather than brittle regex patterns.

    Returns:
    - "coach": User has supplies, ready to start, needs practical guidance
    - "research": User is researching, comparing, wants information
    - "balanced": Default mode
    """
    msg = message.lower()

    # === CATEGORY 1: Possession signals (they have something) ===
    possession_words = ["got", "have", "bought", "ordered", "received", "arrived", "came in", "picked up", "my"]
    has_possession = any(word in msg for word in possession_words)

    # === CATEGORY 2: Supply keywords (injection supplies) ===
    supply_words = [
        "bac water", "back water", "bacteriostatic", "sterile water",
        "insulin needle", "insulin syringe", "syringe", "needle",
        "vial", "reconstitut", "alcohol swab", "alcohol wipe"
    ]
    has_supplies = any(word in msg for word in supply_words)

    # === CATEGORY 3: Readiness/action signals (wanting to do something) ===
    action_words = [
        "start", "begin", "try", "use", "take", "inject", "dose", "dosing",
        "first time", "new to", "how do i", "how should i", "what do i",
        "ready to", "going to", "about to", "planning to", "want to start"
    ]
    has_action_intent = any(word in msg for word in action_words)

    # === CATEGORY 4: Specific peptide mentioned ===
    mentions_peptide = any(peptide in msg for peptide in PEPTIDE_NAMES)

    # === CATEGORY 5: Research signals ===
    research_words = [
        "what is", "tell me about", "benefits of", "side effects of",
        "vs", "versus", "compare", "which is better", "difference between",
        "should i try", "thinking about", "considering", "looking into",
        "research", "studies", "evidence", "learn about", "curious about"
    ]
    has_research_intent = any(word in msg for word in research_words)

    # === SCORING LOGIC ===
    # Coach mode triggers when user seems ready to act
    coach_score = 0
    research_score = 0

    if has_possession:
        coach_score += 2
    if has_supplies:
        coach_score += 2
    if has_action_intent:
        coach_score += 1
    if mentions_peptide and has_possession:
        coach_score += 1  # "I got BPC-157" is strong signal
    if mentions_peptide and has_action_intent:
        coach_score += 1  # "How do I use BPC-157" is strong signal

    if has_research_intent:
        research_score += 2
    if not has_possession and not has_supplies:
        research_score += 1  # No supplies mentioned = probably researching

    logger.info(f"[Intent] Scores - coach: {coach_score}, research: {research_score} | "
                f"possession={has_possession}, supplies={has_supplies}, action={has_action_intent}, "
                f"peptide={mentions_peptide}, research={has_research_intent}")

    # Decision thresholds
    if coach_score >= 3 and coach_score > research_score:
        logger.info(f"[Intent] -> COACH mode")
        return "coach"
    elif research_score >= 2 and research_score > coach_score:
        logger.info(f"[Intent] -> RESEARCH mode")
        return "research"

    logger.info(f"[Intent] -> BALANCED mode (default)")
    return "balanced"

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
    conversation = None
    if conversation_id:
        conversation = await db.conversations.find_one({
            "conversation_id": conversation_id,
            "user_id": user_id
        })
        if not conversation:
            # Conversation doesn't exist for this user - create new one
            # This handles cases where user has an old URL or conversation was from different user
            logger.info(f"Conversation {conversation_id} not found for user {user_id}, creating new")
            conversation_id = str(uuid4())

    if conversation:
        messages = conversation.get("messages", [])
    else:
        conversation_id = conversation_id or str(uuid4())
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
        settings=settings,
        response_mode=body.response_mode or "balanced"
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
    conversation = None
    if conversation_id:
        conversation = await db.conversations.find_one({
            "conversation_id": conversation_id,
            "user_id": user_id
        })
        if not conversation:
            # Conversation doesn't exist for this user - create new one
            # This handles cases where user has an old URL or conversation was from different user
            logger.info(f"[Stream] Conversation {conversation_id} not found for user {user_id}, creating new")
            conversation_id = str(uuid4())

    if conversation:
        messages = conversation.get("messages", [])
    else:
        conversation_id = conversation_id or str(uuid4())
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
                # If no explicit mode set, detect intent from message
                if body.response_mode and body.response_mode != "balanced":
                    response_mode = body.response_mode
                else:
                    response_mode = _detect_intent(body.message)
                    if response_mode != "balanced":
                        logger.info(f"[Chat] Auto-detected mode: {response_mode}")

                # Send detected mode to frontend for UI adjustments
                yield f"data: {json.dumps({'type': 'mode', 'mode': response_mode})}\n\n"

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


@router.patch("/chat/conversations/{conversation_id}")
async def update_conversation(
    conversation_id: str,
    body: dict,
    user: dict = Depends(get_current_user)
):
    """Update a conversation (e.g., rename)"""
    db = get_database()
    user_id = user["user_id"]

    # Only allow updating title for now
    update_fields = {}
    if "title" in body:
        update_fields["title"] = body["title"]

    if not update_fields:
        raise HTTPException(400, "No valid fields to update")

    update_fields["updated_at"] = datetime.utcnow()

    result = await db.conversations.update_one(
        {"conversation_id": conversation_id, "user_id": user_id},
        {"$set": update_fields}
    )

    if result.matched_count == 0:
        raise HTTPException(404, "Conversation not found")

    return {"status": "updated"}


@router.delete("/chat/conversations")
async def delete_all_conversations(
    user: dict = Depends(get_current_user)
):
    """Delete all conversations for a user (admin use)"""
    db = get_database()
    user_id = user["user_id"]

    result = await db.conversations.delete_many({"user_id": user_id})

    return {"deleted": result.deleted_count}


@router.post("/chat/conversations/{conversation_id}/share")
async def create_share_link(
    conversation_id: str,
    user: dict = Depends(get_current_user)
):
    """Create a public share link for a conversation"""
    db = get_database()
    user_id = user["user_id"]

    # Get the conversation
    conversation = await db.conversations.find_one({
        "conversation_id": conversation_id,
        "user_id": user_id
    })

    if not conversation:
        raise HTTPException(404, "Conversation not found")

    # Check if share already exists
    existing_share = await db.shared_conversations.find_one({
        "conversation_id": conversation_id
    })

    if existing_share:
        return {
            "share_id": existing_share["share_id"],
            "share_url": f"/share/{existing_share['share_id']}"
        }

    # Create new share
    share_id = str(uuid4())[:8]  # Short ID for nicer URLs

    await db.shared_conversations.insert_one({
        "share_id": share_id,
        "conversation_id": conversation_id,
        "user_id": user_id,
        "title": conversation.get("title", "Untitled"),
        "messages": conversation.get("messages", []),
        "created_at": conversation.get("created_at", datetime.utcnow()),
        "shared_at": datetime.utcnow()
    })

    return {
        "share_id": share_id,
        "share_url": f"/share/{share_id}"
    }


@router.delete("/admin/shared-conversations/cleanup")
async def cleanup_old_shares(
    user: dict = Depends(get_current_user)
):
    """
    Delete shared conversations older than 3 days (admin only)
    """
    if not user.get("is_admin"):
        raise HTTPException(403, "Admin access required")

    db = get_database()
    from datetime import timedelta

    cutoff_date = datetime.utcnow() - timedelta(days=3)

    result = await db.shared_conversations.delete_many({
        "shared_at": {"$lt": cutoff_date}
    })

    return {"deleted": result.deleted_count}


@router.delete("/admin/shared-conversations/all")
async def delete_all_shares(
    user: dict = Depends(get_current_user)
):
    """
    Delete ALL shared conversations (admin only)
    """
    if not user.get("is_admin"):
        raise HTTPException(403, "Admin access required")

    db = get_database()
    result = await db.shared_conversations.delete_many({})

    return {"deleted": result.deleted_count}


@router.get("/share/{share_id}")
async def get_shared_conversation(share_id: str):
    """
    Get a publicly shared conversation (no auth required)

    This endpoint is public - anyone with the link can view the conversation.
    """
    db = get_database()

    shared = await db.shared_conversations.find_one({"share_id": share_id})

    if not shared:
        raise HTTPException(404, "Shared conversation not found")

    # Return only the necessary fields for public viewing
    return {
        "share_id": shared["share_id"],
        "title": shared.get("title", "Untitled"),
        "messages": [
            {"role": msg.get("role"), "content": msg.get("content")}
            for msg in shared.get("messages", [])
            if msg.get("content")  # Filter out empty messages
        ],
        "created_at": shared.get("created_at"),
        "shared_at": shared.get("shared_at")
    }


# =============================================================================
# HELPER FUNCTIONS (Placeholder implementations)
# =============================================================================

async def _generate_response(
    query: str,
    messages: list,
    user_id: str,
    context: Optional[dict],
    db,
    settings,
    response_mode: str = "balanced"
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
                conversation_history=conversation_history,
                response_mode=response_mode
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

## ⚠️ CRITICAL DOSING SAFETY RULES (NEVER VIOLATE)

### GENERAL PRINCIPLES
1. **ALWAYS START LOW** - For ANY new user, recommend the LOWEST effective dose first
2. **NEVER make up dosages** - If you don't have verified source data, say "dosing data is limited"
3. **CITE YOUR SOURCE** - Every dosing recommendation should reference a study or established protocol
4. **FLAG UNCERTAINTY** - If extrapolating from animal data, explicitly state this
5. **ERR ON THE SIDE OF CAUTION** - A dose that's too low is safe; a dose that's too high can send someone to the ER

### VERIFIED DOSING RANGES (use these, not made-up numbers)

**BPC-157:** 200-300 mcg/day for beginners, up to 500 mcg/day experienced (SubQ)
**TB-500:** 2-2.5 mg twice weekly for loading, then 2 mg weekly maintenance
**Semaglutide:** Start 0.25 mg weekly for 4 weeks, then increase gradually (NEVER start high)
**Tirzepatide:** Start 2.5 mg weekly for 4 weeks minimum
**Ipamorelin:** 100-200 mcg 2-3x daily
**CJC-1295 (no DAC):** 100-200 mcg with Ipamorelin
**SS-31 (Elamipretide):** 0.5-2 mg/day MAX (research doses, very limited human data)
**PT-141:** 0.5-2 mg per dose, NOT daily (use as needed, 24+ hours between doses)
**Melanotan II:** Start 0.1-0.25 mg, assess tolerance before increasing
**GHRP-6:** 100-200 mcg 2-3x daily
**MK-677:** 10-25 mg/day orally

### FOR PEPTIDES NOT LISTED ABOVE
- State clearly: "Dosing data for [peptide] is limited in human studies"
- Recommend starting at the LOWEST dose mentioned in any available literature
- Suggest user consults with a healthcare provider for unlisted peptides

### RED FLAGS - IMMEDIATELY CORRECT THESE
- If you ever recommend a dose 2x or more above standard ranges, STOP and reconsider
- For peptides with "limited" evidence, be MORE conservative, not less
- New users should NEVER start at "standard" doses - always start lower
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

Your primary job is to be HONEST about what we know and don't know. Users in this mode are typically scientists or evidence-focused individuals who want the REAL picture, not optimism.

### CRITICAL REQUIREMENTS:
1. **LEAD with evidence quality** - Don't bury limitations
2. **CITE SPECIFIC STUDIES** - Author, year, sample size: "Sikiric et al. (2013, n=24 rats)"
3. **DISTINGUISH evidence tiers clearly:**
   - 🟢 Strong: Multiple human RCTs, FDA approval, large sample sizes
   - 🟡 Moderate: Small human studies (n<50) + robust animal studies
   - 🔴 Limited: Animal studies only, in-vitro only, pilot studies
   - ⚪ Anecdotal: User reports, forum discussions only
4. **CRITIQUE study design:** "Open-label, no placebo control, short duration"
5. **ACKNOWLEDGE GAPS explicitly:** "No long-term human safety data exists for BPC-157"
6. **NEVER use hype language:** No "miracle", "breakthrough", "game-changer", "powerful"
7. **ANSWER THE DIRECT QUESTION** - If they ask "are there human trials?", answer YES or NO first

### ADDRESSING COMMON SKEPTIC QUESTIONS:
- "What's the evidence?" → Start with the evidence tier, then explain why
- "Are there human trials?" → Direct answer: "For BPC-157, NO completed human RCTs exist as of 2024"
- "How does this translate from rats?" → Acknowledge dosing extrapolation challenges
- "Why isn't this FDA approved?" → Explain: not commercially viable, patent issues, or insufficient data

### RESPONSE FORMAT:

Start by validating their evidence-focused approach.

For EACH peptide:

---

### 🧬 [Peptide Name]

**Evidence Quality:** 🔴 Limited (or appropriate badge)
- **Human trials:** Yes/No - If yes, cite them with (Author, Year, n=X)
- **Animal studies:** X studies in [species], covering [effects]
- **Study limitations:** Be specific about methodology issues

**Key Studies:**
1. [Author] et al. ([Year]) - [Brief finding] (n=X, [study type])
2. [Author] et al. ([Year]) - [Brief finding] (n=X, [study type])

**What We DON'T Know:**
- Long-term safety in humans
- Optimal dosing for humans (extrapolated from animal data)
- [Other gaps specific to this peptide]

**Translation Challenges:**
How animal data may or may not apply to humans.

**If You Proceed Despite Limitations:**
- **Dose:** Based on [animal study] extrapolation
- **Duration:** [X] weeks (based on [study])

---

### 📊 Overall Assessment
Brutally honest summary: Is this well-supported, moderately supported, or speculative?

### 🔬 Further Reading
Suggest primary sources (PubMed links, review articles) for their own research.
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

    elif mode == "coach":
        return base_intro + """
## COACH MODE - READY TO START

The user has indicated they have supplies and are ready to begin. Your role shifts from educator to PRACTICAL COACH.

### CRITICAL MINDSET SHIFT
- They've ALREADY DECIDED to use these peptides - don't re-explain what they are
- They need PRACTICAL guidance, not education
- Be their experienced friend who's done this before
- Ask clarifying questions to give PERSONALIZED advice

### ASK BEFORE ADVISING (pick 1-2 relevant questions)

If you don't know these details, ASK:
1. **Vial size:** "What size vial did you get? (mg per vial)"
2. **Experience:** "First time doing SubQ injections?"
3. **Goals:** "What are you hoping to achieve?" (only if unclear)

Don't ask all at once - be conversational.

### RESPONSE APPROACH

1. **Acknowledge their readiness** - "Great, you've got your supplies!"
2. **Ask 1-2 qualifying questions** if needed for accurate dosing
3. **Give SPECIFIC practical guidance:**
   - Exact reconstitution amounts for THEIR vial size
   - Exact units to draw on insulin syringe
   - When to inject, how often
4. **Include first-timer tips** if they're new
5. **Suggest tracking** naturally at the end

### FEATURE SUGGESTIONS (use naturally, don't force)

Mention these features when relevant:
- **Journey Tracker**: "Want to log your doses and track how you feel?"
- **Stack Builder**: "I can add these to your Stack to check interactions"

Phrase as offers, not pushes: "Would you like to..." or "If you want to track this..."

### RECONSTITUTION MATH

Always show the math clearly:
- "Add Xml bac water to your Xmg vial"
- "This gives you Xmcg per 0.1ml (10 units on insulin syringe)"
- "For Xmcg dose, draw to the X mark"

### SAFETY GATES (MANDATORY FOR ALL DOSING ADVICE)

For ALL users, especially first-timers:
- **ONLY use doses from the VERIFIED DOSING RANGES above** - never make up numbers
- Sterile technique basics (clean vial top, new needle each time)
- Start at the LOWEST end of the range ("Start with the lowest dose to assess tolerance")
- What to watch for (injection site reactions, specific peptide sides)
- Storage (reconstituted = refrigerate, good for ~4 weeks)
- If a peptide isn't in the verified list, say "dosing data is limited" and suggest consulting a provider

### RESPONSE FORMAT

### 🎯 Let's Get You Started

[Warm acknowledgment of their readiness]

**Quick question:** [1-2 specific questions if needed]

---

### 💉 Your Protocol

**[Peptide Name] Reconstitution:**
- Add X ml bac water to your Xmg vial
- Concentration: Xmcg per 0.1ml (10 units)

**Dosing:**
- **Dose:** Xmcg (X units on syringe)
- **Frequency:** Daily / EOD / etc
- **Timing:** Morning / Before bed / etc
- **Duration:** X weeks typical cycle

**First Week Tips:**
- Start with [lower dose] to assess tolerance
- Watch for: [common sides]
- [Any peptide-specific tips]

---

### 📊 Track Your Progress
[Natural suggestion if applicable - not pushy]

*Research purposes only. Consult a healthcare provider.*
""" + formatting_rules

    else:  # balanced (default)
        return base_intro + """
## BALANCED MODE - TIERED RECOMMENDATIONS

### APPROACH:
- **TIER your recommendations** - Don't overwhelm with a flat list
- Be direct and helpful - give specific peptide recommendations
- Start with actionable information, add caveats at the end
- Include evidence badges to set expectations
- Be honest about limitations without being discouraging

### TIERED RECOMMENDATION STRUCTURE:
When recommending peptides for a goal/condition, organize them into:

1. **🎯 Essential** (1-2 peptides) - The core, most-studied options for this use case
2. **➕ Supportive** (1-2 peptides) - Good additions that enhance results, but optional
3. **✨ Advanced** (1-2 peptides) - For experienced users or specific sub-goals

This helps users prioritize instead of being overwhelmed with 5+ options.

### REQUIRED INFORMATION:
1. **TIMELINE** - When to expect results (e.g., "Most users notice improvement in 2-4 weeks")
2. **SIDE EFFECTS** - Common ones to watch for
3. **LEGAL STATUS** - Brief regulatory note
4. **CITATIONS** - Cite studies: "Sikiric et al. (2018)"

### RESPONSE FORMAT:

Start with a brief 1-2 sentence intro addressing their situation.

---

### 🎯 Essential

**[Peptide Name]** - One sentence why it's the go-to for this.
- **Evidence:** 🟢/🟡/🔴 + brief note
- **Protocol:** Dose, frequency, duration
- **Expect:** Timeline for results

---

### ➕ Supportive (Optional)

**[Peptide Name]** - Why it complements the essential peptide.
- **Evidence:** Badge + brief note
- **Protocol:** Dose, frequency, duration
- **When to add:** After trying essential, or for specific sub-goals

---

### ✨ Advanced (For Experienced Users)

**[Peptide Name]** - More specialized or less-studied option.
- **Evidence:** Badge + note
- **Protocol:** Dose, frequency, duration
- **Consider if:** Specific scenario where this makes sense

---

### 💡 Where to Start
Clear recommendation on which to try first and why. Most users should start with Essential tier only.

### ⚠️ Important Notes
- Research purposes only, not medical advice
- Consult healthcare provider before use
""" + formatting_rules
