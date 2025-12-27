"""
Vector store protocol for Weaviate operations.

Defines the interface for vector search operations, enabling mock implementations
for testing without requiring a real Weaviate connection.
"""

from typing import Protocol, Optional, Any, runtime_checkable
from dataclasses import dataclass, field


@dataclass
class SearchResult:
    """A single search result from vector store."""
    id: str
    properties: dict[str, Any]
    score: Optional[float] = None
    vector: Optional[list[float]] = None


@dataclass
class VectorStoreStats:
    """Statistics about the vector store."""
    total_chunks: int = 0
    total_outcomes: int = 0
    collections: list[str] = field(default_factory=list)


@runtime_checkable
class IVectorStore(Protocol):
    """
    Protocol for vector store operations.

    This matches the WeaviateClient interface,
    allowing seamless substitution of mock implementations for testing.
    """

    async def connect(self) -> None:
        """Establish connection to the vector store."""
        ...

    async def close(self) -> None:
        """Close the connection to the vector store."""
        ...

    async def create_schema(self) -> None:
        """Create the required schema/collections."""
        ...

    async def hybrid_search(
        self,
        query: str,
        limit: int = 10,
        alpha: float = 0.5,
        peptide_filter: Optional[list[str]] = None,
        include_outcomes: bool = True,
    ) -> list[dict[str, Any]]:
        """
        Perform hybrid search combining BM25 and vector similarity.

        Args:
            query: The search query
            limit: Maximum number of results
            alpha: Balance between BM25 (0) and vector (1) search
            peptide_filter: Optional list of peptides to filter by
            include_outcomes: Whether to include journey outcomes

        Returns:
            List of search results with properties
        """
        ...

    async def semantic_search(
        self,
        query: str,
        limit: int = 10,
        peptide_filter: Optional[list[str]] = None,
    ) -> list[dict[str, Any]]:
        """
        Perform pure vector/semantic search.

        Args:
            query: The search query
            limit: Maximum number of results
            peptide_filter: Optional list of peptides to filter by

        Returns:
            List of search results with properties
        """
        ...

    async def keyword_search(
        self,
        query: str,
        limit: int = 10,
        peptide_filter: Optional[list[str]] = None,
    ) -> list[dict[str, Any]]:
        """
        Perform pure BM25/keyword search.

        Args:
            query: The search query
            limit: Maximum number of results
            peptide_filter: Optional list of peptides to filter by

        Returns:
            List of search results with properties
        """
        ...

    async def index_chunk(
        self,
        chunk_id: str,
        content: str,
        metadata: dict[str, Any],
        vector: Optional[list[float]] = None,
    ) -> None:
        """
        Index a document chunk in the vector store.

        Args:
            chunk_id: Unique identifier for the chunk
            content: The text content
            metadata: Additional metadata (title, source_type, etc.)
            vector: Optional pre-computed embedding vector
        """
        ...

    async def index_outcome(
        self,
        outcome_id: str,
        content: str,
        metadata: dict[str, Any],
        vector: Optional[list[float]] = None,
    ) -> None:
        """
        Index a journey outcome in the vector store.

        Args:
            outcome_id: Unique identifier for the outcome
            content: The outcome text content
            metadata: Additional metadata (peptide, efficacy, etc.)
            vector: Optional pre-computed embedding vector
        """
        ...

    async def delete_chunk(self, chunk_id: str) -> bool:
        """Delete a chunk by ID."""
        ...

    async def get_stats(self) -> VectorStoreStats:
        """Get statistics about the vector store."""
        ...

    async def health_check(self) -> bool:
        """Check if the vector store is healthy and connected."""
        ...
