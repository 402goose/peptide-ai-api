"""
Pytest fixtures for Peptide AI API tests.

Provides mock implementations for all external services,
enabling tests to run entirely in-memory without network calls.
"""

import pytest
import pytest_asyncio
from typing import AsyncIterator

from httpx import AsyncClient, ASGITransport

from tests.mocks import MockDatabase, MockLLMClient, MockVectorStore


# ============================================================================
# Mock Service Fixtures
# ============================================================================


@pytest.fixture
def mock_db() -> MockDatabase:
    """Create a fresh mock database instance."""
    return MockDatabase()


@pytest.fixture
def mock_llm() -> MockLLMClient:
    """Create a fresh mock LLM client instance."""
    return MockLLMClient()


@pytest.fixture
def mock_vector_store() -> MockVectorStore:
    """Create a fresh mock vector store instance."""
    return MockVectorStore()


# ============================================================================
# Application Fixtures with Dependency Override
# ============================================================================


@pytest_asyncio.fixture
async def app_with_mocks(
    mock_db: MockDatabase,
    mock_llm: MockLLMClient,
    mock_vector_store: MockVectorStore,
):
    """
    Create FastAPI app with all dependencies mocked.

    Uses the setter functions in deps.py to inject mock implementations.
    """
    import deps
    from main import app

    # Reset state before test
    deps.reset_for_testing()

    # Inject mocks using the setter functions
    deps.set_database(mock_db)
    deps.set_weaviate(mock_vector_store)

    yield app, mock_db, mock_llm, mock_vector_store

    # Reset state after test
    deps.reset_for_testing()


@pytest_asyncio.fixture
async def client(app_with_mocks) -> AsyncIterator[AsyncClient]:
    """
    Create an async HTTP client for testing API endpoints.

    Usage:
        async def test_endpoint(client):
            response = await client.get("/health")
            assert response.status_code == 200
    """
    app, mock_db, mock_llm, mock_vector_store = app_with_mocks

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest_asyncio.fixture
async def authenticated_client(client: AsyncClient) -> AsyncClient:
    """
    Create an authenticated client with a valid API key header.
    """
    client.headers["X-API-Key"] = "test-api-key"
    return client


# ============================================================================
# Test Data Fixtures
# ============================================================================


@pytest.fixture
def sample_user() -> dict:
    """Sample user data for testing."""
    return {
        "user_id": "test-user-123",
        "email": "test@example.com",
        "subscription_tier": "pro",
        "created_at": "2024-01-01T00:00:00Z",
    }


@pytest.fixture
def sample_conversation() -> dict:
    """Sample conversation data for testing."""
    return {
        "conversation_id": "conv-123",
        "user_id": "test-user-123",
        "title": "Test Conversation",
        "messages": [
            {"role": "user", "content": "What is BPC-157?"},
            {"role": "assistant", "content": "BPC-157 is a peptide..."},
        ],
        "created_at": "2024-01-01T00:00:00Z",
        "updated_at": "2024-01-01T00:00:00Z",
    }


@pytest.fixture
def sample_journey() -> dict:
    """Sample journey data for testing."""
    return {
        "journey_id": "journey-123",
        "user_id": "test-user-123",
        "title": "My BPC-157 Journey",
        "primary_peptide": "BPC-157",
        "status": "active",
        "goals": ["Healing", "Recovery"],
        "protocol": {
            "peptide": "BPC-157",
            "dose_mcg": 250,
            "frequency": "twice daily",
            "duration_weeks": 4,
        },
        "start_date": "2024-01-01",
        "created_at": "2024-01-01T00:00:00Z",
    }


@pytest.fixture
def sample_chunks() -> list[dict]:
    """Sample vector store chunks for RAG testing."""
    return [
        {
            "chunk_id": "chunk-1",
            "content": "BPC-157 is a synthetic peptide with healing properties.",
            "source": "research-paper-1",
            "metadata": {"peptide": "BPC-157", "topic": "overview"},
        },
        {
            "chunk_id": "chunk-2",
            "content": "Typical BPC-157 dosing ranges from 200-500mcg twice daily.",
            "source": "dosing-guide",
            "metadata": {"peptide": "BPC-157", "topic": "dosing"},
        },
        {
            "chunk_id": "chunk-3",
            "content": "BPC-157 may support gut healing and tissue repair.",
            "source": "research-paper-2",
            "metadata": {"peptide": "BPC-157", "topic": "benefits"},
        },
    ]


# ============================================================================
# Helper Fixtures
# ============================================================================


@pytest.fixture
def seeded_db(mock_db: MockDatabase, sample_user: dict, sample_conversation: dict):
    """Database pre-seeded with common test data."""
    mock_db.seed_data("users", [sample_user])
    mock_db.seed_data("conversations", [sample_conversation])
    return mock_db


@pytest.fixture
def seeded_vector_store(mock_vector_store: MockVectorStore, sample_chunks: list[dict]):
    """Vector store pre-seeded with sample chunks."""
    mock_vector_store.seed_chunks(sample_chunks)
    return mock_vector_store


# ============================================================================
# Clerk Auth Mocking
# ============================================================================


@pytest.fixture
def mock_clerk_user():
    """Mock Clerk user for authenticated routes."""
    return {
        "id": "user_test123",
        "email_addresses": [{"email_address": "test@example.com"}],
        "first_name": "Test",
        "last_name": "User",
    }


@pytest.fixture
def auth_headers(mock_clerk_user) -> dict:
    """Headers for authenticated requests."""
    return {
        "X-Clerk-User-Id": mock_clerk_user["id"],
        "Authorization": "Bearer test-token",
    }
