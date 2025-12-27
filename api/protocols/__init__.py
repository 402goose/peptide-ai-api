"""
Protocol definitions for dependency injection and testing.

These protocols define the interfaces that external services must implement,
enabling in-memory mock implementations for unit testing.
"""

from .database import IDatabase, ICollection
from .llm import ILLMClient
from .vector_store import IVectorStore

__all__ = [
    "IDatabase",
    "ICollection",
    "ILLMClient",
    "IVectorStore",
]
