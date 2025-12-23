"""
Peptide AI - A/B Testing Framework

Run experiments to optimize the product based on real user behavior.

Workflow:
1. Create experiment with variants (control + treatment)
2. Set traffic allocation (e.g., 10% to experiment)
3. Users get assigned to variant on first exposure
4. Track conversion events
5. Calculate statistical significance
6. Auto-promote winners when confident

Statistical Method: Bayesian A/B testing
- No fixed sample size needed
- Can make decisions at any time
- Reports probability that variant beats control
"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
from uuid import uuid4
import hashlib
import math

from api.deps import get_database
from api.middleware.auth import get_current_user

router = APIRouter()


# =============================================================================
# MODELS
# =============================================================================

class VariantConfig(BaseModel):
    """Configuration for an experiment variant"""
    name: str = Field(..., description="Variant name (e.g., 'control', 'treatment_a')")
    description: str = Field("", description="What this variant does")
    config: Dict[str, Any] = Field(default={}, description="Variant-specific configuration")
    weight: float = Field(1.0, description="Traffic weight (relative to other variants)")


class ExperimentCreate(BaseModel):
    """Create a new experiment"""
    name: str = Field(..., description="Experiment name")
    description: str = Field("", description="What we're testing")
    hypothesis: str = Field("", description="Expected outcome")
    metric: str = Field(..., description="Primary metric to measure (e.g., 'conversion', 'engagement')")
    variants: List[VariantConfig] = Field(..., min_items=2, description="At least 2 variants")
    traffic_percent: float = Field(10.0, ge=1, le=100, description="% of users in experiment")
    min_sample_size: int = Field(100, description="Minimum conversions before deciding")
    confidence_threshold: float = Field(0.95, description="Required probability to declare winner")


class ExperimentUpdate(BaseModel):
    """Update experiment status"""
    status: Optional[str] = Field(None, pattern="^(running|paused|completed|archived)$")
    traffic_percent: Optional[float] = Field(None, ge=0, le=100)
    winner: Optional[str] = Field(None, description="Winning variant name")


class ExperimentResponse(BaseModel):
    """Experiment details"""
    id: str
    name: str
    description: str
    hypothesis: str
    metric: str
    variants: List[VariantConfig]
    traffic_percent: float
    status: str
    min_sample_size: int
    confidence_threshold: float
    winner: Optional[str]
    created_at: datetime
    updated_at: datetime


class VariantStats(BaseModel):
    """Statistics for a variant"""
    name: str
    visitors: int
    conversions: int
    conversion_rate: float
    probability_best: float
    uplift_vs_control: Optional[float]


class ExperimentResults(BaseModel):
    """Full experiment results"""
    experiment_id: str
    experiment_name: str
    status: str
    metric: str
    variants: List[VariantStats]
    winner: Optional[str]
    confidence: float
    can_decide: bool
    recommendation: str


# =============================================================================
# ENDPOINTS
# =============================================================================

@router.post("/experiments", response_model=ExperimentResponse)
async def create_experiment(
    body: ExperimentCreate,
    user: dict = Depends(get_current_user)
):
    """
    Create a new A/B experiment.

    Experiments bucket users into variants and track conversions.
    """
    db = get_database()

    experiment_id = str(uuid4())[:8]  # Short ID for easy reference
    now = datetime.utcnow()

    experiment_doc = {
        "id": experiment_id,
        "name": body.name,
        "description": body.description,
        "hypothesis": body.hypothesis,
        "metric": body.metric,
        "variants": [v.dict() for v in body.variants],
        "traffic_percent": body.traffic_percent,
        "status": "running",
        "min_sample_size": body.min_sample_size,
        "confidence_threshold": body.confidence_threshold,
        "winner": None,
        "created_at": now,
        "updated_at": now,
        "created_by": user["user_id"],
    }

    await db.experiments.insert_one(experiment_doc)

    return ExperimentResponse(**experiment_doc)


@router.get("/experiments", response_model=List[ExperimentResponse])
async def list_experiments(
    status: Optional[str] = None,
    user: dict = Depends(get_current_user)
):
    """List all experiments"""
    db = get_database()

    query = {}
    if status:
        query["status"] = status

    experiments = []
    async for doc in db.experiments.find(query).sort("created_at", -1):
        experiments.append(ExperimentResponse(**doc))

    return experiments


@router.get("/experiments/{experiment_id}", response_model=ExperimentResponse)
async def get_experiment(
    experiment_id: str,
    user: dict = Depends(get_current_user)
):
    """Get experiment details"""
    db = get_database()

    doc = await db.experiments.find_one({"id": experiment_id})
    if not doc:
        raise HTTPException(404, "Experiment not found")

    return ExperimentResponse(**doc)


@router.patch("/experiments/{experiment_id}", response_model=ExperimentResponse)
async def update_experiment(
    experiment_id: str,
    body: ExperimentUpdate,
    user: dict = Depends(get_current_user)
):
    """Update experiment (pause, complete, set winner)"""
    db = get_database()

    doc = await db.experiments.find_one({"id": experiment_id})
    if not doc:
        raise HTTPException(404, "Experiment not found")

    update = {"updated_at": datetime.utcnow()}

    if body.status:
        update["status"] = body.status
    if body.traffic_percent is not None:
        update["traffic_percent"] = body.traffic_percent
    if body.winner:
        update["winner"] = body.winner
        update["status"] = "completed"

    await db.experiments.update_one(
        {"id": experiment_id},
        {"$set": update}
    )

    doc.update(update)
    return ExperimentResponse(**doc)


@router.get("/experiments/{experiment_id}/results", response_model=ExperimentResults)
async def get_experiment_results(
    experiment_id: str,
    user: dict = Depends(get_current_user)
):
    """
    Get experiment results with statistical analysis.

    Uses Bayesian analysis to calculate probability each variant is best.
    """
    db = get_database()

    # Get experiment
    experiment = await db.experiments.find_one({"id": experiment_id})
    if not experiment:
        raise HTTPException(404, "Experiment not found")

    # Get variant stats from analytics
    variant_stats = []
    all_conversions = []

    for variant in experiment["variants"]:
        name = variant["name"]

        # Count visitors assigned to this variant
        visitors = await db.experiment_assignments.count_documents({
            "experiment_id": experiment_id,
            "variant": name
        })

        # Count conversions
        conversions = await db.analytics_events.count_documents({
            "experiment_id": experiment_id,
            "variant": name,
            "event_type": "experiment_conversion",
            "properties.metric": experiment["metric"]
        })

        rate = conversions / visitors if visitors > 0 else 0

        variant_stats.append({
            "name": name,
            "visitors": visitors,
            "conversions": conversions,
            "conversion_rate": rate,
        })
        all_conversions.append(conversions)

    # Calculate Bayesian probabilities
    probabilities = _calculate_bayesian_probabilities(variant_stats)

    # Add probabilities and uplift to stats
    control_rate = variant_stats[0]["conversion_rate"] if variant_stats else 0

    final_stats = []
    for i, vs in enumerate(variant_stats):
        uplift = None
        if i > 0 and control_rate > 0:
            uplift = (vs["conversion_rate"] - control_rate) / control_rate

        final_stats.append(VariantStats(
            name=vs["name"],
            visitors=vs["visitors"],
            conversions=vs["conversions"],
            conversion_rate=round(vs["conversion_rate"], 4),
            probability_best=round(probabilities[i], 4),
            uplift_vs_control=round(uplift, 4) if uplift is not None else None
        ))

    # Determine if we can make a decision
    total_conversions = sum(all_conversions)
    min_sample = experiment.get("min_sample_size", 100)
    confidence_threshold = experiment.get("confidence_threshold", 0.95)

    best_prob = max(probabilities) if probabilities else 0
    can_decide = total_conversions >= min_sample and best_prob >= confidence_threshold

    # Find winner if confident
    winner = None
    if can_decide:
        winner_idx = probabilities.index(best_prob)
        winner = variant_stats[winner_idx]["name"]

    # Generate recommendation
    if experiment.get("winner"):
        recommendation = f"Experiment complete. Winner: {experiment['winner']}. Promote to 100%."
    elif can_decide:
        recommendation = f"Confident winner: {winner} ({best_prob*100:.1f}% probability). Ready to promote."
    elif total_conversions < min_sample:
        recommendation = f"Need more data. {total_conversions}/{min_sample} conversions."
    else:
        recommendation = f"No clear winner yet. Best probability: {best_prob*100:.1f}%"

    return ExperimentResults(
        experiment_id=experiment_id,
        experiment_name=experiment["name"],
        status=experiment["status"],
        metric=experiment["metric"],
        variants=final_stats,
        winner=experiment.get("winner") or (winner if can_decide else None),
        confidence=best_prob,
        can_decide=can_decide,
        recommendation=recommendation
    )


@router.post("/experiments/{experiment_id}/assign")
async def assign_user_to_experiment(
    experiment_id: str,
    user_id: str,
    user: dict = Depends(get_current_user)
):
    """
    Assign a user to an experiment variant.

    Uses deterministic hashing for consistent assignment.
    """
    db = get_database()

    # Check if already assigned
    existing = await db.experiment_assignments.find_one({
        "experiment_id": experiment_id,
        "user_id": user_id
    })

    if existing:
        return {"variant": existing["variant"], "already_assigned": True}

    # Get experiment
    experiment = await db.experiments.find_one({"id": experiment_id})
    if not experiment or experiment["status"] != "running":
        raise HTTPException(400, "Experiment not running")

    # Check if user should be in experiment (traffic allocation)
    hash_input = f"{experiment_id}:{user_id}:traffic"
    traffic_hash = int(hashlib.md5(hash_input.encode()).hexdigest(), 16)
    in_experiment = (traffic_hash % 100) < experiment["traffic_percent"]

    if not in_experiment:
        return {"variant": None, "in_experiment": False}

    # Assign to variant based on weights
    variant = _select_variant(experiment["variants"], user_id, experiment_id)

    assignment = {
        "id": str(uuid4()),
        "experiment_id": experiment_id,
        "user_id": user_id,
        "variant": variant,
        "assigned_at": datetime.utcnow(),
    }

    await db.experiment_assignments.insert_one(assignment)

    return {"variant": variant, "in_experiment": True, "already_assigned": False}


@router.get("/experiments/user/{user_id}/assignments")
async def get_user_experiments(
    user_id: str,
    user: dict = Depends(get_current_user)
):
    """Get all experiment assignments for a user"""
    db = get_database()

    assignments = []
    async for doc in db.experiment_assignments.find({"user_id": user_id}):
        assignments.append({
            "experiment_id": doc["experiment_id"],
            "variant": doc["variant"],
            "assigned_at": doc["assigned_at"]
        })

    return {"assignments": assignments}


@router.post("/experiments/auto-promote")
async def auto_promote_winners(
    user: dict = Depends(get_current_user)
):
    """
    Check all running experiments and auto-promote confident winners.

    This should be run periodically (e.g., daily cron job).
    """
    db = get_database()

    promoted = []
    waiting = []
    needs_attention = []

    async for experiment in db.experiments.find({"status": "running"}):
        experiment_id = experiment["id"]

        # Get results
        results = await get_experiment_results(experiment_id, user)

        if results.can_decide and results.winner:
            # Promote winner
            await db.experiments.update_one(
                {"id": experiment_id},
                {"$set": {
                    "status": "completed",
                    "winner": results.winner,
                    "updated_at": datetime.utcnow()
                }}
            )
            promoted.append({
                "experiment_id": experiment_id,
                "name": experiment["name"],
                "winner": results.winner,
                "confidence": results.confidence
            })
        elif results.confidence < 0.5:
            # Control might be winning - flag for attention
            needs_attention.append({
                "experiment_id": experiment_id,
                "name": experiment["name"],
                "recommendation": results.recommendation
            })
        else:
            waiting.append({
                "experiment_id": experiment_id,
                "name": experiment["name"],
                "recommendation": results.recommendation
            })

    return {
        "promoted": promoted,
        "waiting": waiting,
        "needs_attention": needs_attention,
        "summary": f"Promoted {len(promoted)}, waiting on {len(waiting)}, {len(needs_attention)} need attention"
    }


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def _select_variant(variants: List[dict], user_id: str, experiment_id: str) -> str:
    """Select a variant for a user based on weights"""
    # Deterministic hash
    hash_input = f"{experiment_id}:{user_id}:variant"
    hash_value = int(hashlib.md5(hash_input.encode()).hexdigest(), 16)

    # Calculate cumulative weights
    total_weight = sum(v.get("weight", 1.0) for v in variants)
    normalized_hash = (hash_value % 10000) / 10000.0  # 0-1 range

    cumulative = 0
    for variant in variants:
        weight = variant.get("weight", 1.0) / total_weight
        cumulative += weight
        if normalized_hash < cumulative:
            return variant["name"]

    return variants[-1]["name"]  # Fallback


def _calculate_bayesian_probabilities(variant_stats: List[dict]) -> List[float]:
    """
    Calculate Bayesian probability each variant is the best.

    Uses Beta-Binomial conjugate prior.
    Simulates posterior samples to estimate P(variant is best).
    """
    import random

    if not variant_stats:
        return []

    # Number of simulations
    n_simulations = 10000

    # Prior parameters (uninformative prior)
    alpha_prior = 1
    beta_prior = 1

    # Sample from posterior for each variant
    wins = [0] * len(variant_stats)

    for _ in range(n_simulations):
        samples = []
        for vs in variant_stats:
            # Posterior is Beta(alpha_prior + conversions, beta_prior + non-conversions)
            alpha = alpha_prior + vs["conversions"]
            beta = beta_prior + (vs["visitors"] - vs["conversions"])

            # Sample from Beta distribution
            sample = _sample_beta(alpha, beta)
            samples.append(sample)

        # Find winner of this simulation
        best_idx = samples.index(max(samples))
        wins[best_idx] += 1

    # Probability is proportion of wins
    probabilities = [w / n_simulations for w in wins]
    return probabilities


def _sample_beta(alpha: float, beta: float) -> float:
    """
    Sample from Beta distribution using inverse transform.

    Approximation using gamma ratio.
    """
    import random

    # Use gamma sampling: Beta(a,b) = Gamma(a) / (Gamma(a) + Gamma(b))
    x = _sample_gamma(alpha)
    y = _sample_gamma(beta)

    if x + y == 0:
        return 0.5

    return x / (x + y)


def _sample_gamma(shape: float) -> float:
    """Sample from Gamma distribution using Marsaglia's method"""
    import random
    import math

    if shape < 1:
        return _sample_gamma(1 + shape) * (random.random() ** (1 / shape))

    d = shape - 1/3
    c = 1 / math.sqrt(9 * d)

    while True:
        x = random.gauss(0, 1)
        v = (1 + c * x) ** 3

        if v > 0:
            u = random.random()
            if u < 1 - 0.0331 * (x ** 2) ** 2:
                return d * v
            if math.log(u) < 0.5 * x ** 2 + d * (1 - v + math.log(v)):
                return d * v
