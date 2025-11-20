"""Factory for creating LLM adapters."""

from typing import Dict, Optional

from pydantic import BaseModel, Field

from ..errors import ConfigurationError
from .base import BaseLLMAdapter
from .claude import ClaudeAdapter
from .local import LocalAdapter
from .openai import OpenAIAdapter


class LLMConfig(BaseModel):
    """Configuration for LLM providers.

    This model defines the configuration for connecting to various LLM providers.
    """

    provider: str = Field(..., description="Provider name: 'openai', 'claude', 'local'")
    api_key: Optional[str] = Field(None, description="API key for the provider")
    base_url: Optional[str] = Field(
        None, description="Custom base URL (for local providers)"
    )
    default_model: str = Field(..., description="Default model to use")
    timeout: float = Field(60.0, description="Request timeout in seconds")
    max_retries: int = Field(3, description="Maximum retry attempts")


class ProviderFactory:
    """Factory for creating LLM adapters based on configuration.

    This factory creates the appropriate adapter instance based on the provider
    name and configuration. It supports OpenAI, Claude, and Local providers.
    """

    _adapters: Dict[str, type] = {
        "openai": OpenAIAdapter,
        "claude": ClaudeAdapter,
        "local": LocalAdapter,
    }

    @classmethod
    def create_adapter(
        cls,
        provider: str,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        timeout: float = 60.0,
        **kwargs,
    ) -> BaseLLMAdapter:
        """Create an adapter instance for the specified provider.

        Args:
            provider: Provider name ('openai', 'claude', 'local')
            api_key: API key (optional, will use env var if not provided)
            base_url: Custom base URL (for local providers)
            timeout: Request timeout in seconds
            **kwargs: Additional adapter-specific parameters

        Returns:
            An instance of the appropriate adapter

        Raises:
            ConfigurationError: If provider is not supported or config is invalid
            ModelNotFoundError: If provider adapter class is not found
        """
        provider = provider.lower()

        if provider not in cls._adapters:
            raise ConfigurationError(
                f"Unsupported provider: {provider}. "
                f"Supported providers: {', '.join(cls._adapters.keys())}"
            )

        adapter_class = cls._adapters[provider]

        try:
            if provider == "openai":
                return adapter_class(
                    api_key=api_key,
                    base_url=base_url,
                    timeout=timeout,
                )
            elif provider == "claude":
                return adapter_class(
                    api_key=api_key,
                    base_url=base_url,
                    timeout=timeout,
                )
            elif provider == "local":
                if not base_url:
                    raise ConfigurationError("base_url is required for local provider")
                return adapter_class(
                    base_url=base_url,
                    api_key=api_key,
                    timeout=timeout,
                )
        except Exception as e:
            raise ConfigurationError(
                f"Failed to create {provider} adapter: {str(e)}"
            ) from e

    @classmethod
    def create_adapter_from_config(cls, config: LLMConfig) -> BaseLLMAdapter:
        """Create an adapter from a configuration object.

        Args:
            config: LLM configuration object

        Returns:
            An instance of the appropriate adapter
        """
        return cls.create_adapter(
            provider=config.provider,
            api_key=config.api_key,
            base_url=config.base_url,
            timeout=config.timeout,
        )

    @classmethod
    def detect_provider(cls, model: str) -> str:
        """Detect the provider based on the model name.

        Args:
            model: Model name

        Returns:
            Detected provider name

        Raises:
            ModelNotFoundError: If provider cannot be detected
        """
        model_lower = model.lower()

        # OpenAI models
        if (
            model_lower.startswith("gpt-")
            or model_lower.startswith("o1-")
            or model_lower.startswith("o3-")
        ):
            return "openai"

        # Anthropic Claude models
        if model_lower.startswith("claude-"):
            return "claude"

        # Local models (various naming patterns)
        # These are heuristics - actual detection may vary
        local_indicators = [
            "llama",
            "codellama",
            "mistral",
            "phi",
            "gemma",
            "qwen",
            "yi",
            "deepseek",
            "vicuna",
            "alpaca",
        ]
        if any(indicator in model_lower for indicator in local_indicators):
            return "local"

        # Default to OpenAI if we can't determine
        return "openai"

    @classmethod
    def create_adapter_for_model(
        cls,
        model: str,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        timeout: float = 60.0,
        **kwargs,
    ) -> BaseLLMAdapter:
        """Create an adapter based on model name.

        This method detects the provider from the model name and creates
        the appropriate adapter.

        Args:
            model: Model name
            api_key: API key (optional)
            base_url: Custom base URL (for local providers)
            timeout: Request timeout in seconds
            **kwargs: Additional adapter-specific parameters

        Returns:
            An instance of the appropriate adapter
        """
        provider = cls.detect_provider(model)

        return cls.create_adapter(
            provider=provider,
            api_key=api_key,
            base_url=base_url,
            timeout=timeout,
            **kwargs,
        )

    @classmethod
    def register_adapter(cls, provider: str, adapter_class: type) -> None:
        """Register a new adapter for a provider.

        Args:
            provider: Provider name
            adapter_class: Adapter class (must inherit from BaseLLMAdapter)
        """
        if not issubclass(adapter_class, BaseLLMAdapter):
            raise ConfigurationError("Adapter class must inherit from BaseLLMAdapter")

        cls._adapters[provider.lower()] = adapter_class


def create_adapter(
    provider: str,
    model: str,
    api_key: Optional[str] = None,
    base_url: Optional[str] = None,
    timeout: float = 60.0,
    **kwargs,
) -> BaseLLMAdapter:
    """Convenience function to create an adapter.

    Args:
        provider: Provider name ('openai', 'claude', 'local')
        model: Model name
        api_key: API key (optional)
        base_url: Custom base URL (for local providers)
        timeout: Request timeout in seconds
        **kwargs: Additional adapter-specific parameters

    Returns:
        An instance of the appropriate adapter
    """
    return ProviderFactory.create_adapter(
        provider=provider,
        api_key=api_key,
        base_url=base_url,
        timeout=timeout,
        **kwargs,
    )


def create_adapter_for_model(
    model: str,
    api_key: Optional[str] = None,
    base_url: Optional[str] = None,
    timeout: float = 60.0,
    **kwargs,
) -> BaseLLMAdapter:
    """Convenience function to create an adapter for a model.

    Args:
        model: Model name
        api_key: API key (optional)
        base_url: Custom base URL (for local providers)
        timeout: Request timeout in seconds
        **kwargs: Additional adapter-specific parameters

    Returns:
        An instance of the appropriate adapter
    """
    return ProviderFactory.create_adapter_for_model(
        model=model,
        api_key=api_key,
        base_url=base_url,
        timeout=timeout,
        **kwargs,
    )
