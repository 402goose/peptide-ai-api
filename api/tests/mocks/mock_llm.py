"""
Mock LLM client implementation for testing.

Provides an in-memory implementation of OpenAI/Ollama operations,
allowing tests to run without making real API calls.
"""

from typing import Any, Optional, AsyncIterator
from dataclasses import dataclass, field
import asyncio


@dataclass
class MockDelta:
    """Mock delta for streaming responses."""
    role: Optional[str] = None
    content: Optional[str] = None


@dataclass
class MockChoice:
    """Mock choice for completion responses."""
    index: int = 0
    message: Optional["MockMessage"] = None
    delta: Optional[MockDelta] = None
    finish_reason: Optional[str] = None


@dataclass
class MockMessage:
    """Mock message for completion responses."""
    role: str = "assistant"
    content: str = ""


@dataclass
class MockUsage:
    """Mock usage statistics."""
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0


@dataclass
class MockCompletion:
    """Mock completion response."""
    id: str = "mock_completion_id"
    object: str = "chat.completion"
    model: str = "mock-model"
    choices: list[MockChoice] = field(default_factory=list)
    usage: MockUsage = field(default_factory=MockUsage)


class MockStreamChunk:
    """Mock streaming chunk."""
    def __init__(self, content: str, finish_reason: Optional[str] = None):
        self.id = "mock_chunk_id"
        self.object = "chat.completion.chunk"
        self.model = "mock-model"
        self.choices = [
            MockChoice(
                index=0,
                delta=MockDelta(content=content),
                finish_reason=finish_reason
            )
        ]


class MockAsyncStream:
    """Mock async stream for streaming responses."""

    def __init__(self, content: str, chunk_size: int = 10):
        self._content = content
        self._chunk_size = chunk_size
        self._index = 0

    def __aiter__(self):
        return self

    async def __anext__(self) -> MockStreamChunk:
        if self._index >= len(self._content):
            raise StopAsyncIteration

        # Get next chunk of content
        chunk_content = self._content[self._index:self._index + self._chunk_size]
        self._index += self._chunk_size

        # Check if this is the last chunk
        is_last = self._index >= len(self._content)
        finish_reason = "stop" if is_last else None

        # Small delay to simulate network
        await asyncio.sleep(0.001)

        return MockStreamChunk(chunk_content, finish_reason)


class MockChatCompletions:
    """
    Mock chat completions API.

    Supports both regular and streaming completions.
    """

    def __init__(self, parent: "MockLLMClient"):
        self._parent = parent

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

        Returns deterministic responses based on configured responses
        or a default mock response.
        """
        # Record the call for test assertions
        self._parent.call_history.append({
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": stream,
            **kwargs
        })

        # Get response based on messages or use default
        response_content = self._get_response(messages)

        if stream:
            return MockAsyncStream(response_content, chunk_size=self._parent.stream_chunk_size)
        else:
            return MockCompletion(
                model=model,
                choices=[
                    MockChoice(
                        index=0,
                        message=MockMessage(role="assistant", content=response_content),
                        finish_reason="stop"
                    )
                ],
                usage=MockUsage(
                    prompt_tokens=sum(len(m.get("content", "")) for m in messages),
                    completion_tokens=len(response_content),
                    total_tokens=sum(len(m.get("content", "")) for m in messages) + len(response_content)
                )
            )

    def _get_response(self, messages: list[dict[str, str]]) -> str:
        """Get response based on messages."""
        # Check for specific message patterns first
        for pattern, response in self._parent.response_patterns.items():
            last_message = messages[-1].get("content", "") if messages else ""
            if pattern.lower() in last_message.lower():
                return response

        # Check for exact message matches
        last_message = messages[-1].get("content", "") if messages else ""
        if last_message in self._parent.responses:
            return self._parent.responses[last_message]

        # Return default response
        return self._parent.default_response


class MockChatNamespace:
    """Mock chat namespace (client.chat)."""

    def __init__(self, parent: "MockLLMClient"):
        self._completions = MockChatCompletions(parent)

    @property
    def completions(self) -> MockChatCompletions:
        return self._completions


class MockLLMClient:
    """
    Mock LLM client for testing.

    Provides configurable responses for testing different scenarios
    without making real API calls.

    Usage:
        client = MockLLMClient()

        # Set default response
        client.default_response = "This is a mock response"

        # Set specific responses for messages
        client.responses["What is BPC-157?"] = "BPC-157 is a peptide..."

        # Set pattern-based responses
        client.response_patterns["dosing"] = "Here are dosing guidelines..."

        # Use in tests
        response = await client.chat.completions.create(
            model="gpt-4",
            messages=[{"role": "user", "content": "What is BPC-157?"}]
        )

        # Check call history
        assert len(client.call_history) == 1
    """

    def __init__(
        self,
        default_response: str = "This is a mock LLM response for testing.",
        responses: Optional[dict[str, str]] = None,
        response_patterns: Optional[dict[str, str]] = None,
        stream_chunk_size: int = 10,
    ):
        self.default_response = default_response
        self.responses = responses or {}
        self.response_patterns = response_patterns or {}
        self.stream_chunk_size = stream_chunk_size
        self.call_history: list[dict[str, Any]] = []
        self._chat = MockChatNamespace(self)

    @property
    def chat(self) -> MockChatNamespace:
        """Access the chat API namespace."""
        return self._chat

    def reset(self) -> None:
        """Reset call history and responses (helper for tests)."""
        self.call_history = []
        self.responses = {}
        self.response_patterns = {}

    def set_response(self, message: str, response: str) -> None:
        """Set a response for a specific message (helper for tests)."""
        self.responses[message] = response

    def set_pattern_response(self, pattern: str, response: str) -> None:
        """Set a response for messages matching a pattern (helper for tests)."""
        self.response_patterns[pattern] = response

    def get_last_call(self) -> Optional[dict[str, Any]]:
        """Get the last API call (helper for tests)."""
        return self.call_history[-1] if self.call_history else None

    def assert_called_with_model(self, model: str) -> None:
        """Assert the last call used a specific model (helper for tests)."""
        last_call = self.get_last_call()
        assert last_call is not None, "No calls recorded"
        assert last_call["model"] == model, f"Expected model {model}, got {last_call['model']}"

    def assert_message_contains(self, text: str) -> None:
        """Assert the last call's messages contain specific text (helper for tests)."""
        last_call = self.get_last_call()
        assert last_call is not None, "No calls recorded"
        all_content = " ".join(m.get("content", "") for m in last_call["messages"])
        assert text in all_content, f"Expected '{text}' in messages"
