"""
Mock MongoDB database implementation for testing.

Provides an in-memory implementation of MongoDB operations,
allowing tests to run without a real database connection.
"""

from typing import Any, Optional, Iterator
from collections import defaultdict
from copy import deepcopy
import re


class MockInsertOneResult:
    """Mock result for insert_one operation."""
    def __init__(self, inserted_id: str):
        self.inserted_id = inserted_id


class MockInsertManyResult:
    """Mock result for insert_many operation."""
    def __init__(self, inserted_ids: list[str]):
        self.inserted_ids = inserted_ids


class MockUpdateResult:
    """Mock result for update operations."""
    def __init__(self, matched_count: int, modified_count: int, upserted_id: Optional[str] = None):
        self.matched_count = matched_count
        self.modified_count = modified_count
        self.upserted_id = upserted_id


class MockDeleteResult:
    """Mock result for delete operations."""
    def __init__(self, deleted_count: int):
        self.deleted_count = deleted_count


class MockCursor:
    """
    Mock async cursor for database queries.

    Supports chaining operations like sort(), skip(), limit().
    """

    def __init__(self, documents: list[dict[str, Any]]):
        self._documents = deepcopy(documents)
        self._sort_key: Optional[tuple[str, int]] = None
        self._skip_count: int = 0
        self._limit_count: Optional[int] = None
        self._index: int = 0

    def sort(self, key_or_list: Any, direction: Optional[int] = None) -> "MockCursor":
        """Sort the cursor results."""
        if isinstance(key_or_list, str):
            self._sort_key = (key_or_list, direction or 1)
        elif isinstance(key_or_list, list) and len(key_or_list) > 0:
            # Take first sort key for simplicity
            self._sort_key = key_or_list[0]
        return self

    def skip(self, skip: int) -> "MockCursor":
        """Skip a number of documents."""
        self._skip_count = skip
        return self

    def limit(self, limit: int) -> "MockCursor":
        """Limit the number of documents."""
        self._limit_count = limit
        return self

    def _apply_operations(self) -> list[dict[str, Any]]:
        """Apply sort, skip, limit to documents."""
        docs = self._documents

        # Apply sort
        if self._sort_key:
            key, direction = self._sort_key
            docs = sorted(
                docs,
                key=lambda x: x.get(key, ""),
                reverse=(direction == -1)
            )

        # Apply skip
        if self._skip_count:
            docs = docs[self._skip_count:]

        # Apply limit
        if self._limit_count is not None:
            docs = docs[:self._limit_count]

        return docs

    async def to_list(self, length: Optional[int] = None) -> list[dict[str, Any]]:
        """Convert cursor to list."""
        docs = self._apply_operations()
        if length is not None:
            docs = docs[:length]
        return deepcopy(docs)

    def __aiter__(self) -> "MockCursor":
        """Async iteration support."""
        self._index = 0
        self._resolved_docs = self._apply_operations()
        return self

    async def __anext__(self) -> dict[str, Any]:
        """Get next document."""
        if self._index >= len(self._resolved_docs):
            raise StopAsyncIteration
        doc = deepcopy(self._resolved_docs[self._index])
        self._index += 1
        return doc


class MockCollection:
    """
    Mock MongoDB collection for testing.

    Stores documents in memory and supports basic CRUD operations.
    """

    def __init__(self, name: str):
        self.name = name
        self._documents: list[dict[str, Any]] = []
        self._indexes: list[dict[str, Any]] = []
        self._id_counter: int = 0

    def _generate_id(self) -> str:
        """Generate a unique document ID."""
        self._id_counter += 1
        return f"mock_id_{self._id_counter}"

    def _matches_filter(self, doc: dict[str, Any], filter: dict[str, Any]) -> bool:
        """Check if a document matches a filter."""
        for key, value in filter.items():
            if key.startswith("$"):
                # Handle special operators
                if key == "$or":
                    if not any(self._matches_filter(doc, sub_filter) for sub_filter in value):
                        return False
                elif key == "$and":
                    if not all(self._matches_filter(doc, sub_filter) for sub_filter in value):
                        return False
                continue

            doc_value = doc.get(key)

            if isinstance(value, dict):
                # Handle operators like $regex, $gte, etc.
                for op, op_value in value.items():
                    if op == "$regex":
                        if not doc_value or not re.search(op_value, str(doc_value), re.IGNORECASE):
                            return False
                    elif op == "$gte":
                        if doc_value is None or doc_value < op_value:
                            return False
                    elif op == "$lte":
                        if doc_value is None or doc_value > op_value:
                            return False
                    elif op == "$gt":
                        if doc_value is None or doc_value <= op_value:
                            return False
                    elif op == "$lt":
                        if doc_value is None or doc_value >= op_value:
                            return False
                    elif op == "$in":
                        if doc_value not in op_value:
                            return False
                    elif op == "$ne":
                        if doc_value == op_value:
                            return False
                    elif op == "$exists":
                        if op_value and key not in doc:
                            return False
                        if not op_value and key in doc:
                            return False
            else:
                if doc_value != value:
                    return False

        return True

    def _apply_update(self, doc: dict[str, Any], update: dict[str, Any]) -> dict[str, Any]:
        """Apply an update operation to a document."""
        updated = deepcopy(doc)

        for op, fields in update.items():
            if op == "$set":
                for key, value in fields.items():
                    updated[key] = value
            elif op == "$unset":
                for key in fields:
                    updated.pop(key, None)
            elif op == "$inc":
                for key, value in fields.items():
                    updated[key] = updated.get(key, 0) + value
            elif op == "$push":
                for key, value in fields.items():
                    if key not in updated:
                        updated[key] = []
                    updated[key].append(value)
            elif op == "$pull":
                for key, value in fields.items():
                    if key in updated and isinstance(updated[key], list):
                        updated[key] = [x for x in updated[key] if x != value]
            elif op == "$setOnInsert":
                # Only applied on upsert, handled separately
                pass
            elif not op.startswith("$"):
                # Direct field update (not using operators)
                updated[op] = fields

        return updated

    async def find_one(
        self, filter: dict[str, Any], *args: Any, **kwargs: Any
    ) -> Optional[dict[str, Any]]:
        """Find a single document matching the filter."""
        for doc in self._documents:
            if self._matches_filter(doc, filter):
                return deepcopy(doc)
        return None

    def find(
        self, filter: Optional[dict[str, Any]] = None, *args: Any, **kwargs: Any
    ) -> MockCursor:
        """Find documents matching the filter."""
        filter = filter or {}
        matching = [doc for doc in self._documents if self._matches_filter(doc, filter)]
        return MockCursor(matching)

    async def insert_one(
        self, document: dict[str, Any], *args: Any, **kwargs: Any
    ) -> MockInsertOneResult:
        """Insert a single document."""
        doc = deepcopy(document)
        if "_id" not in doc:
            doc["_id"] = self._generate_id()
        self._documents.append(doc)
        return MockInsertOneResult(doc["_id"])

    async def insert_many(
        self, documents: list[dict[str, Any]], *args: Any, **kwargs: Any
    ) -> MockInsertManyResult:
        """Insert multiple documents."""
        ids = []
        for document in documents:
            doc = deepcopy(document)
            if "_id" not in doc:
                doc["_id"] = self._generate_id()
            self._documents.append(doc)
            ids.append(doc["_id"])
        return MockInsertManyResult(ids)

    async def update_one(
        self, filter: dict[str, Any], update: dict[str, Any], *args: Any, upsert: bool = False, **kwargs: Any
    ) -> MockUpdateResult:
        """Update a single document."""
        for i, doc in enumerate(self._documents):
            if self._matches_filter(doc, filter):
                self._documents[i] = self._apply_update(doc, update)
                return MockUpdateResult(matched_count=1, modified_count=1)

        # Handle upsert
        if upsert:
            new_doc = deepcopy(filter)
            new_doc = self._apply_update(new_doc, update)
            # Apply $setOnInsert if present
            if "$setOnInsert" in update:
                for key, value in update["$setOnInsert"].items():
                    new_doc[key] = value
            if "_id" not in new_doc:
                new_doc["_id"] = self._generate_id()
            self._documents.append(new_doc)
            return MockUpdateResult(matched_count=0, modified_count=0, upserted_id=new_doc["_id"])

        return MockUpdateResult(matched_count=0, modified_count=0)

    async def update_many(
        self, filter: dict[str, Any], update: dict[str, Any], *args: Any, **kwargs: Any
    ) -> MockUpdateResult:
        """Update multiple documents."""
        matched = 0
        modified = 0
        for i, doc in enumerate(self._documents):
            if self._matches_filter(doc, filter):
                matched += 1
                self._documents[i] = self._apply_update(doc, update)
                modified += 1
        return MockUpdateResult(matched_count=matched, modified_count=modified)

    async def delete_one(
        self, filter: dict[str, Any], *args: Any, **kwargs: Any
    ) -> MockDeleteResult:
        """Delete a single document."""
        for i, doc in enumerate(self._documents):
            if self._matches_filter(doc, filter):
                self._documents.pop(i)
                return MockDeleteResult(deleted_count=1)
        return MockDeleteResult(deleted_count=0)

    async def delete_many(
        self, filter: dict[str, Any], *args: Any, **kwargs: Any
    ) -> MockDeleteResult:
        """Delete multiple documents."""
        original_count = len(self._documents)
        self._documents = [
            doc for doc in self._documents
            if not self._matches_filter(doc, filter)
        ]
        deleted = original_count - len(self._documents)
        return MockDeleteResult(deleted_count=deleted)

    async def count_documents(
        self, filter: dict[str, Any], *args: Any, **kwargs: Any
    ) -> int:
        """Count documents matching the filter."""
        return sum(1 for doc in self._documents if self._matches_filter(doc, filter))

    def aggregate(
        self, pipeline: list[dict[str, Any]], *args: Any, **kwargs: Any
    ) -> MockCursor:
        """Run an aggregation pipeline (simplified implementation)."""
        docs = deepcopy(self._documents)

        for stage in pipeline:
            if "$match" in stage:
                docs = [d for d in docs if self._matches_filter(d, stage["$match"])]
            elif "$sort" in stage:
                for key, direction in reversed(list(stage["$sort"].items())):
                    docs = sorted(docs, key=lambda x: x.get(key, ""), reverse=(direction == -1))
            elif "$limit" in stage:
                docs = docs[:stage["$limit"]]
            elif "$skip" in stage:
                docs = docs[stage["$skip"]:]
            elif "$group" in stage:
                # Simplified group - just return docs as-is for now
                pass
            elif "$project" in stage:
                projected = []
                for doc in docs:
                    new_doc = {}
                    for key, include in stage["$project"].items():
                        if include and key in doc:
                            new_doc[key] = doc[key]
                    projected.append(new_doc)
                docs = projected

        return MockCursor(docs)

    async def create_index(
        self, keys: Any, *args: Any, **kwargs: Any
    ) -> str:
        """Create an index (no-op for mock)."""
        index_name = f"index_{len(self._indexes)}"
        self._indexes.append({"keys": keys, "name": index_name, **kwargs})
        return index_name

    def clear(self) -> None:
        """Clear all documents (helper for tests)."""
        self._documents = []


class MockDatabase:
    """
    Mock MongoDB database for testing.

    Stores collections in memory and provides the same interface
    as Motor's AsyncIOMotorDatabase.
    """

    def __init__(self, name: str = "test_db"):
        self.name = name
        self._collections: dict[str, MockCollection] = defaultdict(
            lambda: MockCollection("default")
        )

    def __getattr__(self, name: str) -> MockCollection:
        """Get a collection by attribute access."""
        if name.startswith("_"):
            raise AttributeError(name)
        if name not in self._collections:
            self._collections[name] = MockCollection(name)
        return self._collections[name]

    def __getitem__(self, name: str) -> MockCollection:
        """Get a collection by item access."""
        if name not in self._collections:
            self._collections[name] = MockCollection(name)
        return self._collections[name]

    def get_collection(self, name: str) -> MockCollection:
        """Get a collection by name."""
        return self[name]

    async def list_collection_names(self) -> list[str]:
        """List all collection names."""
        return list(self._collections.keys())

    def clear_all(self) -> None:
        """Clear all collections (helper for tests)."""
        for collection in self._collections.values():
            collection.clear()

    def seed_data(self, collection_name: str, documents: list[dict[str, Any]]) -> None:
        """Seed a collection with test data (helper for tests)."""
        collection = self[collection_name]
        for doc in documents:
            collection._documents.append(deepcopy(doc))
