"""Tests for LLM Adapter layer."""

from unittest.mock import AsyncMock, Mock, patch

import pytest

from auto_pilot.llm import (
    ClaudeAdapter,
    LLMConfig,
    LocalAdapter,
    Message,
    ModelCapabilities,
    OpenAIAdapter,
    ProviderFactory,
    TokenUsage,
    create_adapter_for_model,
)


class TestMessage:
    """Test Message type."""

    def test_message_creation(self):
        """Test creating a basic message."""
        msg = Message(role="user", content="Hello")
        assert msg.role == "user"
        assert msg.content == "Hello"
        assert msg.type is None

    def test_message_with_type(self):
        """Test creating a message with type."""
        msg = Message(
            role="assistant",
            content="I'll use a tool",
            type="tool_use",
            name="some_tool",
        )
        assert msg.role == "assistant"
        assert msg.type == "tool_use"
        assert msg.name == "some_tool"


class TestTokenUsage:
    """Test TokenUsage type."""

    def test_token_usage(self):
        """Test token usage calculation."""
        usage = TokenUsage(input_tokens=100, output_tokens=50)
        assert usage.input_tokens == 100
        assert usage.output_tokens == 50
        assert usage.total_tokens == 150


class TestModelCapabilities:
    """Test ModelCapabilities type."""

    def test_default_capabilities(self):
        """Test default capabilities."""
        caps = ModelCapabilities()
        assert caps.supports_tools is False
        assert caps.supports_streaming is False
        assert caps.supports_json_schema is False
        assert caps.supports_images is False

    def test_custom_capabilities(self):
        """Test custom capabilities."""
        caps = ModelCapabilities(
            supports_tools=True,
            supports_streaming=True,
            max_context_length=128000,
        )
        assert caps.supports_tools is True
        assert caps.supports_streaming is True
        assert caps.max_context_length == 128000


class TestProviderFactory:
    """Test ProviderFactory."""

    def test_detect_openai(self):
        """Test detecting OpenAI provider."""
        assert ProviderFactory.detect_provider("gpt-4") == "openai"
        assert ProviderFactory.detect_provider("gpt-3.5-turbo") == "openai"
        assert ProviderFactory.detect_provider("o1-preview") == "openai"

    def test_detect_claude(self):
        """Test detecting Claude provider."""
        assert ProviderFactory.detect_provider("claude-3-sonnet") == "claude"
        assert ProviderFactory.detect_provider("claude-3-opus") == "claude"

    def test_detect_local(self):
        """Test detecting local provider."""
        assert ProviderFactory.detect_provider("llama-2-7b") == "local"
        assert ProviderFactory.detect_provider("codellama-13b") == "local"
        assert ProviderFactory.detect_provider("mistral-7b") == "local"

    @patch.dict("os.environ", {"OPENAI_API_KEY": "test-key"})
    def test_create_openai_adapter(self):
        """Test creating OpenAI adapter."""
        adapter = ProviderFactory.create_adapter("openai")
        assert isinstance(adapter, OpenAIAdapter)

    @patch.dict("os.environ", {"ANTHROPIC_API_KEY": "test-key"})
    def test_create_claude_adapter(self):
        """Test creating Claude adapter."""
        adapter = ProviderFactory.create_adapter("claude")
        assert isinstance(adapter, ClaudeAdapter)

    def test_create_local_adapter(self):
        """Test creating Local adapter."""
        adapter = ProviderFactory.create_adapter(
            "local",
            base_url="http://localhost:11434",
        )
        assert isinstance(adapter, LocalAdapter)

    def test_config_creation(self):
        """Test creating config object."""
        config = LLMConfig(
            provider="openai",
            default_model="gpt-4",
            api_key="test-key",
        )
        assert config.provider == "openai"
        assert config.default_model == "gpt-4"

    @patch.dict("os.environ", {"OPENAI_API_KEY": "test-key"})
    def test_create_adapter_for_model_openai(self):
        """Test creating adapter for OpenAI model."""
        adapter = create_adapter_for_model("gpt-4")
        assert isinstance(adapter, OpenAIAdapter)

    def test_unsupported_provider(self):
        """Test error when provider is not supported."""
        with pytest.raises(Exception):  # ConfigurationError
            ProviderFactory.create_adapter("unsupported")


class TestOpenAIAdapter:
    """Test OpenAI adapter."""

    @pytest.fixture
    def mock_client(self):
        """Create a mock OpenAI client."""
        with patch("auto_pilot.llm.adapters.openai.AsyncOpenAI") as mock:
            yield mock

    @patch.dict("os.environ", {"OPENAI_API_KEY": "test-key"})
    def test_init(self):
        """Test adapter initialization."""
        adapter = OpenAIAdapter()
        assert adapter.api_key == "test-key"

    def test_init_no_api_key(self):
        """Test adapter initialization without API key."""
        with patch.dict("os.environ", {}, clear=True):
            with pytest.raises(Exception):  # AuthenticationError
                OpenAIAdapter()

    @patch.dict("os.environ", {"OPENAI_API_KEY": "test-key"})
    def test_convert_messages_to_openai(self):
        """Test message conversion."""
        adapter = OpenAIAdapter()
        messages = [
            Message(role="system", content="You are helpful"),
            Message(role="user", content="Hello"),
        ]
        openai_messages = adapter._convert_messages_to_openai(messages)
        assert len(openai_messages) == 2
        assert openai_messages[0]["role"] == "system"
        assert openai_messages[1]["role"] == "user"


class TestClaudeAdapter:
    """Test Claude adapter."""

    @pytest.fixture
    def mock_client(self):
        """Create a mock Anthropic client."""
        with patch("auto_pilot.llm.adapters.claude.AsyncAnthropic") as mock:
            yield mock

    @patch.dict("os.environ", {"ANTHROPIC_API_KEY": "test-key"})
    def test_init(self):
        """Test adapter initialization."""
        adapter = ClaudeAdapter()
        assert adapter.api_key == "test-key"

    def test_init_no_api_key(self):
        """Test adapter initialization without API key."""
        with patch.dict("os.environ", {}, clear=True):
            with pytest.raises(Exception):  # AuthenticationError
                ClaudeAdapter()

    @patch.dict("os.environ", {"ANTHROPIC_API_KEY": "test-key"})
    def test_convert_messages_to_claude(self):
        """Test message conversion."""
        adapter = ClaudeAdapter()
        messages = [
            Message(role="system", content="You are helpful"),
            Message(role="user", content="Hello"),
        ]
        request = adapter._convert_messages_to_claude(messages)
        assert "system" in request
        assert "messages" in request


class TestLocalAdapter:
    """Test Local adapter."""

    def test_init(self):
        """Test adapter initialization."""
        adapter = LocalAdapter(base_url="http://localhost:11434")
        assert adapter.base_url == "http://localhost:11434"

    def test_init_no_base_url(self):
        """Test adapter initialization without base URL."""
        with pytest.raises(Exception):  # ConfigurationError
            LocalAdapter(base_url="")

    @patch.dict("os.environ", {"OPENAI_API_KEY": "test-key"})
    def test_convert_messages_to_openai(self):
        """Test message conversion."""
        adapter = LocalAdapter(base_url="http://localhost:11434")
        messages = [
            Message(role="system", content="You are helpful"),
            Message(role="user", content="Hello"),
        ]
        openai_messages = adapter._convert_messages_to_openai(messages)
        assert len(openai_messages) == 2


class TestIntegration:
    """Integration tests."""

    @patch.dict("os.environ", {"OPENAI_API_KEY": "test-key"})
    @pytest.mark.asyncio
    async def test_adapter_lifecycle(self):
        """Test basic adapter lifecycle."""
        adapter = OpenAIAdapter()

        # Test capabilities
        caps = await adapter.get_capabilities("gpt-4")
        assert isinstance(caps, ModelCapabilities)

        # Test message creation
        messages = [Message(role="user", content="Hello")]

        # Mock the OpenAI client response
        with patch.object(
            adapter.client.chat.completions, "create", new_callable=AsyncMock
        ) as mock_create:
            mock_response = Mock()
            mock_response.choices = [Mock()]
            mock_response.choices[0].message = Mock()
            mock_response.choices[0].message.content = "Hello!"
            mock_response.choices[0].message.tool_calls = None
            mock_response.usage = Mock()
            mock_response.usage.prompt_tokens = 10
            mock_response.usage.completion_tokens = 5
            mock_response.model = "gpt-4"
            mock_create.return_value = mock_response

            response = await adapter.generate("gpt-4", messages)

            assert response.content == "Hello!"
            assert response.usage.input_tokens == 10
            assert response.usage.output_tokens == 5
            assert response.model == "gpt-4"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
