"""
Database protocol for MongoDB operations.

Defines the interface for database operations, enabling mock implementations
for testing without requiring a real MongoDB connection.
"""

from typing import Protocol, AsyncIterator, Any, Optional, runtime_checkable, Dict, List


@runtime_checkable
class ICollection(Protocol):
    """Protocol for a database collection (like MongoDB collection)."""

    async def find_one(
        self, filter: Dict[str, Any], *args: Any, **kwargs: Any
    ) -> Optional[Dict[str, Any]]:
        """Find a single document matching the filter."""
        ...

    def find(
        self, filter: Dict[str, Any], *args: Any, **kwargs: Any
    ) -> "IAsyncCursor":
        """Find documents matching the filter. Returns a cursor."""
        ...

    async def insert_one(
        self, document: Dict[str, Any], *args: Any, **kwargs: Any
    ) -> Any:
        """Insert a single document."""
        ...

    async def insert_many(
        self, documents: List[Dict[str, Any]], *args: Any, **kwargs: Any
    ) -> Any:
        """Insert multiple documents."""
        ...

    async def update_one(
        self, filter: Dict[str, Any], update: Dict[str, Any], *args: Any, **kwargs: Any
    ) -> Any:
        """Update a single document."""
        ...

    async def update_many(
        self, filter: Dict[str, Any], update: Dict[str, Any], *args: Any, **kwargs: Any
    ) -> Any:
        """Update multiple documents."""
        ...

    async def delete_one(
        self, filter: Dict[str, Any], *args: Any, **kwargs: Any
    ) -> Any:
        """Delete a single document."""
        ...

    async def delete_many(
        self, filter: Dict[str, Any], *args: Any, **kwargs: Any
    ) -> Any:
        """Delete multiple documents."""
        ...

    async def count_documents(
        self, filter: Dict[str, Any], *args: Any, **kwargs: Any
    ) -> int:
        """Count documents matching the filter."""
        ...

    def aggregate(
        self, pipeline: List[Dict[str, Any]], *args: Any, **kwargs: Any
    ) -> "IAsyncCursor":
        """Run an aggregation pipeline."""
        ...

    async def create_index(
        self, keys: Any, *args: Any, **kwargs: Any
    ) -> str:
        """Create an index on the collection."""
        ...


@runtime_checkable
class IAsyncCursor(Protocol):
    """Protocol for async database cursor."""

    def sort(self, key_or_list: Any, direction: Optional[int] = None) -> "IAsyncCursor":
        """Sort the cursor results."""
        ...

    def skip(self, skip: int) -> "IAsyncCursor":
        """Skip a number of documents."""
        ...

    def limit(self, limit: int) -> "IAsyncCursor":
        """Limit the number of documents."""
        ...

    async def to_list(self, length: Optional[int] = None) -> List[Dict[str, Any]]:
        """Convert cursor to list."""
        ...

    def __aiter__(self) -> "IAsyncCursor":
        """Async iteration support."""
        ...

    async def __anext__(self) -> Dict[str, Any]:
        """Get next document."""
        ...


@runtime_checkable
class IDatabase(Protocol):
    """
    Protocol for database access.

    This matches the Motor AsyncIOMotorDatabase interface for MongoDB,
    allowing seamless substitution of mock implementations for testing.
    """

    def __getattr__(self, name: str) -> ICollection:
        """Get a collection by attribute access (e.g., db.users)."""
        ...

    def __getitem__(self, name: str) -> ICollection:
        """Get a collection by item access (e.g., db['users'])."""
        ...

    def get_collection(self, name: str) -> ICollection:
        """Get a collection by name."""
        ...

    async def list_collection_names(self) -> List[str]:
        """List all collection names."""
        ...
