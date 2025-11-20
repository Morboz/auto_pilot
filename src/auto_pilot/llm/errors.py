"""Error handling for LLM Adapter layer."""

from typing import Any, Dict, Optional


class LLMAdapterError(Exception):
    """Base exception for all LLM adapter errors.

    All adapter-specific exceptions should inherit from this class.
    """

    def __init__(
        self,
        message: str,
        error_code: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        """Initialize LLM adapter error.

        Args:
            message: Human-readable error message
            error_code: Optional machine-readable error code
            details: Optional additional error details
        """
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.details = details or {}


class ConfigurationError(LLMAdapterError):
    """Raised when there's a configuration issue.

    This includes missing API keys, invalid configuration, etc.
    """

    pass


class AuthenticationError(LLMAdapterError):
    """Raised when authentication fails (invalid API key, expired token, etc.)."""

    pass


class RateLimitError(LLMAdapterError):
    """Raised when rate limits are exceeded.

    This is a transient error that may be retried with backoff.
    """

    def __init__(
        self,
        message: str,
        retry_after: Optional[int] = None,
        **kwargs,
    ):
        """Initialize rate limit error.

        Args:
            message: Error message
            retry_after: Optional seconds to wait before retrying
        """
        super().__init__(message, **kwargs)
        self.retry_after = retry_after


class ModelNotFoundError(LLMAdapterError):
    """Raised when the specified model is not available or not found."""

    pass


class InvalidRequestError(LLMAdapterError):
    """Raised when the request is invalid.

    This includes malformed messages, exceeding context length, etc.
    """

    pass


class StreamingError(LLMAdapterError):
    """Raised when an error occurs during streaming."""

    pass


class ToolExecutionError(LLMAdapterError):
    """Raised when there's an error executing a tool."""

    pass


class StructuredOutputError(LLMAdapterError):
    """Raised when structured output validation fails."""

    pass


class ProviderError(LLMAdapterError):
    """Wraps provider-specific errors.

    This exception is used to wrap and normalize errors from the underlying
    LLM provider APIs.
    """

    def __init__(
        self,
        original_error: Exception,
        provider: str,
        message: Optional[str] = None,
        **kwargs,
    ):
        """Initialize provider error.

        Args:
            original_error: The original exception from the provider
            provider: Name of the provider (e.g., 'openai', 'claude')
            message: Optional custom error message
        """
        if message is None:
            message = f"{provider} error: {str(original_error)}"

        super().__init__(
            message,
            details={
                "provider": provider,
                "original_error": str(original_error),
                "original_error_type": type(original_error).__name__,
            },
            **kwargs,
        )

        self.original_error = original_error
        self.provider = provider


def map_provider_error(error: Exception, provider: str) -> LLMAdapterError:
    """Map provider-specific errors to unified error types.

    Args:
        error: The original error from the provider
        provider: Name of the provider (e.g., 'openai', 'claude')

    Returns:
        Mapped LLMAdapterError
    """
    error_str = str(error).lower()

    # Common error mappings
    if "auth" in error_str or "api key" in error_str or "token" in error_str:
        return AuthenticationError(
            f"Authentication failed with {provider}: {error}",
            details={"original_error": str(error), "provider": provider},
        )

    if "rate limit" in error_str or "429" in error_str:
        return RateLimitError(
            f"Rate limit exceeded with {provider}: {error}",
        )

    if "not found" in error_str or "404" in error_str:
        return ModelNotFoundError(
            f"Model not found with {provider}: {error}",
            details={"original_error": str(error), "provider": provider},
        )

    if "invalid" in error_str or "400" in error_str:
        return InvalidRequestError(
            f"Invalid request to {provider}: {error}",
            details={"original_error": str(error), "provider": provider},
        )

    # Generic provider error
    return ProviderError(
        original_error=error,
        provider=provider,
    )
