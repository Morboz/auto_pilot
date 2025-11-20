"""Integration tests for Claude adapter with compatible providers (e.g., MiniMax).

These tests require:
- ANTHROPIC_API_KEY environment variable
- ANTHROPIC_BASE_URL environment variable (optional, for MiniMax)

Run with: pytest tests/test_llm/test_claude_integration.py -v
Skip with: pytest -m "not integration"
"""

import os
from pathlib import Path

import pytest
from dotenv import load_dotenv

from auto_pilot.llm.adapters.claude import ClaudeAdapter
from auto_pilot.llm.types import (
    GenerationParams,
    Message,
    ToolDefinition,
    ToolExecutionParams,
)

# Load environment variables from .env
env_path = Path(__file__).parent.parent.parent / ".env"
if env_path.exists():
    load_dotenv(env_path)

# Skip all tests in this module if API key is not configured
pytestmark = pytest.mark.skipif(
    not os.getenv("ANTHROPIC_API_KEY"),
    reason="ANTHROPIC_API_KEY not set. Set it to run integration tests.",
)


@pytest.fixture
async def adapter():
    """Create a Claude adapter instance."""
    adapter = ClaudeAdapter()
    yield adapter
    await adapter.close()


@pytest.mark.integration
@pytest.mark.asyncio
class TestClaudeBasicGeneration:
    """Test basic text generation with Claude/MiniMax."""

    async def test_simple_generation(self, adapter):
        """Test simple text generation."""
        messages = [Message(role="user", content="Say 'Hello' in Chinese.")]

        params = GenerationParams(
            max_tokens=200,
            temperature=0.7,
        )

        response = await adapter.generate(
            model=os.getenv("CLAUDE_MODEL", "MiniMax-M2"),
            messages=messages,
            params=params,
        )

        # Assertions
        assert response.content is not None
        assert len(response.content) > 0
        assert "你好" in response.content or "hello" in response.content.lower()
        assert response.usage.input_tokens > 0
        assert response.usage.output_tokens > 0
        assert len(response.messages) == 2  # user + assistant

    async def test_generation_with_system_message(self, adapter):
        """Test generation with system message."""
        messages = [
            Message(role="system", content="You are a helpful assistant."),
            Message(role="user", content="What is 2+2?"),
        ]

        params = GenerationParams(max_tokens=100, temperature=0.0)

        response = await adapter.generate(
            model=os.getenv("CLAUDE_MODEL", "MiniMax-M2"),
            messages=messages,
            params=params,
        )

        assert response.content is not None
        assert "4" in response.content

    async def test_multi_turn_conversation(self, adapter):
        """Test multi-turn conversation."""
        messages = [
            Message(role="user", content="My name is Alice."),
        ]

        # First turn
        response1 = await adapter.generate(
            model=os.getenv("CLAUDE_MODEL", "MiniMax-M2"),
            messages=messages,
            params=GenerationParams(max_tokens=200),
        )

        # Second turn
        messages = response1.messages
        messages.append(Message(role="user", content="What's my name?"))

        response2 = await adapter.generate(
            model=os.getenv("CLAUDE_MODEL", "MiniMax-M2"),
            messages=messages,
            params=GenerationParams(max_tokens=200),
        )

        assert "Alice" in response2.content or "alice" in response2.content.lower()


@pytest.mark.integration
@pytest.mark.asyncio
class TestClaudeToolCalling:
    """Test tool calling with Claude/MiniMax."""

    @pytest.fixture
    def weather_tool(self):
        """Create a weather tool definition."""
        return ToolDefinition(
            name="get_weather",
            description=(
                "Get weather of a location, " "the user should supply a location first."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "location": {
                        "type": "string",
                        "description": "The city and state, e.g. San Francisco, US",
                    }
                },
                "required": ["location"],
            },
        )

    async def test_tool_calling_flow(self, adapter, weather_tool):
        """Test complete tool calling flow."""
        tools = [weather_tool]

        # Step 1: Model should call the tool
        messages = [
            Message(
                role="user",
                content=(
                    "Please use the get_weather tool to check the weather "
                    "in San Francisco, US."
                ),
            )
        ]

        params = ToolExecutionParams(
            tools=tools,
            max_tokens=4096,
            temperature=0.7,
        )

        response = await adapter.run_with_tools(
            model=os.getenv("CLAUDE_MODEL", "MiniMax-M2"),
            messages=messages,
            tools=tools,
            params=params,
        )

        # Assertions for first response
        assert response.tool_calls is not None
        assert len(response.tool_calls) > 0

        tool_call = response.tool_calls[0]
        assert tool_call.name == "get_weather"
        assert "location" in tool_call.arguments
        assert tool_call.id is not None

        # Step 2: Simulate tool execution and send result
        tool_result = "24℃, sunny"

        messages = response.messages
        messages.append(
            Message(
                role="user",
                type="tool_result",
                content=tool_result,
                tool_use_id=tool_call.id,
            )
        )

        # Step 3: Get final response
        final_response = await adapter.run_with_tools(
            model=os.getenv("CLAUDE_MODEL", "MiniMax-M2"),
            messages=messages,
            tools=tools,
            params=params,
        )

        # Assertions for final response
        assert final_response.content is not None
        assert len(final_response.content) > 0
        has_temp = "24" in final_response.content
        has_weather = "sunny" in final_response.content.lower()
        assert has_temp or has_weather

    async def test_tool_calling_without_explicit_instruction(
        self, adapter, weather_tool
    ):
        """Test that model can decide to use tool without explicit instruction."""
        tools = [weather_tool]

        messages = [Message(role="user", content="How's the weather in Beijing?")]

        params = ToolExecutionParams(
            tools=tools,
            max_tokens=4096,
            temperature=0.7,
        )

        response = await adapter.run_with_tools(
            model=os.getenv("CLAUDE_MODEL", "MiniMax-M2"),
            messages=messages,
            tools=tools,
            params=params,
        )

        # Model should either call the tool or ask for clarification
        # We just check it doesn't crash
        assert response.content is not None or response.tool_calls is not None


@pytest.mark.integration
@pytest.mark.asyncio
class TestClaudeInterleavedThinking:
    """Test MiniMax's Interleaved Thinking support."""

    async def test_raw_content_preservation(self, adapter):
        """Test that raw_content is preserved for MiniMax."""
        messages = [Message(role="user", content="Say 'Hello' in Chinese.")]

        response = await adapter.generate(
            model=os.getenv("CLAUDE_MODEL", "MiniMax-M2"),
            messages=messages,
            params=GenerationParams(max_tokens=200),
        )

        # Check that raw_content is preserved in response messages
        assistant_message = response.messages[-1]
        assert assistant_message.role == "assistant"

        # If using MiniMax, raw_content should be present
        if os.getenv("ANTHROPIC_BASE_URL"):
            assert assistant_message.raw_content is not None

    async def test_tool_calling_preserves_context(self, adapter):
        """Test tool calling preserves context for Interleaved Thinking."""
        tools = [
            ToolDefinition(
                name="get_weather",
                description="Get weather information",
                parameters={
                    "type": "object",
                    "properties": {"location": {"type": "string"}},
                    "required": ["location"],
                },
            )
        ]

        messages = [
            Message(
                role="user",
                content="Please check the weather in Tokyo, Japan using the tool.",
            )
        ]

        response = await adapter.run_with_tools(
            model=os.getenv("CLAUDE_MODEL", "MiniMax-M2"),
            messages=messages,
            tools=tools,
            params=ToolExecutionParams(tools=tools, max_tokens=4096),
        )

        if response.tool_calls:
            # Check that raw_content is preserved
            assistant_message = response.messages[-1]
            if os.getenv("ANTHROPIC_BASE_URL"):
                assert assistant_message.raw_content is not None


@pytest.mark.integration
@pytest.mark.asyncio
class TestClaudeCompatibility:
    """Test compatibility with different providers."""

    async def test_base_url_configuration(self):
        """Test that adapter respects ANTHROPIC_BASE_URL."""
        base_url = os.getenv("ANTHROPIC_BASE_URL")
        adapter = ClaudeAdapter()

        if base_url:
            assert adapter.base_url == base_url

        await adapter.close()

    async def test_model_capabilities(self, adapter):
        """Test getting model capabilities."""
        model = os.getenv("CLAUDE_MODEL", "MiniMax-M2")
        capabilities = await adapter.get_capabilities(model)

        assert capabilities.supports_tools is True
        assert capabilities.supports_streaming is True


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-m", "integration"])
