#!/usr/bin/env python3
"""
Peptide AI - CLI Tool

Command-line interface for ingestion and management tasks.

Usage:
    python cli.py ingest --source pubmed --max 100
    python cli.py schema --create
    python cli.py stats
"""

import asyncio
import argparse
import logging
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


async def cmd_ingest(args):
    """Run data ingestion"""
    from processing.pipeline import run_full_ingestion

    logger.info("Starting ingestion...")

    queries = None
    if args.query:
        queries = [args.query]

    stats = await run_full_ingestion(
        weaviate_url=os.getenv("WEAVIATE_URL", "http://localhost:8080"),
        openai_api_key=os.getenv("OPENAI_API_KEY", ""),
        queries=queries,
        max_per_query=args.max
    )

    print("\n📊 Ingestion Results:")
    print(f"  Documents: {stats['documents_processed']}")
    print(f"  Chunks: {stats['chunks_indexed']}")
    print(f"  Errors: {stats['errors']}")


async def cmd_schema(args):
    """Manage Weaviate schema"""
    from storage.weaviate_client import WeaviateClient

    weaviate = WeaviateClient(
        url=os.getenv("WEAVIATE_URL", "http://localhost:8080"),
        openai_api_key=os.getenv("OPENAI_API_KEY", "")
    )

    try:
        await weaviate.connect()

        if args.create:
            await weaviate.create_schema()
            print("✅ Schema created successfully")

        elif args.delete:
            confirm = input("⚠️  This will delete all data. Type 'DELETE' to confirm: ")
            if confirm == "DELETE":
                await weaviate.clear_collection("PeptideChunk")
                await weaviate.clear_collection("JourneyOutcome")
                print("✅ Collections deleted")
            else:
                print("Cancelled")

    finally:
        await weaviate.close()


async def cmd_stats(args):
    """Show database statistics"""
    from storage.weaviate_client import WeaviateClient

    weaviate = WeaviateClient(
        url=os.getenv("WEAVIATE_URL", "http://localhost:8080"),
    )

    try:
        await weaviate.connect()
        stats = await weaviate.get_stats()

        print("\n📈 Database Statistics:")
        for collection, data in stats.items():
            if "count" in data:
                print(f"  {collection}: {data['count']} documents")
            elif "error" in data:
                print(f"  {collection}: Error - {data['error']}")

    finally:
        await weaviate.close()


async def cmd_search(args):
    """Test search functionality"""
    from storage.weaviate_client import WeaviateClient

    weaviate = WeaviateClient(
        url=os.getenv("WEAVIATE_URL", "http://localhost:8080"),
        openai_api_key=os.getenv("OPENAI_API_KEY", "")
    )

    try:
        await weaviate.connect()

        results = await weaviate.hybrid_search(
            query=args.query,
            limit=args.limit,
            alpha=0.5
        )

        print(f"\n🔍 Search Results for: '{args.query}'")
        print(f"   Found {len(results)} results\n")

        for i, result in enumerate(results, 1):
            props = result.get("properties", {})
            print(f"{i}. {props.get('title', 'Untitled')[:60]}...")
            print(f"   Score: {result.get('score', 0):.3f}")
            print(f"   Source: {props.get('source_type', 'unknown')}")
            print(f"   Peptides: {', '.join(props.get('peptides_mentioned', []))}")
            print()

    finally:
        await weaviate.close()


async def cmd_test_pubmed(args):
    """Test PubMed adapter"""
    from sources.pubmed import PubMedAdapter

    adapter = PubMedAdapter({
        "api_key": os.getenv("NCBI_API_KEY", "")
    })

    query = args.query or "BPC-157"
    print(f"\n🔬 Testing PubMed search: '{query}'")

    docs = await adapter.search(query, max_results=args.max)

    print(f"   Found {len(docs)} papers\n")

    for doc in docs[:5]:
        print(f"📄 {doc.title[:70]}...")
        print(f"   Authors: {', '.join(doc.authors[:3])}")
        print(f"   Date: {doc.publication_date}")
        print(f"   PMID: {doc.source_id}")
        print()


def main():
    parser = argparse.ArgumentParser(
        description="Peptide AI CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    subparsers = parser.add_subparsers(dest="command", help="Commands")

    # Ingest command
    ingest_parser = subparsers.add_parser("ingest", help="Run data ingestion")
    ingest_parser.add_argument("--source", default="pubmed", help="Data source")
    ingest_parser.add_argument("--query", help="Specific search query")
    ingest_parser.add_argument("--max", type=int, default=100, help="Max documents per query")

    # Schema command
    schema_parser = subparsers.add_parser("schema", help="Manage Weaviate schema")
    schema_parser.add_argument("--create", action="store_true", help="Create schema")
    schema_parser.add_argument("--delete", action="store_true", help="Delete all data")

    # Stats command
    subparsers.add_parser("stats", help="Show database statistics")

    # Search command
    search_parser = subparsers.add_parser("search", help="Test search")
    search_parser.add_argument("query", help="Search query")
    search_parser.add_argument("--limit", type=int, default=5, help="Result limit")

    # Test PubMed command
    test_parser = subparsers.add_parser("test-pubmed", help="Test PubMed adapter")
    test_parser.add_argument("--query", help="Search query")
    test_parser.add_argument("--max", type=int, default=5, help="Max results")

    args = parser.parse_args()

    if args.command == "ingest":
        asyncio.run(cmd_ingest(args))
    elif args.command == "schema":
        asyncio.run(cmd_schema(args))
    elif args.command == "stats":
        asyncio.run(cmd_stats(args))
    elif args.command == "search":
        asyncio.run(cmd_search(args))
    elif args.command == "test-pubmed":
        asyncio.run(cmd_test_pubmed(args))
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
