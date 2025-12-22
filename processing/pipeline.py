"""
Peptide AI - Ingestion Pipeline

Orchestrates the full document processing flow:
1. Fetch from source (PubMed, etc.)
2. Chunk documents
3. Enrich with metadata
4. Index in Weaviate
"""

import asyncio
import logging
from typing import Optional, AsyncGenerator, List
from datetime import datetime

from sources.pubmed import PubMedAdapter
from processing.chunker import PeptideChunker, SimpleChunker
from processing.enricher import PeptideEnricher
from storage.weaviate_client import WeaviateClient
from models.documents import RawDocument, ProcessedChunk

logger = logging.getLogger(__name__)


class IngestionPipeline:
    """
    Full ingestion pipeline for peptide data

    Coordinates:
    - Source adapters (PubMed, etc.)
    - Document chunking
    - Metadata enrichment
    - Vector storage indexing
    """

    def __init__(
        self,
        weaviate_client: WeaviateClient,
        chunker: Optional[PeptideChunker] = None,
        enricher: Optional[PeptideEnricher] = None
    ):
        self.weaviate = weaviate_client
        self.chunker = chunker or SimpleChunker()
        self.enricher = enricher or PeptideEnricher()

        # Stats
        self.stats = {
            "documents_processed": 0,
            "chunks_created": 0,
            "chunks_indexed": 0,
            "errors": 0,
            "start_time": None,
            "end_time": None,
        }

    async def ingest_pubmed(
        self,
        queries: Optional[List[str]] = None,
        max_per_query: int = 100,
        batch_size: int = 50
    ) -> dict:
        """
        Ingest papers from PubMed

        Args:
            queries: List of search queries (uses defaults if None)
            max_per_query: Max papers per query
            batch_size: Documents per processing batch

        Returns:
            Stats dictionary
        """
        self.stats["start_time"] = datetime.utcnow()

        adapter = PubMedAdapter()

        if queries is None:
            queries = adapter.PEPTIDE_QUERIES[:10]  # Start with top 10

        logger.info(f"Starting PubMed ingestion with {len(queries)} queries")

        for query in queries:
            logger.info(f"Processing query: {query}")

            try:
                # Fetch documents
                documents = await adapter.search(query, max_results=max_per_query)
                logger.info(f"  Found {len(documents)} documents")

                # Process in batches
                for i in range(0, len(documents), batch_size):
                    batch = documents[i:i + batch_size]
                    await self._process_batch(batch)

            except Exception as e:
                logger.error(f"Error processing query '{query}': {e}")
                self.stats["errors"] += 1

        self.stats["end_time"] = datetime.utcnow()
        self._log_stats()

        return self.stats

    async def ingest_documents(
        self,
        documents: AsyncGenerator[List[RawDocument], None]
    ) -> dict:
        """
        Ingest documents from any async generator

        Use this for custom ingestion flows.
        """
        self.stats["start_time"] = datetime.utcnow()

        async for batch in documents:
            await self._process_batch(batch)

        self.stats["end_time"] = datetime.utcnow()
        self._log_stats()

        return self.stats

    async def _process_batch(self, documents: List[RawDocument]):
        """Process a batch of documents"""
        all_chunks = []

        for doc in documents:
            try:
                # Chunk the document
                chunks = self.chunker.chunk_document(doc)

                # Enrich each chunk
                enriched = self.enricher.enrich_batch(chunks)

                all_chunks.extend(enriched)
                self.stats["documents_processed"] += 1
                self.stats["chunks_created"] += len(chunks)

            except Exception as e:
                logger.error(f"Error processing document {doc.source_id}: {e}")
                self.stats["errors"] += 1

        # Index chunks in Weaviate
        if all_chunks:
            try:
                indexed = await self.weaviate.index_chunks_batch(all_chunks)
                self.stats["chunks_indexed"] += indexed
                logger.info(f"  Indexed {indexed} chunks")
            except Exception as e:
                logger.error(f"Error indexing chunks: {e}")
                self.stats["errors"] += 1

    def _log_stats(self):
        """Log ingestion statistics"""
        duration = (
            self.stats["end_time"] - self.stats["start_time"]
        ).total_seconds() if self.stats["end_time"] else 0

        logger.info("=" * 50)
        logger.info("Ingestion Complete")
        logger.info("=" * 50)
        logger.info(f"Documents processed: {self.stats['documents_processed']}")
        logger.info(f"Chunks created: {self.stats['chunks_created']}")
        logger.info(f"Chunks indexed: {self.stats['chunks_indexed']}")
        logger.info(f"Errors: {self.stats['errors']}")
        logger.info(f"Duration: {duration:.1f} seconds")
        logger.info("=" * 50)


async def run_full_ingestion(
    weaviate_url: str = "http://localhost:8080",
    weaviate_api_key: str = "",
    openai_api_key: str = "",
    queries: Optional[List[str]] = None,
    max_per_query: int = 100
):
    """
    Run full ingestion pipeline

    Standalone function for CLI usage.
    """
    # Initialize Weaviate
    weaviate = WeaviateClient(
        url=weaviate_url,
        api_key=weaviate_api_key if weaviate_api_key else None,
        openai_api_key=openai_api_key
    )

    try:
        await weaviate.connect()
        logger.info("Connected to Weaviate")

        # Create schema if needed
        await weaviate.create_schema()
        logger.info("Schema ready")

        # Run ingestion
        pipeline = IngestionPipeline(weaviate_client=weaviate)
        stats = await pipeline.ingest_pubmed(
            queries=queries,
            max_per_query=max_per_query
        )

        return stats

    finally:
        await weaviate.close()
