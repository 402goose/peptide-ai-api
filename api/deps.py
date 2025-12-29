"""
Peptide AI - Dependency Injection

Database connections and shared dependencies for FastAPI.
Supports protocol-based injection for testing.
"""

from typing import Optional, Union, Any
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from functools import lru_cache
import os

from api.storage.weaviate_client import WeaviateClient
from api.protocols import IDatabase, IVectorStore


def _build_mongo_url() -> str:
    """Build MongoDB URL from environment, handling password escaping"""
    # Check MONGODB_URL first (user-configured)
    mongo_url = os.getenv("MONGODB_URL")
    if mongo_url and mongo_url != "mongodb://localhost:27017":
        return mongo_url

    # Fall back to MONGO_PUBLIC_URL
    mongo_url = os.getenv("MONGO_PUBLIC_URL")
    if mongo_url:
        return mongo_url

    # Last resort: local
    return "mongodb://localhost:27017"

# Global database connection
# Supports both real Motor client and mock implementations
_db_client: Optional[AsyncIOMotorClient] = None
_db: Optional[Union[AsyncIOMotorDatabase, IDatabase]] = None

# Global Weaviate client
# Supports both real WeaviateClient and mock implementations
_weaviate: Optional[Union[WeaviateClient, IVectorStore]] = None

# Flag to indicate if we're in test mode (skip initialization checks)
_test_mode: bool = False


class Settings:
    """Application settings from environment"""

    # Database (built from components to handle password escaping)
    mongodb_url: str = _build_mongo_url()
    mongodb_database: str = os.getenv("MONGODB_DATABASE", "peptide_ai")

    # API Keys
    api_key_header: str = "X-API-Key"
    master_api_key: str = os.getenv("PEPTIDE_AI_MASTER_KEY", "dev-key-change-me")

    # Rate limiting
    rate_limit_requests: int = int(os.getenv("RATE_LIMIT_REQUESTS", "60"))
    rate_limit_window: int = int(os.getenv("RATE_LIMIT_WINDOW", "60"))  # seconds

    # Subscription tier limits (requests per minute)
    tier_limits: dict = {
        "free": 10,
        "pro": 60,
        "pro_ship": 60,
        "creator": 120,
        "admin": 1000
    }

    # LLM Configuration (supports OpenAI or Ollama)
    llm_provider: str = os.getenv("LLM_PROVIDER", "ollama")  # "openai" or "ollama"
    openai_api_key: str = os.getenv("OPENAI_API_KEY", "")
    openai_model: str = os.getenv("OPENAI_MODEL", "gpt-4o")

    # Ollama (local LLM)
    ollama_url: str = os.getenv("OLLAMA_URL", "http://host.docker.internal:11434")
    ollama_model: str = os.getenv("OLLAMA_MODEL", "llama3.2")

    # Weaviate
    weaviate_url: str = os.getenv("WEAVIATE_URL", "http://localhost:8080")
    weaviate_api_key: str = os.getenv("WEAVIATE_API_KEY", "")

    # Redis (for rate limiting and caching)
    redis_url: str = os.getenv("REDIS_URL", "redis://localhost:6379")


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance"""
    return Settings()


async def init_database():
    """Initialize database connection"""
    global _db_client, _db

    settings = get_settings()
    _db_client = AsyncIOMotorClient(settings.mongodb_url)
    _db = _db_client[settings.mongodb_database]

    # Create indexes
    await _create_indexes(_db)


async def _create_indexes(db: AsyncIOMotorDatabase):
    """Create necessary database indexes"""
    # Users
    await db.users.create_index("user_id", unique=True)
    await db.users.create_index("subscription_tier")

    # Journeys
    await db.journeys.create_index("journey_id", unique=True)
    await db.journeys.create_index("user_id")
    await db.journeys.create_index([("user_id", 1), ("status", 1)])
    await db.journeys.create_index("primary_peptide")

    # Dose logs
    await db.dose_logs.create_index([("journey_id", 1), ("timestamp", -1)])

    # Symptom logs
    await db.symptom_logs.create_index([("journey_id", 1), ("log_date", 1)], unique=True)

    # Journey outcomes (for RAG)
    await db.journey_outcomes.create_index("journey_id", unique=True)
    await db.journey_outcomes.create_index("peptide")
    await db.journey_outcomes.create_index([("peptide", 1), ("overall_efficacy", -1)])

    # Peptide stats
    await db.peptide_stats.create_index("peptide", unique=True)

    # API keys
    await db.api_keys.create_index("key_hash", unique=True)
    await db.api_keys.create_index("user_id")

    # Conversations (for chat history)
    await db.conversations.create_index("conversation_id", unique=True)
    await db.conversations.create_index([("user_id", 1), ("updated_at", -1)])

    # Rate limiting
    await db.rate_limits.create_index("key", unique=True)
    await db.rate_limits.create_index("expires_at", expireAfterSeconds=0)

    # Affiliate & Holistic Products
    await db.products.create_index("product_id", unique=True)
    await db.products.create_index("name")
    await db.products.create_index("product_type")
    await db.products.create_index([("name", "text")])

    await db.symptoms.create_index("symptom_id", unique=True)
    await db.symptoms.create_index("slug", unique=True)
    await db.symptoms.create_index("category")
    await db.symptoms.create_index([("name", "text"), ("keywords", "text")])

    await db.lab_tests.create_index("test_id", unique=True)
    await db.lab_tests.create_index("name")

    await db.symptom_product_mappings.create_index([("symptom_id", 1), ("product_id", 1)], unique=True)

    await db.affiliate_clicks.create_index("click_id", unique=True)
    await db.affiliate_clicks.create_index([("user_id", 1), ("clicked_at", -1)])
    await db.affiliate_clicks.create_index("product_id")
    await db.affiliate_clicks.create_index("symptom_id")
    await db.affiliate_clicks.create_index("source")

    await db.affiliate_conversions.create_index("conversion_id", unique=True)
    await db.affiliate_conversions.create_index("click_id")

    await db.symptom_searches.create_index("search_id", unique=True)
    await db.symptom_searches.create_index([("user_id", 1), ("searched_at", -1)])
    await db.symptom_searches.create_index("query")


async def close_database():
    """Close database connection"""
    global _db_client
    if _db_client:
        _db_client.close()


def get_database() -> Union[AsyncIOMotorDatabase, IDatabase]:
    """Get database instance for dependency injection.

    Returns either a real AsyncIOMotorDatabase or a mock IDatabase.
    """
    if _db is None:
        raise RuntimeError("Database not initialized. Call init_database() first.")
    return _db


def set_database(db: Union[AsyncIOMotorDatabase, IDatabase]) -> None:
    """Set database instance for testing.

    Allows injecting a mock database implementation.

    Args:
        db: Database instance (real or mock)
    """
    global _db, _test_mode
    _db = db
    _test_mode = True


async def init_weaviate():
    """Initialize Weaviate connection and create schema"""
    global _weaviate

    settings = get_settings()
    _weaviate = WeaviateClient(
        url=settings.weaviate_url,
        api_key=settings.weaviate_api_key if settings.weaviate_api_key else None,
        openai_api_key=settings.openai_api_key
    )
    await _weaviate.connect()
    await _weaviate.create_schema()


async def close_weaviate():
    """Close Weaviate connection"""
    global _weaviate
    if _weaviate:
        await _weaviate.close()


def get_weaviate() -> Union[WeaviateClient, IVectorStore]:
    """Get Weaviate client instance for dependency injection.

    Returns either a real WeaviateClient or a mock IVectorStore.
    """
    if _weaviate is None:
        raise RuntimeError("Weaviate not initialized. Call init_weaviate() first.")
    return _weaviate


def set_weaviate(client: Union[WeaviateClient, IVectorStore]) -> None:
    """Set Weaviate client instance for testing.

    Allows injecting a mock vector store implementation.

    Args:
        client: Weaviate client instance (real or mock)
    """
    global _weaviate, _test_mode
    _weaviate = client
    _test_mode = True


def reset_for_testing() -> None:
    """Reset all global state for testing.

    Call this in test fixtures to ensure clean state between tests.
    """
    global _db_client, _db, _weaviate, _test_mode
    _db_client = None
    _db = None
    _weaviate = None
    _test_mode = False
    # Clear settings cache
    get_settings.cache_clear()


def is_test_mode() -> bool:
    """Check if running in test mode."""
    return _test_mode
