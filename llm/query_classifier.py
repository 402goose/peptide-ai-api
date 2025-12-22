"""
Peptide AI - Query Classifier

Classifies user queries to determine:
- Query type (research, dosing, sourcing, safety, etc.)
- Intent (informational, comparison, protocol, etc.)
- Peptides mentioned
- Risk level
"""

import logging
from typing import Optional, List
from enum import Enum
from pydantic import BaseModel
import openai

logger = logging.getLogger(__name__)


class QueryType(str, Enum):
    """Types of queries we handle"""
    RESEARCH = "research"           # What does the research say about X?
    MECHANISM = "mechanism"         # How does X work?
    DOSING = "dosing"               # What's the protocol/dosage for X?
    COMPARISON = "comparison"       # X vs Y, which is better?
    SAFETY = "safety"               # Side effects, interactions, risks
    SOURCING = "sourcing"           # Where to get X (requires careful handling)
    EXPERIENCE = "experience"       # User experience questions
    STACKING = "stacking"           # Combining peptides
    PREPARATION = "preparation"     # Reconstitution, storage
    GENERAL = "general"             # General peptide questions
    OFF_TOPIC = "off_topic"         # Not peptide-related


class RiskLevel(str, Enum):
    """Risk level of query response"""
    LOW = "low"                     # General info, no action advice
    MEDIUM = "medium"               # Protocol info, standard disclaimers
    HIGH = "high"                   # Dosing, sourcing, requires strong disclaimers
    BLOCKED = "blocked"             # Cannot answer (medical emergency, illegal)


class QueryClassification(BaseModel):
    """Result of query classification"""
    query_type: QueryType
    intent: str                     # Brief description of what user wants
    peptides_mentioned: List[str]   # Peptides detected in query
    conditions_mentioned: List[str] # Health conditions mentioned
    risk_level: RiskLevel
    requires_disclaimer: bool
    disclaimer_types: List[str]     # Which disclaimers to include
    search_strategy: str            # How to search (research, experiences, both)
    confidence: float               # 0-1 confidence in classification


class QueryClassifier:
    """
    Classifies user queries for appropriate handling

    Uses a combination of:
    - Rule-based keyword matching (fast)
    - LLM classification (when needed)
    """

    # Peptide name patterns for detection
    PEPTIDE_PATTERNS = [
        "bpc-157", "bpc157", "body protective compound",
        "tb-500", "tb500", "thymosin beta",
        "semaglutide", "ozempic", "wegovy", "rybelsus",
        "tirzepatide", "mounjaro", "zepbound",
        "ghk-cu", "ghk copper",
        "ipamorelin",
        "cjc-1295", "cjc1295",
        "ghrp-6", "ghrp6", "ghrp-2", "ghrp2",
        "melanotan", "mt-2", "mt2",
        "pt-141", "pt141", "bremelanotide",
        "epitalon", "epithalon",
        "semax",
        "selank",
        "dihexa",
        "kisspeptin",
        "mots-c", "motsc",
        "ss-31", "elamipretide",
        "pentosan", "bpc",
        "aod-9604", "aod9604",
        "tesamorelin",
        "sermorelin",
        "hexarelin",
        "igf-1", "igf1",
        "mgf", "mechano growth factor",
        "follistatin",
        "ll-37",
    ]

    # Sourcing-related keywords (high risk)
    SOURCING_KEYWORDS = [
        "buy", "purchase", "order", "source", "vendor", "supplier",
        "where to get", "where can i get", "how to get",
        "website", "online", "ship", "shipping",
        "price", "cost", "cheap", "affordable",
        "legit", "legitimate", "trusted", "reliable",
        "prescription", "without prescription",
    ]

    # Safety-related keywords
    SAFETY_KEYWORDS = [
        "side effect", "adverse", "danger", "risk", "safe",
        "interaction", "contraindication", "warning",
        "overdose", "too much", "toxic",
        "allergy", "allergic", "reaction",
        "long-term", "long term",
    ]

    # Dosing-related keywords
    DOSING_KEYWORDS = [
        "dose", "dosage", "protocol", "cycle",
        "how much", "how often", "frequency",
        "mcg", "mg", "iu", "units",
        "injection", "inject", "subcutaneous", "intramuscular",
        "reconstitute", "reconstitution", "bac water",
        "loading", "maintenance", "saturation",
    ]

    def __init__(self, openai_client: Optional[openai.AsyncOpenAI] = None):
        self.openai_client = openai_client

    async def classify(self, query: str) -> QueryClassification:
        """
        Classify a user query

        Uses rule-based classification first, falls back to LLM for complex cases.
        """
        query_lower = query.lower()

        # Detect peptides mentioned
        peptides = self._detect_peptides(query_lower)

        # Detect conditions
        conditions = self._detect_conditions(query_lower)

        # Rule-based classification
        query_type, confidence = self._rule_based_classify(query_lower)

        # Determine risk level
        risk_level = self._assess_risk(query_lower, query_type)

        # Determine disclaimers needed
        disclaimer_types = self._get_disclaimer_types(query_type, risk_level, peptides)

        # Determine search strategy
        search_strategy = self._get_search_strategy(query_type)

        # Generate intent description
        intent = self._generate_intent(query_type, peptides)

        return QueryClassification(
            query_type=query_type,
            intent=intent,
            peptides_mentioned=peptides,
            conditions_mentioned=conditions,
            risk_level=risk_level,
            requires_disclaimer=len(disclaimer_types) > 0,
            disclaimer_types=disclaimer_types,
            search_strategy=search_strategy,
            confidence=confidence
        )

    def _detect_peptides(self, query: str) -> List[str]:
        """Detect peptide names in query"""
        found = []
        for pattern in self.PEPTIDE_PATTERNS:
            if pattern in query:
                # Normalize the name
                normalized = self._normalize_peptide_name(pattern)
                if normalized not in found:
                    found.append(normalized)
        return found

    def _normalize_peptide_name(self, name: str) -> str:
        """Normalize peptide name to canonical form"""
        mappings = {
            "bpc-157": "BPC-157", "bpc157": "BPC-157", "body protective compound": "BPC-157",
            "tb-500": "TB-500", "tb500": "TB-500", "thymosin beta": "TB-500",
            "semaglutide": "Semaglutide", "ozempic": "Semaglutide", "wegovy": "Semaglutide",
            "tirzepatide": "Tirzepatide", "mounjaro": "Tirzepatide", "zepbound": "Tirzepatide",
            "ghk-cu": "GHK-Cu", "ghk copper": "GHK-Cu",
            "ipamorelin": "Ipamorelin",
            "cjc-1295": "CJC-1295", "cjc1295": "CJC-1295",
            "ghrp-6": "GHRP-6", "ghrp6": "GHRP-6",
            "ghrp-2": "GHRP-2", "ghrp2": "GHRP-2",
            "melanotan": "Melanotan II", "mt-2": "Melanotan II", "mt2": "Melanotan II",
            "pt-141": "PT-141", "pt141": "PT-141", "bremelanotide": "PT-141",
            "epitalon": "Epitalon", "epithalon": "Epitalon",
            "semax": "Semax",
            "selank": "Selank",
            "dihexa": "Dihexa",
        }
        return mappings.get(name.lower(), name.upper())

    def _detect_conditions(self, query: str) -> List[str]:
        """Detect health conditions mentioned"""
        conditions = []
        condition_patterns = [
            ("injury", "injury"), ("healing", "healing"), ("tendon", "tendon injury"),
            ("muscle", "muscle"), ("fat loss", "weight loss"), ("weight loss", "weight loss"),
            ("sleep", "sleep"), ("cognitive", "cognitive"), ("memory", "cognitive"),
            ("anxiety", "anxiety"), ("depression", "mood"), ("mood", "mood"),
            ("skin", "skin"), ("hair", "hair loss"), ("aging", "anti-aging"),
            ("gut", "gut health"), ("inflammation", "inflammation"),
            ("immune", "immune"), ("sexual", "sexual health"), ("libido", "sexual health"),
            # Cancer types
            ("cancer", "cancer"), ("breast cancer", "breast cancer"), ("prostate cancer", "prostate cancer"),
            ("tumor", "cancer"), ("oncology", "cancer"), ("chemo", "cancer recovery"),
            ("radiation", "cancer recovery"), ("remission", "cancer recovery"),
            # More conditions
            ("autoimmune", "autoimmune"), ("arthritis", "arthritis"), ("joint", "joint pain"),
            ("chronic pain", "pain"), ("fibromyalgia", "chronic pain"),
            ("diabetes", "metabolic"), ("insulin", "metabolic"), ("blood sugar", "metabolic"),
            ("thyroid", "thyroid"), ("hormone", "hormonal"), ("testosterone", "hormonal"),
            ("fertility", "fertility"), ("ed ", "erectile dysfunction"), ("erectile", "erectile dysfunction"),
            ("recovery", "recovery"), ("surgery", "post-surgery"), ("wound", "wound healing"),
        ]
        for pattern, condition in condition_patterns:
            if pattern in query and condition not in conditions:
                conditions.append(condition)
        return conditions

    def _rule_based_classify(self, query: str) -> tuple[QueryType, float]:
        """Rule-based query classification"""
        # Check for off-topic
        if not any(p in query for p in self.PEPTIDE_PATTERNS) and \
           not any(kw in query for kw in ["peptide", "peptides"]):
            # Might be off-topic, but give benefit of doubt
            pass

        # Check for sourcing (highest priority - needs careful handling)
        if any(kw in query for kw in self.SOURCING_KEYWORDS):
            return QueryType.SOURCING, 0.9

        # Check for safety
        if any(kw in query for kw in self.SAFETY_KEYWORDS):
            return QueryType.SAFETY, 0.85

        # Check for dosing
        if any(kw in query for kw in self.DOSING_KEYWORDS):
            return QueryType.DOSING, 0.85

        # Check for comparison
        if " vs " in query or " versus " in query or "compare" in query or "better" in query:
            return QueryType.COMPARISON, 0.8

        # Check for mechanism
        if "how does" in query or "mechanism" in query or "works" in query:
            return QueryType.MECHANISM, 0.8

        # Check for stacking
        if "stack" in query or "combine" in query or "together" in query:
            return QueryType.STACKING, 0.8

        # Check for preparation
        if "reconstitute" in query or "storage" in query or "prepare" in query:
            return QueryType.PREPARATION, 0.85

        # Check for experience
        if "experience" in query or "results" in query or "worked" in query:
            return QueryType.EXPERIENCE, 0.75

        # Check for research
        if "study" in query or "research" in query or "evidence" in query or "clinical" in query:
            return QueryType.RESEARCH, 0.8

        # Default to general
        return QueryType.GENERAL, 0.6

    def _assess_risk(self, query: str, query_type: QueryType) -> RiskLevel:
        """Assess risk level of responding"""
        # Blocked queries
        blocked_patterns = [
            "suicide", "kill myself", "overdose on purpose",
            "poison", "harm someone",
        ]
        if any(p in query for p in blocked_patterns):
            return RiskLevel.BLOCKED

        # High risk
        if query_type == QueryType.SOURCING:
            return RiskLevel.HIGH
        if query_type == QueryType.DOSING:
            return RiskLevel.HIGH

        # Medium risk
        if query_type in [QueryType.SAFETY, QueryType.STACKING]:
            return RiskLevel.MEDIUM

        # Low risk
        return RiskLevel.LOW

    def _get_disclaimer_types(
        self,
        query_type: QueryType,
        risk_level: RiskLevel,
        peptides: List[str]
    ) -> List[str]:
        """Determine which disclaimers to include"""
        disclaimers = []

        # Always include base disclaimer
        disclaimers.append("research_only")

        if risk_level in [RiskLevel.HIGH, RiskLevel.MEDIUM]:
            disclaimers.append("consult_professional")

        if query_type == QueryType.SOURCING:
            disclaimers.append("sourcing_legal")
            disclaimers.append("verify_source")

        if query_type == QueryType.DOSING:
            disclaimers.append("dosing_individual")

        if query_type == QueryType.SAFETY:
            disclaimers.append("side_effects")

        # Check FDA status of mentioned peptides
        # TODO: Look up actual FDA status
        disclaimers.append("fda_status")

        return disclaimers

    def _get_search_strategy(self, query_type: QueryType) -> str:
        """Determine search strategy based on query type"""
        if query_type == QueryType.RESEARCH:
            return "research_heavy"  # Weight research papers more
        if query_type == QueryType.EXPERIENCE:
            return "experience_heavy"  # Weight user journeys more
        if query_type in [QueryType.DOSING, QueryType.STACKING]:
            return "balanced"  # Both research and experience
        if query_type == QueryType.SOURCING:
            return "minimal"  # Limited search, mostly canned response
        return "balanced"

    def _generate_intent(self, query_type: QueryType, peptides: List[str]) -> str:
        """Generate intent description"""
        peptide_str = ", ".join(peptides) if peptides else "peptides"

        intents = {
            QueryType.RESEARCH: f"Seeking research information about {peptide_str}",
            QueryType.MECHANISM: f"Understanding how {peptide_str} works",
            QueryType.DOSING: f"Looking for dosing/protocol information for {peptide_str}",
            QueryType.COMPARISON: f"Comparing peptides or protocols",
            QueryType.SAFETY: f"Concerned about safety/side effects of {peptide_str}",
            QueryType.SOURCING: f"Looking for where to obtain {peptide_str}",
            QueryType.EXPERIENCE: f"Interested in user experiences with {peptide_str}",
            QueryType.STACKING: f"Interested in combining {peptide_str} with other peptides",
            QueryType.PREPARATION: f"Questions about preparing/storing {peptide_str}",
            QueryType.GENERAL: f"General questions about {peptide_str}",
            QueryType.OFF_TOPIC: "Question not related to peptides",
        }

        return intents.get(query_type, "General peptide inquiry")
