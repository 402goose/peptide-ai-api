"""
Peptide AI - Core Data Models

This module contains all Pydantic models for:
- Raw documents from data sources
- Processed chunks for vector storage
- User journey tracking
- Analytics and aggregations
"""

from pydantic import BaseModel, Field, field_validator
from typing import Optional, List, Dict, Any
from datetime import datetime, date
from enum import Enum
from uuid import uuid4
import hashlib


# =============================================================================
# ENUMS
# =============================================================================

class SourceType(str, Enum):
    """Data source types for RAG system"""
    PUBMED = "pubmed"
    ARXIV = "arxiv"
    BIORXIV = "biorxiv"
    MEDRXIV = "medrxiv"
    CHINAXIV = "chinaxiv"
    REDDIT = "reddit"
    FORUM = "forum"
    USER_JOURNEY = "user_journey"
    WEB = "web"


class FDAStatus(str, Enum):
    """FDA approval status for peptides"""
    APPROVED = "approved"
    TRIAL = "trial"
    INVESTIGATIONAL = "investigational"
    NOT_APPROVED = "not_approved"
    BANNED_COMPOUNDING = "banned_compounding"
    UNKNOWN = "unknown"


class JourneyStatus(str, Enum):
    """Status of a user's peptide journey"""
    PLANNING = "planning"           # Researching, not started
    ACTIVE = "active"               # Currently using
    PAUSED = "paused"               # Temporarily stopped
    COMPLETED = "completed"         # Finished cycle
    DISCONTINUED = "discontinued"   # Stopped early


class AdministrationRoute(str, Enum):
    """How the peptide is administered"""
    SUBCUTANEOUS = "subcutaneous"
    INTRAMUSCULAR = "intramuscular"
    ORAL = "oral"
    NASAL = "nasal"
    TOPICAL = "topical"
    SUBLINGUAL = "sublingual"
    OTHER = "other"


class GoalCategory(str, Enum):
    """Categories of user goals"""
    HEALING_RECOVERY = "healing_recovery"
    MUSCLE_GROWTH = "muscle_growth"
    FAT_LOSS = "fat_loss"
    COGNITIVE = "cognitive"
    SLEEP = "sleep"
    LONGEVITY = "longevity"
    SEXUAL_HEALTH = "sexual_health"
    IMMUNE = "immune"
    SKIN_HAIR = "skin_hair"
    GUT_HEALTH = "gut_health"
    ENERGY = "energy"
    OTHER = "other"


class SeverityLevel(str, Enum):
    """Severity of side effects"""
    NONE = "none"
    MILD = "mild"
    MODERATE = "moderate"
    SEVERE = "severe"


class ExpertiseLevel(str, Enum):
    """User's experience level with peptides"""
    BEGINNER = "beginner"       # First time, no experience
    INTERMEDIATE = "intermediate"  # Some experience, 1-3 cycles
    ADVANCED = "advanced"       # Experienced, 3+ cycles


# =============================================================================
# RAG DOCUMENT MODELS
# =============================================================================

class RawDocument(BaseModel):
    """Raw document from any source before processing"""
    source_id: str                          # Original ID from source
    source_type: SourceType
    title: str
    content: str                            # Full text or abstract
    authors: List[str] = []
    publication_date: Optional[datetime] = None
    url: str
    doi: Optional[str] = None
    citation: Optional[str] = None
    raw_metadata: Dict[str, Any] = {}       # Source-specific metadata


class ProcessedChunk(BaseModel):
    """A chunk ready for embedding and storage"""
    chunk_id: str                           # Generated unique ID
    document_id: str                        # Parent document ID
    source_type: SourceType
    content: str                            # Chunk text
    section_type: Optional[str] = None      # abstract, methods, results, etc.

    # Enrichments
    peptides_mentioned: List[str] = []
    fda_status: FDAStatus = FDAStatus.UNKNOWN
    conditions_mentioned: List[str] = []

    # Metadata
    title: str
    authors: List[str] = []
    publication_date: Optional[datetime] = None
    url: str
    doi: Optional[str] = None
    citation: str = ""
    original_language: str = "en"

    # Embeddings (populated after embedding step)
    embedding_pubmedbert: Optional[List[float]] = None
    embedding_openai: Optional[List[float]] = None


# =============================================================================
# USER MODELS
# =============================================================================

class UserProfile(BaseModel):
    """
    Core user profile - stores preferences and context
    Separate from auth (handled by Clerk/Auth0)
    """
    user_id: str                            # From auth provider
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    # Preferences
    expertise_level: ExpertiseLevel = ExpertiseLevel.BEGINNER
    primary_goals: List[GoalCategory] = []
    units_preference: str = "metric"        # metric or imperial

    # Anonymized demographics (optional, for personalization)
    age_range: Optional[str] = None         # "25-34", "35-44", etc.
    sex: Optional[str] = None               # "male", "female", "other", "prefer_not_to_say"
    activity_level: Optional[str] = None    # "sedentary", "moderate", "active", "very_active"

    # Health context (optional, user-provided)
    relevant_conditions: List[str] = []     # e.g., ["diabetes", "hypertension"]
    current_medications: List[str] = []     # For interaction awareness
    allergies: List[str] = []

    # Subscription
    subscription_tier: str = "free"         # free, pro, pro_ship, creator
    subscription_started: Optional[datetime] = None

    # Creator status
    is_creator: bool = False
    creator_handle: Optional[str] = None
    content_sharing_consent: bool = False   # Consent to share journey publicly

    def get_anonymized_id(self) -> str:
        """Generate anonymized ID for data that gets shared/aggregated"""
        return hashlib.sha256(f"{self.user_id}_pepper_xyz".encode()).hexdigest()[:16]


# =============================================================================
# JOURNEY MODELS - THE CORE DATA MOAT
# =============================================================================

class JourneyGoal(BaseModel):
    """
    A specific goal within a journey
    Users often have multiple goals for a single peptide
    """
    goal_id: str = Field(default_factory=lambda: str(uuid4()))
    category: GoalCategory
    description: str                        # Free-form description
    target_metric: Optional[str] = None     # e.g., "heal shoulder tendon"
    baseline_value: Optional[str] = None    # Starting state
    target_value: Optional[str] = None      # Desired end state
    achieved: Optional[bool] = None
    achievement_notes: Optional[str] = None


class DoseLog(BaseModel):
    """
    Individual dose log entry
    Core tracking data for protocol efficacy
    """
    log_id: str = Field(default_factory=lambda: str(uuid4()))
    timestamp: datetime = Field(default_factory=datetime.utcnow)

    # Dose details
    peptide: str                            # Canonical peptide name
    dose_amount: float                      # Numeric amount
    dose_unit: str                          # "mcg", "mg", "IU", etc.
    route: AdministrationRoute
    injection_site: Optional[str] = None    # For SubQ/IM: "abdomen", "thigh", etc.

    # Context
    time_of_day: Optional[str] = None       # "morning", "evening", "pre_workout", etc.
    fasted: Optional[bool] = None           # Taken fasted?
    notes: Optional[str] = None             # Any notes about this dose

    # For stacks
    is_part_of_stack: bool = False
    stack_name: Optional[str] = None        # e.g., "Wolverine Stack"


class SymptomLog(BaseModel):
    """
    Daily/periodic symptom and wellness tracking
    This data feeds into outcome analysis
    """
    log_id: str = Field(default_factory=lambda: str(uuid4()))
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    log_date: date                          # Date this log is for

    # Wellness metrics (1-10 scale)
    energy_level: Optional[int] = Field(None, ge=1, le=10)
    sleep_quality: Optional[int] = Field(None, ge=1, le=10)
    mood: Optional[int] = Field(None, ge=1, le=10)
    pain_level: Optional[int] = Field(None, ge=1, le=10)  # 1=no pain, 10=severe
    recovery_feeling: Optional[int] = Field(None, ge=1, le=10)

    # Goal-specific tracking
    goal_progress: Dict[str, int] = {}      # goal_id -> progress (1-10)

    # Side effects
    side_effects: List[str] = []            # List of experienced side effects
    side_effect_severity: SeverityLevel = SeverityLevel.NONE

    # Body metrics (optional)
    weight_kg: Optional[float] = None
    body_fat_percent: Optional[float] = None

    # Free-form
    notes: Optional[str] = None

    @field_validator('energy_level', 'sleep_quality', 'mood', 'pain_level', 'recovery_feeling')
    @classmethod
    def validate_scale(cls, v):
        if v is not None and (v < 1 or v > 10):
            raise ValueError('Scale values must be between 1 and 10')
        return v


class JourneyMilestone(BaseModel):
    """
    Significant events or observations during a journey
    These are key data points for the AI and for creator content
    """
    milestone_id: str = Field(default_factory=lambda: str(uuid4()))
    timestamp: datetime = Field(default_factory=datetime.utcnow)

    milestone_type: str                     # "improvement", "setback", "side_effect", "adjustment", "completion"
    title: str                              # Brief title
    description: str                        # Detailed description

    # Related data
    related_goal_id: Optional[str] = None
    related_peptide: Optional[str] = None

    # For sharing
    is_shareable: bool = False              # User marks as OK to share
    media_urls: List[str] = []              # Before/after photos, etc.


class PeptideJourney(BaseModel):
    """
    A complete peptide journey/cycle
    This is the primary unit of user data tracking

    One user can have multiple journeys (different peptides, different cycles)
    """
    journey_id: str = Field(default_factory=lambda: str(uuid4()))
    user_id: str                            # Reference to user
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    # Journey identification
    title: Optional[str] = None             # User-given title, e.g., "BPC-157 for Shoulder"
    status: JourneyStatus = JourneyStatus.PLANNING

    # What they're taking
    primary_peptide: str                    # Main peptide
    secondary_peptides: List[str] = []      # Stacking compounds
    is_stack: bool = False
    stack_name: Optional[str] = None

    # Protocol details
    planned_protocol: Optional[str] = None  # Free-form planned protocol
    actual_protocol_summary: Optional[str] = None  # Generated summary of actual use
    administration_route: AdministrationRoute = AdministrationRoute.SUBCUTANEOUS

    # Timing
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    planned_duration_weeks: Optional[int] = None
    actual_duration_weeks: Optional[int] = None

    # Goals
    goals: List[JourneyGoal] = []

    # Source (for research)
    peptide_source: Optional[str] = None    # Where they got it (can be anonymized)
    source_verified: bool = False           # Did they verify with COA?

    # Nested logs (for quick access - full logs in separate collection)
    dose_count: int = 0
    symptom_log_count: int = 0

    # Outcomes (populated during/after journey)
    overall_efficacy_rating: Optional[int] = Field(None, ge=1, le=10)
    would_recommend: Optional[bool] = None
    would_use_again: Optional[bool] = None
    outcome_summary: Optional[str] = None   # AI-generated or user-written

    # Key learnings
    what_worked: Optional[str] = None
    what_didnt_work: Optional[str] = None
    advice_for_others: Optional[str] = None

    # Milestones
    milestones: List[JourneyMilestone] = []

    # Privacy/sharing
    is_public: bool = False                 # Can be shown (anonymized) to others
    is_creator_content: bool = False        # Part of creator's public journey

    def calculate_duration(self) -> Optional[int]:
        """Calculate actual duration in weeks"""
        if self.start_date and self.end_date:
            delta = self.end_date - self.start_date
            return delta.days // 7
        return None


class JourneyNote(BaseModel):
    """
    Free-form notes attached to a journey
    For thoughts that don't fit structured logging
    """
    note_id: str = Field(default_factory=lambda: str(uuid4()))
    journey_id: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    content: str
    note_type: str = "general"              # "general", "research", "question", "observation"


# =============================================================================
# AGGREGATED/ANALYTICS MODELS
# =============================================================================

class JourneyOutcomeSummary(BaseModel):
    """
    Aggregated outcome data for a journey
    Used for RAG retrieval and analytics
    This is what gets embedded and searched
    """
    journey_id: str
    user_hash: str                          # Anonymized user ID

    # What was done
    peptide: str
    secondary_peptides: List[str] = []
    duration_weeks: int
    administration_route: str
    average_dose: Optional[str] = None      # e.g., "250mcg daily"

    # Goals and outcomes
    goal_categories: List[str] = []
    goals_achieved: int = 0
    goals_total: int = 0

    # Efficacy
    overall_efficacy: Optional[int] = None  # 1-10
    would_recommend: Optional[bool] = None

    # Wellness trends (averages over journey)
    avg_energy_delta: Optional[float] = None  # Change from baseline
    avg_sleep_delta: Optional[float] = None
    avg_pain_delta: Optional[float] = None

    # Side effects
    side_effects_reported: List[str] = []
    max_side_effect_severity: str = "none"

    # Demographics (anonymized)
    age_range: Optional[str] = None
    sex: Optional[str] = None
    activity_level: Optional[str] = None

    # Narrative (for RAG)
    outcome_narrative: str                  # Generated summary for embedding

    # Metadata
    created_at: datetime
    source_type: SourceType = SourceType.USER_JOURNEY


class PeptideStats(BaseModel):
    """
    Aggregated statistics for a peptide across all user journeys
    Used for general recommendations
    """
    peptide: str
    total_journeys: int = 0
    active_journeys: int = 0
    completed_journeys: int = 0

    # Efficacy stats
    avg_efficacy_rating: Optional[float] = None
    efficacy_std_dev: Optional[float] = None
    recommend_rate: Optional[float] = None  # % who would recommend

    # Common goals
    top_goal_categories: List[Dict[str, Any]] = []  # [{category, count, avg_success}]

    # Common protocols
    common_doses: List[str] = []            # Most common dose strings
    common_durations: List[int] = []        # Most common durations in weeks
    common_routes: List[str] = []           # Most common administration routes

    # Side effects
    reported_side_effects: List[Dict[str, Any]] = []  # [{effect, frequency, avg_severity}]

    # Stacking
    common_stack_partners: List[str] = []   # Other peptides commonly used with this one

    last_updated: datetime = Field(default_factory=datetime.utcnow)


class UserJourneyContext(BaseModel):
    """
    Context object passed to AI for personalization
    Summarizes user's relevant history
    """
    user_id: str
    expertise_level: str
    primary_goals: List[str]

    # Journey history
    total_journeys: int
    active_journeys: List[Dict[str, Any]]   # Current active journeys summary
    past_peptides: List[str]                # Peptides they've used before

    # Outcomes
    best_results_with: List[str]            # Peptides that worked well
    poor_results_with: List[str]            # Peptides that didn't work
    reported_sensitivities: List[str]       # Side effects they're prone to

    # Health context
    relevant_conditions: List[str]
    current_medications: List[str]

    # Preferences
    preferred_administration: Optional[str] = None

    def to_prompt_string(self) -> str:
        """Format for inclusion in prompts"""
        parts = [
            f"**Expertise Level**: {self.expertise_level}",
            f"**Primary Goals**: {', '.join(self.primary_goals) if self.primary_goals else 'Not specified'}",
            f"**Journey History**: {self.total_journeys} total journeys",
        ]

        if self.active_journeys:
            active_str = ", ".join([
                f"{j['peptide']} ({j['status']})"
                for j in self.active_journeys
            ])
            parts.append(f"**Currently Using**: {active_str}")

        if self.past_peptides:
            parts.append(f"**Past Experience With**: {', '.join(self.past_peptides)}")

        if self.best_results_with:
            parts.append(f"**Good Results With**: {', '.join(self.best_results_with)}")

        if self.reported_sensitivities:
            parts.append(f"**Known Sensitivities**: {', '.join(self.reported_sensitivities)}")

        if self.relevant_conditions:
            parts.append(f"**Health Considerations**: {', '.join(self.relevant_conditions)}")

        return "\n".join(parts)


# =============================================================================
# CREATOR MODELS
# =============================================================================

class CreatorProfile(BaseModel):
    """
    Extended profile for creators who share content
    """
    user_id: str
    creator_handle: str                     # Public handle
    bio: Optional[str] = None

    # Links
    tiktok_handle: Optional[str] = None
    instagram_handle: Optional[str] = None
    youtube_handle: Optional[str] = None
    twitter_handle: Optional[str] = None

    # Stats
    public_journeys: int = 0
    followers_on_platform: int = 0
    total_content_pieces: int = 0

    # Tier
    creator_tier: str = "explorer"          # explorer, creator, ambassador

    # Earnings
    affiliate_earnings_total: float = 0.0
    last_payout: Optional[datetime] = None

    # Verification
    is_verified: bool = False
    verified_at: Optional[datetime] = None


class CreatorContent(BaseModel):
    """
    Content created by creators about their journeys
    Can be linked to external platforms
    """
    content_id: str = Field(default_factory=lambda: str(uuid4()))
    creator_id: str
    journey_id: Optional[str] = None        # Related journey if any

    # Content details
    content_type: str                       # "post", "video", "story", "reel"
    platform: str                           # "tiktok", "instagram", "youtube", "platform"
    external_url: Optional[str] = None      # Link to external content

    # On-platform content
    title: Optional[str] = None
    description: Optional[str] = None
    media_urls: List[str] = []

    # Engagement
    views: int = 0
    likes: int = 0
    comments: int = 0
    shares: int = 0

    # Attribution
    attributed_signups: int = 0
    attributed_revenue: float = 0.0

    created_at: datetime = Field(default_factory=datetime.utcnow)


# =============================================================================
# AFFILIATE & HOLISTIC PRODUCTS MODELS
# =============================================================================

class ProductType(str, Enum):
    """Type of product"""
    PEPTIDE = "peptide"
    SUPPLEMENT = "supplement"
    HERB = "herb"
    AMINO_ACID = "amino_acid"
    VITAMIN = "vitamin"
    MINERAL = "mineral"
    ADAPTOGEN = "adaptogen"
    PROBIOTIC = "probiotic"
    ENZYME = "enzyme"
    HORMONE = "hormone"
    OTHER = "other"


class SymptomCategory(str, Enum):
    """Categories for symptoms"""
    ENERGY_FATIGUE = "energy_fatigue"
    COGNITIVE = "cognitive"
    MOOD_MENTAL = "mood_mental"
    SLEEP = "sleep"
    GUT_DIGESTIVE = "gut_digestive"
    HORMONAL_FEMALE = "hormonal_female"
    HORMONAL_MALE = "hormonal_male"
    HORMONAL_GENERAL = "hormonal_general"
    THYROID = "thyroid"
    METABOLIC = "metabolic"
    IMMUNE = "immune"
    INFLAMMATION_PAIN = "inflammation_pain"
    LIVER_DETOX = "liver_detox"
    CARDIOVASCULAR = "cardiovascular"
    KIDNEY_FLUID = "kidney_fluid"
    SKIN_HAIR = "skin_hair"
    NEUROLOGICAL = "neurological"
    RECOVERY = "recovery"
    APPETITE_CRAVINGS = "appetite_cravings"
    URINARY_REPRODUCTIVE = "urinary_reproductive"
    TEMPERATURE = "temperature"


class HolisticProduct(BaseModel):
    """
    A product (peptide or supplement) that can be recommended for symptoms
    """
    product_id: str = Field(default_factory=lambda: str(uuid4()))
    name: str                                   # Product name
    product_type: ProductType
    description: Optional[str] = None

    # Affiliate info
    affiliate_url: Optional[str] = None         # Link to purchase
    affiliate_code: Optional[str] = None        # Discount/tracking code
    vendor: Optional[str] = None                # Recommended vendor

    # Metadata
    is_peptide: bool = False
    requires_prescription: bool = False
    typical_dose: Optional[str] = None
    typical_frequency: Optional[str] = None

    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class LabTest(BaseModel):
    """
    A lab test that can be recommended for symptoms
    """
    test_id: str = Field(default_factory=lambda: str(uuid4()))
    name: str                                   # Test name
    description: Optional[str] = None

    # Affiliate info
    affiliate_url: Optional[str] = None
    vendor: Optional[str] = None                # Lab provider

    # Metadata
    typical_cost_range: Optional[str] = None    # e.g., "$50-100"
    requires_fasting: bool = False
    at_home_available: bool = False

    created_at: datetime = Field(default_factory=datetime.utcnow)


class Symptom(BaseModel):
    """
    A symptom that users may experience
    """
    symptom_id: str = Field(default_factory=lambda: str(uuid4()))
    name: str                                   # Symptom name (e.g., "Brain fog")
    slug: str                                   # URL-friendly slug
    category: SymptomCategory
    description: Optional[str] = None

    # Related products and tests (stored as IDs for lookup)
    recommended_products: List[str] = []        # Product IDs
    recommended_labs: List[str] = []            # Lab test IDs

    # Search optimization
    keywords: List[str] = []                    # Alternative names/search terms

    created_at: datetime = Field(default_factory=datetime.utcnow)


class SymptomProductMapping(BaseModel):
    """
    Maps symptoms to products with additional context
    """
    mapping_id: str = Field(default_factory=lambda: str(uuid4()))
    symptom_id: str
    product_id: str

    # Recommendation strength
    is_primary: bool = True                     # Primary vs supplementary recommendation
    efficacy_notes: Optional[str] = None        # Why this product helps

    # Source tracking
    source: str = "holistic_guide"              # Where this recommendation came from

    created_at: datetime = Field(default_factory=datetime.utcnow)


class AffiliateClick(BaseModel):
    """
    Tracks when users click affiliate links
    """
    click_id: str = Field(default_factory=lambda: str(uuid4()))
    user_id: Optional[str] = None               # May be anonymous
    session_id: Optional[str] = None

    # What was clicked
    product_id: str
    symptom_id: Optional[str] = None            # If clicked from symptom context

    # Context
    source: str                                 # "journey", "chat", "stacks", "search"
    source_id: Optional[str] = None             # journey_id, conversation_id, etc.

    # Metadata
    clicked_at: datetime = Field(default_factory=datetime.utcnow)
    ip_hash: Optional[str] = None               # Anonymized IP for fraud detection
    user_agent: Optional[str] = None


class AffiliateConversion(BaseModel):
    """
    Tracks conversions from affiliate clicks
    """
    conversion_id: str = Field(default_factory=lambda: str(uuid4()))
    click_id: str                               # Related click

    # Conversion details
    order_amount: Optional[float] = None
    commission_amount: Optional[float] = None
    vendor: str

    # Status
    status: str = "pending"                     # pending, confirmed, cancelled

    converted_at: datetime = Field(default_factory=datetime.utcnow)


class SymptomSearch(BaseModel):
    """
    Tracks what symptoms users search for
    """
    search_id: str = Field(default_factory=lambda: str(uuid4()))
    user_id: Optional[str] = None
    session_id: Optional[str] = None

    # Search details
    query: str                                  # Raw search query
    matched_symptoms: List[str] = []            # Symptom IDs that matched

    # Context
    source: str                                 # "journey", "chat", "stacks", "search"

    searched_at: datetime = Field(default_factory=datetime.utcnow)
