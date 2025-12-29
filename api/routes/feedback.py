"""
Peptide AI - Feedback Endpoints

Collect and manage user feedback for product iteration.
"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from typing import Optional, List, Dict
from datetime import datetime
from uuid import uuid4

from api.deps import get_database
from api.middleware.auth import get_current_user, get_optional_user

router = APIRouter()


# =============================================================================
# REQUEST/RESPONSE MODELS
# =============================================================================

class FeedbackCreate(BaseModel):
    """Create new feedback"""
    component_name: str = Field(..., description="Component being reviewed")
    component_path: str = Field(..., description="File path of component")
    conversation: List[dict] = Field(default=[], description="Chat conversation with feedback bot")
    summary: str = Field(..., description="AI-generated summary of feedback")
    product_prompt: str = Field(default="", description="Generated prompt for product iteration")
    insights: List[str] = Field(default=[], description="Key insights extracted")
    priority: str = Field(default="medium", pattern="^(low|medium|high)$")
    category: str = Field(default="other", pattern="^(bug|feature|ux|content|other)$")
    user_context: Optional[dict] = Field(default=None, description="Page, screen size, etc.")
    user_email: Optional[str] = Field(default=None, description="User's email for follow-up notifications")


class FeedbackUpdate(BaseModel):
    """Update feedback status"""
    status: str = Field(..., pattern="^(new|reviewed|implemented|dismissed)$")
    notes: Optional[str] = None


class FeedbackResponse(BaseModel):
    """Feedback item response"""
    id: str
    component_name: str
    component_path: str
    conversation: List[dict]
    summary: str
    product_prompt: str
    insights: List[str]
    priority: str
    category: str
    status: str
    user_context: Optional[dict]
    user_id: str
    user_email: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    notes: Optional[str] = None
    notified_at: Optional[datetime] = None


# =============================================================================
# ENDPOINTS
# =============================================================================

@router.post("/feedback", response_model=FeedbackResponse)
async def create_feedback(
    body: FeedbackCreate,
    user: Optional[dict] = Depends(get_optional_user)
):
    """
    Submit new feedback from a user.

    This captures structured feedback from the in-app feedback system
    and stores it for product iteration. Works for both authenticated
    and anonymous users.
    """
    db = get_database()
    user_id = user["user_id"] if user else "anonymous"

    feedback_id = str(uuid4())
    now = datetime.utcnow()

    feedback_doc = {
        "id": feedback_id,
        "component_name": body.component_name,
        "component_path": body.component_path,
        "conversation": body.conversation,
        "summary": body.summary,
        "product_prompt": body.product_prompt,
        "insights": body.insights,
        "priority": body.priority,
        "category": body.category,
        "status": "new",
        "user_context": body.user_context,
        "user_id": user_id,
        "user_email": body.user_email,
        "created_at": now,
        "updated_at": now,
        "notes": None,
        "notified_at": None,
    }

    await db.feedback.insert_one(feedback_doc)

    return FeedbackResponse(**feedback_doc)


@router.get("/feedback", response_model=List[FeedbackResponse])
async def list_feedback(
    status: Optional[str] = None,
    category: Optional[str] = None,
    priority: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
    user: dict = Depends(get_current_user)
):
    """
    List all feedback (admin only in production).

    Supports filtering by status, category, and priority.
    """
    db = get_database()

    # Build filter
    query = {}
    if status:
        query["status"] = status
    if category:
        query["category"] = category
    if priority:
        query["priority"] = priority

    cursor = db.feedback.find(query).sort("created_at", -1).skip(offset).limit(limit)

    feedback_items = []
    async for doc in cursor:
        feedback_items.append(FeedbackResponse(**doc))

    return feedback_items


@router.get("/feedback/{feedback_id}", response_model=FeedbackResponse)
async def get_feedback(
    feedback_id: str,
    user: dict = Depends(get_current_user)
):
    """Get a specific feedback item"""
    db = get_database()

    doc = await db.feedback.find_one({"id": feedback_id})
    if not doc:
        raise HTTPException(404, "Feedback not found")

    return FeedbackResponse(**doc)


@router.patch("/feedback/{feedback_id}", response_model=FeedbackResponse)
async def update_feedback(
    feedback_id: str,
    body: FeedbackUpdate,
    user: dict = Depends(get_current_user)
):
    """
    Update feedback status (mark as reviewed, implemented, etc.)
    """
    db = get_database()

    doc = await db.feedback.find_one({"id": feedback_id})
    if not doc:
        raise HTTPException(404, "Feedback not found")

    update = {
        "status": body.status,
        "updated_at": datetime.utcnow(),
    }
    if body.notes is not None:
        update["notes"] = body.notes

    await db.feedback.update_one(
        {"id": feedback_id},
        {"$set": update}
    )

    doc.update(update)
    return FeedbackResponse(**doc)


@router.delete("/feedback/{feedback_id}")
async def delete_feedback(
    feedback_id: str,
    user: dict = Depends(get_current_user)
):
    """Delete a feedback item"""
    db = get_database()

    result = await db.feedback.delete_one({"id": feedback_id})
    if result.deleted_count == 0:
        raise HTTPException(404, "Feedback not found")

    return {"status": "deleted"}


@router.get("/feedback/stats/summary")
async def feedback_stats(
    user: dict = Depends(get_current_user)
):
    """
    Get feedback statistics for dashboard.
    """
    db = get_database()

    # Count by status
    pipeline = [
        {"$group": {"_id": "$status", "count": {"$sum": 1}}}
    ]
    status_counts = {}
    async for doc in db.feedback.aggregate(pipeline):
        status_counts[doc["_id"]] = doc["count"]

    # Count by category
    pipeline = [
        {"$group": {"_id": "$category", "count": {"$sum": 1}}}
    ]
    category_counts = {}
    async for doc in db.feedback.aggregate(pipeline):
        category_counts[doc["_id"]] = doc["count"]

    # Count by priority
    pipeline = [
        {"$group": {"_id": "$priority", "count": {"$sum": 1}}}
    ]
    priority_counts = {}
    async for doc in db.feedback.aggregate(pipeline):
        priority_counts[doc["_id"]] = doc["count"]

    total = await db.feedback.count_documents({})

    return {
        "total": total,
        "by_status": status_counts,
        "by_category": category_counts,
        "by_priority": priority_counts,
    }


# =============================================================================
# FEEDBACK NOTIFICATION ENDPOINTS
# =============================================================================

class NotifyFeedbackRequest(BaseModel):
    """Request to notify feedback givers about updates"""
    feedback_ids: List[str] = Field(..., description="List of feedback IDs to notify")
    update_title: str = Field(..., description="Title of the update (e.g., 'Calculator Improvements')")
    update_message: str = Field(..., description="What was changed in response to feedback")
    test_instructions: Optional[str] = Field(None, description="Instructions for testing the changes")


class NotifyFeedbackResponse(BaseModel):
    """Response from notify endpoint"""
    notified_count: int
    skipped_count: int
    conversations_created: List[str]
    errors: List[str]


@router.post("/feedback/notify", response_model=NotifyFeedbackResponse)
async def notify_feedback_givers(
    body: NotifyFeedbackRequest,
    user: dict = Depends(get_current_user)
):
    """
    Send update notifications to users who gave feedback.

    For each feedback item:
    - Sends an email notification (if user_email is available)
    - Creates a new conversation with the update message
    - Marks the feedback as notified

    Requires admin access (TODO: add proper admin check).
    """
    from api.utils.email import send_email, format_feedback_update_email
    from api.utils.clerk import get_user_email

    db = get_database()
    now = datetime.utcnow()

    notified_count = 0
    skipped_count = 0
    conversations_created = []
    errors = []

    # Group feedback by user to avoid duplicate notifications
    user_feedback_map: Dict[str, List[dict]] = {}

    for feedback_id in body.feedback_ids:
        doc = await db.feedback.find_one({"id": feedback_id})
        if not doc:
            errors.append(f"Feedback {feedback_id} not found")
            continue

        user_id = doc.get("user_id")
        if user_id == "anonymous":
            skipped_count += 1
            continue

        if user_id not in user_feedback_map:
            user_feedback_map[user_id] = []
        user_feedback_map[user_id].append(doc)

    # Notify each user once (even if they gave multiple pieces of feedback)
    for feedback_user_id, feedback_docs in user_feedback_map.items():
        # Look up user email from Clerk (primary source)
        user_email = get_user_email(feedback_user_id)

        # Fallback to stored email if Clerk lookup fails
        if not user_email:
            for doc in feedback_docs:
                if doc.get("user_email"):
                    user_email = doc["user_email"]
                    break

        # Combine summaries if multiple feedback items
        summaries = [doc.get("summary", "No summary") for doc in feedback_docs]
        combined_summary = "\n\n".join(summaries) if len(summaries) > 1 else summaries[0]

        # Send email if we have an address
        if user_email:
            text_content, html_content = format_feedback_update_email(
                update_title=body.update_title,
                update_message=body.update_message,
                original_feedback_summary=combined_summary,
                test_instructions=body.test_instructions
            )

            email_sent = send_email(
                to_email=user_email,
                subject=f"Your Feedback Led to Changes: {body.update_title}",
                text_content=text_content,
                html_content=html_content
            )

            if not email_sent:
                errors.append(f"Failed to send email to {user_email}")

        # Create a conversation with the update message
        conversation_id = str(uuid4())

        # Build the assistant message content
        assistant_message = f"""Hey there! Great news - we've made some updates based on your feedback!

**{body.update_title}**

{body.update_message}"""

        if body.test_instructions:
            assistant_message += f"""

**How to test:**
{body.test_instructions}"""

        assistant_message += """

Thank you for helping us improve Peptide AI! Your feedback makes a real difference.

Feel free to reply here if you have any questions or more feedback!"""

        conversation_doc = {
            "conversation_id": conversation_id,
            "user_id": feedback_user_id,
            "title": f"Update: {body.update_title}",
            "messages": [
                {
                    "role": "assistant",
                    "content": assistant_message
                }
            ],
            "created_at": now,
            "updated_at": now,
            "is_feedback_update": True,  # Flag to identify these special conversations
        }

        await db.conversations.insert_one(conversation_doc)
        conversations_created.append(conversation_id)

        # Mark all feedback items for this user as notified
        for doc in feedback_docs:
            await db.feedback.update_one(
                {"id": doc["id"]},
                {"$set": {
                    "notified_at": now,
                    "status": "implemented",
                    "updated_at": now
                }}
            )

        notified_count += 1

    return NotifyFeedbackResponse(
        notified_count=notified_count,
        skipped_count=skipped_count,
        conversations_created=conversations_created,
        errors=errors
    )
