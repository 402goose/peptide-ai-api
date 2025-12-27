"""
Mock Weaviate vector store implementation for testing.

Provides an in-memory implementation of vector search operations,
allowing tests to run without a real Weaviate connection.
"""

from typing import Any, Optional
from dataclasses import dataclass, field
from copy import deepcopy


@dataclass
class MockChunk:
    """A document chunk stored in the mock vector store."""
    id: str
    content: str
    properties: dict[str, Any] = field(default_factory=dict)
    vector: Optional[list[float]] = None


@dataclass
class MockOutcome:
    """A journey outcome stored in the mock vector store."""
    id: str
    content: str
    properties: dict[str, Any] = field(default_factory=dict)
    vector: Optional[list[float]] = None


class MockVectorStore:
    """
    Mock Weaviate vector store for testing.

    Provides simple keyword-based search (no actual vector similarity)
    for testing purposes.

    Usage:
        store = MockVectorStore()

        # Seed with test data
        await store.index_chunk(
            chunk_id="chunk1",
            content="BPC-157 is a peptide used for healing",
            metadata={"title": "BPC-157 Overview", "source_type": "pubmed"}
        )

        # Search
        results = await store.hybrid_search("BPC-157 healing", limit=5)

        # Check operations
        assert len(store.call_history) > 0
    """

    def __init__(self):
        self._chunks: dict[str, MockChunk] = {}
        self._outcomes: dict[str, MockOutcome] = {}
        self._connected: bool = False
        self._schema_created: bool = False
        self.call_history: list[dict[str, Any]] = []

    async def connect(self) -> None:
        """Establish connection (no-op for mock)."""
        self._connected = True
        self.call_history.append({"operation": "connect"})

    async def close(self) -> None:
        """Close connection (no-op for mock)."""
        self._connected = False
        self.call_history.append({"operation": "close"})

    async def create_schema(self) -> None:
        """Create schema (no-op for mock)."""
        self._schema_created = True
        self.call_history.append({"operation": "create_schema"})

    def _keyword_match_score(self, content: str, query: str) -> float:
        """
        Simple keyword matching score.

        Returns a score between 0 and 1 based on how many query words
        appear in the content.
        """
        content_lower = content.lower()
        query_words = query.lower().split()
        if not query_words:
            return 0.0

        matches = sum(1 for word in query_words if word in content_lower)
        return matches / len(query_words)

    def _matches_peptide_filter(
        self, properties: dict[str, Any], peptide_filter: Optional[list[str]]
    ) -> bool:
        """Check if a document matches the peptide filter."""
        if not peptide_filter:
            return True

        # Check various fields that might contain peptide names
        searchable = " ".join([
            properties.get("title", ""),
            properties.get("content", ""),
            properties.get("peptide", ""),
            " ".join(properties.get("peptides", [])),
        ]).lower()

        return any(peptide.lower() in searchable for peptide in peptide_filter)

    async def hybrid_search(
        self,
        query: str,
        limit: int = 10,
        alpha: float = 0.5,
        peptide_filter: Optional[list[str]] = None,
        include_outcomes: bool = True,
    ) -> list[dict[str, Any]]:
        """
        Perform hybrid search (keyword-based for mock).

        Combines chunk and outcome results based on keyword matching.
        """
        self.call_history.append({
            "operation": "hybrid_search",
            "query": query,
            "limit": limit,
            "alpha": alpha,
            "peptide_filter": peptide_filter,
            "include_outcomes": include_outcomes,
        })

        results: list[tuple[float, dict[str, Any]]] = []

        # Search chunks
        for chunk in self._chunks.values():
            if not self._matches_peptide_filter(chunk.properties, peptide_filter):
                continue

            score = self._keyword_match_score(chunk.content, query)
            if score > 0:
                results.append((score, {
                    "id": chunk.id,
                    "properties": {
                        **chunk.properties,
                        "content": chunk.content,
                    },
                    "score": score,
                    "source": "chunk",
                }))

        # Search outcomes if included
        if include_outcomes:
            for outcome in self._outcomes.values():
                if not self._matches_peptide_filter(outcome.properties, peptide_filter):
                    continue

                score = self._keyword_match_score(outcome.content, query)
                if score > 0:
                    results.append((score, {
                        "id": outcome.id,
                        "properties": {
                            **outcome.properties,
                            "content": outcome.content,
                        },
                        "score": score,
                        "source": "outcome",
                    }))

        # Sort by score and limit
        results.sort(key=lambda x: x[0], reverse=True)
        return [r[1] for r in results[:limit]]

    async def semantic_search(
        self,
        query: str,
        limit: int = 10,
        peptide_filter: Optional[list[str]] = None,
    ) -> list[dict[str, Any]]:
        """
        Perform semantic search (uses keyword matching for mock).
        """
        self.call_history.append({
            "operation": "semantic_search",
            "query": query,
            "limit": limit,
            "peptide_filter": peptide_filter,
        })

        # Use same logic as hybrid search for mock
        return await self.hybrid_search(
            query, limit, alpha=1.0, peptide_filter=peptide_filter, include_outcomes=False
        )

    async def keyword_search(
        self,
        query: str,
        limit: int = 10,
        peptide_filter: Optional[list[str]] = None,
    ) -> list[dict[str, Any]]:
        """
        Perform keyword search.
        """
        self.call_history.append({
            "operation": "keyword_search",
            "query": query,
            "limit": limit,
            "peptide_filter": peptide_filter,
        })

        # Use same logic as hybrid search for mock
        return await self.hybrid_search(
            query, limit, alpha=0.0, peptide_filter=peptide_filter, include_outcomes=False
        )

    async def index_chunk(
        self,
        chunk_id: str,
        content: str,
        metadata: dict[str, Any],
        vector: Optional[list[float]] = None,
    ) -> None:
        """Index a document chunk."""
        self.call_history.append({
            "operation": "index_chunk",
            "chunk_id": chunk_id,
            "content_length": len(content),
            "metadata_keys": list(metadata.keys()),
        })

        self._chunks[chunk_id] = MockChunk(
            id=chunk_id,
            content=content,
            properties=deepcopy(metadata),
            vector=vector,
        )

    async def index_outcome(
        self,
        outcome_id: str,
        content: str,
        metadata: dict[str, Any],
        vector: Optional[list[float]] = None,
    ) -> None:
        """Index a journey outcome."""
        self.call_history.append({
            "operation": "index_outcome",
            "outcome_id": outcome_id,
            "content_length": len(content),
            "metadata_keys": list(metadata.keys()),
        })

        self._outcomes[outcome_id] = MockOutcome(
            id=outcome_id,
            content=content,
            properties=deepcopy(metadata),
            vector=vector,
        )

    async def delete_chunk(self, chunk_id: str) -> bool:
        """Delete a chunk by ID."""
        self.call_history.append({
            "operation": "delete_chunk",
            "chunk_id": chunk_id,
        })

        if chunk_id in self._chunks:
            del self._chunks[chunk_id]
            return True
        return False

    async def get_stats(self) -> dict[str, Any]:
        """Get statistics about the vector store."""
        self.call_history.append({"operation": "get_stats"})

        return {
            "total_chunks": len(self._chunks),
            "total_outcomes": len(self._outcomes),
            "collections": ["PeptideChunk", "JourneyOutcome"],
        }

    async def health_check(self) -> bool:
        """Check if the vector store is healthy."""
        self.call_history.append({"operation": "health_check"})
        return self._connected

    # Helper methods for testing

    def reset(self) -> None:
        """Reset all data and history (helper for tests)."""
        self._chunks = {}
        self._outcomes = {}
        self.call_history = []

    def seed_chunks(self, chunks: list[dict[str, Any]]) -> None:
        """
        Seed the vector store with test chunks.

        Each chunk dict should have: id, content, and optionally metadata.
        """
        for chunk in chunks:
            self._chunks[chunk["id"]] = MockChunk(
                id=chunk["id"],
                content=chunk["content"],
                properties=chunk.get("metadata", {}),
            )

    def seed_outcomes(self, outcomes: list[dict[str, Any]]) -> None:
        """
        Seed the vector store with test outcomes.

        Each outcome dict should have: id, content, and optionally metadata.
        """
        for outcome in outcomes:
            self._outcomes[outcome["id"]] = MockOutcome(
                id=outcome["id"],
                content=outcome["content"],
                properties=outcome.get("metadata", {}),
            )

    def get_operation_count(self, operation: str) -> int:
        """Count how many times an operation was called (helper for tests)."""
        return sum(1 for call in self.call_history if call.get("operation") == operation)

    def get_last_search_query(self) -> Optional[str]:
        """Get the query from the last search operation (helper for tests)."""
        for call in reversed(self.call_history):
            if call.get("operation") in ("hybrid_search", "semantic_search", "keyword_search"):
                return call.get("query")
        return None
