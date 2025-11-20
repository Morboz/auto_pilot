"""LLM Adapter Layer for auto_pilot.

This module provides a unified interface for working with multiple LLM providers
including OpenAI, Claude, and local/self-hosted models.

Example usage:
    from auto_pilot.llm import create_adapter_for_model

    # Create adapter for OpenAI
    adapter = create_adapter_for_model(
        model="gpt-4",
        api_key="your-api-key",
    )

    # Generate text
    response = await adapter.generate(
        model="gpt-4",
        messages=[
            Message(role="user", content="Hello, world!")
        ]
    )

    print(response.content)
    print(f"Token usage: {response.usage}")
"""

from .adapters.base import BaseLLMAdapter
from .adapters.claude import ClaudeAdapter
from .adapters.factory import (
    LLMConfig,
    ProviderFactory,
    create_adapter,
    create_adapter_for_model,
)
from .adapters.local import LocalAdapter
from .adapters.openai import OpenAIAdapter
from .errors import (
    AuthenticationError,
    ConfigurationError,
    InvalidRequestError,
    LLMAdapterError,
    ModelNotFoundError,
    ProviderError,
    RateLimitError,
    StreamingError,
    StructuredOutputError,
    ToolExecutionError,
    map_provider_error,
)
from .types import (
    GenerationParams,
    GenerationResponse,
    Message,
    ModelCapabilities,
    StreamingChunk,
    StreamOptions,
    StreamParams,
    StructuredGenerationParams,
    TokenUsage,
    ToolCall,
    ToolDefinition,
    ToolExecutionParams,
    ToolResult,
)

__all__ = [
    # Types
    "Message",
    "ToolCall",
    "ToolResult",
    "TokenUsage",
    "ModelCapabilities",
    "GenerationResponse",
    "StreamingChunk",
    "GenerationParams",
    "StructuredGenerationParams",
    "ToolDefinition",
    "ToolExecutionParams",
    "StreamParams",
    "StreamOptions",
    # Adapters
    "BaseLLMAdapter",
    "OpenAIAdapter",
    "ClaudeAdapter",
    "LocalAdapter",
    # Factory
    "ProviderFactory",
    "LLMConfig",
    "create_adapter",
    "create_adapter_for_model",
    # Errors
    "LLMAdapterError",
    "ConfigurationError",
    "AuthenticationError",
    "RateLimitError",
    "ModelNotFoundError",
    "InvalidRequestError",
    "StreamingError",
    "ToolExecutionError",
    "StructuredOutputError",
    "ProviderError",
    "map_provider_error",
]
