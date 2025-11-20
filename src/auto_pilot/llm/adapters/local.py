"""Local/Self-hosted LLM adapter implementation."""

import json
from typing import Any, AsyncIterator, Dict, List, Optional

from openai import AsyncOpenAI

from ..errors import AuthenticationError, map_provider_error
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


class LocalAdapter(BaseLLMAdapter):
    """Adapter for local or self-hosted LLMs.

    Supports OpenAI-compatible APIs for local/self-hosted models.
    Many local models may not support all features (function calling, streaming, etc.),
    so this adapter provides graceful fallbacks.

    Typical use cases:
    - Ollama (ollama.ai)
    - LM Studio
    - vLLM
    - OpenRouter
    - Other OpenAI-compatible APIs
    """

    def __init__(
        self,
        base_url: str,
        api_key: Optional[str] = None,
        timeout: float = 60.0,
    ):
        """Initialize Local adapter.

        Args:
            base_url: Base URL of the local/openai-compatible API
            api_key: API key (optional for some local deployments)
            timeout: Request timeout in seconds
        """
        if not base_url:
            raise AuthenticationError("base_url is required for local adapters")

        self.client = AsyncOpenAI(
            api_key=api_key or "local",
            base_url=base_url,
            timeout=timeout,
        )

        self.base_url = base_url
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
                if msg.type == "tool_result":
                    openai_msg = {
                        "role": "tool",
                        "name": msg.name,
                        "content": msg.content or "",
                    }
                else:
                    openai_msg = {
                        "role": "assistant",
                        "name": msg.name,
                        "content": msg.content or "",
                    }
            elif msg.role == "assistant" and msg.type == "tool_use":
                # Local models may not support function calling
                # We'll include as regular content
                openai_msg = {
                    "role": "assistant",
                    "content": (
                        f"Tool call: {msg.name}\n" f"Arguments: {msg.content or '{}'}"
                    ),
                }
            else:
                openai_msg = {
                    "role": msg.role,
                    "content": msg.content or "",
                }
                if msg.name:
                    openai_msg["name"] = msg.name

            openai_messages.append(openai_msg)

        return openai_messages

    def _convert_openai_response(
        self,
        response: Any,
        messages: List[Message],
    ) -> GenerationResponse:
        """Convert OpenAI-style response to internal format.

        Args:
            response: OpenAI-style response
            messages: Original message list

        Returns:
            Internal GenerationResponse
        """
        choice = response.choices[0]
        msg = choice.message

        updated_messages = list(messages)
        updated_messages.append(
            Message(
                role="assistant",
                content=msg.content or "",
            )
        )

        # Local models may not support tool calls
        tool_calls = None
        if hasattr(msg, "tool_calls") and msg.tool_calls:
            tool_calls = [
                ToolCall(
                    type="tool_call",
                    name=tc.function.name,
                    arguments=json.loads(tc.function.arguments or "{}"),
                )
                for tc in msg.tool_calls
            ]

        # Token usage - may not be available from all local providers
        usage = TokenUsage()
        if hasattr(response, "usage") and response.usage:
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
        """Generate text response from local model.

        Args:
            model: The model name
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
            )

            return self._convert_openai_response(response, messages)

        except Exception as e:
            raise map_provider_error(e, "local")

    async def structured_generate(
        self,
        model: str,
        messages: List[Message],
        params: StructuredGenerationParams,
    ) -> GenerationResponse:
        """Generate structured output matching JSON Schema.

        Note: Many local models may not support structured output.
        We'll attempt to use response_format if supported, otherwise
        fall back to requesting JSON in the prompt.

        Args:
            model: The model name
            messages: List of messages in the conversation
            params: Parameters including JSON schema

        Returns:
            GenerationResponse with structured content
        """
        try:
            openai_messages = self._convert_messages_to_openai(messages)

            # Try to use response_format if the provider supports it
            try:
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
            except Exception:
                # Fall back to prompting for JSON
                # Add instruction to output JSON
                system_msg = {
                    "role": "system",
                    "content": (
                        "Please respond with valid JSON that matches this schema:\n"
                        f"{json.dumps(params.json_schema, indent=2)}"
                    ),
                }
                openai_messages.insert(0, system_msg)

                response = await self.client.chat.completions.create(
                    model=model,
                    messages=openai_messages,
                    temperature=params.temperature,
                    max_tokens=params.max_tokens,
                )

            response_obj = self._convert_openai_response(response, messages)

            # Validate JSON if possible
            try:
                json.loads(response_obj.content)
            except json.JSONDecodeError:
                pass  # Some local models may not output valid JSON

            return response_obj

        except Exception as e:
            raise map_provider_error(e, "local")

    async def run_with_tools(
        self,
        model: str,
        messages: List[Message],
        tools: List[ToolDefinition],
        params: Optional[ToolExecutionParams] = None,
    ) -> GenerationResponse:
        """Execute tool calling.

        Note: Most local models don't support native function calling.
        This method will fall back to prompting the model to describe
        what tool it would call.

        Args:
            model: The model name
            messages: List of messages in the conversation
            tools: List of available tools
            params: Execution parameters

        Returns:
            GenerationResponse with tool call descriptions
        """
        try:
            params = params or ToolExecutionParams()

            # For local models, prompt the model to describe which tool to use
            tools_description = "\n".join(
                [
                    (
                        f"- {tool.name}: {tool.description}\n"
                        f"  Parameters: {json.dumps(tool.parameters, indent=2)}"
                    )
                    for tool in tools
                ]
            )

            system_msg = f"""Available tools:
{tools_description}

If you need to use a tool, describe what you would do. Format as:
Tool: <tool_name>
Arguments: <json_arguments>
Otherwise, provide your direct answer."""

            # Add system message
            messages = messages.copy()
            if not any(m.role == "system" for m in messages):
                messages.insert(0, Message(role="system", content=system_msg))
            else:
                # Append to existing system message
                for msg in messages:
                    if msg.role == "system":
                        msg.content = (msg.content or "") + "\n" + system_msg
                        break

            openai_messages = self._convert_messages_to_openai(messages)

            response = await self.client.chat.completions.create(
                model=model,
                messages=openai_messages,
                temperature=params.temperature,
                max_tokens=params.max_tokens,
            )

            return self._convert_openai_response(response, messages)

        except Exception as e:
            raise map_provider_error(e, "local")

    async def stream(
        self,
        model: str,
        messages: List[Message],
        params: Optional[StreamParams] = None,
        options: Optional[StreamOptions] = None,
    ) -> AsyncIterator[StreamingChunk]:
        """Stream text response from the model.

        Note: Streaming support varies by local provider.

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

        except Exception as e:
            yield StreamingChunk(
                type="error",
                content={"error": str(e)},
                delta=False,
            )
            raise map_provider_error(e, "local")

    async def stream_with_tools(
        self,
        model: str,
        messages: List[Message],
        tools: List[ToolDefinition],
        params: Optional[StreamParams] = None,
    ) -> AsyncIterator[StreamingChunk]:
        """Stream response with tool calls.

        Args:
            model: The model name
            messages: List of messages in the conversation
            tools: List of available tools
            params: Generation parameters

        Yields:
            StreamingChunk events in order
        """
        params = params or StreamParams()

        async for chunk in self.stream(model, messages, params):
            yield chunk

    async def get_capabilities(self, model: str) -> ModelCapabilities:
        """Get the capabilities of a specific model.

        Note: Local models have varying capabilities. This method provides
        conservative defaults and should be updated based on the specific model.

        Args:
            model: The model name to check

        Returns:
            ModelCapabilities describing supported features
        """
        # Check cache first
        if model in self._capabilities_cache:
            return self._capabilities_cache[model]

        # Conservative defaults for local models
        # Actual capabilities depend on the specific model and provider
        capabilities = ModelCapabilities(
            supports_tools=True,  # Most can be prompted for tool calls
            supports_streaming=True,  # Many local providers support streaming
            supports_json_schema=False,  # Most don't support native structured output
            supports_images=False,  # Varies by model
            max_context_length=32768,  # Conservative default
        )

        # Cache the capabilities
        self._capabilities_cache[model] = capabilities
        return capabilities

    async def close(self) -> None:
        """Clean up resources used by the adapter."""
        await self.client.close()
