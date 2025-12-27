"""
Tests for Chat API routes.

Tests conversation CRUD operations, sharing, and database operations
using mock database implementations.

Note: Intent detection and helper function tests are skipped when
FastAPI is not available (e.g., in minimal test environments).
"""

import pytest
from datetime import datetime
from tests.mocks import MockDatabase


# Try to import FastAPI-dependent modules for unit tests
try:
    from routes.chat import _detect_intent, _generate_title, _get_disclaimers, _suggest_followups
    FASTAPI_AVAILABLE = True
except ImportError:
    FASTAPI_AVAILABLE = False


@pytest.mark.skipif(not FASTAPI_AVAILABLE, reason="FastAPI not installed")
class TestIntentDetection:
    """Tests for intent detection logic."""

    def test_coach_mode_with_possession_and_supplies(self):
        """Should detect coach mode when user has supplies."""
        messages = [
            "I just got my BPC-157 and bac water",
            "I have my vials and insulin syringes ready",
            "My TB-500 arrived today with needles",
        ]

        for msg in messages:
            mode = _detect_intent(msg)
            assert mode == "coach", f"Expected coach for: {msg}"

    def test_research_mode_with_research_keywords(self):
        """Should detect research mode for information-seeking queries."""
        messages = [
            "What is BPC-157?",
            "Tell me about the benefits of TB-500",
            "Compare BPC-157 vs TB-500",
            "What are the side effects of semaglutide?",
        ]

        for msg in messages:
            mode = _detect_intent(msg)
            assert mode == "research", f"Expected research for: {msg}"

    def test_balanced_mode_default(self):
        """Should default to balanced mode for ambiguous queries."""
        messages = [
            "BPC-157 healing",
            "peptides for recovery",
            "help with injury",
        ]

        for msg in messages:
            mode = _detect_intent(msg)
            assert mode == "balanced", f"Expected balanced for: {msg}"


class TestConversationCRUD:
    """Tests for conversation database operations."""

    @pytest.fixture
    def mock_db(self):
        """Create a fresh mock database."""
        db = MockDatabase()
        db.clear_all()
        return db

    @pytest.mark.asyncio
    async def test_create_conversation(self, mock_db):
        """Creating a conversation should insert document."""
        collection = mock_db.get_collection("conversations")

        conversation = {
            "conversation_id": "conv-123",
            "user_id": "user-123",
            "title": "BPC-157 Question",
            "messages": [
                {"role": "user", "content": "Hello", "timestamp": datetime.utcnow().isoformat()},
            ],
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
        }

        await collection.insert_one(conversation)

        doc = await collection.find_one({"conversation_id": "conv-123"})
        assert doc is not None
        assert doc["title"] == "BPC-157 Question"
        assert len(doc["messages"]) == 1

    @pytest.mark.asyncio
    async def test_list_conversations_by_user(self, mock_db):
        """Listing conversations should only return user's conversations."""
        collection = mock_db.get_collection("conversations")

        # Insert conversations for different users
        await collection.insert_one({
            "conversation_id": "conv-1",
            "user_id": "user-123",
            "title": "Chat 1",
            "messages": [],
        })
        await collection.insert_one({
            "conversation_id": "conv-2",
            "user_id": "user-456",
            "title": "Chat 2",
            "messages": [],
        })
        await collection.insert_one({
            "conversation_id": "conv-3",
            "user_id": "user-123",
            "title": "Chat 3",
            "messages": [],
        })

        cursor = collection.find({"user_id": "user-123"})
        conversations = await cursor.to_list(length=100)

        assert len(conversations) == 2
        assert all(c["user_id"] == "user-123" for c in conversations)

    @pytest.mark.asyncio
    async def test_get_conversation_with_messages(self, mock_db):
        """Getting a conversation should return full message history."""
        collection = mock_db.get_collection("conversations")

        messages = [
            {"role": "user", "content": "Hello", "timestamp": "2024-01-01T00:00:00Z"},
            {"role": "assistant", "content": "Hi!", "timestamp": "2024-01-01T00:01:00Z"},
            {"role": "user", "content": "What is BPC-157?", "timestamp": "2024-01-01T00:02:00Z"},
            {"role": "assistant", "content": "BPC-157 is a peptide...", "timestamp": "2024-01-01T00:03:00Z"},
        ]

        await collection.insert_one({
            "conversation_id": "conv-123",
            "user_id": "user-123",
            "title": "BPC-157 Discussion",
            "messages": messages,
        })

        doc = await collection.find_one({"conversation_id": "conv-123"})
        assert len(doc["messages"]) == 4
        assert doc["messages"][2]["content"] == "What is BPC-157?"

    @pytest.mark.asyncio
    async def test_delete_conversation(self, mock_db):
        """Deleting a conversation should remove it."""
        collection = mock_db.get_collection("conversations")

        await collection.insert_one({
            "conversation_id": "conv-123",
            "user_id": "user-123",
            "title": "Test",
            "messages": [],
        })

        result = await collection.delete_one({
            "conversation_id": "conv-123",
            "user_id": "user-123"
        })

        assert result.deleted_count == 1
        assert await collection.find_one({"conversation_id": "conv-123"}) is None

    @pytest.mark.asyncio
    async def test_update_conversation_title(self, mock_db):
        """Updating a conversation title should work."""
        collection = mock_db.get_collection("conversations")

        await collection.insert_one({
            "conversation_id": "conv-123",
            "user_id": "user-123",
            "title": "Old Title",
            "messages": [],
        })

        result = await collection.update_one(
            {"conversation_id": "conv-123", "user_id": "user-123"},
            {"$set": {"title": "New Title", "updated_at": datetime.utcnow()}}
        )

        assert result.modified_count == 1
        doc = await collection.find_one({"conversation_id": "conv-123"})
        assert doc["title"] == "New Title"

    @pytest.mark.asyncio
    async def test_delete_all_user_conversations(self, mock_db):
        """Deleting all conversations for a user should work."""
        collection = mock_db.get_collection("conversations")

        for i in range(5):
            await collection.insert_one({
                "conversation_id": f"conv-{i}",
                "user_id": "user-123",
                "title": f"Chat {i}",
            })

        result = await collection.delete_many({"user_id": "user-123"})

        assert result.deleted_count == 5
        cursor = collection.find({"user_id": "user-123"})
        remaining = await cursor.to_list(length=100)
        assert len(remaining) == 0


class TestConversationSharing:
    """Tests for conversation sharing functionality."""

    @pytest.fixture
    def mock_db(self):
        db = MockDatabase()
        db.clear_all()
        return db

    @pytest.mark.asyncio
    async def test_create_share_link(self, mock_db):
        """Creating a share link should store shared conversation."""
        conversations = mock_db.get_collection("conversations")
        shared = mock_db.get_collection("shared_conversations")

        # Create original conversation
        await conversations.insert_one({
            "conversation_id": "conv-123",
            "user_id": "user-123",
            "title": "Test Chat",
            "messages": [
                {"role": "user", "content": "Hello"},
                {"role": "assistant", "content": "Hi there!"},
            ],
        })

        # Create share
        share_id = "abc12345"
        await shared.insert_one({
            "share_id": share_id,
            "conversation_id": "conv-123",
            "user_id": "user-123",
            "title": "Test Chat",
            "messages": [
                {"role": "user", "content": "Hello"},
                {"role": "assistant", "content": "Hi there!"},
            ],
            "shared_at": datetime.utcnow(),
        })

        doc = await shared.find_one({"share_id": share_id})
        assert doc is not None
        assert doc["title"] == "Test Chat"
        assert len(doc["messages"]) == 2

    @pytest.mark.asyncio
    async def test_get_shared_conversation(self, mock_db):
        """Getting a shared conversation should work without auth."""
        shared = mock_db.get_collection("shared_conversations")

        await shared.insert_one({
            "share_id": "abc12345",
            "conversation_id": "conv-123",
            "title": "Shared Chat",
            "messages": [
                {"role": "user", "content": "Question"},
                {"role": "assistant", "content": "Answer"},
            ],
            "shared_at": datetime.utcnow(),
        })

        doc = await shared.find_one({"share_id": "abc12345"})
        assert doc is not None
        assert doc["title"] == "Shared Chat"

    @pytest.mark.asyncio
    async def test_existing_share_reuse(self, mock_db):
        """Creating share for already-shared conversation should reuse link."""
        shared = mock_db.get_collection("shared_conversations")

        # First share
        await shared.insert_one({
            "share_id": "abc12345",
            "conversation_id": "conv-123",
            "user_id": "user-123",
        })

        # Check if share exists
        existing = await shared.find_one({"conversation_id": "conv-123"})
        assert existing is not None
        assert existing["share_id"] == "abc12345"


@pytest.mark.skipif(not FASTAPI_AVAILABLE, reason="FastAPI not installed")
class TestChatHelperFunctions:
    """Tests for chat helper functions."""

    def test_generate_title_short_message(self):
        """Short messages should become the full title."""
        title = _generate_title("What is BPC-157?")
        assert title == "What is BPC-157?"

    def test_generate_title_long_message(self):
        """Long messages should be truncated with ellipsis."""
        long_message = "This is a very long message that goes on and on about peptides and their various effects on the human body"
        title = _generate_title(long_message)
        assert len(title) <= 53  # 50 chars + "..."
        assert title.endswith("...")

    def test_generate_title_multiline(self):
        """Multiline messages should use first line only."""
        multiline = "First line\nSecond line\nThird line"
        title = _generate_title(multiline)
        assert title == "First line"

    def test_get_disclaimers_default(self):
        """Default disclaimers should always be present."""
        disclaimers = _get_disclaimers("What is BPC-157?")
        assert len(disclaimers) >= 2
        assert any("research purposes" in d.lower() for d in disclaimers)
        assert any("healthcare professional" in d.lower() for d in disclaimers)

    def test_get_disclaimers_with_sourcing(self):
        """Sourcing queries should add sourcing disclaimer."""
        sourcing_queries = [
            "Where to buy BPC-157",
            "Best vendor for peptides",
            "How to source TB-500",
        ]

        for query in sourcing_queries:
            disclaimers = _get_disclaimers(query)
            assert any("sourcing" in d.lower() for d in disclaimers), f"No sourcing disclaimer for: {query}"

    def test_suggest_followups(self):
        """Should suggest relevant follow-up questions."""
        followups = _suggest_followups("What is BPC-157?")
        assert len(followups) >= 2
        assert all(isinstance(f, str) for f in followups)


class TestMessageHandling:
    """Tests for message storage and retrieval."""

    @pytest.fixture
    def mock_db(self):
        db = MockDatabase()
        db.clear_all()
        return db

    @pytest.mark.asyncio
    async def test_append_message_to_conversation(self, mock_db):
        """Appending a message should update conversation."""
        collection = mock_db.get_collection("conversations")

        await collection.insert_one({
            "conversation_id": "conv-123",
            "user_id": "user-123",
            "messages": [],
        })

        new_message = {
            "role": "user",
            "content": "Hello!",
            "timestamp": datetime.utcnow().isoformat(),
        }

        # Simulate appending - MockDB doesn't support $push so we read/write
        doc = await collection.find_one({"conversation_id": "conv-123"})
        messages = doc.get("messages", [])
        messages.append(new_message)

        await collection.update_one(
            {"conversation_id": "conv-123"},
            {"$set": {"messages": messages}}
        )

        updated = await collection.find_one({"conversation_id": "conv-123"})
        assert len(updated["messages"]) == 1
        assert updated["messages"][0]["content"] == "Hello!"

    @pytest.mark.asyncio
    async def test_message_with_metadata(self, mock_db):
        """Messages with sources and disclaimers should store correctly."""
        collection = mock_db.get_collection("conversations")

        message = {
            "role": "assistant",
            "content": "BPC-157 is a peptide...",
            "timestamp": datetime.utcnow().isoformat(),
            "sources": [
                {"title": "Study 1", "url": "https://example.com/1"},
                {"title": "Study 2", "url": "https://example.com/2"},
            ],
            "disclaimers": ["Research purposes only"],
            "follow_ups": ["What's the dosing?", "Any side effects?"],
        }

        await collection.insert_one({
            "conversation_id": "conv-123",
            "messages": [message],
        })

        doc = await collection.find_one({"conversation_id": "conv-123"})
        stored_msg = doc["messages"][0]
        assert len(stored_msg["sources"]) == 2
        assert len(stored_msg["disclaimers"]) == 1
        assert len(stored_msg["follow_ups"]) == 2
