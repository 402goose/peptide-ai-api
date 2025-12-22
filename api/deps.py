"""
Peptide AI - Dependency Injection

Database connections and shared dependencies for FastAPI.
"""

from typing import Optional
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from functools import lru_cache
import os

from storage.weaviate_client import WeaviateClient

# Global database connection
_db_client: Optional[AsyncIOMotorClient] = None
_db: Optional[AsyncIOMotorDatabase] = None

# Global Weaviate client
_weaviate: Optional[WeaviateClient] = None


class Settings:
    """Application settings from environment"""

    # Database
    mongodb_url: str = os.getenv("MONGODB_URL", "mongodb://localhost:27017")
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


async def close_database():
    """Close database connection"""
    global _db_client
    if _db_client:
        _db_client.close()


def get_database() -> AsyncIOMotorDatabase:
    """Get database instance for dependency injection"""
    if _db is None:
        raise RuntimeError("Database not initialized. Call init_database() first.")
    return _db


async def init_weaviate():
    """Initialize Weaviate connection"""
    global _weaviate

    settings = get_settings()
    _weaviate = WeaviateClient(
        url=settings.weaviate_url,
        openai_api_key=settings.openai_api_key
    )
    await _weaviate.connect()


async def close_weaviate():
    """Close Weaviate connection"""
    global _weaviate
    if _weaviate:
        await _weaviate.close()


def get_weaviate() -> WeaviateClient:
    """Get Weaviate client instance for dependency injection"""
    if _weaviate is None:
        raise RuntimeError("Weaviate not initialized. Call init_weaviate() first.")
    return _weaviate
