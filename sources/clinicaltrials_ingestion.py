"""
ClinicalTrials.gov Data Ingestion for Peptide AI

Fetches and processes clinical trial data for peptides:
- Active trials
- Completed trials with results
- Study designs and outcomes
"""

import asyncio
import logging
import httpx
from typing import List, Dict, Any, Optional
from datetime import datetime
from dataclasses import dataclass
import json

logger = logging.getLogger(__name__)


@dataclass
class ClinicalTrial:
    """Represents a clinical trial"""
    nct_id: str
    title: str
    brief_summary: str
    status: str  # Recruiting, Active, Completed, etc.
    phase: str
    conditions: List[str]
    interventions: List[str]
    start_date: Optional[str]
    completion_date: Optional[str]
    enrollment: Optional[int]
    sponsor: str
    locations: List[str]
    url: str
    peptides_mentioned: List[str]


class ClinicalTrialsIngestion:
    """
    Ingests peptide-related clinical trials from ClinicalTrials.gov API
    """

    BASE_URL = "https://clinicaltrials.gov/api/v2/studies"

    # Peptide search terms
    PEPTIDE_TERMS = [
        "BPC-157",
        "TB-500",
        "Thymosin alpha-1",
        "Thymosin beta-4",
        "Semaglutide",
        "Tirzepatide",
        "GHK-Cu",
        "Ipamorelin",
        "CJC-1295",
        "GHRP-6",
        "GHRP-2",
        "Melanotan",
        "PT-141",
        "Bremelanotide",
        "Epitalon",
        "Semax",
        "Selank",
        "LL-37",
        "Cathelicidin",
        "AOD-9604",
        "Tesamorelin",
        "Sermorelin",
        "MOTS-c",
        "SS-31",
        "Elamipretide",
        "growth hormone releasing peptide",
        "growth hormone secretagogue",
    ]

    def __init__(self):
        self.client = httpx.AsyncClient(timeout=30.0)

    async def search_trials(
        self,
        query: str,
        page_size: int = 50,
        status_filter: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """Search ClinicalTrials.gov for studies matching query"""
        params = {
            "query.term": query,
            "pageSize": page_size,
            "format": "json",
            "fields": "NCTId,BriefTitle,BriefSummary,OverallStatus,Phase,Condition,InterventionName,StartDate,CompletionDate,EnrollmentCount,LeadSponsorName,LocationCity,LocationCountry"
        }

        if status_filter:
            params["filter.overallStatus"] = ",".join(status_filter)

        try:
            response = await self.client.get(self.BASE_URL, params=params)
            response.raise_for_status()
            data = response.json()

            studies = data.get("studies", [])
            logger.info(f"Found {len(studies)} trials for '{query}'")
            return studies

        except Exception as e:
            logger.error(f"Error searching ClinicalTrials.gov for '{query}': {e}")
            return []

    def process_trial(self, study_data: Dict[str, Any], search_term: str) -> Optional[ClinicalTrial]:
        """Process a study into structured ClinicalTrial data"""
        try:
            protocol = study_data.get("protocolSection", {})
            id_module = protocol.get("identificationModule", {})
            status_module = protocol.get("statusModule", {})
            design_module = protocol.get("designModule", {})
            conditions_module = protocol.get("conditionsModule", {})
            interventions_module = protocol.get("armsInterventionsModule", {})
            sponsor_module = protocol.get("sponsorCollaboratorsModule", {})
            contacts_module = protocol.get("contactsLocationsModule", {})
            description_module = protocol.get("descriptionModule", {})

            nct_id = id_module.get("nctId", "")
            if not nct_id:
                return None

            # Extract interventions
            interventions = []
            for intervention in interventions_module.get("interventions", []):
                name = intervention.get("name", "")
                if name:
                    interventions.append(name)

            # Extract locations
            locations = []
            for location in contacts_module.get("locations", [])[:5]:
                city = location.get("city", "")
                country = location.get("country", "")
                if city or country:
                    locations.append(f"{city}, {country}".strip(", "))

            # Get lead sponsor
            sponsor = ""
            lead_sponsor = sponsor_module.get("leadSponsor", {})
            if lead_sponsor:
                sponsor = lead_sponsor.get("name", "")

            return ClinicalTrial(
                nct_id=nct_id,
                title=id_module.get("briefTitle", ""),
                brief_summary=description_module.get("briefSummary", ""),
                status=status_module.get("overallStatus", ""),
                phase=", ".join(design_module.get("phases", [])),
                conditions=conditions_module.get("conditions", []),
                interventions=interventions,
                start_date=status_module.get("startDateStruct", {}).get("date"),
                completion_date=status_module.get("completionDateStruct", {}).get("date"),
                enrollment=design_module.get("enrollmentInfo", {}).get("count"),
                sponsor=sponsor,
                locations=locations,
                url=f"https://clinicaltrials.gov/study/{nct_id}",
                peptides_mentioned=[search_term],
            )

        except Exception as e:
            logger.error(f"Error processing trial: {e}")
            return None

    async def ingest_all_peptides(self) -> List[ClinicalTrial]:
        """Ingest clinical trials for all peptide terms"""
        all_trials = []
        seen_nct_ids = set()

        for term in self.PEPTIDE_TERMS:
            logger.info(f"Searching trials for: {term}")

            # Search all statuses
            studies = await self.search_trials(term)

            for study in studies:
                trial = self.process_trial(study, term)
                if trial and trial.nct_id not in seen_nct_ids:
                    all_trials.append(trial)
                    seen_nct_ids.add(trial.nct_id)

            # Rate limiting
            await asyncio.sleep(0.5)

        logger.info(f"Total unique trials found: {len(all_trials)}")
        return all_trials

    def to_weaviate_format(self, trial: ClinicalTrial) -> Dict[str, Any]:
        """Convert ClinicalTrial to Weaviate document format"""
        content = f"""
Trial: {trial.title}

Status: {trial.status}
Phase: {trial.phase}
Enrollment: {trial.enrollment or 'Not specified'}
Sponsor: {trial.sponsor}

Conditions: {', '.join(trial.conditions)}
Interventions: {', '.join(trial.interventions)}

Summary: {trial.brief_summary}
"""

        return {
            'title': trial.title,
            'content': content.strip(),
            'source_type': 'clinical_trial',
            'url': trial.url,
            'citation': f"ClinicalTrials.gov {trial.nct_id} - {trial.status}",
            'peptides': trial.peptides_mentioned,
            'metadata': {
                'nct_id': trial.nct_id,
                'status': trial.status,
                'phase': trial.phase,
                'enrollment': trial.enrollment,
                'sponsor': trial.sponsor,
                'conditions': trial.conditions,
                'start_date': trial.start_date,
                'completion_date': trial.completion_date,
            }
        }

    async def close(self):
        """Close the HTTP client"""
        await self.client.aclose()


async def run_clinical_trials_ingestion():
    """Run the clinical trials ingestion pipeline"""
    ingestion = ClinicalTrialsIngestion()

    try:
        trials = await ingestion.ingest_all_peptides()

        # Convert to Weaviate format
        documents = [ingestion.to_weaviate_format(t) for t in trials]

        # Save to file for inspection
        with open('clinical_trials_data.json', 'w') as f:
            json.dump(documents, f, indent=2, default=str)

        logger.info(f"Saved {len(documents)} trial documents to clinical_trials_data.json")

        # Print summary
        statuses = {}
        for trial in trials:
            status = trial.status
            statuses[status] = statuses.get(status, 0) + 1

        logger.info("Trial status breakdown:")
        for status, count in sorted(statuses.items(), key=lambda x: -x[1]):
            logger.info(f"  {status}: {count}")

        return documents

    finally:
        await ingestion.close()


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    asyncio.run(run_clinical_trials_ingestion())
