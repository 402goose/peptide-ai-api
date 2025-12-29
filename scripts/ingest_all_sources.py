"""
Ingest data from all sources and index to Weaviate.

Sources:
1. Reddit - User experiences from r/peptides, r/Nootropics, etc.
2. ClinicalTrials.gov - Active and completed clinical trials

Usage:
    python scripts/ingest_all_sources.py --reddit        # Ingest Reddit only
    python scripts/ingest_all_sources.py --clinical      # Ingest ClinicalTrials only
    python scripts/ingest_all_sources.py --all           # Ingest all sources
    python scripts/ingest_all_sources.py --check         # Check current counts
"""

import asyncio
import os
import sys
import argparse
import logging
from datetime import datetime
from typing import List, Dict, Any
from uuid import uuid4

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

from storage.weaviate_client import WeaviateClient, CHUNKS_COLLECTION
from models.documents import ProcessedChunk, SourceType, FDAStatus
from sources.reddit_ingestion import RedditIngestion
from sources.clinicaltrials_ingestion import ClinicalTrialsIngestion

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


async def ingest_reddit(weaviate: WeaviateClient, posts_per_sub: int = 50) -> int:
    """Ingest Reddit data and index to Weaviate"""
    logger.info("Starting Reddit ingestion...")

    ingestion = RedditIngestion()
    indexed = 0

    try:
        posts = await ingestion.ingest_all(posts_per_sub=posts_per_sub)
        logger.info(f"Fetched {len(posts)} Reddit posts/comments")

        for post in posts:
            try:
                # Convert to ProcessedChunk
                doc = ingestion.to_weaviate_format(post)

                chunk = ProcessedChunk(
                    chunk_id=f"reddit_{post.subreddit}_{post.id}",
                    document_id=f"reddit_{post.id}",
                    source_type=SourceType.REDDIT,
                    content=doc['content'],
                    section_type='experience_report' if post.is_experience_report else 'discussion',
                    peptides_mentioned=doc['peptides'],
                    fda_status=FDAStatus.UNKNOWN,
                    conditions_mentioned=[],
                    title=doc['title'],
                    authors=[post.author],
                    publication_date=post.created_utc,
                    url=doc['url'],
                    citation=doc['citation'],
                )

                await weaviate.index_chunk(chunk)
                indexed += 1

                if indexed % 20 == 0:
                    logger.info(f"  Indexed {indexed} Reddit documents...")

            except Exception as e:
                logger.warning(f"Failed to index Reddit post {post.id}: {e}")

    finally:
        await ingestion.close()

    logger.info(f"Reddit ingestion complete: {indexed} documents indexed")
    return indexed


async def ingest_clinical_trials(weaviate: WeaviateClient) -> int:
    """Ingest ClinicalTrials.gov data and index to Weaviate"""
    logger.info("Starting ClinicalTrials.gov ingestion...")

    ingestion = ClinicalTrialsIngestion()
    indexed = 0

    try:
        trials = await ingestion.ingest_all_peptides()
        logger.info(f"Fetched {len(trials)} clinical trials")

        for trial in trials:
            try:
                doc = ingestion.to_weaviate_format(trial)

                chunk = ProcessedChunk(
                    chunk_id=f"ct_{trial.nct_id}",
                    document_id=f"clinicaltrial_{trial.nct_id}",
                    source_type=SourceType.CLINICALTRIALS,
                    content=doc['content'],
                    section_type='clinical_trial',
                    peptides_mentioned=doc['peptides'],
                    fda_status=FDAStatus.INVESTIGATIONAL if 'Phase' in trial.phase else FDAStatus.UNKNOWN,
                    conditions_mentioned=trial.conditions[:10],
                    title=doc['title'],
                    authors=[trial.sponsor] if trial.sponsor else [],
                    publication_date=datetime.fromisoformat(trial.start_date) if trial.start_date else None,
                    url=doc['url'],
                    citation=doc['citation'],
                )

                await weaviate.index_chunk(chunk)
                indexed += 1

                if indexed % 10 == 0:
                    logger.info(f"  Indexed {indexed} clinical trials...")

            except Exception as e:
                logger.warning(f"Failed to index trial {trial.nct_id}: {e}")

    finally:
        await ingestion.close()

    logger.info(f"ClinicalTrials ingestion complete: {indexed} documents indexed")
    return indexed


async def check_weaviate_status(weaviate: WeaviateClient):
    """Check current Weaviate document counts"""
    stats = await weaviate.get_stats()

    print("\nWeaviate Document Counts:")
    print("-" * 40)
    for collection, info in stats.items():
        count = info.get('count', 0) if isinstance(info, dict) else 0
        print(f"  {collection}: {count}")
    print("-" * 40)

    return stats


async def main():
    parser = argparse.ArgumentParser(description="Ingest data from all sources to Weaviate")
    parser.add_argument("--reddit", action="store_true", help="Ingest Reddit data")
    parser.add_argument("--clinical", action="store_true", help="Ingest ClinicalTrials.gov data")
    parser.add_argument("--all", action="store_true", help="Ingest all sources")
    parser.add_argument("--check", action="store_true", help="Just check current counts")
    parser.add_argument("--posts", type=int, default=50, help="Posts per subreddit (default: 50)")
    args = parser.parse_args()

    # Connect to Weaviate
    weaviate_url = os.getenv("WEAVIATE_URL", "http://localhost:8080")
    weaviate_api_key = os.getenv("WEAVIATE_API_KEY")
    openai_api_key = os.getenv("OPENAI_API_KEY")

    logger.info(f"Connecting to Weaviate: {weaviate_url}")

    weaviate = WeaviateClient(
        url=weaviate_url,
        api_key=weaviate_api_key if weaviate_api_key else None,
        openai_api_key=openai_api_key
    )

    try:
        await weaviate.connect()
        await weaviate.create_schema()

        # Check current status
        await check_weaviate_status(weaviate)

        if args.check:
            return

        total_indexed = 0

        # Ingest based on flags
        if args.reddit or args.all:
            count = await ingest_reddit(weaviate, posts_per_sub=args.posts)
            total_indexed += count

        if args.clinical or args.all:
            count = await ingest_clinical_trials(weaviate)
            total_indexed += count

        if not (args.reddit or args.clinical or args.all):
            print("\nNo sources specified. Use --reddit, --clinical, or --all")
            print("Run with --help for usage information.")
            return

        # Final status
        print(f"\nTotal documents indexed this run: {total_indexed}")
        await check_weaviate_status(weaviate)

    except Exception as e:
        logger.error(f"Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await weaviate.close()


if __name__ == "__main__":
    asyncio.run(main())
