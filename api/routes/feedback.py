"""
Peptide AI - Feedback Endpoints

Collect and manage user feedback for product iteration.
"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from typing import Optional, List
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
    created_at: datetime
    updated_at: datetime
    notes: Optional[str] = None


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
        "created_at": now,
        "updated_at": now,
        "notes": None,
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
