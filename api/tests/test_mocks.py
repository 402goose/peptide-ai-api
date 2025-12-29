"""
Tests for mock implementations.

Verifies that the mock database, LLM, and vector store work correctly
without requiring any external dependencies.
"""

import pytest
from api.tests.mocks import MockDatabase, MockLLMClient, MockVectorStore


class TestMockDatabase:
    """Tests for MockDatabase."""

    @pytest.fixture
    def db(self):
        return MockDatabase()

    @pytest.mark.asyncio
    async def test_insert_and_find_one(self, db):
        """Test basic insert and find operations."""
        collection = db.get_collection("users")

        # Insert a document
        result = await collection.insert_one({
            "user_id": "user-123",
            "name": "Test User",
            "email": "test@example.com",
        })

        assert result.inserted_id is not None

        # Find the document
        doc = await collection.find_one({"user_id": "user-123"})
        assert doc is not None
        assert doc["name"] == "Test User"

    @pytest.mark.asyncio
    async def test_find_returns_none_when_not_found(self, db):
        """Test find_one returns None for missing docs."""
        collection = db.get_collection("users")
        doc = await collection.find_one({"user_id": "nonexistent"})
        assert doc is None

    @pytest.mark.asyncio
    async def test_update_one(self, db):
        """Test update operation."""
        collection = db.get_collection("users")

        await collection.insert_one({
            "user_id": "user-123",
            "name": "Old Name",
        })

        result = await collection.update_one(
            {"user_id": "user-123"},
            {"$set": {"name": "New Name"}}
        )

        assert result.modified_count == 1

        doc = await collection.find_one({"user_id": "user-123"})
        assert doc["name"] == "New Name"

    @pytest.mark.asyncio
    async def test_delete_one(self, db):
        """Test delete operation."""
        collection = db.get_collection("users")

        await collection.insert_one({"user_id": "user-123"})
        result = await collection.delete_one({"user_id": "user-123"})

        assert result.deleted_count == 1
        assert await collection.find_one({"user_id": "user-123"}) is None

    @pytest.mark.asyncio
    async def test_find_many(self, db):
        """Test finding multiple documents."""
        collection = db.get_collection("users")

        await collection.insert_one({"role": "admin", "name": "Admin 1"})
        await collection.insert_one({"role": "admin", "name": "Admin 2"})
        await collection.insert_one({"role": "user", "name": "User 1"})

        cursor = collection.find({"role": "admin"})
        docs = await cursor.to_list(length=10)

        assert len(docs) == 2
        assert all(d["role"] == "admin" for d in docs)

    @pytest.mark.asyncio
    async def test_seed_data(self, db):
        """Test seeding data helper."""
        db.seed_data("users", [
            {"user_id": "1", "name": "User 1"},
            {"user_id": "2", "name": "User 2"},
        ])

        collection = db.get_collection("users")
        count = await collection.count_documents({})
        assert count == 2

    @pytest.mark.asyncio
    async def test_clear_all(self, db):
        """Test clearing all data."""
        db.seed_data("users", [{"id": "1"}])
        db.seed_data("products", [{"id": "1"}])

        db.clear_all()

        users = db.get_collection("users")
        products = db.get_collection("products")
        assert await users.count_documents({}) == 0
        assert await products.count_documents({}) == 0


class TestMockLLMClient:
    """Tests for MockLLMClient."""

    @pytest.fixture
    def llm(self):
        return MockLLMClient()

    @pytest.mark.asyncio
    async def test_chat_completion_default(self, llm):
        """Test default chat completion response."""
        response = await llm.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": "Hello"}]
        )

        # Default response contains the mock response text
        assert response.choices[0].message.content is not None
        assert len(response.choices[0].message.content) > 0

    @pytest.mark.asyncio
    async def test_set_custom_response(self, llm):
        """Test setting custom response for specific message."""
        llm.set_response("Hello", "Hi there!")

        response = await llm.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": "Hello"}]
        )

        assert response.choices[0].message.content == "Hi there!"

    @pytest.mark.asyncio
    async def test_pattern_responses(self, llm):
        """Test pattern-based responses."""
        # Pattern matching uses substring matching (case-insensitive)
        llm.set_pattern_response("bpc-157", "BPC-157 is a healing peptide.")

        response = await llm.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": "Tell me about BPC-157"}]
        )

        assert "BPC-157 is a healing peptide" in response.choices[0].message.content

    @pytest.mark.asyncio
    async def test_streaming(self, llm):
        """Test streaming response."""
        chunks = []
        async for chunk in await llm.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": "test"}],
            stream=True
        ):
            if chunk.choices and chunk.choices[0].delta.content:
                chunks.append(chunk.choices[0].delta.content)

        assert len(chunks) > 0

    @pytest.mark.asyncio
    async def test_call_history(self, llm):
        """Test that calls are recorded."""
        await llm.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": "test"}]
        )

        assert len(llm.call_history) == 1
        assert llm.call_history[0]["model"] == "gpt-4o"


class TestMockVectorStore:
    """Tests for MockVectorStore."""

    @pytest.fixture
    def vector_store(self):
        vs = MockVectorStore()
        vs.reset()  # Ensure clean state
        return vs

    @pytest.mark.asyncio
    async def test_connect_and_close(self, vector_store):
        """Test connection lifecycle."""
        await vector_store.connect()
        assert vector_store._connected

        await vector_store.close()
        assert not vector_store._connected

    @pytest.mark.asyncio
    async def test_hybrid_search(self, vector_store):
        """Test hybrid search with seeded chunks."""
        vector_store.seed_chunks([
            {"id": "1", "content": "BPC-157 helps with healing"},
            {"id": "2", "content": "TB-500 is good for recovery"},
            {"id": "3", "content": "BPC-157 dosing recommendations"},
        ])

        results = await vector_store.hybrid_search("BPC-157", limit=5)

        assert len(results) == 2
        # Content is nested under properties
        assert all("BPC-157" in r["properties"]["content"] for r in results)

    @pytest.mark.asyncio
    async def test_semantic_search(self, vector_store):
        """Test semantic search."""
        vector_store.seed_chunks([
            {"id": "1", "content": "peptide healing properties"},
        ])

        results = await vector_store.semantic_search("healing", limit=5)
        assert len(results) == 1

    @pytest.mark.asyncio
    async def test_keyword_search(self, vector_store):
        """Test keyword search."""
        vector_store.seed_chunks([
            {"id": "1", "content": "dosing schedule"},
            {"id": "2", "content": "side effects"},
        ])

        results = await vector_store.keyword_search("dosing", limit=5)
        assert len(results) == 1
        # Content is nested under properties
        assert "dosing" in results[0]["properties"]["content"]

    @pytest.mark.asyncio
    async def test_index_chunk(self, vector_store):
        """Test indexing a new chunk."""
        await vector_store.index_chunk(
            chunk_id="new-chunk",
            content="New content for indexing",
            metadata={"source": "test"},
        )

        results = await vector_store.hybrid_search("New content", limit=5)
        assert len(results) == 1

    @pytest.mark.asyncio
    async def test_operation_count(self, vector_store):
        """Test operation counting."""
        # Reset call history to ensure clean counting
        vector_store.call_history = []

        # Only call hybrid_search directly (keyword/semantic delegate to it internally)
        await vector_store.hybrid_search("test1", 5)
        await vector_store.hybrid_search("test2", 5)

        assert vector_store.get_operation_count("hybrid_search") == 2
        assert vector_store.get_operation_count("index_chunk") == 0
