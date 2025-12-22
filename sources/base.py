"""
Peptide AI - Base Adapter

Abstract base class for all data source adapters.
"""

from abc import ABC, abstractmethod
from typing import AsyncGenerator, List, Optional
from datetime import datetime

from models.documents import RawDocument, SourceType


class BaseAdapter(ABC):
    """
    Abstract base class for data source adapters

    All adapters should implement:
    - search(): Find documents matching a query
    - fetch(): Get a specific document by ID
    - stream(): Stream documents for bulk ingestion
    """

    source_type: SourceType

    def __init__(self, config: dict = None):
        """
        Initialize adapter with optional config

        Config may include:
        - api_key: API key for the source
        - rate_limit: Requests per second
        - timeout: Request timeout in seconds
        """
        self.config = config or {}
        self.rate_limit = self.config.get("rate_limit", 3)  # Default 3 req/sec
        self.timeout = self.config.get("timeout", 30)

    @abstractmethod
    async def search(
        self,
        query: str,
        max_results: int = 100,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> List[RawDocument]:
        """
        Search for documents matching a query

        Args:
            query: Search query (source-specific syntax)
            max_results: Maximum number of results to return
            start_date: Filter to documents after this date
            end_date: Filter to documents before this date

        Returns:
            List of RawDocument objects
        """
        pass

    @abstractmethod
    async def fetch(self, source_id: str) -> Optional[RawDocument]:
        """
        Fetch a specific document by its source ID

        Args:
            source_id: The ID of the document in the source system

        Returns:
            RawDocument if found, None otherwise
        """
        pass

    @abstractmethod
    async def stream(
        self,
        query: str,
        batch_size: int = 100,
        start_date: Optional[datetime] = None
    ) -> AsyncGenerator[List[RawDocument], None]:
        """
        Stream documents for bulk ingestion

        Yields batches of documents for efficient processing.

        Args:
            query: Search query
            batch_size: Number of documents per batch
            start_date: Only fetch documents after this date

        Yields:
            Batches of RawDocument objects
        """
        pass

    def _build_citation(self, doc: dict) -> str:
        """
        Build a citation string from document metadata

        Override in subclasses for source-specific formatting.
        """
        authors = doc.get("authors", [])
        title = doc.get("title", "")
        year = doc.get("publication_date", datetime.now()).year if doc.get("publication_date") else ""

        if authors:
            first_author = authors[0].split()[-1] if authors[0] else "Unknown"
            author_str = f"{first_author} et al." if len(authors) > 1 else first_author
        else:
            author_str = "Unknown"

        return f"{author_str}, {year}. {title}"
