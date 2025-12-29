"""
Peptide AI - Journey Service

Business logic for user journey tracking, logging, and aggregation.
This is the core service for building the data moat.
"""

from typing import Optional, List, Dict, Any
from datetime import datetime, date, timedelta
from uuid import uuid4
import statistics

from api.models.documents import (
    UserProfile, PeptideJourney, JourneyGoal, DoseLog, SymptomLog,
    JourneyMilestone, JourneyNote, JourneyOutcomeSummary,
    PeptideStats, UserJourneyContext, JourneyStatus, GoalCategory,
    ExpertiseLevel, SourceType
)


class JourneyService:
    """
    Service for managing user peptide journeys

    Handles:
    - Journey CRUD
    - Dose and symptom logging
    - Outcome aggregation
    - Context building for personalization
    - Data export for creators
    """

    def __init__(self, db):
        """
        Initialize with database connection

        db should have collections:
        - users
        - journeys
        - dose_logs
        - symptom_logs
        - journey_outcomes (aggregated for RAG)
        - peptide_stats (aggregated)
        """
        self.db = db

    # =========================================================================
    # JOURNEY LIFECYCLE
    # =========================================================================

    async def create_journey(
        self,
        user_id: str,
        primary_peptide: str,
        goals: List[Dict[str, Any]],
        planned_protocol: Optional[str] = None,
        planned_duration_weeks: Optional[int] = None,
        secondary_peptides: List[str] = None,
        title: Optional[str] = None
    ) -> PeptideJourney:
        """
        Create a new peptide journey
        """
        # Build goal objects
        goal_objects = [
            JourneyGoal(
                category=GoalCategory(g.get("category", "other")),
                description=g.get("description", ""),
                target_metric=g.get("target_metric"),
                baseline_value=g.get("baseline_value"),
                target_value=g.get("target_value")
            )
            for g in goals
        ]

        journey = PeptideJourney(
            user_id=user_id,
            title=title or f"{primary_peptide} Journey",
            primary_peptide=primary_peptide,
            secondary_peptides=secondary_peptides or [],
            is_stack=bool(secondary_peptides),
            goals=goal_objects,
            planned_protocol=planned_protocol,
            planned_duration_weeks=planned_duration_weeks,
            status=JourneyStatus.PLANNING
        )

        await self.db.journeys.insert_one(journey.model_dump())

        # Update user stats
        await self._update_user_journey_count(user_id)

        return journey

    async def start_journey(
        self,
        journey_id: str,
        start_date: Optional[date] = None
    ) -> PeptideJourney:
        """
        Mark a journey as active (started)
        """
        journey = await self.get_journey(journey_id)
        if not journey:
            raise ValueError(f"Journey {journey_id} not found")

        journey.status = JourneyStatus.ACTIVE
        journey.start_date = start_date or date.today()
        journey.updated_at = datetime.utcnow()

        await self.db.journeys.update_one(
            {"journey_id": journey_id},
            {"$set": journey.model_dump()}
        )

        return journey

    async def complete_journey(
        self,
        journey_id: str,
        overall_efficacy_rating: int,
        would_recommend: bool,
        would_use_again: bool,
        outcome_summary: Optional[str] = None,
        what_worked: Optional[str] = None,
        what_didnt_work: Optional[str] = None,
        advice_for_others: Optional[str] = None
    ) -> PeptideJourney:
        """
        Mark a journey as completed and record outcomes
        """
        journey = await self.get_journey(journey_id)
        if not journey:
            raise ValueError(f"Journey {journey_id} not found")

        journey.status = JourneyStatus.COMPLETED
        journey.end_date = date.today()
        journey.actual_duration_weeks = journey.calculate_duration()
        journey.overall_efficacy_rating = overall_efficacy_rating
        journey.would_recommend = would_recommend
        journey.would_use_again = would_use_again
        journey.outcome_summary = outcome_summary
        journey.what_worked = what_worked
        journey.what_didnt_work = what_didnt_work
        journey.advice_for_others = advice_for_others
        journey.updated_at = datetime.utcnow()

        await self.db.journeys.update_one(
            {"journey_id": journey_id},
            {"$set": journey.model_dump()}
        )

        # Generate outcome summary for RAG
        await self._generate_outcome_summary(journey)

        # Update peptide stats
        await self._update_peptide_stats(journey.primary_peptide)

        return journey

    async def pause_journey(self, journey_id: str, reason: Optional[str] = None) -> PeptideJourney:
        """Pause an active journey"""
        journey = await self.get_journey(journey_id)
        if not journey:
            raise ValueError(f"Journey {journey_id} not found")

        journey.status = JourneyStatus.PAUSED
        journey.updated_at = datetime.utcnow()

        if reason:
            milestone = JourneyMilestone(
                milestone_type="adjustment",
                title="Journey Paused",
                description=reason,
                related_peptide=journey.primary_peptide
            )
            journey.milestones.append(milestone)

        await self.db.journeys.update_one(
            {"journey_id": journey_id},
            {"$set": journey.model_dump()}
        )

        return journey

    async def resume_journey(self, journey_id: str) -> PeptideJourney:
        """Resume a paused journey"""
        journey = await self.get_journey(journey_id)
        if not journey:
            raise ValueError(f"Journey {journey_id} not found")

        journey.status = JourneyStatus.ACTIVE
        journey.updated_at = datetime.utcnow()

        milestone = JourneyMilestone(
            milestone_type="adjustment",
            title="Journey Resumed",
            description="Resumed after pause",
            related_peptide=journey.primary_peptide
        )
        journey.milestones.append(milestone)

        await self.db.journeys.update_one(
            {"journey_id": journey_id},
            {"$set": journey.model_dump()}
        )

        return journey

    async def discontinue_journey(
        self,
        journey_id: str,
        reason: str,
        overall_efficacy_rating: Optional[int] = None
    ) -> PeptideJourney:
        """Discontinue a journey early"""
        journey = await self.get_journey(journey_id)
        if not journey:
            raise ValueError(f"Journey {journey_id} not found")

        journey.status = JourneyStatus.DISCONTINUED
        journey.end_date = date.today()
        journey.actual_duration_weeks = journey.calculate_duration()
        journey.outcome_summary = f"Discontinued: {reason}"
        journey.updated_at = datetime.utcnow()

        if overall_efficacy_rating:
            journey.overall_efficacy_rating = overall_efficacy_rating

        milestone = JourneyMilestone(
            milestone_type="setback",
            title="Journey Discontinued",
            description=reason,
            related_peptide=journey.primary_peptide
        )
        journey.milestones.append(milestone)

        await self.db.journeys.update_one(
            {"journey_id": journey_id},
            {"$set": journey.model_dump()}
        )

        # Still generate outcome summary (valuable data)
        await self._generate_outcome_summary(journey)

        return journey

    async def get_journey(self, journey_id: str) -> Optional[PeptideJourney]:
        """Get a journey by ID"""
        data = await self.db.journeys.find_one({"journey_id": journey_id})
        if data:
            return PeptideJourney(**data)
        return None

    async def get_user_journeys(
        self,
        user_id: str,
        status: Optional[JourneyStatus] = None,
        limit: int = 50
    ) -> List[PeptideJourney]:
        """Get all journeys for a user"""
        query = {"user_id": user_id}
        if status:
            query["status"] = status.value

        cursor = self.db.journeys.find(query).sort("created_at", -1).limit(limit)
        journeys = []
        async for doc in cursor:
            journeys.append(PeptideJourney(**doc))
        return journeys

    # =========================================================================
    # LOGGING
    # =========================================================================

    async def log_dose(
        self,
        journey_id: str,
        peptide: str,
        dose_amount: float,
        dose_unit: str,
        route: str,
        injection_site: Optional[str] = None,
        time_of_day: Optional[str] = None,
        fasted: Optional[bool] = None,
        notes: Optional[str] = None
    ) -> DoseLog:
        """
        Log a single dose
        This is the most frequent operation - optimize for speed
        """
        log = DoseLog(
            peptide=peptide,
            dose_amount=dose_amount,
            dose_unit=dose_unit,
            route=route,
            injection_site=injection_site,
            time_of_day=time_of_day,
            fasted=fasted,
            notes=notes
        )

        # Store log with journey reference
        log_data = log.model_dump()
        log_data["journey_id"] = journey_id

        await self.db.dose_logs.insert_one(log_data)

        # Update journey dose count
        await self.db.journeys.update_one(
            {"journey_id": journey_id},
            {
                "$inc": {"dose_count": 1},
                "$set": {"updated_at": datetime.utcnow()}
            }
        )

        return log

    async def log_symptoms(
        self,
        journey_id: str,
        log_date: date,
        energy_level: Optional[int] = None,
        sleep_quality: Optional[int] = None,
        mood: Optional[int] = None,
        pain_level: Optional[int] = None,
        recovery_feeling: Optional[int] = None,
        goal_progress: Optional[Dict[str, int]] = None,
        side_effects: Optional[List[str]] = None,
        side_effect_severity: str = "none",
        weight_kg: Optional[float] = None,
        body_fat_percent: Optional[float] = None,
        notes: Optional[str] = None
    ) -> SymptomLog:
        """
        Log daily symptoms and wellness metrics
        """
        log = SymptomLog(
            log_date=log_date,
            energy_level=energy_level,
            sleep_quality=sleep_quality,
            mood=mood,
            pain_level=pain_level,
            recovery_feeling=recovery_feeling,
            goal_progress=goal_progress or {},
            side_effects=side_effects or [],
            side_effect_severity=side_effect_severity,
            weight_kg=weight_kg,
            body_fat_percent=body_fat_percent,
            notes=notes
        )

        log_data = log.model_dump()
        log_data["journey_id"] = journey_id

        # Upsert - one log per date per journey
        await self.db.symptom_logs.update_one(
            {"journey_id": journey_id, "log_date": log_date.isoformat()},
            {"$set": log_data},
            upsert=True
        )

        # Update journey log count
        count = await self.db.symptom_logs.count_documents({"journey_id": journey_id})
        await self.db.journeys.update_one(
            {"journey_id": journey_id},
            {
                "$set": {
                    "symptom_log_count": count,
                    "updated_at": datetime.utcnow()
                }
            }
        )

        return log

    async def add_milestone(
        self,
        journey_id: str,
        milestone_type: str,
        title: str,
        description: str,
        related_goal_id: Optional[str] = None,
        is_shareable: bool = False,
        media_urls: List[str] = None
    ) -> JourneyMilestone:
        """
        Add a milestone to a journey
        Milestones are key moments that can be shared
        """
        milestone = JourneyMilestone(
            milestone_type=milestone_type,
            title=title,
            description=description,
            related_goal_id=related_goal_id,
            is_shareable=is_shareable,
            media_urls=media_urls or []
        )

        # Get journey and get the peptide
        journey = await self.get_journey(journey_id)
        if journey:
            milestone.related_peptide = journey.primary_peptide

        await self.db.journeys.update_one(
            {"journey_id": journey_id},
            {
                "$push": {"milestones": milestone.model_dump()},
                "$set": {"updated_at": datetime.utcnow()}
            }
        )

        return milestone

    async def add_note(
        self,
        journey_id: str,
        content: str,
        note_type: str = "general"
    ) -> JourneyNote:
        """Add a free-form note to a journey"""
        note = JourneyNote(
            journey_id=journey_id,
            content=content,
            note_type=note_type
        )

        await self.db.journey_notes.insert_one(note.model_dump())

        return note

    async def get_dose_logs(
        self,
        journey_id: str,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None
    ) -> List[DoseLog]:
        """Get dose logs for a journey"""
        query = {"journey_id": journey_id}

        if start_date or end_date:
            query["timestamp"] = {}
            if start_date:
                query["timestamp"]["$gte"] = datetime.combine(start_date, datetime.min.time())
            if end_date:
                query["timestamp"]["$lte"] = datetime.combine(end_date, datetime.max.time())

        cursor = self.db.dose_logs.find(query).sort("timestamp", 1)
        logs = []
        async for doc in cursor:
            logs.append(DoseLog(**doc))
        return logs

    async def get_symptom_logs(
        self,
        journey_id: str,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None
    ) -> List[SymptomLog]:
        """Get symptom logs for a journey"""
        query = {"journey_id": journey_id}

        if start_date or end_date:
            date_query = {}
            if start_date:
                date_query["$gte"] = start_date.isoformat()
            if end_date:
                date_query["$lte"] = end_date.isoformat()
            if date_query:
                query["log_date"] = date_query

        cursor = self.db.symptom_logs.find(query).sort("log_date", 1)
        logs = []
        async for doc in cursor:
            logs.append(SymptomLog(**doc))
        return logs

    # =========================================================================
    # AGGREGATION & ANALYTICS
    # =========================================================================

    async def _generate_outcome_summary(self, journey: PeptideJourney) -> JourneyOutcomeSummary:
        """
        Generate an outcome summary for a completed journey
        This gets embedded and stored for RAG retrieval
        """
        user = await self.db.users.find_one({"user_id": journey.user_id})
        user_profile = UserProfile(**user) if user else None

        # Get all symptom logs to calculate trends
        symptom_logs = await self.get_symptom_logs(journey.journey_id)

        # Calculate average dose
        dose_logs = await self.get_dose_logs(journey.journey_id)
        avg_dose = self._calculate_average_dose(dose_logs)

        # Calculate wellness trends
        wellness_trends = self._calculate_wellness_trends(symptom_logs)

        # Count achieved goals
        goals_achieved = sum(1 for g in journey.goals if g.achieved)

        # Collect all side effects
        all_side_effects = set()
        max_severity = "none"
        severity_order = ["none", "mild", "moderate", "severe"]
        for log in symptom_logs:
            all_side_effects.update(log.side_effects)
            if severity_order.index(log.side_effect_severity.value) > severity_order.index(max_severity):
                max_severity = log.side_effect_severity.value

        # Generate narrative for embedding
        narrative = self._generate_outcome_narrative(
            journey, avg_dose, goals_achieved, wellness_trends, list(all_side_effects)
        )

        summary = JourneyOutcomeSummary(
            journey_id=journey.journey_id,
            user_hash=user_profile.get_anonymized_id() if user_profile else "anonymous",
            peptide=journey.primary_peptide,
            secondary_peptides=journey.secondary_peptides,
            duration_weeks=journey.actual_duration_weeks or 0,
            administration_route=journey.administration_route.value,
            average_dose=avg_dose,
            goal_categories=[g.category.value for g in journey.goals],
            goals_achieved=goals_achieved,
            goals_total=len(journey.goals),
            overall_efficacy=journey.overall_efficacy_rating,
            would_recommend=journey.would_recommend,
            avg_energy_delta=wellness_trends.get("energy_delta"),
            avg_sleep_delta=wellness_trends.get("sleep_delta"),
            avg_pain_delta=wellness_trends.get("pain_delta"),
            side_effects_reported=list(all_side_effects),
            max_side_effect_severity=max_severity,
            age_range=user_profile.age_range if user_profile else None,
            sex=user_profile.sex if user_profile else None,
            activity_level=user_profile.activity_level if user_profile else None,
            outcome_narrative=narrative,
            created_at=datetime.utcnow()
        )

        # Store for RAG
        await self.db.journey_outcomes.insert_one(summary.model_dump())

        return summary

    def _calculate_average_dose(self, dose_logs: List[DoseLog]) -> Optional[str]:
        """Calculate average dose from logs"""
        if not dose_logs:
            return None

        # Group by peptide and unit
        dose_groups: Dict[str, List[float]] = {}
        for log in dose_logs:
            key = f"{log.peptide}_{log.dose_unit}"
            if key not in dose_groups:
                dose_groups[key] = []
            dose_groups[key].append(log.dose_amount)

        # Calculate averages
        parts = []
        for key, amounts in dose_groups.items():
            peptide, unit = key.rsplit("_", 1)
            avg = sum(amounts) / len(amounts)
            parts.append(f"{avg:.0f}{unit} {peptide}")

        return ", ".join(parts) if parts else None

    def _calculate_wellness_trends(self, symptom_logs: List[SymptomLog]) -> Dict[str, Optional[float]]:
        """Calculate wellness metric trends (first week vs last week)"""
        if len(symptom_logs) < 7:
            return {}

        first_week = symptom_logs[:7]
        last_week = symptom_logs[-7:]

        def avg_metric(logs, attr):
            values = [getattr(log, attr) for log in logs if getattr(log, attr) is not None]
            return statistics.mean(values) if values else None

        trends = {}
        for metric in ["energy_level", "sleep_quality", "mood", "pain_level", "recovery_feeling"]:
            first_avg = avg_metric(first_week, metric)
            last_avg = avg_metric(last_week, metric)
            if first_avg is not None and last_avg is not None:
                # For pain, negative delta is good
                delta = last_avg - first_avg
                key = metric.replace("_level", "").replace("_quality", "").replace("_feeling", "")
                trends[f"{key}_delta"] = round(delta, 2)

        return trends

    def _generate_outcome_narrative(
        self,
        journey: PeptideJourney,
        avg_dose: Optional[str],
        goals_achieved: int,
        wellness_trends: Dict,
        side_effects: List[str]
    ) -> str:
        """
        Generate a natural language summary for RAG embedding
        This is what gets searched when users ask about outcomes
        """
        parts = []

        # Basic info
        duration = journey.actual_duration_weeks or journey.planned_duration_weeks or "unknown"
        status_text = "completed" if journey.status == JourneyStatus.COMPLETED else "discontinued"

        parts.append(
            f"User {status_text} a {duration}-week {journey.primary_peptide} journey"
        )

        if journey.secondary_peptides:
            parts.append(f"stacked with {', '.join(journey.secondary_peptides)}")

        # Goals
        if journey.goals:
            goal_cats = [g.category.value.replace("_", " ") for g in journey.goals]
            parts.append(f"for {', '.join(goal_cats)}")

        parts.append(".")

        # Protocol
        if avg_dose:
            parts.append(f"Average dose: {avg_dose} via {journey.administration_route.value}.")

        # Outcomes
        if journey.overall_efficacy_rating:
            parts.append(f"Overall efficacy rated {journey.overall_efficacy_rating}/10.")

        if goals_achieved > 0:
            parts.append(f"Achieved {goals_achieved} of {len(journey.goals)} goals.")

        # Wellness changes
        if wellness_trends:
            changes = []
            for key, delta in wellness_trends.items():
                direction = "improved" if delta > 0 else "decreased"
                # For pain, reverse the interpretation
                if "pain" in key:
                    direction = "improved" if delta < 0 else "worsened"
                    delta = abs(delta)
                metric = key.replace("_delta", "")
                changes.append(f"{metric} {direction} by {delta:.1f} points")
            if changes:
                parts.append(f"Wellness changes: {'; '.join(changes)}.")

        # Side effects
        if side_effects:
            parts.append(f"Reported side effects: {', '.join(side_effects)}.")
        else:
            parts.append("No significant side effects reported.")

        # Recommendation
        if journey.would_recommend is not None:
            rec = "would recommend" if journey.would_recommend else "would not recommend"
            parts.append(f"User {rec} this peptide.")

        # User notes
        if journey.what_worked:
            parts.append(f"What worked: {journey.what_worked}")

        if journey.what_didnt_work:
            parts.append(f"Challenges: {journey.what_didnt_work}")

        if journey.advice_for_others:
            parts.append(f"Advice: {journey.advice_for_others}")

        return " ".join(parts)

    async def _update_peptide_stats(self, peptide: str):
        """
        Update aggregated statistics for a peptide
        Called when a journey is completed
        """
        # Get all completed journeys for this peptide
        cursor = self.db.journeys.find({
            "primary_peptide": peptide,
            "status": {"$in": [JourneyStatus.COMPLETED.value, JourneyStatus.DISCONTINUED.value]}
        })

        journeys = []
        async for doc in cursor:
            journeys.append(PeptideJourney(**doc))

        if not journeys:
            return

        # Calculate stats
        efficacy_ratings = [j.overall_efficacy_rating for j in journeys if j.overall_efficacy_rating]
        recommend_count = sum(1 for j in journeys if j.would_recommend)

        # Goal categories frequency
        goal_freq: Dict[str, Dict] = {}
        for j in journeys:
            for g in j.goals:
                cat = g.category.value
                if cat not in goal_freq:
                    goal_freq[cat] = {"count": 0, "achieved": 0}
                goal_freq[cat]["count"] += 1
                if g.achieved:
                    goal_freq[cat]["achieved"] += 1

        top_goals = [
            {
                "category": cat,
                "count": data["count"],
                "success_rate": data["achieved"] / data["count"] if data["count"] > 0 else 0
            }
            for cat, data in sorted(goal_freq.items(), key=lambda x: x[1]["count"], reverse=True)[:5]
        ]

        # Common doses
        all_doses = []
        for j in journeys:
            dose_logs = await self.get_dose_logs(j.journey_id)
            if dose_logs:
                # Get most common dose for this journey
                dose_strings = [f"{l.dose_amount}{l.dose_unit}" for l in dose_logs]
                if dose_strings:
                    most_common = max(set(dose_strings), key=dose_strings.count)
                    all_doses.append(most_common)

        # Stack partners
        stack_partners: Dict[str, int] = {}
        for j in journeys:
            for secondary in j.secondary_peptides:
                stack_partners[secondary] = stack_partners.get(secondary, 0) + 1

        stats = PeptideStats(
            peptide=peptide,
            total_journeys=len(journeys),
            active_journeys=sum(1 for j in journeys if j.status == JourneyStatus.ACTIVE),
            completed_journeys=sum(1 for j in journeys if j.status == JourneyStatus.COMPLETED),
            avg_efficacy_rating=statistics.mean(efficacy_ratings) if efficacy_ratings else None,
            efficacy_std_dev=statistics.stdev(efficacy_ratings) if len(efficacy_ratings) > 1 else None,
            recommend_rate=recommend_count / len(journeys) if journeys else None,
            top_goal_categories=top_goals,
            common_doses=list(set(all_doses))[:5],
            common_durations=[j.actual_duration_weeks for j in journeys if j.actual_duration_weeks][:5],
            common_routes=list(set(j.administration_route.value for j in journeys))[:3],
            common_stack_partners=sorted(stack_partners, key=stack_partners.get, reverse=True)[:5]
        )

        # Upsert stats
        await self.db.peptide_stats.update_one(
            {"peptide": peptide},
            {"$set": stats.model_dump()},
            upsert=True
        )

    async def _update_user_journey_count(self, user_id: str):
        """Update user's journey count"""
        count = await self.db.journeys.count_documents({"user_id": user_id})
        await self.db.users.update_one(
            {"user_id": user_id},
            {"$set": {"total_journeys": count, "updated_at": datetime.utcnow()}}
        )

    # =========================================================================
    # CONTEXT BUILDING FOR AI
    # =========================================================================

    async def build_user_context(self, user_id: str) -> UserJourneyContext:
        """
        Build context object for AI personalization
        This summarizes a user's journey history for the prompt
        """
        user_data = await self.db.users.find_one({"user_id": user_id})
        user = UserProfile(**user_data) if user_data else None

        if not user:
            return UserJourneyContext(
                user_id=user_id,
                expertise_level="beginner",
                primary_goals=[],
                total_journeys=0,
                active_journeys=[],
                past_peptides=[],
                best_results_with=[],
                poor_results_with=[],
                reported_sensitivities=[],
                relevant_conditions=[],
                current_medications=[]
            )

        # Get all journeys
        all_journeys = await self.get_user_journeys(user_id, limit=100)

        # Active journeys
        active = [
            {
                "peptide": j.primary_peptide,
                "status": j.status.value,
                "started": j.start_date.isoformat() if j.start_date else None,
                "duration_weeks": (date.today() - j.start_date).days // 7 if j.start_date else 0
            }
            for j in all_journeys if j.status == JourneyStatus.ACTIVE
        ]

        # Past peptides
        past_peptides = list(set(j.primary_peptide for j in all_journeys))

        # Best results (efficacy >= 7)
        best = [
            j.primary_peptide for j in all_journeys
            if j.overall_efficacy_rating and j.overall_efficacy_rating >= 7
        ]

        # Poor results (efficacy <= 4)
        poor = [
            j.primary_peptide for j in all_journeys
            if j.overall_efficacy_rating and j.overall_efficacy_rating <= 4
        ]

        # Collect side effect sensitivities
        sensitivities = set()
        for j in all_journeys:
            logs = await self.get_symptom_logs(j.journey_id)
            for log in logs:
                if log.side_effect_severity.value in ["moderate", "severe"]:
                    sensitivities.update(log.side_effects)

        # Preferred administration (most common)
        routes = [j.administration_route.value for j in all_journeys]
        preferred_route = max(set(routes), key=routes.count) if routes else None

        return UserJourneyContext(
            user_id=user_id,
            expertise_level=user.expertise_level.value,
            primary_goals=[g.value for g in user.primary_goals],
            total_journeys=len(all_journeys),
            active_journeys=active,
            past_peptides=past_peptides,
            best_results_with=list(set(best)),
            poor_results_with=list(set(poor)),
            reported_sensitivities=list(sensitivities),
            relevant_conditions=user.relevant_conditions,
            current_medications=user.current_medications,
            preferred_administration=preferred_route
        )

    # =========================================================================
    # CREATOR EXPORTS
    # =========================================================================

    async def export_journey_for_content(self, journey_id: str) -> Dict[str, Any]:
        """
        Export a journey in a format suitable for content creation
        Includes all the data a creator might want to share
        """
        journey = await self.get_journey(journey_id)
        if not journey:
            raise ValueError(f"Journey {journey_id} not found")

        dose_logs = await self.get_dose_logs(journey_id)
        symptom_logs = await self.get_symptom_logs(journey_id)

        # Calculate weekly summaries
        weekly_summaries = self._calculate_weekly_summaries(symptom_logs)

        # Format dose protocol
        protocol = self._format_dose_protocol(dose_logs)

        return {
            "journey_id": journey.journey_id,
            "title": journey.title,
            "peptide": journey.primary_peptide,
            "stack": journey.secondary_peptides if journey.is_stack else None,
            "duration_weeks": journey.actual_duration_weeks or journey.planned_duration_weeks,
            "status": journey.status.value,

            "goals": [
                {
                    "category": g.category.value,
                    "description": g.description,
                    "achieved": g.achieved,
                    "notes": g.achievement_notes
                }
                for g in journey.goals
            ],

            "protocol": protocol,

            "weekly_progress": weekly_summaries,

            "milestones": [
                {
                    "date": m.timestamp.isoformat(),
                    "type": m.milestone_type,
                    "title": m.title,
                    "description": m.description,
                    "media": m.media_urls if m.is_shareable else []
                }
                for m in journey.milestones
            ],

            "outcomes": {
                "overall_efficacy": journey.overall_efficacy_rating,
                "would_recommend": journey.would_recommend,
                "would_use_again": journey.would_use_again,
                "summary": journey.outcome_summary,
                "what_worked": journey.what_worked,
                "what_didnt_work": journey.what_didnt_work,
                "advice": journey.advice_for_others
            },

            "stats": {
                "total_doses": len(dose_logs),
                "days_logged": len(symptom_logs),
                "avg_dose": self._calculate_average_dose(dose_logs)
            }
        }

    def _calculate_weekly_summaries(self, symptom_logs: List[SymptomLog]) -> List[Dict]:
        """Calculate weekly progress summaries"""
        if not symptom_logs:
            return []

        # Group by week
        weeks: Dict[int, List[SymptomLog]] = {}
        first_date = min(log.log_date for log in symptom_logs)

        for log in symptom_logs:
            week_num = (log.log_date - first_date).days // 7 + 1
            if week_num not in weeks:
                weeks[week_num] = []
            weeks[week_num].append(log)

        summaries = []
        for week_num in sorted(weeks.keys()):
            logs = weeks[week_num]

            def avg(attr):
                vals = [getattr(l, attr) for l in logs if getattr(l, attr) is not None]
                return round(statistics.mean(vals), 1) if vals else None

            all_effects = set()
            for l in logs:
                all_effects.update(l.side_effects)

            summaries.append({
                "week": week_num,
                "days_logged": len(logs),
                "avg_energy": avg("energy_level"),
                "avg_sleep": avg("sleep_quality"),
                "avg_mood": avg("mood"),
                "avg_pain": avg("pain_level"),
                "avg_recovery": avg("recovery_feeling"),
                "side_effects": list(all_effects)
            })

        return summaries

    def _format_dose_protocol(self, dose_logs: List[DoseLog]) -> Dict[str, Any]:
        """Format dose logs into a protocol summary"""
        if not dose_logs:
            return {}

        # Group by peptide
        by_peptide: Dict[str, List[DoseLog]] = {}
        for log in dose_logs:
            if log.peptide not in by_peptide:
                by_peptide[log.peptide] = []
            by_peptide[log.peptide].append(log)

        protocols = {}
        for peptide, logs in by_peptide.items():
            doses = [l.dose_amount for l in logs]
            units = list(set(l.dose_unit for l in logs))
            routes = list(set(l.route.value for l in logs))
            times = list(set(l.time_of_day for l in logs if l.time_of_day))

            # Estimate frequency
            if len(logs) >= 2:
                dates = sorted(set(l.timestamp.date() for l in logs))
                if len(dates) >= 2:
                    avg_gap = (dates[-1] - dates[0]).days / (len(dates) - 1)
                    if avg_gap <= 1.5:
                        frequency = "daily"
                    elif avg_gap <= 3.5:
                        frequency = "every other day"
                    elif avg_gap <= 5:
                        frequency = "2x per week"
                    else:
                        frequency = "weekly"
                else:
                    frequency = "variable"
            else:
                frequency = "single dose"

            protocols[peptide] = {
                "avg_dose": round(statistics.mean(doses), 1),
                "min_dose": min(doses),
                "max_dose": max(doses),
                "unit": units[0] if len(units) == 1 else units,
                "route": routes[0] if len(routes) == 1 else routes,
                "frequency": frequency,
                "typical_timing": times[0] if len(times) == 1 else times,
                "total_doses": len(logs)
            }

        return protocols
