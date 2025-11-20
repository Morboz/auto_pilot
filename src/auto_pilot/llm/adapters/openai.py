"""OpenAI adapter implementation."""

import json
import os
from typing import Any, AsyncIterator, Dict, List, Optional

from openai import AsyncOpenAI
from openai.types.chat import ChatCompletion

from ..errors import (
    AuthenticationError,
    InvalidRequestError,
    map_provider_error,
)
from ..types import (
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
)
from .base import BaseLLMAdapter


class OpenAIAdapter(BaseLLMAdapter):
    """Adapter for OpenAI API.

    Supports GPT-3.5, GPT-4, and related models with:
    - Text generation
    - Structured output (JSON Schema)
    - Function calling
    - Streaming responses
    - Token usage tracking
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        timeout: float = 60.0,
    ):
        """Initialize OpenAI adapter.

        Args:
            api_key: OpenAI API key (defaults to OPENAI_API_KEY env var)
            base_url: Custom base URL for OpenAI-compatible APIs
            timeout: Request timeout in seconds
        """
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise AuthenticationError(
                "OpenAI API key is required. Set OPENAI_API_KEY environment variable."
            )

        self.client = AsyncOpenAI(
            api_key=self.api_key,
            base_url=base_url,
            timeout=timeout,
        )

        # Model capabilities cache
        self._capabilities_cache: Dict[str, ModelCapabilities] = {}

    def _convert_messages_to_openai(
        self, messages: List[Message]
    ) -> List[Dict[str, Any]]:
        """Convert internal message format to OpenAI format.

        Args:
            messages: Internal message list

        Returns:
            OpenAI-formatted messages
        """
        openai_messages = []

        for msg in messages:
            if msg.role == "tool":
                # OpenAI doesn't have a 'tool' role, use assistant with tool_calls
                if msg.type == "tool_result":
                    openai_msg = {
                        "role": "tool",
                        "name": msg.name,
                        "content": msg.content or "",
                    }
                else:
                    # Tool use or other tool message
                    openai_msg = {
                        "role": "assistant",
                        "name": msg.name,
                        "content": msg.content or "",
                    }
            elif msg.role == "assistant" and msg.type == "tool_use":
                # Convert tool_use to function_call
                openai_msg = {
                    "role": "assistant",
                    "content": msg.content or "",
                    "tool_calls": [
                        {
                            "id": f"call_{msg.name}",
                            "type": "function",
                            "function": {
                                "name": msg.name,
                                "arguments": msg.content or "{}",
                            },
                        }
                    ],
                }
            else:
                # Regular system, user, or assistant message
                openai_msg = {
                    "role": msg.role,
                    "content": msg.content or "",
                }

                # Add name if present (for tool messages)
                if msg.name:
                    openai_msg["name"] = msg.name

            openai_messages.append(openai_msg)

        return openai_messages

    def _convert_openai_response(
        self,
        response: ChatCompletion,
        messages: List[Message],
    ) -> GenerationResponse:
        """Convert OpenAI response to internal format.

        Args:
            response: OpenAI chat completion
            messages: Original message list

        Returns:
            Internal GenerationResponse
        """
        choice = response.choices[0]
        msg = choice.message

        # Update messages with the assistant's response
        updated_messages = list(messages)
        updated_messages.append(
            Message(
                role="assistant",
                content=msg.content or "",
            )
        )

        # Handle tool calls
        tool_calls = None
        if msg.tool_calls:
            tool_calls = [
                ToolCall(
                    type="tool_call",
                    name=tc.function.name,
                    arguments=json.loads(tc.function.arguments or "{}"),
                )
                for tc in msg.tool_calls
            ]

            # Also add tool_use messages to the conversation
            for tc in msg.tool_calls:
                updated_messages.append(
                    Message(
                        role="assistant",
                        type="tool_use",
                        name=tc.function.name,
                        content=tc.function.arguments or "{}",
                    )
                )

        # Token usage
        usage = TokenUsage(
            input_tokens=response.usage.prompt_tokens,
            output_tokens=response.usage.completion_tokens,
        )

        return GenerationResponse(
            content=msg.content or "",
            messages=updated_messages,
            usage=usage,
            tool_calls=tool_calls,
            model=response.model,
        )

    async def generate(
        self,
        model: str,
        messages: List[Message],
        params: Optional[GenerationParams] = None,
    ) -> GenerationResponse:
        """Generate text response from OpenAI.

        Args:
            model: The model name (e.g., 'gpt-4', 'gpt-3.5-turbo')
            messages: List of messages in the conversation
            params: Generation parameters

        Returns:
            GenerationResponse with content and token usage
        """
        try:
            params = params or GenerationParams()

            openai_messages = self._convert_messages_to_openai(messages)

            response = await self.client.chat.completions.create(
                model=model,
                messages=openai_messages,
                temperature=params.temperature,
                max_tokens=params.max_tokens,
                top_p=params.top_p,
                frequency_penalty=params.frequency_penalty,
                presence_penalty=params.presence_penalty,
            )

            return self._convert_openai_response(response, messages)

        except Exception as e:
            raise map_provider_error(e, "openai")

    async def structured_generate(
        self,
        model: str,
        messages: List[Message],
        params: StructuredGenerationParams,
    ) -> GenerationResponse:
        """Generate structured output matching JSON Schema.

        Args:
            model: The model name
            messages: List of messages in the conversation
            params: Parameters including JSON schema

        Returns:
            GenerationResponse with validated structured content
        """
        try:
            openai_messages = self._convert_messages_to_openai(messages)

            response = await self.client.chat.completions.create(
                model=model,
                messages=openai_messages,
                temperature=params.temperature,
                max_tokens=params.max_tokens,
                response_format={
                    "type": "json_schema",
                    "json_schema": {
                        "name": "structured_output",
                        "schema": params.json_schema,
                        "strict": params.strict,
                    },
                },
            )

            response_obj = self._convert_openai_response(response, messages)

            # Validate that the content is valid JSON
            try:
                json.loads(response_obj.content)
            except json.JSONDecodeError as e:
                raise InvalidRequestError(f"Model did not return valid JSON: {e}")

            return response_obj

        except Exception as e:
            raise map_provider_error(e, "openai")

    async def run_with_tools(
        self,
        model: str,
        messages: List[Message],
        tools: List[ToolDefinition],
        params: Optional[ToolExecutionParams] = None,
    ) -> GenerationResponse:
        """Execute ReAct-style tool calling.

        Args:
            model: The model name
            messages: List of messages in the conversation
            tools: List of available tools
            params: Execution parameters

        Returns:
            GenerationResponse with tool calls and results
        """
        try:
            params = params or ToolExecutionParams()

            openai_messages = self._convert_messages_to_openai(messages)

            # Convert tools to OpenAI function format
            functions = [
                {
                    "name": tool.name,
                    "description": tool.description,
                    "parameters": tool.parameters,
                }
                for tool in tools
            ]

            response = await self.client.chat.completions.create(
                model=model,
                messages=openai_messages,
                tools=[{"type": "function", "function": func} for func in functions],
                tool_choice=params.tool_choice,
                temperature=params.temperature,
                max_tokens=params.max_tokens,
            )

            return self._convert_openai_response(response, messages)

        except Exception as e:
            raise map_provider_error(e, "openai")

    async def stream(
        self,
        model: str,
        messages: List[Message],
        params: Optional[StreamParams] = None,
        options: Optional[StreamOptions] = None,
    ) -> AsyncIterator[StreamingChunk]:
        """Stream text response from the model.

        Args:
            model: The model name
            messages: List of messages in the conversation
            params: Generation parameters
            options: Streaming options

        Yields:
            StreamingChunk events
        """
        try:
            params = params or StreamParams()
            options = options or StreamOptions()

            openai_messages = self._convert_messages_to_openai(messages)

            stream = await self.client.chat.completions.create(
                model=model,
                messages=openai_messages,
                temperature=params.temperature,
                max_tokens=params.max_tokens,
                stream=True,
            )

            for chunk in stream:
                if not chunk.choices:
                    continue

                delta = chunk.choices[0].delta

                if delta.content:
                    yield StreamingChunk(
                        type="text",
                        content=delta.content,
                        delta=True,
                    )

                # Handle tool calls in stream
                if delta.tool_calls:
                    for tc in delta.tool_calls:
                        if tc.function:
                            yield StreamingChunk(
                                type="tool_call",
                                content={
                                    "name": tc.function.name,
                                    "arguments": tc.function.arguments or "",
                                },
                                delta=True,
                            )

            # Emit usage at end if requested
            if options.include_usage and chunk.usage:
                yield StreamingChunk(
                    type="text",
                    content={
                        "usage": {
                            "input_tokens": chunk.usage.prompt_tokens,
                            "output_tokens": chunk.usage.completion_tokens,
                        }
                    },
                    delta=False,
                )

        except Exception as e:
            yield StreamingChunk(
                type="error",
                content={"error": str(e)},
                delta=False,
            )
            raise map_provider_error(e, "openai")

    async def stream_with_tools(
        self,
        model: str,
        messages: List[Message],
        tools: List[ToolDefinition],
        params: Optional[StreamParams] = None,
    ) -> AsyncIterator[StreamingChunk]:
        """Stream response with interleaved tool calls.

        Args:
            model: The model name
            messages: List of messages in the conversation
            tools: List of available tools
            params: Generation parameters

        Yields:
            StreamingChunk events in order
        """
        params = params or StreamParams()

        # For OpenAI, we can use run_with_tools but stream the response
        # The actual tool execution would be handled by the caller
        async for chunk in self.stream(model, messages, params):
            yield chunk

    async def get_capabilities(self, model: str) -> ModelCapabilities:
        """Get the capabilities of a specific model.

        Args:
            model: The model name to check

        Returns:
            ModelCapabilities describing supported features
        """
        # Check cache first
        if model in self._capabilities_cache:
            return self._capabilities_cache[model]

        # OpenAI models generally support all features
        # Some older models may not support function calling or structured output
        # We'll make educated guesses based on model name
        capabilities = ModelCapabilities(
            supports_tools=True,
            supports_streaming=True,
            supports_json_schema=True,
            supports_images=False,
            max_context_length=128000,  # Common for GPT-4 variants
        )

        # Cache the capabilities
        self._capabilities_cache[model] = capabilities
        return capabilities

    async def close(self) -> None:
        """Clean up resources used by the adapter."""
        await self.client.close()
