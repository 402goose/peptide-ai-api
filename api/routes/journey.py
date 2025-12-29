"""
Peptide AI - Journey Management Endpoints

CRUD and logging endpoints for user peptide journeys.
"""

from fastapi import APIRouter, Depends, Request, HTTPException, Query
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime, date
from enum import Enum

from api.deps import get_database
from api.middleware.auth import get_current_user
from api.journey_service import JourneyService
from api.models.documents import (
    JourneyStatus, GoalCategory, AdministrationRoute,
    PeptideJourney, DoseLog, SymptomLog, JourneyMilestone
)

router = APIRouter()


# =============================================================================
# REQUEST MODELS
# =============================================================================

class GoalInput(BaseModel):
    """Goal input for journey creation"""
    category: GoalCategory
    description: str
    target_metric: Optional[str] = None
    baseline_value: Optional[str] = None
    target_value: Optional[str] = None


class CreateJourneyRequest(BaseModel):
    """Request to create a new journey"""
    title: Optional[str] = None
    primary_peptide: str = Field(..., min_length=1)
    secondary_peptides: List[str] = []
    goals: List[GoalInput]
    planned_protocol: Optional[str] = None
    planned_duration_weeks: Optional[int] = Field(None, ge=1, le=52)
    administration_route: AdministrationRoute = AdministrationRoute.SUBCUTANEOUS


class StartJourneyRequest(BaseModel):
    """Request to start a journey"""
    start_date: Optional[date] = None  # Defaults to today


class CompleteJourneyRequest(BaseModel):
    """Request to complete a journey with outcomes"""
    overall_efficacy_rating: int = Field(..., ge=1, le=10)
    would_recommend: bool
    would_use_again: bool
    outcome_summary: Optional[str] = None
    what_worked: Optional[str] = None
    what_didnt_work: Optional[str] = None
    advice_for_others: Optional[str] = None


class DiscontinueJourneyRequest(BaseModel):
    """Request to discontinue a journey"""
    reason: str
    overall_efficacy_rating: Optional[int] = Field(None, ge=1, le=10)


class LogDoseRequest(BaseModel):
    """Request to log a dose"""
    peptide: str
    dose_amount: float = Field(..., gt=0)
    dose_unit: str  # mcg, mg, IU
    route: AdministrationRoute = AdministrationRoute.SUBCUTANEOUS
    injection_site: Optional[str] = None
    time_of_day: Optional[str] = None  # morning, evening, pre_workout
    fasted: Optional[bool] = None
    notes: Optional[str] = None


class LogSymptomsRequest(BaseModel):
    """Request to log daily symptoms"""
    log_date: date
    energy_level: Optional[int] = Field(None, ge=1, le=10)
    sleep_quality: Optional[int] = Field(None, ge=1, le=10)
    mood: Optional[int] = Field(None, ge=1, le=10)
    pain_level: Optional[int] = Field(None, ge=1, le=10)
    recovery_feeling: Optional[int] = Field(None, ge=1, le=10)
    goal_progress: Optional[dict] = None  # goal_id -> progress (1-10)
    side_effects: List[str] = []
    side_effect_severity: str = "none"  # none, mild, moderate, severe
    weight_kg: Optional[float] = None
    body_fat_percent: Optional[float] = None
    notes: Optional[str] = None


class AddMilestoneRequest(BaseModel):
    """Request to add a milestone"""
    milestone_type: str  # improvement, setback, side_effect, adjustment
    title: str
    description: str
    related_goal_id: Optional[str] = None
    is_shareable: bool = False
    media_urls: List[str] = []


class AddNoteRequest(BaseModel):
    """Request to add a note"""
    content: str
    note_type: str = "general"  # general, research, question, observation


# =============================================================================
# JOURNEY CRUD ENDPOINTS
# =============================================================================

@router.post("/journeys", response_model=dict)
async def create_journey(
    request: Request,
    body: CreateJourneyRequest,
    user: dict = Depends(get_current_user)
):
    """Create a new peptide journey"""
    db = get_database()
    service = JourneyService(db)

    journey = await service.create_journey(
        user_id=user["user_id"],
        primary_peptide=body.primary_peptide,
        goals=[g.model_dump() for g in body.goals],
        planned_protocol=body.planned_protocol,
        planned_duration_weeks=body.planned_duration_weeks,
        secondary_peptides=body.secondary_peptides,
        title=body.title
    )

    return {"journey_id": journey.journey_id, "status": journey.status.value}


@router.get("/journeys", response_model=List[dict])
async def list_journeys(
    request: Request,
    status: Optional[JourneyStatus] = None,
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    user: dict = Depends(get_current_user)
):
    """List user's journeys"""
    db = get_database()
    service = JourneyService(db)

    journeys = await service.get_user_journeys(
        user_id=user["user_id"],
        status=status,
        limit=limit
    )

    return [
        {
            "journey_id": j.journey_id,
            "title": j.title,
            "primary_peptide": j.primary_peptide,
            "status": j.status.value,
            "start_date": j.start_date.isoformat() if j.start_date else None,
            "dose_count": j.dose_count,
            "overall_efficacy_rating": j.overall_efficacy_rating,
            "created_at": j.created_at.isoformat()
        }
        for j in journeys
    ][offset:offset + limit]


@router.get("/journeys/{journey_id}")
async def get_journey(
    journey_id: str,
    user: dict = Depends(get_current_user)
):
    """Get a specific journey with full details"""
    db = get_database()
    service = JourneyService(db)

    journey = await service.get_journey(journey_id)

    if not journey:
        raise HTTPException(404, "Journey not found")

    if journey.user_id != user["user_id"] and not user.get("is_admin"):
        raise HTTPException(403, "Not authorized to view this journey")

    return journey.model_dump()


@router.post("/journeys/{journey_id}/start")
async def start_journey(
    journey_id: str,
    body: StartJourneyRequest,
    user: dict = Depends(get_current_user)
):
    """Start a journey (transition from PLANNING to ACTIVE)"""
    db = get_database()
    service = JourneyService(db)

    journey = await service.get_journey(journey_id)
    if not journey:
        raise HTTPException(404, "Journey not found")
    if journey.user_id != user["user_id"]:
        raise HTTPException(403, "Not authorized")

    journey = await service.start_journey(journey_id, body.start_date)
    return {"journey_id": journey.journey_id, "status": journey.status.value}


@router.post("/journeys/{journey_id}/complete")
async def complete_journey(
    journey_id: str,
    body: CompleteJourneyRequest,
    user: dict = Depends(get_current_user)
):
    """Complete a journey with outcomes"""
    db = get_database()
    service = JourneyService(db)

    journey = await service.get_journey(journey_id)
    if not journey:
        raise HTTPException(404, "Journey not found")
    if journey.user_id != user["user_id"]:
        raise HTTPException(403, "Not authorized")

    journey = await service.complete_journey(
        journey_id=journey_id,
        overall_efficacy_rating=body.overall_efficacy_rating,
        would_recommend=body.would_recommend,
        would_use_again=body.would_use_again,
        outcome_summary=body.outcome_summary,
        what_worked=body.what_worked,
        what_didnt_work=body.what_didnt_work,
        advice_for_others=body.advice_for_others
    )

    return {"journey_id": journey.journey_id, "status": journey.status.value}


@router.post("/journeys/{journey_id}/pause")
async def pause_journey(
    journey_id: str,
    reason: Optional[str] = None,
    user: dict = Depends(get_current_user)
):
    """Pause an active journey"""
    db = get_database()
    service = JourneyService(db)

    journey = await service.get_journey(journey_id)
    if not journey:
        raise HTTPException(404, "Journey not found")
    if journey.user_id != user["user_id"]:
        raise HTTPException(403, "Not authorized")

    journey = await service.pause_journey(journey_id, reason)
    return {"journey_id": journey.journey_id, "status": journey.status.value}


@router.post("/journeys/{journey_id}/resume")
async def resume_journey(
    journey_id: str,
    user: dict = Depends(get_current_user)
):
    """Resume a paused journey"""
    db = get_database()
    service = JourneyService(db)

    journey = await service.get_journey(journey_id)
    if not journey:
        raise HTTPException(404, "Journey not found")
    if journey.user_id != user["user_id"]:
        raise HTTPException(403, "Not authorized")

    journey = await service.resume_journey(journey_id)
    return {"journey_id": journey.journey_id, "status": journey.status.value}


@router.post("/journeys/{journey_id}/discontinue")
async def discontinue_journey(
    journey_id: str,
    body: DiscontinueJourneyRequest,
    user: dict = Depends(get_current_user)
):
    """Discontinue a journey early"""
    db = get_database()
    service = JourneyService(db)

    journey = await service.get_journey(journey_id)
    if not journey:
        raise HTTPException(404, "Journey not found")
    if journey.user_id != user["user_id"]:
        raise HTTPException(403, "Not authorized")

    journey = await service.discontinue_journey(
        journey_id=journey_id,
        reason=body.reason,
        overall_efficacy_rating=body.overall_efficacy_rating
    )

    return {"journey_id": journey.journey_id, "status": journey.status.value}


# =============================================================================
# LOGGING ENDPOINTS
# =============================================================================

@router.post("/journeys/{journey_id}/doses")
async def log_dose(
    journey_id: str,
    body: LogDoseRequest,
    user: dict = Depends(get_current_user)
):
    """Log a dose for a journey"""
    db = get_database()
    service = JourneyService(db)

    journey = await service.get_journey(journey_id)
    if not journey:
        raise HTTPException(404, "Journey not found")
    if journey.user_id != user["user_id"]:
        raise HTTPException(403, "Not authorized")

    log = await service.log_dose(
        journey_id=journey_id,
        peptide=body.peptide,
        dose_amount=body.dose_amount,
        dose_unit=body.dose_unit,
        route=body.route.value,
        injection_site=body.injection_site,
        time_of_day=body.time_of_day,
        fasted=body.fasted,
        notes=body.notes
    )

    return {"log_id": log.log_id, "timestamp": log.timestamp.isoformat()}


@router.get("/journeys/{journey_id}/doses")
async def get_doses(
    journey_id: str,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    user: dict = Depends(get_current_user)
):
    """Get dose logs for a journey"""
    db = get_database()
    service = JourneyService(db)

    journey = await service.get_journey(journey_id)
    if not journey:
        raise HTTPException(404, "Journey not found")
    if journey.user_id != user["user_id"] and not user.get("is_admin"):
        raise HTTPException(403, "Not authorized")

    logs = await service.get_dose_logs(journey_id, start_date, end_date)
    return [log.model_dump() for log in logs]


@router.post("/journeys/{journey_id}/symptoms")
async def log_symptoms(
    journey_id: str,
    body: LogSymptomsRequest,
    user: dict = Depends(get_current_user)
):
    """Log daily symptoms for a journey"""
    db = get_database()
    service = JourneyService(db)

    journey = await service.get_journey(journey_id)
    if not journey:
        raise HTTPException(404, "Journey not found")
    if journey.user_id != user["user_id"]:
        raise HTTPException(403, "Not authorized")

    log = await service.log_symptoms(
        journey_id=journey_id,
        log_date=body.log_date,
        energy_level=body.energy_level,
        sleep_quality=body.sleep_quality,
        mood=body.mood,
        pain_level=body.pain_level,
        recovery_feeling=body.recovery_feeling,
        goal_progress=body.goal_progress,
        side_effects=body.side_effects,
        side_effect_severity=body.side_effect_severity,
        weight_kg=body.weight_kg,
        body_fat_percent=body.body_fat_percent,
        notes=body.notes
    )

    return {"log_id": log.log_id, "log_date": log.log_date.isoformat()}


@router.get("/journeys/{journey_id}/symptoms")
async def get_symptoms(
    journey_id: str,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    user: dict = Depends(get_current_user)
):
    """Get symptom logs for a journey"""
    db = get_database()
    service = JourneyService(db)

    journey = await service.get_journey(journey_id)
    if not journey:
        raise HTTPException(404, "Journey not found")
    if journey.user_id != user["user_id"] and not user.get("is_admin"):
        raise HTTPException(403, "Not authorized")

    logs = await service.get_symptom_logs(journey_id, start_date, end_date)
    return [log.model_dump() for log in logs]


@router.post("/journeys/{journey_id}/milestones")
async def add_milestone(
    journey_id: str,
    body: AddMilestoneRequest,
    user: dict = Depends(get_current_user)
):
    """Add a milestone to a journey"""
    db = get_database()
    service = JourneyService(db)

    journey = await service.get_journey(journey_id)
    if not journey:
        raise HTTPException(404, "Journey not found")
    if journey.user_id != user["user_id"]:
        raise HTTPException(403, "Not authorized")

    milestone = await service.add_milestone(
        journey_id=journey_id,
        milestone_type=body.milestone_type,
        title=body.title,
        description=body.description,
        related_goal_id=body.related_goal_id,
        is_shareable=body.is_shareable,
        media_urls=body.media_urls
    )

    return {"milestone_id": milestone.milestone_id}


@router.post("/journeys/{journey_id}/notes")
async def add_note(
    journey_id: str,
    body: AddNoteRequest,
    user: dict = Depends(get_current_user)
):
    """Add a note to a journey"""
    db = get_database()
    service = JourneyService(db)

    journey = await service.get_journey(journey_id)
    if not journey:
        raise HTTPException(404, "Journey not found")
    if journey.user_id != user["user_id"]:
        raise HTTPException(403, "Not authorized")

    note = await service.add_note(
        journey_id=journey_id,
        content=body.content,
        note_type=body.note_type
    )

    return {"note_id": note.note_id}


# =============================================================================
# CONTEXT & EXPORT ENDPOINTS
# =============================================================================

@router.get("/journeys/context")
async def get_user_context(
    user: dict = Depends(get_current_user)
):
    """
    Get user's journey context for AI personalization

    Returns a summary of user's journey history suitable for
    inclusion in AI prompts.
    """
    db = get_database()
    service = JourneyService(db)

    context = await service.build_user_context(user["user_id"])
    return context.model_dump()


@router.get("/journeys/{journey_id}/export")
async def export_journey(
    journey_id: str,
    user: dict = Depends(get_current_user)
):
    """
    Export a journey for content creation

    Returns a comprehensive export suitable for creators
    to use in their content.
    """
    db = get_database()
    service = JourneyService(db)

    journey = await service.get_journey(journey_id)
    if not journey:
        raise HTTPException(404, "Journey not found")
    if journey.user_id != user["user_id"] and not user.get("is_admin"):
        raise HTTPException(403, "Not authorized")

    export_data = await service.export_journey_for_content(journey_id)
    return export_data


@router.get("/peptides/{peptide}/stats")
async def get_peptide_stats(
    peptide: str,
    user: dict = Depends(get_current_user)
):
    """
    Get aggregated statistics for a peptide

    Shows community data across all journeys.
    """
    db = get_database()

    stats = await db.peptide_stats.find_one({"peptide": peptide})

    if not stats:
        return {
            "peptide": peptide,
            "total_journeys": 0,
            "message": "No journey data available for this peptide yet"
        }

    # Remove internal fields
    stats.pop("_id", None)
    return stats
