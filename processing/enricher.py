"""
Peptide AI - Document Enricher

Enriches chunks with:
- Peptide name extraction (NER)
- FDA status lookup
- Condition extraction
"""

import re
import logging
from typing import List, Set

from models.documents import ProcessedChunk, FDAStatus

logger = logging.getLogger(__name__)


class PeptideEnricher:
    """
    Enriches document chunks with peptide-specific metadata

    Extracts:
    - Peptide names mentioned
    - FDA approval status
    - Medical conditions
    """

    # Peptide name patterns and their canonical forms
    PEPTIDE_PATTERNS = {
        # BPC-157 variants
        r"\b(?:bpc[- ]?157|body protective compound[- ]?157)\b": "BPC-157",

        # TB-500 / Thymosin Beta-4
        r"\b(?:tb[- ]?500|thymosin[- ]?beta[- ]?4|tβ4)\b": "TB-500",

        # GLP-1 agonists
        r"\bsemaglutide\b": "Semaglutide",
        r"\b(?:ozempic|wegovy|rybelsus)\b": "Semaglutide",
        r"\btirzepatide\b": "Tirzepatide",
        r"\b(?:mounjaro|zepbound)\b": "Tirzepatide",
        r"\bliraglutide\b": "Liraglutide",
        r"\b(?:victoza|saxenda)\b": "Liraglutide",

        # Growth hormone secretagogues
        r"\bipamorelin\b": "Ipamorelin",
        r"\b(?:cjc[- ]?1295|mod[- ]?grf)\b": "CJC-1295",
        r"\bghrp[- ]?6\b": "GHRP-6",
        r"\bghrp[- ]?2\b": "GHRP-2",
        r"\bsermorelin\b": "Sermorelin",
        r"\btesamorelin\b": "Tesamorelin",
        r"\bhexarelin\b": "Hexarelin",

        # Melanocortins
        r"\b(?:melanotan[- ]?(?:ii|2)|mt[- ]?(?:ii|2))\b": "Melanotan II",
        r"\b(?:pt[- ]?141|bremelanotide)\b": "PT-141",

        # Copper peptides
        r"\b(?:ghk[- ]?cu|copper peptide)\b": "GHK-Cu",

        # Nootropics
        r"\bsemax\b": "Semax",
        r"\bselank\b": "Selank",
        r"\bdihexa\b": "Dihexa",
        r"\b(?:p21|cerebrolysin)\b": "Cerebrolysin",

        # Longevity
        r"\b(?:epitalon|epithalon)\b": "Epitalon",
        r"\b(?:mots[- ]?c)\b": "MOTS-c",
        r"\b(?:ss[- ]?31|elamipretide)\b": "SS-31",

        # IGF/MGF
        r"\b(?:igf[- ]?1(?:[- ]?lr3)?)\b": "IGF-1",
        r"\b(?:mgf|mechano[- ]?growth[- ]?factor)\b": "MGF",

        # Others
        r"\b(?:aod[- ]?9604)\b": "AOD-9604",
        r"\bfollistatin\b": "Follistatin",
        r"\b(?:ll[- ]?37|cathelicidin)\b": "LL-37",
        r"\bkisspeptin\b": "Kisspeptin",
        r"\bpentosan\b": "Pentosan",
        r"\b(?:bpc|body protective compound)\b": "BPC-157",
        r"\bthymosin\b": "Thymosin",
    }

    # FDA status for known peptides
    FDA_STATUS = {
        # FDA Approved
        "Semaglutide": FDAStatus.APPROVED,
        "Tirzepatide": FDAStatus.APPROVED,
        "Liraglutide": FDAStatus.APPROVED,
        "Tesamorelin": FDAStatus.APPROVED,
        "Sermorelin": FDAStatus.APPROVED,
        "PT-141": FDAStatus.APPROVED,  # Vyleesi for HSDD

        # In clinical trials
        "BPC-157": FDAStatus.INVESTIGATIONAL,
        "TB-500": FDAStatus.INVESTIGATIONAL,

        # Research only / Not approved
        "Ipamorelin": FDAStatus.NOT_APPROVED,
        "CJC-1295": FDAStatus.NOT_APPROVED,
        "GHRP-6": FDAStatus.NOT_APPROVED,
        "GHRP-2": FDAStatus.NOT_APPROVED,
        "Hexarelin": FDAStatus.NOT_APPROVED,
        "Melanotan II": FDAStatus.NOT_APPROVED,
        "GHK-Cu": FDAStatus.NOT_APPROVED,
        "Semax": FDAStatus.NOT_APPROVED,  # Approved in Russia
        "Selank": FDAStatus.NOT_APPROVED,  # Approved in Russia
        "Dihexa": FDAStatus.NOT_APPROVED,
        "Epitalon": FDAStatus.NOT_APPROVED,
        "MOTS-c": FDAStatus.INVESTIGATIONAL,
        "SS-31": FDAStatus.TRIAL,
        "IGF-1": FDAStatus.NOT_APPROVED,  # Mecasermin is approved but different
        "MGF": FDAStatus.NOT_APPROVED,
        "AOD-9604": FDAStatus.NOT_APPROVED,
        "Follistatin": FDAStatus.NOT_APPROVED,
        "LL-37": FDAStatus.INVESTIGATIONAL,
        "Kisspeptin": FDAStatus.INVESTIGATIONAL,
    }

    # Medical condition patterns
    CONDITION_PATTERNS = {
        r"\b(?:wound|injury|healing|tissue repair)\b": "healing",
        r"\b(?:tendon|tendinitis|tendinopathy)\b": "tendon injury",
        r"\b(?:muscle|muscular|hypertrophy)\b": "muscle",
        r"\b(?:fat loss|weight loss|obesity|adipose)\b": "weight loss",
        r"\b(?:diabetes|diabetic|glycemic|insulin)\b": "diabetes",
        r"\b(?:sleep|insomnia|circadian)\b": "sleep",
        r"\b(?:cognitive|memory|learning|brain)\b": "cognitive",
        r"\b(?:anxiety|anxiolytic)\b": "anxiety",
        r"\b(?:depression|depressive|mood)\b": "mood",
        r"\b(?:skin|dermal|collagen|wrinkle)\b": "skin",
        r"\b(?:hair|alopecia|follicle)\b": "hair",
        r"\b(?:aging|longevity|senescence)\b": "aging",
        r"\b(?:gut|intestinal|gastric|ibs|ibd)\b": "gut health",
        r"\b(?:inflammation|inflammatory|anti-inflammatory)\b": "inflammation",
        r"\b(?:immune|immunity|immunomodulat)\b": "immune",
        r"\b(?:sexual|libido|erectile)\b": "sexual health",
        r"\b(?:energy|fatigue|mitochondr)\b": "energy",
        r"\b(?:recovery|regenerat|repair)\b": "recovery",
        r"\b(?:pain|analges|nocicepti)\b": "pain",
        r"\b(?:neuroprotect|neurodegenerat)\b": "neuroprotection",
        r"\b(?:cardio|heart|vascular)\b": "cardiovascular",
        r"\b(?:bone|osteo|fracture)\b": "bone health",
    }

    def __init__(self):
        # Compile patterns for efficiency
        self._peptide_regex = {
            re.compile(pattern, re.IGNORECASE): name
            for pattern, name in self.PEPTIDE_PATTERNS.items()
        }
        self._condition_regex = {
            re.compile(pattern, re.IGNORECASE): condition
            for pattern, condition in self.CONDITION_PATTERNS.items()
        }

    def enrich(self, chunk: ProcessedChunk) -> ProcessedChunk:
        """
        Enrich a chunk with extracted metadata

        Modifies the chunk in place and returns it.
        """
        content = chunk.content.lower()

        # Extract peptides
        peptides = self._extract_peptides(content)
        chunk.peptides_mentioned = list(peptides)

        # Determine FDA status (use most restrictive if multiple peptides)
        chunk.fda_status = self._get_fda_status(peptides)

        # Extract conditions
        conditions = self._extract_conditions(content)
        chunk.conditions_mentioned = list(conditions)

        return chunk

    def enrich_batch(self, chunks: List[ProcessedChunk]) -> List[ProcessedChunk]:
        """Enrich multiple chunks"""
        return [self.enrich(chunk) for chunk in chunks]

    def _extract_peptides(self, text: str) -> Set[str]:
        """Extract peptide names from text"""
        found = set()

        for pattern, name in self._peptide_regex.items():
            if pattern.search(text):
                found.add(name)

        return found

    def _extract_conditions(self, text: str) -> Set[str]:
        """Extract medical conditions from text"""
        found = set()

        for pattern, condition in self._condition_regex.items():
            if pattern.search(text):
                found.add(condition)

        return found

    def _get_fda_status(self, peptides: Set[str]) -> FDAStatus:
        """
        Get FDA status based on peptides mentioned

        Uses the most restrictive status if multiple peptides.
        """
        if not peptides:
            return FDAStatus.UNKNOWN

        statuses = [
            self.FDA_STATUS.get(p, FDAStatus.UNKNOWN)
            for p in peptides
        ]

        # Priority order (most restrictive first)
        priority = [
            FDAStatus.BANNED_COMPOUNDING,
            FDAStatus.NOT_APPROVED,
            FDAStatus.INVESTIGATIONAL,
            FDAStatus.TRIAL,
            FDAStatus.APPROVED,
            FDAStatus.UNKNOWN,
        ]

        for status in priority:
            if status in statuses:
                return status

        return FDAStatus.UNKNOWN
