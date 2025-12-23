"""
Peptide AI - Analytics & Tracking Service

Tracks user events and funnel metrics for product optimization.
Integrates with A/B testing to measure experiment outcomes.

Key Metrics (SaaS funnel):
1. Acquisition: Landing page visits, sign-ups
2. Activation: First meaningful action (first chat, first source view)
3. Engagement: Sessions, chats per session, sources viewed
4. Retention: Return visits, time between visits
5. Satisfaction: Feedback scores, NPS
"""

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
from uuid import uuid4
import hashlib

from api.deps import get_database
from api.middleware.auth import get_current_user, get_optional_user

router = APIRouter()


# =============================================================================
# EVENT TYPES
# =============================================================================

class EventType:
    """Standard event types for funnel tracking"""
    # Acquisition
    PAGE_VIEW = "page_view"
    SIGN_UP_START = "sign_up_start"
    SIGN_UP_COMPLETE = "sign_up_complete"

    # Activation
    FIRST_CHAT = "first_chat"
    FIRST_SOURCE_VIEW = "first_source_view"
    FIRST_FOLLOW_UP = "first_follow_up"

    # Engagement
    CHAT_SENT = "chat_sent"
    CHAT_RECEIVED = "chat_received"
    SOURCE_CLICKED = "source_clicked"
    FOLLOW_UP_CLICKED = "follow_up_clicked"
    SESSION_START = "session_start"
    SESSION_END = "session_end"

    # Retention
    RETURN_VISIT = "return_visit"

    # Satisfaction
    FEEDBACK_SUBMITTED = "feedback_submitted"
    NPS_SUBMITTED = "nps_submitted"

    # Experiment
    EXPERIMENT_ASSIGNED = "experiment_assigned"
    EXPERIMENT_CONVERSION = "experiment_conversion"

    # Affiliate / Outbound
    AFFILIATE_CLICK = "affiliate_click"  # User clicks to vendor
    AFFILIATE_RETURN = "affiliate_return"  # User comes back after purchase
    JOURNEY_STARTED = "journey_started"  # User starts tracking their peptide journey
    JOURNEY_UPDATED = "journey_updated"  # User logs outcome/experience


# =============================================================================
# REQUEST/RESPONSE MODELS
# =============================================================================

class TrackEvent(BaseModel):
    """Track a user event"""
    event_type: str = Field(..., description="Type of event")
    properties: Dict[str, Any] = Field(default={}, description="Event properties")
    session_id: Optional[str] = Field(None, description="Session identifier")
    page_path: Optional[str] = Field(None, description="Current page path")
    referrer: Optional[str] = Field(None, description="Referrer URL")
    user_agent: Optional[str] = Field(None, description="Browser user agent")
    experiment_id: Optional[str] = Field(None, description="Active experiment ID")
    variant: Optional[str] = Field(None, description="Experiment variant")


class FunnelStep(BaseModel):
    """A step in the funnel"""
    name: str
    count: int
    conversion_rate: float


class FunnelAnalysis(BaseModel):
    """Funnel analysis response"""
    steps: List[FunnelStep]
    total_users: int
    overall_conversion: float
    time_range: str


class UserJourney(BaseModel):
    """User journey summary"""
    user_id: str
    first_seen: datetime
    last_seen: datetime
    total_sessions: int
    total_chats: int
    sources_viewed: int
    feedback_submitted: int
    experiments: List[str]
    activation_status: str  # "not_activated", "activated", "engaged"


# =============================================================================
# ENDPOINTS
# =============================================================================

@router.post("/analytics/track")
async def track_event(
    body: TrackEvent,
    request: Request,
    user: Optional[dict] = Depends(get_optional_user)
):
    """
    Track a user event for analytics.

    Can be called authenticated or anonymously (for pre-signup tracking).
    Uses a consistent anonymous_id for unauthenticated users.
    """
    db = get_database()

    # Get or create user identifier
    user_id = user["user_id"] if user else None

    # Generate anonymous ID from IP + user agent for consistency
    client_ip = request.client.host if request.client else "unknown"
    ua = body.user_agent or request.headers.get("user-agent", "")
    anonymous_id = hashlib.sha256(f"{client_ip}:{ua}".encode()).hexdigest()[:16]

    event_doc = {
        "id": str(uuid4()),
        "event_type": body.event_type,
        "properties": body.properties,
        "user_id": user_id,
        "anonymous_id": anonymous_id,
        "session_id": body.session_id,
        "page_path": body.page_path,
        "referrer": body.referrer,
        "user_agent": ua,
        "experiment_id": body.experiment_id,
        "variant": body.variant,
        "timestamp": datetime.utcnow(),
        "ip_hash": hashlib.sha256(client_ip.encode()).hexdigest()[:8],  # Privacy-preserving
    }

    await db.analytics_events.insert_one(event_doc)

    # Update user metrics if authenticated
    if user_id:
        await _update_user_metrics(db, user_id, body.event_type, body.properties)

    return {"status": "tracked", "event_id": event_doc["id"]}


@router.get("/analytics/funnel")
async def get_funnel_analysis(
    start_date: Optional[str] = None,  # ISO format
    end_date: Optional[str] = None,
    user: dict = Depends(get_current_user)
):
    """
    Analyze the user funnel.

    Funnel steps:
    1. Page View → 2. Sign Up → 3. First Chat → 4. Source View → 5. Return Visit
    """
    db = get_database()

    # Parse date range
    if start_date:
        start = datetime.fromisoformat(start_date)
    else:
        start = datetime.utcnow() - timedelta(days=30)

    if end_date:
        end = datetime.fromisoformat(end_date)
    else:
        end = datetime.utcnow()

    date_filter = {"timestamp": {"$gte": start, "$lte": end}}

    # Count each funnel step
    steps = []

    # Step 1: Page views (unique anonymous_ids)
    page_views = await db.analytics_events.distinct(
        "anonymous_id",
        {"event_type": EventType.PAGE_VIEW, **date_filter}
    )

    # Step 2: Sign ups
    sign_ups = await db.analytics_events.distinct(
        "user_id",
        {"event_type": EventType.SIGN_UP_COMPLETE, **date_filter}
    )

    # Step 3: First chats
    first_chats = await db.analytics_events.distinct(
        "user_id",
        {"event_type": EventType.FIRST_CHAT, **date_filter}
    )

    # Step 4: Source views
    source_views = await db.analytics_events.distinct(
        "user_id",
        {"event_type": EventType.SOURCE_CLICKED, **date_filter}
    )

    # Step 5: Return visits
    return_visits = await db.analytics_events.distinct(
        "user_id",
        {"event_type": EventType.RETURN_VISIT, **date_filter}
    )

    total = len(page_views) if page_views else 1

    steps = [
        FunnelStep(name="Page View", count=len(page_views), conversion_rate=1.0),
        FunnelStep(name="Sign Up", count=len(sign_ups), conversion_rate=len(sign_ups)/total),
        FunnelStep(name="First Chat", count=len(first_chats), conversion_rate=len(first_chats)/total),
        FunnelStep(name="Source View", count=len(source_views), conversion_rate=len(source_views)/total),
        FunnelStep(name="Return Visit", count=len(return_visits), conversion_rate=len(return_visits)/total),
    ]

    return FunnelAnalysis(
        steps=steps,
        total_users=total,
        overall_conversion=len(return_visits)/total if total > 0 else 0,
        time_range=f"{start.date()} to {end.date()}"
    )


@router.get("/analytics/metrics")
async def get_key_metrics(
    days: int = 7,
    user: dict = Depends(get_current_user)
):
    """
    Get key metrics dashboard.
    """
    db = get_database()

    start = datetime.utcnow() - timedelta(days=days)
    date_filter = {"timestamp": {"$gte": start}}

    # Active users
    active_users = await db.analytics_events.distinct(
        "user_id",
        {"user_id": {"$ne": None}, **date_filter}
    )

    # Total chats
    chat_count = await db.analytics_events.count_documents(
        {"event_type": EventType.CHAT_SENT, **date_filter}
    )

    # Average chats per user
    avg_chats = chat_count / len(active_users) if active_users else 0

    # Sessions
    session_count = await db.analytics_events.count_documents(
        {"event_type": EventType.SESSION_START, **date_filter}
    )

    # Feedback
    feedback_count = await db.analytics_events.count_documents(
        {"event_type": EventType.FEEDBACK_SUBMITTED, **date_filter}
    )

    # New sign ups
    new_signups = await db.analytics_events.count_documents(
        {"event_type": EventType.SIGN_UP_COMPLETE, **date_filter}
    )

    # Return rate (users with >1 session)
    pipeline = [
        {"$match": {"event_type": EventType.SESSION_START, **date_filter}},
        {"$group": {"_id": "$user_id", "sessions": {"$sum": 1}}},
        {"$match": {"sessions": {"$gt": 1}}}
    ]
    returning_users = 0
    async for doc in db.analytics_events.aggregate(pipeline):
        returning_users += 1

    return_rate = returning_users / len(active_users) if active_users else 0

    return {
        "time_range_days": days,
        "active_users": len(active_users),
        "new_signups": new_signups,
        "total_sessions": session_count,
        "total_chats": chat_count,
        "avg_chats_per_user": round(avg_chats, 2),
        "feedback_submissions": feedback_count,
        "return_rate": round(return_rate, 3),
    }


@router.get("/analytics/user/{user_id}/journey")
async def get_user_journey(
    user_id: str,
    user: dict = Depends(get_current_user)
):
    """
    Get a specific user's journey summary.
    """
    db = get_database()

    # Get all events for user
    events = []
    async for event in db.analytics_events.find({"user_id": user_id}).sort("timestamp", 1):
        events.append(event)

    if not events:
        raise HTTPException(404, "User not found")

    first_event = events[0]
    last_event = events[-1]

    # Count specific events
    chats = sum(1 for e in events if e["event_type"] == EventType.CHAT_SENT)
    sources = sum(1 for e in events if e["event_type"] == EventType.SOURCE_CLICKED)
    feedback = sum(1 for e in events if e["event_type"] == EventType.FEEDBACK_SUBMITTED)
    sessions = sum(1 for e in events if e["event_type"] == EventType.SESSION_START)

    # Get experiments
    experiments = list(set(e.get("experiment_id") for e in events if e.get("experiment_id")))

    # Determine activation status
    has_chatted = chats > 0
    has_viewed_sources = sources > 0
    has_returned = sessions > 1

    if has_chatted and has_viewed_sources and has_returned:
        activation = "engaged"
    elif has_chatted:
        activation = "activated"
    else:
        activation = "not_activated"

    return UserJourney(
        user_id=user_id,
        first_seen=first_event["timestamp"],
        last_seen=last_event["timestamp"],
        total_sessions=sessions,
        total_chats=chats,
        sources_viewed=sources,
        feedback_submitted=feedback,
        experiments=experiments,
        activation_status=activation
    )


@router.get("/analytics/compare-to-personas")
async def compare_real_vs_personas(
    user: dict = Depends(get_current_user)
):
    """
    Compare real user metrics to persona test results.

    Helps validate if persona testing reflects reality.
    """
    db = get_database()

    # Get real user metrics (last 30 days)
    start = datetime.utcnow() - timedelta(days=30)

    # Average chats per session for real users
    pipeline = [
        {"$match": {"event_type": EventType.CHAT_SENT, "timestamp": {"$gte": start}}},
        {"$group": {"_id": "$session_id", "chats": {"$sum": 1}}},
        {"$group": {"_id": None, "avg_chats": {"$avg": "$chats"}}}
    ]
    real_avg_chats = 0
    async for doc in db.analytics_events.aggregate(pipeline):
        real_avg_chats = doc.get("avg_chats", 0)

    # Return rate for real users
    active_users = await db.analytics_events.distinct(
        "user_id",
        {"user_id": {"$ne": None}, "timestamp": {"$gte": start}}
    )

    return_users = await db.analytics_events.distinct(
        "user_id",
        {"event_type": EventType.RETURN_VISIT, "timestamp": {"$gte": start}}
    )

    real_return_rate = len(return_users) / len(active_users) if active_users else 0

    # Load latest persona results
    import os
    import json

    project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    results_path = os.path.join(project_root, "testing", "browser_test_results.json")

    persona_data = {}
    if os.path.exists(results_path):
        with open(results_path) as f:
            results = json.load(f)
            summary = results.get("summary", {})
            persona_data = {
                "avg_chats_per_session": sum(
                    p.get("chats", 0) for p in summary.get("by_persona", {}).values()
                ) / len(summary.get("by_persona", {})) if summary.get("by_persona") else 0,
                "return_rate": summary.get("would_return_rate", 0),
                "satisfaction": summary.get("overall_satisfaction", 0),
            }

    return {
        "real_users": {
            "avg_chats_per_session": round(real_avg_chats, 2),
            "return_rate": round(real_return_rate, 3),
            "active_users_30d": len(active_users),
        },
        "persona_tests": persona_data,
        "alignment": {
            "chats_diff": abs(real_avg_chats - persona_data.get("avg_chats_per_session", 0)),
            "return_diff": abs(real_return_rate - persona_data.get("return_rate", 0)),
        }
    }


# =============================================================================
# PERSONA TESTING RESULTS
# =============================================================================

@router.get("/analytics/persona-tests")
async def get_persona_test_results(
    user: dict = Depends(get_current_user)
):
    """
    Get the full persona test results from the latest browser test run.

    Returns all personas, their sessions, evaluations, and feedback.
    Checks MongoDB first, then falls back to local file for dev.
    """
    db = get_database()

    # Try to get from database first (production)
    latest = await db.persona_test_runs.find_one(
        sort=[("timestamp", -1)]
    )

    if latest:
        # Remove MongoDB _id for JSON serialization
        latest.pop("_id", None)
        return {
            "status": "ok",
            "results": latest
        }

    # Fall back to local file (development)
    import os
    import json

    project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    results_path = os.path.join(project_root, "testing", "browser_test_results.json")

    if os.path.exists(results_path):
        with open(results_path) as f:
            results = json.load(f)
        return {
            "status": "ok",
            "results": results
        }

    return {
        "status": "no_results",
        "message": "No persona test results found. Run browser_agent.py to generate.",
        "results": None
    }


@router.post("/analytics/persona-tests")
async def store_persona_test_results(
    request: Request,
    user: dict = Depends(get_current_user)
):
    """
    Store persona test results in the database.

    Called by browser_agent.py after running tests.
    """
    db = get_database()

    # Parse JSON body
    results = await request.json()

    # Add timestamp if not present
    if "timestamp" not in results:
        results["timestamp"] = datetime.utcnow().isoformat()

    # Store in database
    await db.persona_test_runs.insert_one(results)

    return {"status": "stored", "timestamp": results["timestamp"]}


@router.get("/analytics/persona-tests/history")
async def get_persona_test_history(
    limit: int = 10,
    user: dict = Depends(get_current_user)
):
    """
    Get historical persona test runs from the database.
    """
    db = get_database()

    history = []

    # Get from database
    cursor = db.persona_test_runs.find(
        {},
        {
            "timestamp": 1,
            "target_url": 1,
            "personas_tested": 1,
            "summary.overall_satisfaction": 1,
            "summary.would_return_rate": 1,
        }
    ).sort("timestamp", -1).limit(limit)

    async for doc in cursor:
        history.append({
            "timestamp": doc.get("timestamp"),
            "target_url": doc.get("target_url"),
            "personas_tested": doc.get("personas_tested"),
            "overall_satisfaction": doc.get("summary", {}).get("overall_satisfaction"),
            "would_return_rate": doc.get("summary", {}).get("would_return_rate"),
            "is_current": len(history) == 0  # First one is current
        })

    # If no DB results, try local file (dev fallback)
    if not history:
        import os
        import json

        project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        results_path = os.path.join(project_root, "testing", "browser_test_results.json")

        if os.path.exists(results_path):
            with open(results_path) as f:
                data = json.load(f)
                history.append({
                    "timestamp": data.get("timestamp"),
                    "target_url": data.get("target_url"),
                    "personas_tested": data.get("personas_tested"),
                    "overall_satisfaction": data.get("summary", {}).get("overall_satisfaction"),
                    "would_return_rate": data.get("summary", {}).get("would_return_rate"),
                    "is_current": True
                })

    return {"history": history}


# =============================================================================
# AFFILIATE TRACKING
# =============================================================================

class AffiliateClick(BaseModel):
    """Track outbound affiliate click"""
    vendor_name: str = Field(..., description="Vendor/site name")
    vendor_url: str = Field(..., description="Outbound URL")
    peptide: Optional[str] = Field(None, description="Peptide being researched")
    source_context: Optional[str] = Field(None, description="Where the click came from (chat, source)")


class AffiliateReturn(BaseModel):
    """Track user returning after purchase"""
    vendor_name: str = Field(..., description="Where they purchased")
    peptide: str = Field(..., description="What they bought")
    purchased: bool = Field(True, description="Did they purchase?")
    experience_notes: Optional[str] = Field(None, description="Initial notes")


@router.post("/analytics/affiliate/click")
async def track_affiliate_click(
    body: AffiliateClick,
    request: Request,
    user: Optional[dict] = Depends(get_optional_user)
):
    """
    Track when a user clicks out to a vendor/affiliate link.

    This starts the attribution chain:
    Research → Click to vendor → Return → Share experience
    """
    db = get_database()

    user_id = user["user_id"] if user else None
    client_ip = request.client.host if request.client else "unknown"
    ua = request.headers.get("user-agent", "")
    anonymous_id = hashlib.sha256(f"{client_ip}:{ua}".encode()).hexdigest()[:16]

    click_id = str(uuid4())[:12]

    event_doc = {
        "id": str(uuid4()),
        "event_type": EventType.AFFILIATE_CLICK,
        "properties": {
            "click_id": click_id,
            "vendor_name": body.vendor_name,
            "vendor_url": body.vendor_url,
            "peptide": body.peptide,
            "source_context": body.source_context,
        },
        "user_id": user_id,
        "anonymous_id": anonymous_id,
        "timestamp": datetime.utcnow(),
    }

    await db.analytics_events.insert_one(event_doc)

    # Store in affiliate_clicks for easy lookup
    await db.affiliate_clicks.insert_one({
        "click_id": click_id,
        "user_id": user_id,
        "anonymous_id": anonymous_id,
        "vendor_name": body.vendor_name,
        "vendor_url": body.vendor_url,
        "peptide": body.peptide,
        "source_context": body.source_context,
        "clicked_at": datetime.utcnow(),
        "returned": False,
        "purchased": None,
        "journey_id": None,
    })

    return {
        "status": "tracked",
        "click_id": click_id,
        "message": "Come back and share your experience!"
    }


@router.post("/analytics/affiliate/return")
async def track_affiliate_return(
    body: AffiliateReturn,
    user: dict = Depends(get_current_user)
):
    """
    Track when a user returns after visiting a vendor.

    Completes the attribution chain and optionally starts a journey.
    """
    db = get_database()

    user_id = user["user_id"]

    # Find their most recent click for this vendor/peptide
    click = await db.affiliate_clicks.find_one(
        {
            "user_id": user_id,
            "vendor_name": body.vendor_name,
            "peptide": body.peptide,
        },
        sort=[("clicked_at", -1)]
    )

    # Track the return event
    event_doc = {
        "id": str(uuid4()),
        "event_type": EventType.AFFILIATE_RETURN,
        "properties": {
            "vendor_name": body.vendor_name,
            "peptide": body.peptide,
            "purchased": body.purchased,
            "click_id": click["click_id"] if click else None,
        },
        "user_id": user_id,
        "timestamp": datetime.utcnow(),
    }

    await db.analytics_events.insert_one(event_doc)

    # Update the click record
    if click:
        await db.affiliate_clicks.update_one(
            {"click_id": click["click_id"]},
            {"$set": {
                "returned": True,
                "returned_at": datetime.utcnow(),
                "purchased": body.purchased,
            }}
        )

    return {
        "status": "tracked",
        "click_id": click["click_id"] if click else None,
        "message": "Thanks for sharing! Start tracking your journey?"
    }


@router.get("/analytics/affiliate/stats")
async def get_affiliate_stats(
    days: int = 30,
    user: dict = Depends(get_current_user)
):
    """
    Get affiliate tracking statistics.

    Shows the research → purchase → experience funnel.
    """
    db = get_database()

    start = datetime.utcnow() - timedelta(days=days)

    # Total clicks
    total_clicks = await db.affiliate_clicks.count_documents(
        {"clicked_at": {"$gte": start}}
    )

    # Returns (came back to app)
    returns = await db.affiliate_clicks.count_documents(
        {"clicked_at": {"$gte": start}, "returned": True}
    )

    # Purchases (confirmed they bought)
    purchases = await db.affiliate_clicks.count_documents(
        {"clicked_at": {"$gte": start}, "purchased": True}
    )

    # By vendor
    pipeline = [
        {"$match": {"clicked_at": {"$gte": start}}},
        {"$group": {
            "_id": "$vendor_name",
            "clicks": {"$sum": 1},
            "returns": {"$sum": {"$cond": ["$returned", 1, 0]}},
            "purchases": {"$sum": {"$cond": ["$purchased", 1, 0]}},
        }},
        {"$sort": {"clicks": -1}}
    ]
    by_vendor = []
    async for doc in db.affiliate_clicks.aggregate(pipeline):
        by_vendor.append({
            "vendor": doc["_id"],
            "clicks": doc["clicks"],
            "returns": doc["returns"],
            "purchases": doc["purchases"],
            "return_rate": doc["returns"] / doc["clicks"] if doc["clicks"] > 0 else 0,
            "purchase_rate": doc["purchases"] / doc["clicks"] if doc["clicks"] > 0 else 0,
        })

    # By peptide
    pipeline = [
        {"$match": {"clicked_at": {"$gte": start}, "peptide": {"$ne": None}}},
        {"$group": {
            "_id": "$peptide",
            "clicks": {"$sum": 1},
            "returns": {"$sum": {"$cond": ["$returned", 1, 0]}},
            "purchases": {"$sum": {"$cond": ["$purchased", 1, 0]}},
        }},
        {"$sort": {"clicks": -1}}
    ]
    by_peptide = []
    async for doc in db.affiliate_clicks.aggregate(pipeline):
        by_peptide.append({
            "peptide": doc["_id"],
            "clicks": doc["clicks"],
            "returns": doc["returns"],
            "purchases": doc["purchases"],
        })

    return {
        "time_range_days": days,
        "totals": {
            "clicks": total_clicks,
            "returns": returns,
            "purchases": purchases,
            "return_rate": returns / total_clicks if total_clicks > 0 else 0,
            "purchase_rate": purchases / total_clicks if total_clicks > 0 else 0,
        },
        "by_vendor": by_vendor,
        "by_peptide": by_peptide,
    }


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

async def _update_user_metrics(db, user_id: str, event_type: str, properties: dict):
    """Update user-level metrics for quick access"""

    update = {"$set": {"last_seen": datetime.utcnow()}}

    if event_type == EventType.CHAT_SENT:
        update["$inc"] = {"total_chats": 1}
    elif event_type == EventType.SOURCE_CLICKED:
        update["$inc"] = {"sources_viewed": 1}
    elif event_type == EventType.SESSION_START:
        update["$inc"] = {"total_sessions": 1}
    elif event_type == EventType.FEEDBACK_SUBMITTED:
        update["$inc"] = {"feedback_count": 1}

    await db.user_metrics.update_one(
        {"user_id": user_id},
        update,
        upsert=True
    )
