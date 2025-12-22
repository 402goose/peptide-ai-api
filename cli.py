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
        weaviate_api_key=os.getenv("WEAVIATE_API_KEY", ""),
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
        api_key=os.getenv("WEAVIATE_API_KEY") or None,
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
        api_key=os.getenv("WEAVIATE_API_KEY") or None,
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
        api_key=os.getenv("WEAVIATE_API_KEY") or None,
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


async def cmd_ingest_reddit(args):
    """Ingest Reddit data into Weaviate"""
    from sources.reddit_ingestion import RedditIngestion
    from storage.weaviate_client import WeaviateClient
    from processing.chunker import SimpleChunker
    from models.documents import RawDocument, SourceType

    logger.info("🔴 Starting Reddit ingestion...")

    # Initialize Reddit ingestion
    reddit = RedditIngestion()
    chunker = SimpleChunker(chunk_size=1500, overlap=150)

    # Initialize Weaviate
    weaviate = WeaviateClient(
        url=os.getenv("WEAVIATE_URL", "http://localhost:8080"),
        api_key=os.getenv("WEAVIATE_API_KEY") or None,
        openai_api_key=os.getenv("OPENAI_API_KEY", "")
    )

    try:
        await weaviate.connect()

        # Fetch Reddit posts
        posts = await reddit.ingest_all(posts_per_sub=args.max)

        print(f"\n📊 Fetched {len(posts)} Reddit posts/comments")
        print(f"   Experience reports: {sum(1 for p in posts if p.is_experience_report)}")

        # Convert and store in Weaviate
        chunks_stored = 0
        errors = 0

        for post in posts:
            try:
                # Create RawDocument for chunking
                raw_doc = RawDocument(
                    source_id=f"reddit_{post.id}",
                    source_type=SourceType.REDDIT,
                    title=post.title if post.title else f"Reddit: {', '.join(post.peptides_mentioned)}",
                    content=post.content,
                    authors=[post.author] if post.author != '[deleted]' else [],
                    publication_date=post.created_utc,
                    url=post.url,
                    citation=f"Reddit r/{post.subreddit} - u/{post.author} ({post.created_utc.strftime('%Y-%m-%d')})",
                )

                # Chunk the document
                chunks = chunker.chunk_document(raw_doc)

                # Enrich and store chunks
                for chunk in chunks:
                    # Add peptide mentions from post
                    chunk.peptides_mentioned = post.peptides_mentioned

                    # Store in Weaviate using index_chunk
                    await weaviate.index_chunk(chunk)
                    chunks_stored += 1

            except Exception as e:
                logger.error(f"Error storing post {post.id}: {e}")
                errors += 1

        print(f"\n✅ Reddit Ingestion Complete!")
        print(f"   Posts processed: {len(posts)}")
        print(f"   Chunks stored: {chunks_stored}")
        print(f"   Errors: {errors}")

    finally:
        await reddit.close()
        await weaviate.close()


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

    # Reddit ingestion command
    reddit_parser = subparsers.add_parser("ingest-reddit", help="Ingest Reddit data")
    reddit_parser.add_argument("--max", type=int, default=50, help="Max posts per subreddit")

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
    elif args.command == "ingest-reddit":
        asyncio.run(cmd_ingest_reddit(args))
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
