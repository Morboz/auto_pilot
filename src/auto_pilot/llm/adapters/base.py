"""Base adapter interface for LLM providers."""

from abc import ABC, abstractmethod
from typing import AsyncIterator, List, Optional

from ..types import (
    GenerationParams,
    GenerationResponse,
    Message,
    ModelCapabilities,
    StreamingChunk,
    StreamOptions,
    StreamParams,
    StructuredGenerationParams,
    ToolDefinition,
    ToolExecutionParams,
)


class BaseLLMAdapter(ABC):
    """Base interface for all LLM provider adapters.

    This abstract class defines the 7 required capabilities:
    1. Text generation (generate)
    2. Structured output (structured_generate)
    3. Tool calling (run_with_tools)
    4. Streaming (stream)
    5. Token usage tracking (implicit in all responses)
    6. Model capabilities (get_capabilities)
    7. Multi-turn conversation support (implicit in message handling)
    """

    @abstractmethod
    async def generate(
        self,
        model: str,
        messages: List[Message],
        params: Optional[GenerationParams] = None,
    ) -> GenerationResponse:
        """Generate text response from the model.

        Args:
            model: The model name to use
            messages: List of messages in the conversation
            params: Generation parameters (temperature, max_tokens, etc.)

        Returns:
            GenerationResponse with content and token usage
        """
        pass

    @abstractmethod
    async def structured_generate(
        self,
        model: str,
        messages: List[Message],
        params: StructuredGenerationParams,
    ) -> GenerationResponse:
        """Generate structured output matching a JSON Schema.

        Args:
            model: The model name to use
            messages: List of messages in the conversation
            params: Parameters including JSON schema and generation settings

        Returns:
            GenerationResponse with validated structured content
        """
        pass

    @abstractmethod
    async def run_with_tools(
        self,
        model: str,
        messages: List[Message],
        tools: List[ToolDefinition],
        params: Optional[ToolExecutionParams] = None,
    ) -> GenerationResponse:
        """Execute ReAct-style tool calling.

        Args:
            model: The model name to use
            messages: List of messages in the conversation
            tools: List of available tools with schemas
            params: Execution parameters

        Returns:
            GenerationResponse with any tool calls and results
        """
        pass

    @abstractmethod
    async def stream(
        self,
        model: str,
        messages: List[Message],
        params: Optional[StreamParams] = None,
        options: Optional[StreamOptions] = None,
    ) -> AsyncIterator[StreamingChunk]:
        """Stream text response from the model.

        Args:
            model: The model name to use
            messages: List of messages in the conversation
            params: Generation parameters
            options: Streaming options

        Yields:
            StreamingChunk events (text, tool_call, tool_result, error)
        """
        pass

    @abstractmethod
    async def stream_with_tools(
        self,
        model: str,
        messages: List[Message],
        tools: List[ToolDefinition],
        params: Optional[StreamParams] = None,
    ) -> AsyncIterator[StreamingChunk]:
        """Stream response with interleaved tool calls.

        This method handles the complete ReAct cycle in streaming mode:
        - Emits thinking text
        - Emits tool_use events
        - Inserts tool_result events
        - Continues with more thinking

        Args:
            model: The model name to use
            messages: List of messages in the conversation
            tools: List of available tools
            params: Generation parameters

        Yields:
            StreamingChunk events in order: text → tool_use → tool_result → text
        """
        pass

    @abstractmethod
    async def get_capabilities(self, model: str) -> ModelCapabilities:
        """Get the capabilities of a specific model.

        Args:
            model: The model name to check

        Returns:
            ModelCapabilities describing supported features
        """
        pass

    @abstractmethod
    async def close(self) -> None:
        """Clean up resources used by the adapter.

        This should close any open connections or client sessions.
        """
        pass
