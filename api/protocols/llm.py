"""
LLM client protocol for OpenAI/Ollama operations.

Defines the interface for LLM operations, enabling mock implementations
for testing without making real API calls.
"""

from typing import Protocol, AsyncIterator, Any, Optional, runtime_checkable
from dataclasses import dataclass


@dataclass
class ChatMessage:
    """A message in a chat conversation."""
    role: str  # "system", "user", "assistant"
    content: str


@dataclass
class ChatCompletionChoice:
    """A single choice in a chat completion response."""
    index: int
    message: ChatMessage
    finish_reason: Optional[str] = None


@dataclass
class ChatCompletionChunk:
    """A chunk of streaming chat completion."""
    id: str
    choices: list["ChatCompletionChunkChoice"]


@dataclass
class ChatCompletionChunkChoice:
    """A choice in a streaming chunk."""
    index: int
    delta: "ChatCompletionDelta"
    finish_reason: Optional[str] = None


@dataclass
class ChatCompletionDelta:
    """Delta content in a streaming chunk."""
    role: Optional[str] = None
    content: Optional[str] = None


@dataclass
class ChatCompletionResponse:
    """Response from a chat completion."""
    id: str
    choices: list[ChatCompletionChoice]
    model: str
    usage: Optional[dict[str, int]] = None


@runtime_checkable
class IChatCompletions(Protocol):
    """Protocol for chat completions API."""

    async def create(
        self,
        model: str,
        messages: list[dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 2000,
        stream: bool = False,
        **kwargs: Any,
    ) -> Any:
        """
        Create a chat completion.

        When stream=False, returns ChatCompletionResponse.
        When stream=True, returns an async iterator of ChatCompletionChunk.
        """
        ...


@runtime_checkable
class IChatNamespace(Protocol):
    """Protocol for the chat namespace (client.chat)."""

    @property
    def completions(self) -> IChatCompletions:
        """Access the completions API."""
        ...


@runtime_checkable
class ILLMClient(Protocol):
    """
    Protocol for LLM client operations.

    This matches the OpenAI AsyncOpenAI client interface,
    allowing seamless substitution of mock implementations for testing.
    """

    @property
    def chat(self) -> IChatNamespace:
        """Access the chat API namespace."""
        ...


# Convenience type for messages
MessageList = list[dict[str, str]]
