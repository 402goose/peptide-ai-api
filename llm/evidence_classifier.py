"""
Peptide AI - Evidence Quality Classifier

Classifies the evidence quality for peptides to show users
how strong the research backing is.

Evidence Levels:
- 🟢 STRONG: Multiple human RCTs, FDA-approved indications
- 🟡 MODERATE: Small human studies, large animal studies
- 🔴 LIMITED: Animal studies only, in-vitro only
- ⚪ ANECDOTAL: User reports, forum discussions only
"""

from enum import Enum
from typing import Dict, List, Optional
from dataclasses import dataclass


class EvidenceLevel(str, Enum):
    STRONG = "strong"           # 🟢 Human RCTs, FDA-approved
    MODERATE = "moderate"       # 🟡 Small human studies + animal
    LIMITED = "limited"         # 🔴 Animal/in-vitro only
    ANECDOTAL = "anecdotal"     # ⚪ User reports only
    UNKNOWN = "unknown"         # No data


@dataclass
class PeptideEvidence:
    """Evidence summary for a peptide"""
    peptide: str
    level: EvidenceLevel
    human_studies: int
    animal_studies: int
    in_vitro_studies: int
    anecdotal_reports: int
    fda_status: str
    summary: str
    key_studies: List[str]


# Evidence database for common peptides
# This would ideally be populated from actual research data
PEPTIDE_EVIDENCE_DB: Dict[str, PeptideEvidence] = {
    "BPC-157": PeptideEvidence(
        peptide="BPC-157",
        level=EvidenceLevel.MODERATE,
        human_studies=2,
        animal_studies=100,
        in_vitro_studies=50,
        anecdotal_reports=10000,
        fda_status="Not FDA approved",
        summary="Strong animal data for tissue healing, limited human trials",
        key_studies=[
            "Sikiric et al. (2013) - Rat tendon healing",
            "Sikiric et al. (2018) - Comprehensive review",
            "ClinicalTrials.gov NCT04150666 - IBD trial (ongoing)"
        ]
    ),
    "TB-500": PeptideEvidence(
        peptide="TB-500",
        level=EvidenceLevel.LIMITED,
        human_studies=0,
        animal_studies=40,
        in_vitro_studies=30,
        anecdotal_reports=5000,
        fda_status="Not FDA approved",
        summary="Animal data for wound healing, NO human trials",
        key_studies=[
            "Philp et al. (2004) - Wound healing in mice",
            "Sosne et al. (2012) - Corneal healing"
        ]
    ),
    "Semaglutide": PeptideEvidence(
        peptide="Semaglutide",
        level=EvidenceLevel.STRONG,
        human_studies=200,
        animal_studies=50,
        in_vitro_studies=100,
        anecdotal_reports=50000,
        fda_status="FDA approved (Ozempic, Wegovy)",
        summary="Extensive human RCTs, FDA-approved for diabetes and obesity",
        key_studies=[
            "STEP 1-5 Trials - Weight loss efficacy",
            "SUSTAIN Trials - Diabetes outcomes",
            "PIONEER Trials - Oral formulation"
        ]
    ),
    "Tirzepatide": PeptideEvidence(
        peptide="Tirzepatide",
        level=EvidenceLevel.STRONG,
        human_studies=50,
        animal_studies=20,
        in_vitro_studies=30,
        anecdotal_reports=20000,
        fda_status="FDA approved (Mounjaro, Zepbound)",
        summary="Strong RCT data, FDA-approved for diabetes and obesity",
        key_studies=[
            "SURMOUNT Trials - Weight loss",
            "SURPASS Trials - Diabetes"
        ]
    ),
    "GHK-Cu": PeptideEvidence(
        peptide="GHK-Cu",
        level=EvidenceLevel.MODERATE,
        human_studies=10,
        animal_studies=30,
        in_vitro_studies=60,
        anecdotal_reports=3000,
        fda_status="Not FDA approved (in cosmetics)",
        summary="Human studies for skin/wound healing, mostly topical",
        key_studies=[
            "Pickart et al. (2012) - Skin remodeling",
            "Multiple cosmetic studies"
        ]
    ),
    "Ipamorelin": PeptideEvidence(
        peptide="Ipamorelin",
        level=EvidenceLevel.MODERATE,
        human_studies=5,
        animal_studies=20,
        in_vitro_studies=15,
        anecdotal_reports=8000,
        fda_status="Not FDA approved",
        summary="Limited human data, primarily GH secretagogue studies",
        key_studies=[
            "Raun et al. (1998) - GH release",
            "Phase I/II trials for GH deficiency"
        ]
    ),
    "CJC-1295": PeptideEvidence(
        peptide="CJC-1295",
        level=EvidenceLevel.MODERATE,
        human_studies=3,
        animal_studies=15,
        in_vitro_studies=10,
        anecdotal_reports=6000,
        fda_status="Not FDA approved",
        summary="Few human studies showing GH elevation",
        key_studies=[
            "Teichman et al. (2006) - GH release in humans"
        ]
    ),
    "Epitalon": PeptideEvidence(
        peptide="Epitalon",
        level=EvidenceLevel.LIMITED,
        human_studies=0,
        animal_studies=20,
        in_vitro_studies=30,
        anecdotal_reports=2000,
        fda_status="Not FDA approved",
        summary="Russian research on telomeres, no Western human trials",
        key_studies=[
            "Khavinson et al. - Telomerase activation (Russian literature)"
        ]
    ),
    "Semax": PeptideEvidence(
        peptide="Semax",
        level=EvidenceLevel.MODERATE,
        human_studies=15,
        animal_studies=40,
        in_vitro_studies=20,
        anecdotal_reports=4000,
        fda_status="Approved in Russia, not FDA approved",
        summary="Russian human studies for stroke/cognitive, not FDA approved",
        key_studies=[
            "Russian clinical trials for stroke",
            "Ashmarin et al. - Cognitive effects"
        ]
    ),
    "Selank": PeptideEvidence(
        peptide="Selank",
        level=EvidenceLevel.MODERATE,
        human_studies=10,
        animal_studies=30,
        in_vitro_studies=15,
        anecdotal_reports=3000,
        fda_status="Approved in Russia, not FDA approved",
        summary="Russian human studies for anxiety, not FDA approved",
        key_studies=[
            "Russian clinical trials for anxiety"
        ]
    ),
    "PT-141": PeptideEvidence(
        peptide="PT-141",
        level=EvidenceLevel.STRONG,
        human_studies=30,
        animal_studies=20,
        in_vitro_studies=10,
        anecdotal_reports=5000,
        fda_status="FDA approved (Vyleesi)",
        summary="FDA-approved for female HSDD",
        key_studies=[
            "RECONNECT trials - Female sexual dysfunction"
        ]
    ),
    "AOD-9604": PeptideEvidence(
        peptide="AOD-9604",
        level=EvidenceLevel.LIMITED,
        human_studies=2,
        animal_studies=10,
        in_vitro_studies=5,
        anecdotal_reports=2000,
        fda_status="Not FDA approved",
        summary="Failed Phase 2 trial for weight loss, limited evidence",
        key_studies=[
            "Metabolic Pharmaceuticals trials (discontinued)"
        ]
    ),
    "LL-37": PeptideEvidence(
        peptide="LL-37",
        level=EvidenceLevel.LIMITED,
        human_studies=1,
        animal_studies=30,
        in_vitro_studies=50,
        anecdotal_reports=1000,
        fda_status="Not FDA approved",
        summary="Antimicrobial peptide, mostly in-vitro research",
        key_studies=[
            "Antimicrobial activity studies"
        ]
    ),
    "MOTS-c": PeptideEvidence(
        peptide="MOTS-c",
        level=EvidenceLevel.LIMITED,
        human_studies=1,
        animal_studies=15,
        in_vitro_studies=20,
        anecdotal_reports=500,
        fda_status="Not FDA approved",
        summary="Emerging research on mitochondrial function",
        key_studies=[
            "Lee et al. (2015) - Metabolic homeostasis"
        ]
    ),
    "SS-31": PeptideEvidence(
        peptide="SS-31",
        level=EvidenceLevel.MODERATE,
        human_studies=10,
        animal_studies=40,
        in_vitro_studies=30,
        anecdotal_reports=500,
        fda_status="Investigational (Elamipretide)",
        summary="Clinical trials for mitochondrial disease",
        key_studies=[
            "Stealth BioTherapeutics trials - Barth syndrome"
        ]
    ),
    "Melanotan II": PeptideEvidence(
        peptide="Melanotan II",
        level=EvidenceLevel.LIMITED,
        human_studies=3,
        animal_studies=15,
        in_vitro_studies=10,
        anecdotal_reports=10000,
        fda_status="Not FDA approved, banned in many countries",
        summary="Limited human data, significant safety concerns",
        key_studies=[
            "Early tanning studies (discontinued)"
        ]
    ),
    "Thymosin Alpha-1": PeptideEvidence(
        peptide="Thymosin Alpha-1",
        level=EvidenceLevel.STRONG,
        human_studies=50,
        animal_studies=30,
        in_vitro_studies=40,
        anecdotal_reports=2000,
        fda_status="Approved in 35+ countries, not FDA approved",
        summary="Extensive clinical use for HBV/HCV, immune modulation",
        key_studies=[
            "Multiple Hepatitis B/C trials",
            "Cancer immunotherapy trials"
        ]
    ),
    "GHRP-6": PeptideEvidence(
        peptide="GHRP-6",
        level=EvidenceLevel.MODERATE,
        human_studies=5,
        animal_studies=25,
        in_vitro_studies=15,
        anecdotal_reports=7000,
        fda_status="Not FDA approved",
        summary="GH-releasing peptide, limited human data",
        key_studies=["Bowers et al. - GH release studies"]
    ),
    "GHRP-2": PeptideEvidence(
        peptide="GHRP-2",
        level=EvidenceLevel.MODERATE,
        human_studies=8,
        animal_studies=20,
        in_vitro_studies=15,
        anecdotal_reports=6000,
        fda_status="Not FDA approved",
        summary="GH-releasing peptide, more potent than GHRP-6",
        key_studies=["Multiple GH secretagogue studies"]
    ),
    "Dihexa": PeptideEvidence(
        peptide="Dihexa",
        level=EvidenceLevel.LIMITED,
        human_studies=0,
        animal_studies=10,
        in_vitro_studies=15,
        anecdotal_reports=1500,
        fda_status="Not FDA approved",
        summary="Cognitive peptide, animal studies only",
        key_studies=["McCoy et al. - Cognitive enhancement in rats"]
    ),
    "KPV": PeptideEvidence(
        peptide="KPV",
        level=EvidenceLevel.LIMITED,
        human_studies=0,
        animal_studies=10,
        in_vitro_studies=20,
        anecdotal_reports=500,
        fda_status="Not FDA approved",
        summary="Anti-inflammatory peptide from alpha-MSH",
        key_studies=["Inflammation studies in vitro"]
    ),
    "Larazotide": PeptideEvidence(
        peptide="Larazotide",
        level=EvidenceLevel.MODERATE,
        human_studies=15,
        animal_studies=20,
        in_vitro_studies=10,
        anecdotal_reports=1000,
        fda_status="Investigational (Phase 3 trials)",
        summary="Tight junction modulator for celiac disease",
        key_studies=["Phase 3 celiac disease trials"]
    ),
    "DSIP": PeptideEvidence(
        peptide="DSIP",
        level=EvidenceLevel.LIMITED,
        human_studies=5,
        animal_studies=30,
        in_vitro_studies=10,
        anecdotal_reports=2000,
        fda_status="Not FDA approved",
        summary="Sleep-promoting peptide, limited human data",
        key_studies=["Graf et al. - Sleep pattern studies"]
    ),
    "Kisspeptin": PeptideEvidence(
        peptide="Kisspeptin",
        level=EvidenceLevel.MODERATE,
        human_studies=30,
        animal_studies=50,
        in_vitro_studies=40,
        anecdotal_reports=500,
        fda_status="Investigational",
        summary="Key reproductive hormone regulator",
        key_studies=["Multiple fertility trials", "Endocrinology studies"]
    ),
    "Humanin": PeptideEvidence(
        peptide="Humanin",
        level=EvidenceLevel.LIMITED,
        human_studies=2,
        animal_studies=25,
        in_vitro_studies=30,
        anecdotal_reports=300,
        fda_status="Not FDA approved",
        summary="Mitochondrial peptide, neuroprotective research",
        key_studies=["Alzheimer's disease models"]
    ),
    "5-Amino 1MQ": PeptideEvidence(
        peptide="5-Amino 1MQ",
        level=EvidenceLevel.LIMITED,
        human_studies=0,
        animal_studies=5,
        in_vitro_studies=10,
        anecdotal_reports=500,
        fda_status="Not FDA approved",
        summary="NNMT inhibitor, fat loss research",
        key_studies=["Obesity research in mice"]
    ),
    "P21": PeptideEvidence(
        peptide="P21",
        level=EvidenceLevel.LIMITED,
        human_studies=0,
        animal_studies=8,
        in_vitro_studies=5,
        anecdotal_reports=300,
        fda_status="Not FDA approved",
        summary="CNTF-derived peptide, neurogenesis research",
        key_studies=["Neurogenesis studies in mice"]
    ),
    "Tesamorelin": PeptideEvidence(
        peptide="Tesamorelin",
        level=EvidenceLevel.STRONG,
        human_studies=40,
        animal_studies=15,
        in_vitro_studies=10,
        anecdotal_reports=3000,
        fda_status="FDA approved (Egrifta)",
        summary="FDA-approved for HIV lipodystrophy",
        key_studies=["HIV lipodystrophy trials"]
    ),
    "Sermorelin": PeptideEvidence(
        peptide="Sermorelin",
        level=EvidenceLevel.STRONG,
        human_studies=30,
        animal_studies=20,
        in_vitro_studies=15,
        anecdotal_reports=8000,
        fda_status="FDA approved (pediatric GH deficiency)",
        summary="FDA-approved for GH deficiency in children",
        key_studies=["Pediatric growth hormone trials"]
    ),
    "NA-Selank": PeptideEvidence(
        peptide="NA-Selank",
        level=EvidenceLevel.LIMITED,
        human_studies=0,
        animal_studies=5,
        in_vitro_studies=5,
        anecdotal_reports=500,
        fda_status="Not FDA approved",
        summary="Acetylated Selank variant, limited research",
        key_studies=["Modified from Selank studies"]
    ),
    "SR9009": PeptideEvidence(
        peptide="SR9009",
        level=EvidenceLevel.LIMITED,
        human_studies=0,
        animal_studies=15,
        in_vitro_studies=20,
        anecdotal_reports=3000,
        fda_status="Not FDA approved",
        summary="Rev-ErbA agonist, not a true peptide",
        key_studies=["Solt et al. - Metabolic studies"]
    ),
}


def get_evidence_for_peptide(peptide_name: str) -> PeptideEvidence:
    """Get evidence summary for a peptide"""
    # Normalize the name
    normalized = peptide_name.strip().upper().replace(" ", "-").replace("_", "-")

    # Check for known variants
    name_mappings = {
        "BPC157": "BPC-157",
        "TB500": "TB-500",
        "TB4": "TB-500",
        "THYMOSIN-BETA-4": "TB-500",
        "GHKCU": "GHK-Cu",
        "GHK": "GHK-Cu",
        "CJC1295": "CJC-1295",
        "OZEMPIC": "Semaglutide",
        "WEGOVY": "Semaglutide",
        "RYBELSUS": "Semaglutide",
        "MOUNJARO": "Tirzepatide",
        "ZEPBOUND": "Tirzepatide",
        "PT141": "PT-141",
        "PT-141": "PT-141",
        "VYLEESI": "PT-141",
        "BREMELANOTIDE": "PT-141",
        "AOD9604": "AOD-9604",
        "LL37": "LL-37",
        "SS31": "SS-31",
        "ELAMIPRETIDE": "SS-31",
        "MOTSC": "MOTS-c",
        "MT2": "Melanotan II",
        "MTII": "Melanotan II",
        "MELANOTAN": "Melanotan II",
        "TA1": "Thymosin Alpha-1",
        "THYMOSIN-ALPHA-1": "Thymosin Alpha-1",
        "ZADAXIN": "Thymosin Alpha-1",
        "GHRP6": "GHRP-6",
        "GHRP2": "GHRP-2",
        "EGRIFTA": "Tesamorelin",
        "GEREF": "Sermorelin",
        "5-AMINO-1MQ": "5-Amino 1MQ",
        "5AMINO1MQ": "5-Amino 1MQ",
        "NA-SELANK": "NA-Selank",
        "NASELANK": "NA-Selank",
    }

    if normalized in name_mappings:
        normalized = name_mappings[normalized]

    # Look up in database
    for key, evidence in PEPTIDE_EVIDENCE_DB.items():
        if key.upper() == normalized or normalized in key.upper():
            return evidence

    # Return unknown if not found
    return PeptideEvidence(
        peptide=peptide_name,
        level=EvidenceLevel.UNKNOWN,
        human_studies=0,
        animal_studies=0,
        in_vitro_studies=0,
        anecdotal_reports=0,
        fda_status="Unknown",
        summary="No evidence data available for this peptide",
        key_studies=[]
    )


def get_evidence_badge(level: EvidenceLevel) -> str:
    """Get emoji badge for evidence level"""
    badges = {
        EvidenceLevel.STRONG: "🟢 Strong Evidence",
        EvidenceLevel.MODERATE: "🟡 Moderate Evidence",
        EvidenceLevel.LIMITED: "🔴 Limited Evidence",
        EvidenceLevel.ANECDOTAL: "⚪ Anecdotal Only",
        EvidenceLevel.UNKNOWN: "❓ Unknown",
    }
    return badges.get(level, "❓ Unknown")


def format_evidence_summary(evidence: PeptideEvidence) -> str:
    """Format evidence summary for display"""
    badge = get_evidence_badge(evidence.level)

    lines = [
        f"**Evidence Level:** {badge}",
        f"- Human studies: {evidence.human_studies}",
        f"- Animal studies: {evidence.animal_studies}",
        f"- FDA Status: {evidence.fda_status}",
        f"- Summary: {evidence.summary}",
    ]

    if evidence.key_studies:
        lines.append("- Key studies: " + "; ".join(evidence.key_studies[:2]))

    return "\n".join(lines)


def enrich_context_with_evidence(peptides: List[str]) -> str:
    """Generate evidence context for multiple peptides"""
    if not peptides:
        return ""

    sections = ["## EVIDENCE QUALITY FOR MENTIONED PEPTIDES\n"]

    for peptide in peptides:
        evidence = get_evidence_for_peptide(peptide)
        badge = get_evidence_badge(evidence.level)
        sections.append(f"### {peptide}: {badge}")
        sections.append(f"- Human trials: {evidence.human_studies}")
        sections.append(f"- Animal studies: {evidence.animal_studies}")
        sections.append(f"- FDA: {evidence.fda_status}")
        sections.append(f"- {evidence.summary}")
        sections.append("")

    return "\n".join(sections)
