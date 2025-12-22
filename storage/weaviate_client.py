"""
Peptide AI - Weaviate Vector Store

Handles all vector storage and retrieval operations.
Supports hybrid search (BM25 + vector) with RRF fusion.
"""

import logging
from typing import List, Optional, Dict, Any
from datetime import datetime
import weaviate
from weaviate.classes.query import Filter, MetadataQuery, HybridFusion
from weaviate.classes.config import Property, DataType, Configure, VectorDistances
from weaviate.classes.data import DataObject

from models.documents import ProcessedChunk, SourceType, FDAStatus

logger = logging.getLogger(__name__)


# Collection names
CHUNKS_COLLECTION = "PeptideChunk"
OUTCOMES_COLLECTION = "JourneyOutcome"


class WeaviateClient:
    """
    Client for Weaviate vector database operations

    Handles:
    - Schema management
    - Document indexing
    - Hybrid search (BM25 + semantic)
    - Filtering and aggregation
    """

    def __init__(
        self,
        url: str = "http://localhost:8080",
        api_key: Optional[str] = None,
        openai_api_key: Optional[str] = None
    ):
        """
        Initialize Weaviate client

        Args:
            url: Weaviate instance URL
            api_key: Weaviate API key (for cloud)
            openai_api_key: OpenAI API key for vectorization
        """
        self.url = url
        self.api_key = api_key
        self.openai_api_key = openai_api_key
        self._client = None

    async def connect(self):
        """Connect to Weaviate instance"""
        try:
            if self.api_key:
                # Weaviate Cloud - strip protocol and whitespace
                cluster_url = self.url.strip()
                cluster_url = cluster_url.replace("https://", "").replace("http://", "")
                logger.info(f"Connecting to Weaviate Cloud: {cluster_url}")
                self._client = weaviate.connect_to_weaviate_cloud(
                    cluster_url=cluster_url,
                    auth_credentials=weaviate.auth.AuthApiKey(self.api_key),
                    headers={"X-OpenAI-Api-Key": self.openai_api_key} if self.openai_api_key else None
                )
            else:
                # Local instance
                self._client = weaviate.connect_to_local(
                    host=self.url.replace("http://", "").replace("https://", "").split(":")[0],
                    port=int(self.url.split(":")[-1]) if ":" in self.url else 8080,
                    headers={"X-OpenAI-Api-Key": self.openai_api_key} if self.openai_api_key else None
                )

            logger.info(f"Connected to Weaviate at {self.url}")

        except Exception as e:
            logger.error(f"Failed to connect to Weaviate: {e}")
            raise

    async def close(self):
        """Close Weaviate connection"""
        if self._client:
            self._client.close()

    @property
    def client(self):
        """Get the Weaviate client"""
        if not self._client:
            raise RuntimeError("Not connected to Weaviate. Call connect() first.")
        return self._client

    # =========================================================================
    # SCHEMA MANAGEMENT
    # =========================================================================

    async def create_schema(self):
        """Create Weaviate collections for peptide data"""
        await self._create_chunks_collection()
        await self._create_outcomes_collection()
        logger.info("Weaviate schema created successfully")

    async def _create_chunks_collection(self):
        """Create collection for processed document chunks"""
        if self.client.collections.exists(CHUNKS_COLLECTION):
            logger.info(f"Collection {CHUNKS_COLLECTION} already exists")
            return

        self.client.collections.create(
            name=CHUNKS_COLLECTION,
            description="Processed document chunks from research papers and other sources",

            # Enable hybrid search with OpenAI embeddings (for Weaviate Cloud)
            vectorizer_config=Configure.Vectorizer.text2vec_openai(),

            # Vector index config
            vector_index_config=Configure.VectorIndex.hnsw(
                distance_metric=VectorDistances.COSINE,
                ef_construction=128,
                max_connections=64
            ),

            # Properties
            properties=[
                Property(
                    name="chunk_id",
                    data_type=DataType.TEXT,
                    description="Unique chunk identifier",
                    skip_vectorization=True
                ),
                Property(
                    name="document_id",
                    data_type=DataType.TEXT,
                    description="Parent document ID",
                    skip_vectorization=True
                ),
                Property(
                    name="source_type",
                    data_type=DataType.TEXT,
                    description="Source type (pubmed, arxiv, etc.)",
                    skip_vectorization=True
                ),
                Property(
                    name="content",
                    data_type=DataType.TEXT,
                    description="Chunk text content"
                    # This gets vectorized
                ),
                Property(
                    name="section_type",
                    data_type=DataType.TEXT,
                    description="Section type (abstract, methods, results)",
                    skip_vectorization=True
                ),
                Property(
                    name="peptides_mentioned",
                    data_type=DataType.TEXT_ARRAY,
                    description="Peptides mentioned in this chunk",
                    skip_vectorization=True
                ),
                Property(
                    name="fda_status",
                    data_type=DataType.TEXT,
                    description="FDA status of primary peptide",
                    skip_vectorization=True
                ),
                Property(
                    name="conditions_mentioned",
                    data_type=DataType.TEXT_ARRAY,
                    description="Medical conditions mentioned",
                    skip_vectorization=True
                ),
                Property(
                    name="title",
                    data_type=DataType.TEXT,
                    description="Document title"
                ),
                Property(
                    name="authors",
                    data_type=DataType.TEXT_ARRAY,
                    description="Document authors",
                    skip_vectorization=True
                ),
                Property(
                    name="publication_date",
                    data_type=DataType.DATE,
                    description="Publication date",
                    skip_vectorization=True
                ),
                Property(
                    name="url",
                    data_type=DataType.TEXT,
                    description="Source URL",
                    skip_vectorization=True
                ),
                Property(
                    name="doi",
                    data_type=DataType.TEXT,
                    description="DOI if available",
                    skip_vectorization=True
                ),
                Property(
                    name="citation",
                    data_type=DataType.TEXT,
                    description="Formatted citation",
                    skip_vectorization=True
                ),
                Property(
                    name="original_language",
                    data_type=DataType.TEXT,
                    description="Original language code",
                    skip_vectorization=True
                ),
            ],

            # Enable BM25 for hybrid search
            inverted_index_config=Configure.inverted_index(
                bm25_b=0.75,
                bm25_k1=1.2
            )
        )

        logger.info(f"Created collection: {CHUNKS_COLLECTION}")

    async def _create_outcomes_collection(self):
        """Create collection for user journey outcomes"""
        if self.client.collections.exists(OUTCOMES_COLLECTION):
            logger.info(f"Collection {OUTCOMES_COLLECTION} already exists")
            return

        self.client.collections.create(
            name=OUTCOMES_COLLECTION,
            description="Aggregated user journey outcomes for RAG",

            vectorizer_config=Configure.Vectorizer.text2vec_transformers(),

            properties=[
                Property(
                    name="journey_id",
                    data_type=DataType.TEXT,
                    skip_vectorization=True
                ),
                Property(
                    name="user_hash",
                    data_type=DataType.TEXT,
                    description="Anonymized user ID",
                    skip_vectorization=True
                ),
                Property(
                    name="peptide",
                    data_type=DataType.TEXT,
                    description="Primary peptide used"
                ),
                Property(
                    name="secondary_peptides",
                    data_type=DataType.TEXT_ARRAY,
                    skip_vectorization=True
                ),
                Property(
                    name="duration_weeks",
                    data_type=DataType.INT,
                    skip_vectorization=True
                ),
                Property(
                    name="administration_route",
                    data_type=DataType.TEXT,
                    skip_vectorization=True
                ),
                Property(
                    name="goal_categories",
                    data_type=DataType.TEXT_ARRAY
                ),
                Property(
                    name="goals_achieved",
                    data_type=DataType.INT,
                    skip_vectorization=True
                ),
                Property(
                    name="goals_total",
                    data_type=DataType.INT,
                    skip_vectorization=True
                ),
                Property(
                    name="overall_efficacy",
                    data_type=DataType.INT,
                    skip_vectorization=True
                ),
                Property(
                    name="would_recommend",
                    data_type=DataType.BOOL,
                    skip_vectorization=True
                ),
                Property(
                    name="side_effects_reported",
                    data_type=DataType.TEXT_ARRAY
                ),
                Property(
                    name="outcome_narrative",
                    data_type=DataType.TEXT,
                    description="Natural language summary for embedding"
                ),
                Property(
                    name="age_range",
                    data_type=DataType.TEXT,
                    skip_vectorization=True
                ),
                Property(
                    name="sex",
                    data_type=DataType.TEXT,
                    skip_vectorization=True
                ),
            ]
        )

        logger.info(f"Created collection: {OUTCOMES_COLLECTION}")

    # =========================================================================
    # INDEXING
    # =========================================================================

    async def index_chunk(self, chunk: ProcessedChunk) -> str:
        """Index a single processed chunk"""
        collection = self.client.collections.get(CHUNKS_COLLECTION)

        obj = DataObject(
            properties={
                "chunk_id": chunk.chunk_id,
                "document_id": chunk.document_id,
                "source_type": chunk.source_type.value,
                "content": chunk.content,
                "section_type": chunk.section_type,
                "peptides_mentioned": chunk.peptides_mentioned,
                "fda_status": chunk.fda_status.value,
                "conditions_mentioned": chunk.conditions_mentioned,
                "title": chunk.title,
                "authors": chunk.authors,
                "publication_date": (chunk.publication_date.isoformat() + "Z") if chunk.publication_date else None,
                "url": chunk.url,
                "doi": chunk.doi,
                "citation": chunk.citation,
                "original_language": chunk.original_language,
            }
        )

        result = collection.data.insert(obj)
        return str(result)

    async def index_chunks_batch(self, chunks: List[ProcessedChunk]) -> int:
        """Index multiple chunks in a batch"""
        collection = self.client.collections.get(CHUNKS_COLLECTION)

        objects = []
        for chunk in chunks:
            objects.append(DataObject(
                properties={
                    "chunk_id": chunk.chunk_id,
                    "document_id": chunk.document_id,
                    "source_type": chunk.source_type.value,
                    "content": chunk.content,
                    "section_type": chunk.section_type,
                    "peptides_mentioned": chunk.peptides_mentioned,
                    "fda_status": chunk.fda_status.value,
                    "conditions_mentioned": chunk.conditions_mentioned,
                    "title": chunk.title,
                    "authors": chunk.authors,
                    "publication_date": (chunk.publication_date.isoformat() + "Z") if chunk.publication_date else None,
                    "url": chunk.url,
                    "doi": chunk.doi,
                    "citation": chunk.citation,
                    "original_language": chunk.original_language,
                }
            ))

        result = collection.data.insert_many(objects)
        return len(result.all_responses)

    async def index_outcome(self, outcome: Dict[str, Any]) -> str:
        """Index a journey outcome for RAG"""
        collection = self.client.collections.get(OUTCOMES_COLLECTION)

        obj = DataObject(properties=outcome)
        result = collection.data.insert(obj)
        return str(result)

    # =========================================================================
    # SEARCH
    # =========================================================================

    async def hybrid_search(
        self,
        query: str,
        limit: int = 20,
        alpha: float = 0.5,
        source_filter: Optional[str] = None,
        peptide_filter: Optional[List[str]] = None,
        include_outcomes: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Perform hybrid search (BM25 + vector)

        Args:
            query: Search query
            limit: Maximum results
            alpha: Balance between keyword (0) and vector (1) search
            source_filter: Filter by source type
            peptide_filter: Filter to specific peptides
            include_outcomes: Include user journey outcomes

        Returns:
            List of search results with scores
        """
        results = []

        # Search chunks collection
        chunk_results = await self._search_collection(
            collection_name=CHUNKS_COLLECTION,
            query=query,
            limit=limit,
            alpha=alpha,
            filters=self._build_filters(source_filter, peptide_filter)
        )
        results.extend(chunk_results)

        # Optionally search outcomes
        if include_outcomes:
            outcome_results = await self._search_collection(
                collection_name=OUTCOMES_COLLECTION,
                query=query,
                limit=limit // 2,  # Fewer outcomes than research
                alpha=alpha,
                filters=self._build_peptide_filter(peptide_filter) if peptide_filter else None
            )
            results.extend(outcome_results)

        # Sort by score and limit
        results.sort(key=lambda x: x.get("score", 0), reverse=True)
        return results[:limit]

    async def _search_collection(
        self,
        collection_name: str,
        query: str,
        limit: int,
        alpha: float,
        filters: Optional[Filter] = None
    ) -> List[Dict[str, Any]]:
        """Search a specific collection"""
        collection = self.client.collections.get(collection_name)

        try:
            response = collection.query.hybrid(
                query=query,
                limit=limit,
                alpha=alpha,
                fusion_type=HybridFusion.RELATIVE_SCORE,
                filters=filters,
                return_metadata=MetadataQuery(score=True, distance=True)
            )

            results = []
            for obj in response.objects:
                result = {
                    "collection": collection_name,
                    "properties": obj.properties,
                    "score": obj.metadata.score if obj.metadata else 0,
                }
                results.append(result)

            return results

        except Exception as e:
            logger.error(f"Search failed in {collection_name}: {e}")
            return []

    def _build_filters(
        self,
        source_filter: Optional[str],
        peptide_filter: Optional[List[str]]
    ) -> Optional[Filter]:
        """Build Weaviate filters from parameters"""
        filters = []

        if source_filter and source_filter != "all":
            if source_filter == "research":
                filters.append(
                    Filter.by_property("source_type").contains_any(["pubmed", "arxiv", "biorxiv"])
                )
            elif source_filter == "user_journeys":
                filters.append(
                    Filter.by_property("source_type").equal("user_journey")
                )
            else:
                filters.append(
                    Filter.by_property("source_type").equal(source_filter)
                )

        if peptide_filter:
            filters.append(
                Filter.by_property("peptides_mentioned").contains_any(peptide_filter)
            )

        if not filters:
            return None

        if len(filters) == 1:
            return filters[0]

        # Combine with AND
        result = filters[0]
        for f in filters[1:]:
            result = result & f

        return result

    def _build_peptide_filter(self, peptides: List[str]) -> Filter:
        """Build filter for peptide field"""
        return Filter.by_property("peptide").contains_any(peptides)

    async def semantic_search(
        self,
        query: str,
        limit: int = 20,
        **filters
    ) -> List[Dict[str, Any]]:
        """Pure vector/semantic search"""
        return await self.hybrid_search(
            query=query,
            limit=limit,
            alpha=1.0,  # Pure vector
            **filters
        )

    async def keyword_search(
        self,
        query: str,
        limit: int = 20,
        **filters
    ) -> List[Dict[str, Any]]:
        """Pure BM25 keyword search"""
        return await self.hybrid_search(
            query=query,
            limit=limit,
            alpha=0.0,  # Pure BM25
            **filters
        )

    # =========================================================================
    # UTILITIES
    # =========================================================================

    async def get_stats(self) -> Dict[str, Any]:
        """Get collection statistics"""
        stats = {}

        for collection_name in [CHUNKS_COLLECTION, OUTCOMES_COLLECTION]:
            try:
                collection = self.client.collections.get(collection_name)
                aggregate = collection.aggregate.over_all(total_count=True)
                stats[collection_name] = {
                    "count": aggregate.total_count
                }
            except Exception as e:
                stats[collection_name] = {"error": str(e)}

        return stats

    async def delete_by_document_id(self, document_id: str) -> int:
        """Delete all chunks for a document"""
        collection = self.client.collections.get(CHUNKS_COLLECTION)

        result = collection.data.delete_many(
            where=Filter.by_property("document_id").equal(document_id)
        )

        return result.successful

    async def clear_collection(self, collection_name: str):
        """Clear all data from a collection (use with caution!)"""
        if self.client.collections.exists(collection_name):
            self.client.collections.delete(collection_name)
            logger.warning(f"Deleted collection: {collection_name}")
