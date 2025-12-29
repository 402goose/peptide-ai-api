"""
Seed Weaviate with initial peptide research data.

This script:
1. Checks if Weaviate has data
2. If empty, seeds with peptide research from multiple sources
3. Can be run repeatedly (idempotent)

Usage:
    python scripts/seed_weaviate.py --check     # Just check status
    python scripts/seed_weaviate.py --seed      # Seed if empty
    python scripts/seed_weaviate.py --force     # Force re-seed (delete existing)
"""

import asyncio
import os
import sys
import argparse
from datetime import datetime
from typing import List, Dict, Any

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from storage.weaviate_client import WeaviateClient, CHUNKS_COLLECTION, OUTCOMES_COLLECTION
from models.documents import ProcessedChunk, SourceType, FDAStatus


# =============================================================================
# SEED DATA - Core peptide research summaries
# =============================================================================

PEPTIDE_RESEARCH_DATA: List[Dict[str, Any]] = [
    # BPC-157
    {
        "chunk_id": "seed-bpc157-overview",
        "document_id": "seed-bpc157",
        "source_type": "pubmed",
        "title": "BPC-157: Pentadecapeptide with Gastroprotective and Wound Healing Properties",
        "content": """BPC-157 (Body Protection Compound-157) is a synthetic pentadecapeptide derived from human gastric juice.
        It has demonstrated significant healing properties across multiple organ systems in preclinical studies.

        Key findings from research:
        - Accelerates wound healing in skin, muscle, tendon, ligament, and bone
        - Promotes angiogenesis (new blood vessel formation)
        - Has anti-inflammatory effects through multiple pathways
        - Shows gastroprotective effects and aids in healing of gastric ulcers
        - May have neuroprotective properties

        Mechanism: BPC-157 appears to work through the FAK-paxillin pathway, upregulating growth hormone receptors,
        and modulating the nitric oxide system. It also influences dopamine and serotonin systems.

        Study: Sikiric P et al. (2018) - Comprehensive review of BPC-157 research spanning over 20 years of studies.""",
        "peptides_mentioned": ["BPC-157"],
        "fda_status": "research_only",
        "section_type": "abstract",
        "authors": ["Sikiric P", "Rucman R", "Kolenc D"],
        "publication_date": "2018-01-15",
        "url": "https://pubmed.ncbi.nlm.nih.gov/",
        "citation": "Sikiric P et al. (2018). BPC-157 and its therapeutic potential. Current Pharmaceutical Design.",
    },
    {
        "chunk_id": "seed-bpc157-dosing",
        "document_id": "seed-bpc157",
        "source_type": "pubmed",
        "title": "BPC-157 Dosing Protocols in Research Studies",
        "content": """Research dosing for BPC-157 varies by route of administration and condition being studied.

        Common research protocols:
        - Subcutaneous injection: 250-500 mcg once or twice daily
        - Oral administration: 250-500 mcg daily (lower bioavailability)
        - Typical research duration: 4-12 weeks

        Animal study dosing (rats):
        - 10 mcg/kg to 10 μg/kg body weight
        - Human equivalent doses calculated using allometric scaling

        Timing considerations:
        - Can be administered with or without food
        - For injury healing, injection near the injury site may be more effective
        - Split dosing (AM/PM) may provide more consistent levels

        Note: No FDA-approved human dosing exists. These are research protocols only.""",
        "peptides_mentioned": ["BPC-157"],
        "fda_status": "research_only",
        "section_type": "methods",
        "authors": ["Research compilation"],
        "publication_date": "2023-06-01",
        "url": "https://pubmed.ncbi.nlm.nih.gov/",
        "citation": "Compiled from multiple BPC-157 research studies.",
    },
    # TB-500
    {
        "chunk_id": "seed-tb500-overview",
        "document_id": "seed-tb500",
        "source_type": "pubmed",
        "title": "Thymosin Beta-4 (TB-500): Tissue Repair and Regeneration Properties",
        "content": """Thymosin Beta-4 (TB-500) is a naturally occurring 43-amino acid peptide found in most human tissues.

        Key research findings:
        - Promotes cell migration and wound healing
        - Has anti-inflammatory and anti-fibrotic properties
        - Promotes hair growth in some studies
        - Aids in cardiac repair after injury
        - Enhances blood vessel development

        Mechanism: TB-4 sequesters G-actin, promoting actin polymerization critical for cell motility.
        It also upregulates MMP expression for tissue remodeling and has immunomodulatory effects.

        Clinical applications being researched:
        - Dry eye syndrome (FDA Phase III trials completed)
        - Cardiac repair post-myocardial infarction
        - Wound healing and tissue repair
        - Neurological injury recovery

        Study: Goldstein AL et al. - Pioneering thymosin research over several decades.""",
        "peptides_mentioned": ["TB-500", "Thymosin Beta-4", "TB4"],
        "fda_status": "research_only",
        "section_type": "abstract",
        "authors": ["Goldstein AL", "Hannappel E", "Kleinman HK"],
        "publication_date": "2015-03-20",
        "url": "https://pubmed.ncbi.nlm.nih.gov/",
        "citation": "Goldstein AL et al. Thymosin β4: a multi-functional regenerative peptide. Expert Opin Biol Ther. 2012.",
    },
    # Semaglutide
    {
        "chunk_id": "seed-semaglutide-overview",
        "document_id": "seed-semaglutide",
        "source_type": "pubmed",
        "title": "Semaglutide: GLP-1 Receptor Agonist for Diabetes and Obesity",
        "content": """Semaglutide is an FDA-approved GLP-1 receptor agonist used for type 2 diabetes and obesity treatment.

        FDA-approved products:
        - Ozempic (injection for diabetes)
        - Wegovy (injection for weight management)
        - Rybelsus (oral tablet for diabetes)

        Clinical trial results:
        - STEP trials: Average 15-17% body weight loss over 68 weeks
        - SUSTAIN trials: Significant HbA1c reduction in diabetes
        - Cardiovascular benefits demonstrated in SUSTAIN-6 trial

        Mechanism: Mimics GLP-1 hormone, promoting insulin secretion, reducing glucagon,
        slowing gastric emptying, and acting on brain appetite centers.

        Common side effects:
        - Nausea (usually transient)
        - Vomiting
        - Diarrhea or constipation
        - Injection site reactions

        Dosing: Titrated from 0.25mg to 2.4mg weekly (Wegovy) over 16-20 weeks.""",
        "peptides_mentioned": ["Semaglutide", "Ozempic", "Wegovy"],
        "fda_status": "approved",
        "section_type": "abstract",
        "authors": ["Wilding JPH", "Batterham RL", "Calanna S"],
        "publication_date": "2021-02-10",
        "url": "https://pubmed.ncbi.nlm.nih.gov/33567185/",
        "citation": "Wilding JPH et al. Once-Weekly Semaglutide in Adults with Overweight or Obesity. N Engl J Med. 2021.",
    },
    # Tirzepatide
    {
        "chunk_id": "seed-tirzepatide-overview",
        "document_id": "seed-tirzepatide",
        "source_type": "pubmed",
        "title": "Tirzepatide: Dual GIP/GLP-1 Receptor Agonist",
        "content": """Tirzepatide is an FDA-approved dual GIP/GLP-1 receptor agonist for diabetes and obesity.

        FDA-approved products:
        - Mounjaro (for type 2 diabetes)
        - Zepbound (for chronic weight management)

        Clinical trial results (SURMOUNT-1):
        - 22.5% weight loss at highest dose (15mg) over 72 weeks
        - Superior efficacy compared to semaglutide in head-to-head trials
        - Significant improvements in metabolic markers

        Mechanism: Activates both GIP and GLP-1 receptors, providing enhanced metabolic effects
        compared to GLP-1 agonists alone.

        Dosing: Started at 2.5mg weekly, titrated up to 5mg, 10mg, or 15mg based on response.

        Side effects similar to GLP-1 agonists but may include:
        - Gastrointestinal effects (nausea, vomiting, diarrhea)
        - Decreased appetite
        - Injection site reactions""",
        "peptides_mentioned": ["Tirzepatide", "Mounjaro", "Zepbound"],
        "fda_status": "approved",
        "section_type": "abstract",
        "authors": ["Jastreboff AM", "Aronne LJ", "Ahmad NN"],
        "publication_date": "2022-06-04",
        "url": "https://pubmed.ncbi.nlm.nih.gov/35658024/",
        "citation": "Jastreboff AM et al. Tirzepatide Once Weekly for the Treatment of Obesity. N Engl J Med. 2022.",
    },
    # Ipamorelin
    {
        "chunk_id": "seed-ipamorelin-overview",
        "document_id": "seed-ipamorelin",
        "source_type": "pubmed",
        "title": "Ipamorelin: Growth Hormone Secretagogue Properties",
        "content": """Ipamorelin is a selective growth hormone secretagogue that stimulates GH release from the pituitary.

        Key characteristics:
        - Selective for GH release (doesn't significantly affect cortisol or prolactin)
        - Mimics ghrelin's action at GHS-R receptors
        - More stable and longer-acting than natural GHRP

        Research applications:
        - Growth hormone deficiency studies
        - Muscle wasting conditions
        - Anti-aging research
        - Body composition improvement studies

        Common research protocols:
        - 200-300 mcg, 2-3 times daily
        - Often combined with CJC-1295 for synergistic effects
        - Administered on empty stomach for optimal results

        Side effects in research:
        - Water retention (temporary)
        - Increased hunger (ghrelin effect)
        - Tingling/numbness (transient)

        Note: Not FDA approved for human use.""",
        "peptides_mentioned": ["Ipamorelin", "GHRP"],
        "fda_status": "research_only",
        "section_type": "abstract",
        "authors": ["Raun K", "Hansen BS", "Johansen NL"],
        "publication_date": "1998-04-01",
        "url": "https://pubmed.ncbi.nlm.nih.gov/",
        "citation": "Raun K et al. Ipamorelin, the first selective growth hormone secretagogue. Eur J Endocrinol. 1998.",
    },
    # CJC-1295
    {
        "chunk_id": "seed-cjc1295-overview",
        "document_id": "seed-cjc1295",
        "source_type": "pubmed",
        "title": "CJC-1295: Modified Growth Hormone Releasing Hormone",
        "content": """CJC-1295 is a synthetic analog of growth hormone releasing hormone (GHRH) with extended half-life.

        Two forms exist:
        - CJC-1295 with DAC: Drug Affinity Complex extends half-life to ~8 days
        - CJC-1295 without DAC (Mod GRF 1-29): Shorter half-life, more natural pulsatile release

        Mechanism:
        - Stimulates pituitary to release growth hormone
        - Works synergistically with GHRPs like Ipamorelin
        - Maintains more natural GH pulsatility than exogenous GH

        Research protocols:
        - CJC-1295 DAC: 1-2mg once or twice weekly
        - CJC-1295 no DAC: 100-300mcg, 2-3 times daily

        Potential benefits being researched:
        - Increased lean muscle mass
        - Reduced body fat
        - Improved sleep quality
        - Enhanced recovery

        Not FDA approved for human use. Research compound only.""",
        "peptides_mentioned": ["CJC-1295", "Mod GRF 1-29", "GHRH"],
        "fda_status": "research_only",
        "section_type": "abstract",
        "authors": ["Teichman SL", "Neale A", "Lawrence B"],
        "publication_date": "2006-01-01",
        "url": "https://pubmed.ncbi.nlm.nih.gov/",
        "citation": "Teichman SL et al. Prolonged stimulation of growth hormone (GH) release by CJC-1295. J Clin Endocrinol Metab. 2006.",
    },
    # Semax
    {
        "chunk_id": "seed-semax-overview",
        "document_id": "seed-semax",
        "source_type": "pubmed",
        "title": "Semax: Synthetic ACTH Fragment with Nootropic Properties",
        "content": """Semax is a synthetic peptide derived from ACTH (4-10) with an added Pro-Gly-Pro sequence.

        Approved in Russia for:
        - Cognitive enhancement
        - Stroke recovery
        - ADHD treatment
        - Optic nerve conditions

        Mechanism:
        - Increases BDNF (Brain-Derived Neurotrophic Factor)
        - Modulates dopamine and serotonin systems
        - Has neuroprotective effects
        - Does not affect cortisol (unlike ACTH)

        Research findings:
        - Improved attention and memory in studies
        - Accelerated recovery from stroke
        - Anxiolytic effects without sedation
        - Potential for neurodegenerative disease treatment

        Administration:
        - Typically intranasal spray
        - Doses: 300-600 mcg daily
        - Rapid absorption through nasal mucosa

        Well-tolerated with minimal side effects reported in research.""",
        "peptides_mentioned": ["Semax", "ACTH"],
        "fda_status": "research_only",
        "section_type": "abstract",
        "authors": ["Ashmarin IP", "Nezavibatko VN", "Myasoedov NF"],
        "publication_date": "1997-01-01",
        "url": "https://pubmed.ncbi.nlm.nih.gov/",
        "citation": "Ashmarin IP et al. A nootropic regulatory peptide Semax. Neurosci Behav Physiol. 1997.",
    },
    # GHK-Cu
    {
        "chunk_id": "seed-ghkcu-overview",
        "document_id": "seed-ghkcu",
        "source_type": "pubmed",
        "title": "GHK-Cu: Copper Peptide with Regenerative Properties",
        "content": """GHK-Cu (Glycyl-L-histidyl-L-lysine copper) is a naturally occurring copper complex in human plasma.

        Biological functions:
        - Stimulates collagen and elastin synthesis
        - Promotes wound healing and tissue repair
        - Has anti-inflammatory effects
        - Attracts immune cells for tissue remodeling
        - May have anti-cancer properties

        Applications:
        - Skin aging (topical cosmetic use)
        - Wound healing
        - Hair growth promotion
        - Post-procedure recovery (laser, peels)

        Mechanism:
        - Activates genes involved in tissue remodeling
        - Increases glycosaminoglycan synthesis
        - Promotes stem cell attraction to wounds
        - Modulates gene expression (over 4,000 genes)

        Administration:
        - Topical: 0.01-0.1% in serums/creams
        - Subcutaneous: Research protocols vary
        - Generally well-tolerated

        One of few peptides with both topical and systemic research applications.""",
        "peptides_mentioned": ["GHK-Cu", "GHK", "Copper peptide"],
        "fda_status": "research_only",
        "section_type": "abstract",
        "authors": ["Pickart L", "Margolina A"],
        "publication_date": "2018-07-01",
        "url": "https://pubmed.ncbi.nlm.nih.gov/",
        "citation": "Pickart L, Margolina A. Regenerative and Protective Actions of the GHK-Cu Peptide. Int J Mol Sci. 2018.",
    },
    # PT-141
    {
        "chunk_id": "seed-pt141-overview",
        "document_id": "seed-pt141",
        "source_type": "pubmed",
        "title": "PT-141 (Bremelanotide): Melanocortin Receptor Agonist for Sexual Dysfunction",
        "content": """PT-141 (Bremelanotide) is an FDA-approved melanocortin receptor agonist for treating hypoactive sexual desire disorder (HSDD) in premenopausal women.

        FDA Status:
        - Approved as Vyleesi (2019) for HSDD in premenopausal women
        - Administered via subcutaneous injection

        Mechanism:
        - Activates MC3R and MC4R receptors in the brain
        - Works centrally on sexual arousal pathways
        - Does not affect blood pressure like earlier melanocortin peptides

        Clinical efficacy:
        - RECONNECT trials showed statistically significant improvement in sexual desire
        - Onset: 45 minutes to 2 hours post-injection
        - Duration: Varies, typically used as needed (not daily)

        Side effects:
        - Nausea (most common, usually transient)
        - Flushing
        - Headache
        - Injection site reactions

        Research also ongoing for male sexual dysfunction.""",
        "peptides_mentioned": ["PT-141", "Bremelanotide", "Vyleesi"],
        "fda_status": "approved",
        "section_type": "abstract",
        "authors": ["Clayton AH", "Althof SE", "Kingsberg S"],
        "publication_date": "2016-06-01",
        "url": "https://pubmed.ncbi.nlm.nih.gov/",
        "citation": "Clayton AH et al. Bremelanotide for female sexual dysfunctions. Expert Opin Investig Drugs. 2016.",
    },
    # Epithalon
    {
        "chunk_id": "seed-epithalon-overview",
        "document_id": "seed-epithalon",
        "source_type": "pubmed",
        "title": "Epithalon: Synthetic Pineal Peptide and Telomerase Activation",
        "content": """Epithalon (Epitalon) is a synthetic tetrapeptide (Ala-Glu-Asp-Gly) studied for anti-aging properties.

        Research focus:
        - Telomerase activation
        - Pineal gland function
        - Melatonin production
        - Circadian rhythm regulation

        Key research findings:
        - Activates telomerase in human somatic cells
        - May elongate telomeres (associated with cellular aging)
        - Normalizes melatonin production in elderly
        - Improved sleep patterns in some studies

        Animal studies:
        - Extended lifespan in rodent models
        - Reduced tumor incidence
        - Improved immune function

        Research protocols:
        - 5-10mg daily for 10-20 days
        - Cycles repeated 2-3 times per year
        - Subcutaneous or intramuscular injection

        Developed by Prof. Khavinson at the St. Petersburg Institute of Bioregulation.
        Not FDA approved. Limited human clinical trial data available.""",
        "peptides_mentioned": ["Epithalon", "Epitalon", "AEDG"],
        "fda_status": "research_only",
        "section_type": "abstract",
        "authors": ["Khavinson VK", "Bondarev IE", "Butyugov AA"],
        "publication_date": "2003-01-01",
        "url": "https://pubmed.ncbi.nlm.nih.gov/",
        "citation": "Khavinson VK et al. Epithalon peptide induces telomerase activity and telomere elongation. Bull Exp Biol Med. 2003.",
    },
    # MK-677
    {
        "chunk_id": "seed-mk677-overview",
        "document_id": "seed-mk677",
        "source_type": "pubmed",
        "title": "MK-677 (Ibutamoren): Oral Growth Hormone Secretagogue",
        "content": """MK-677 (Ibutamoren) is an orally active growth hormone secretagogue that mimics ghrelin.

        Mechanism:
        - Activates ghrelin receptors (GHS-R1a)
        - Stimulates pulsatile GH release
        - Increases IGF-1 levels
        - Does not suppress natural GH production

        Research findings:
        - Increases lean body mass
        - Improves sleep quality (more REM sleep)
        - Increases bone mineral density
        - Does not significantly affect cortisol

        Studies in elderly:
        - Reversed diet-induced nitrogen wasting
        - Increased IGF-1 to young adult levels
        - Well-tolerated over extended periods

        Typical research dosing:
        - 10-25mg daily (oral)
        - Taken before bed (may cause drowsiness)
        - Can be used continuously

        Side effects:
        - Increased appetite
        - Water retention
        - Mild lethargy
        - May affect insulin sensitivity

        Not FDA approved despite extensive clinical research.""",
        "peptides_mentioned": ["MK-677", "Ibutamoren"],
        "fda_status": "research_only",
        "section_type": "abstract",
        "authors": ["Nass R", "Pezzoli SS", "Oliveri MC"],
        "publication_date": "2008-11-01",
        "url": "https://pubmed.ncbi.nlm.nih.gov/",
        "citation": "Nass R et al. Effects of an oral ghrelin mimetic on body composition and clinical outcomes. Ann Intern Med. 2008.",
    },
]


async def check_weaviate_status(client: WeaviateClient) -> Dict[str, Any]:
    """Check Weaviate collections and data counts"""
    try:
        stats = await client.get_stats()
        return {
            "connected": True,
            "collections": stats
        }
    except Exception as e:
        return {
            "connected": False,
            "error": str(e)
        }


async def seed_peptide_research(client: WeaviateClient) -> int:
    """Seed Weaviate with peptide research data"""
    count = 0

    for data in PEPTIDE_RESEARCH_DATA:
        try:
            chunk = ProcessedChunk(
                chunk_id=data["chunk_id"],
                document_id=data["document_id"],
                source_type=SourceType(data["source_type"]),
                content=data["content"],
                section_type=data.get("section_type", "abstract"),
                peptides_mentioned=data.get("peptides_mentioned", []),
                fda_status=FDAStatus(data.get("fda_status", "research_only")),
                conditions_mentioned=data.get("conditions_mentioned", []),
                title=data["title"],
                authors=data.get("authors", []),
                publication_date=datetime.fromisoformat(data["publication_date"]) if data.get("publication_date") else None,
                url=data.get("url"),
                doi=data.get("doi"),
                citation=data.get("citation"),
            )

            await client.index_chunk(chunk)
            count += 1
            print(f"  Indexed: {data['title'][:50]}...")

        except Exception as e:
            print(f"  Error indexing {data['chunk_id']}: {e}")

    return count


async def main():
    parser = argparse.ArgumentParser(description="Seed Weaviate with peptide research data")
    parser.add_argument("--check", action="store_true", help="Just check Weaviate status")
    parser.add_argument("--seed", action="store_true", help="Seed data if collections are empty")
    parser.add_argument("--force", action="store_true", help="Force re-seed (clear existing data)")
    args = parser.parse_args()

    # Load environment
    from dotenv import load_dotenv
    load_dotenv()

    weaviate_url = os.getenv("WEAVIATE_URL", "http://localhost:8080")
    weaviate_api_key = os.getenv("WEAVIATE_API_KEY")
    openai_api_key = os.getenv("OPENAI_API_KEY")

    print(f"Connecting to Weaviate: {weaviate_url}")

    client = WeaviateClient(
        url=weaviate_url,
        api_key=weaviate_api_key if weaviate_api_key else None,
        openai_api_key=openai_api_key
    )

    try:
        await client.connect()
        await client.create_schema()

        # Check status
        status = await check_weaviate_status(client)
        print(f"\nWeaviate Status: {'Connected' if status['connected'] else 'Disconnected'}")

        if status['connected']:
            for collection, stats in status['collections'].items():
                count = stats.get('count', 0) if isinstance(stats, dict) else 0
                print(f"  {collection}: {count} documents")

        if args.check:
            return

        # Determine if we should seed
        chunks_count = status.get('collections', {}).get(CHUNKS_COLLECTION, {}).get('count', 0)

        if args.force:
            print("\n--force flag set. Clearing existing data...")
            await client.clear_collection(CHUNKS_COLLECTION)
            chunks_count = 0

        if args.seed or args.force:
            if chunks_count == 0:
                print(f"\nSeeding {len(PEPTIDE_RESEARCH_DATA)} peptide research documents...")
                count = await seed_peptide_research(client)
                print(f"\nSeeded {count} documents successfully!")
            else:
                print(f"\nWeaviate already has {chunks_count} documents. Use --force to re-seed.")

        # Final status
        final_status = await check_weaviate_status(client)
        print("\nFinal Status:")
        for collection, stats in final_status['collections'].items():
            count = stats.get('count', 0) if isinstance(stats, dict) else 0
            print(f"  {collection}: {count} documents")

    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await client.close()


if __name__ == "__main__":
    asyncio.run(main())
