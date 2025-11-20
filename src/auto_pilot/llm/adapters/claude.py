"""Claude adapter implementation."""

import json
import os
from typing import Any, AsyncIterator, Dict, List, Optional

from anthropic import AsyncAnthropic
from anthropic.types import Message

from ..errors import (
    AuthenticationError,
    InvalidRequestError,
    map_provider_error,
)
from ..types import (
    GenerationParams,
    GenerationResponse,
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
from ..types import (
    Message as InternalMessage,
)
from .base import BaseLLMAdapter


class ClaudeAdapter(BaseLLMAdapter):
    """Adapter for Anthropic Claude API and compatible providers.

    Supports Claude 3 (Haiku, Sonnet, Opus) and Anthropic-compatible providers with:
    - Text generation
    - Structured output
    - Tool calling (tool_use)
    - Streaming responses
    - Token usage tracking

    Compatible with any provider that implements the Anthropic Messages API standard,
    including but not limited to:
    - Anthropic (official)
    - MiniMax
    - Other Anthropic-compatible endpoints
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        timeout: float = 60.0,
    ):
        """Initialize Claude adapter.

        Args:
            api_key: API key (defaults to ANTHROPIC_API_KEY env var)
            base_url: Custom base URL for Anthropic-compatible providers
                     (defaults to ANTHROPIC_BASE_URL env var)
            timeout: Request timeout in seconds
        """
        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        if not self.api_key:
            raise AuthenticationError(
                "API key is required. Set ANTHROPIC_API_KEY environment variable."
            )

        # Support custom base URL for compatible providers (e.g., MiniMax)
        self.base_url = base_url or os.getenv("ANTHROPIC_BASE_URL")

        self.client = AsyncAnthropic(
            api_key=self.api_key,
            base_url=self.base_url,
            timeout=timeout,
        )

        # Model capabilities cache
        self._capabilities_cache: Dict[str, ModelCapabilities] = {}

    def _convert_messages_to_claude(
        self, messages: List[InternalMessage]
    ) -> Dict[str, Any]:
        """Convert internal message format to Claude format.

        Args:
            messages: Internal message list

        Returns:
            Claude-formatted request dict
        """
        system_messages = []
        claude_messages = []

        for msg in messages:
            if msg.role == "system":
                # Claude handles system messages separately
                system_messages.append(msg.content or "")
            elif msg.role == "user" and msg.type == "tool_result":
                # Tool results need tool_use_id
                tool_result_block = {
                    "type": "tool_result",
                    "content": msg.content or "",
                }
                # Add tool_use_id if available
                if msg.tool_use_id:
                    tool_result_block["tool_use_id"] = msg.tool_use_id

                claude_messages.append(
                    {
                        "role": "user",
                        "content": [tool_result_block],
                    }
                )
            elif msg.role == "assistant":
                # ⚠️ CRITICAL: Use raw_content if available (for MiniMax compatibility)
                # This preserves the complete content blocks including thinking
                if msg.raw_content is not None:
                    claude_messages.append(
                        {
                            "role": "assistant",
                            "content": msg.raw_content,
                        }
                    )
                else:
                    # Fallback to string content
                    claude_messages.append(
                        {
                            "role": msg.role,
                            "content": msg.content or "",
                        }
                    )
            else:
                # Regular user message
                claude_messages.append(
                    {
                        "role": msg.role,
                        "content": msg.content or "",
                    }
                )

        return {
            "system": "\n".join(system_messages) if system_messages else None,
            "messages": claude_messages,
        }

    def _convert_claude_response(
        self,
        response: Message,
        messages: List[InternalMessage],
    ) -> GenerationResponse:
        """Convert Claude response to internal format.

        Args:
            response: Claude message
            messages: Original message list

        Returns:
            Internal GenerationResponse
        """
        # Update messages with the assistant's response
        updated_messages = list(messages)

        # Extract content from Claude's content blocks
        assistant_content = ""
        tool_calls = []
        has_text = False

        for block in response.content:
            if block.type == "text":
                assistant_content += block.text
                has_text = True
            elif block.type == "thinking":
                # MiniMax's thinking block - include if no text blocks
                if not has_text:
                    # Store thinking content as fallback
                    pass
            elif block.type == "tool_use":
                tool_calls.append(
                    ToolCall(
                        type="tool_call",
                        name=block.name,
                        arguments=block.input,
                        id=block.id,  # Save tool_use_id for later use
                    )
                )

        # ⚠️ CRITICAL: Save the complete response.content for MiniMax
        # This preserves all blocks (thinking, text, tool_use)
        # for proper Interleaved Thinking support
        updated_messages.append(
            InternalMessage(
                role="assistant",
                content=assistant_content,
                raw_content=response.content,  # Preserve original blocks
            )
        )

        # Token usage
        usage = TokenUsage(
            input_tokens=response.usage.input_tokens,
            output_tokens=response.usage.output_tokens,
        )

        return GenerationResponse(
            content=assistant_content,
            messages=updated_messages,
            usage=usage,
            tool_calls=tool_calls if tool_calls else None,
            model=response.model,
        )

    async def generate(
        self,
        model: str,
        messages: List[InternalMessage],
        params: Optional[GenerationParams] = None,
    ) -> GenerationResponse:
        """Generate text response from Claude.

        Args:
            model: The model name (e.g., 'claude-3-sonnet-20240229')
            messages: List of messages in the conversation
            params: Generation parameters

        Returns:
            GenerationResponse with content and token usage
        """
        try:
            params = params or GenerationParams()

            request = self._convert_messages_to_claude(messages)

            response = await self.client.messages.create(
                model=model,
                max_tokens=params.max_tokens or 1024,
                temperature=params.temperature,
                top_p=params.top_p,
                **request,
            )

            return self._convert_claude_response(response, messages)

        except Exception as e:
            raise map_provider_error(e, "claude")

    async def structured_generate(
        self,
        model: str,
        messages: List[InternalMessage],
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
            request = self._convert_messages_to_claude(messages)

            # Claude uses JSON schema format in the prompt
            # We'll ask the model to output JSON matching the schema
            system_prompt = request.get("system", "")
            schema_str = json.dumps(params.json_schema, indent=2)
            system_prompt += (
                "\n\nPlease respond with valid JSON only that matches "
                f"the following schema:\n{schema_str}"
            )

            response = await self.client.messages.create(
                model=model,
                max_tokens=params.max_tokens or 2048,
                temperature=params.temperature,
                system=system_prompt,
                messages=request["messages"],
            )

            response_obj = self._convert_claude_response(response, messages)

            # Validate that the content is valid JSON
            try:
                json.loads(response_obj.content)
            except json.JSONDecodeError as e:
                raise InvalidRequestError(f"Model did not return valid JSON: {e}")

            return response_obj

        except Exception as e:
            raise map_provider_error(e, "claude")

    async def run_with_tools(
        self,
        model: str,
        messages: List[InternalMessage],
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

            request = self._convert_messages_to_claude(messages)

            # Convert tools to Claude tool format
            claude_tools = [
                {
                    "name": tool.name,
                    "description": tool.description,
                    "input_schema": tool.parameters,
                }
                for tool in tools
            ]

            # Prepare API call parameters
            api_params = {
                "model": model,
                "max_tokens": params.max_tokens or 1024,
                "temperature": params.temperature,
                "tools": claude_tools,
                **request,
            }

            # Only include tool_choice if explicitly set to non-default value
            if params.tool_choice and params.tool_choice != "auto":
                api_params["tool_choice"] = {"type": params.tool_choice}

            response = await self.client.messages.create(**api_params)

            return self._convert_claude_response(response, messages)

        except Exception as e:
            raise map_provider_error(e, "claude")

    async def stream(
        self,
        model: str,
        messages: List[InternalMessage],
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

            request = self._convert_messages_to_claude(messages)

            async with self.client.messages.stream(
                model=model,
                max_tokens=params.max_tokens or 1024,
                temperature=params.temperature,
                **request,
            ) as stream:
                async for event in stream:
                    if event.type == "content_block_delta":
                        if event.delta.type == "text_delta":
                            yield StreamingChunk(
                                type="text",
                                content=event.delta.text,
                                delta=True,
                            )
                        elif event.delta.type == "tool_use_delta":
                            yield StreamingChunk(
                                type="tool_call",
                                content={
                                    "name": event.delta.name,
                                    "arguments": event.delta.input,
                                },
                                delta=True,
                            )

                    elif event.type == "message_stop":
                        if options.include_usage and hasattr(event, "usage"):
                            yield StreamingChunk(
                                type="text",
                                content={
                                    "usage": {
                                        "input_tokens": event.usage.input_tokens,
                                        "output_tokens": event.usage.output_tokens,
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
            raise map_provider_error(e, "claude")

    async def stream_with_tools(
        self,
        model: str,
        messages: List[InternalMessage],
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
        try:
            params = params or StreamParams()

            request = self._convert_messages_to_claude(messages)

            # Convert tools to Claude tool format
            claude_tools = [
                {
                    "name": tool.name,
                    "description": tool.description,
                    "input_schema": tool.parameters,
                }
                for tool in tools
            ]

            async with self.client.messages.stream(
                model=model,
                max_tokens=params.max_tokens or 1024,
                temperature=params.temperature,
                tools=claude_tools,
                **request,
            ) as stream:
                async for event in stream:
                    if event.type == "content_block_delta":
                        if event.delta.type == "text_delta":
                            yield StreamingChunk(
                                type="text",
                                content=event.delta.text,
                                delta=True,
                            )
                        elif event.delta.type == "tool_use_delta":
                            yield StreamingChunk(
                                type="tool_call",
                                content={
                                    "name": event.delta.name,
                                    "arguments": event.delta.input,
                                },
                                delta=True,
                            )

                    elif event.type == "message_stop":
                        if hasattr(event, "usage"):
                            yield StreamingChunk(
                                type="text",
                                content={
                                    "usage": {
                                        "input_tokens": event.usage.input_tokens,
                                        "output_tokens": event.usage.output_tokens,
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
            raise map_provider_error(e, "claude")

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

        # Claude 3 models support most features
        # Check model family for context length
        is_opus = "opus" in model.lower()

        capabilities = ModelCapabilities(
            supports_tools=True,
            supports_streaming=True,
            supports_json_schema=True,
            supports_images=True,  # Claude 3 supports image input
            max_context_length=200000 if is_opus else 100000,  # Opus has larger context
        )

        # Cache the capabilities
        self._capabilities_cache[model] = capabilities
        return capabilities

    async def close(self) -> None:
        """Clean up resources used by the adapter."""
        await self.client.close()
