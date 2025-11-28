"""Retry logic for tool execution with intelligent error categorization."""

import logging
import re
from enum import Enum
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class ErrorCategory(str, Enum):
    """Error categories for retry logic."""

    TRANSIENT = "transient"
    PERMANENT = "permanent"
    VALIDATION = "validation"
    PERMISSION = "permission"
    TIMEOUT = "timeout"
    NETWORK = "network"
    RESOURCE = "resource"
    UNKNOWN = "unknown"


class RetryManager:
    """Manages retry logic for tool execution."""

    def __init__(self):
        """Initialize the retry manager."""
        # Define retryable error patterns
        self.transient_error_patterns = [
            r"timeout",
            r"connection.*error",
            r"network.*error",
            r"rate.?limit",
            r"503",
            r"504",
            r"502",
            r"429",
            r"temporarily unavailable",
            r"server.*error",
            r"internal.*error",
            r"try.?again",
            r"retry",
        ]

        self.network_error_patterns = [
            r"connection.*refused",
            r"connection.*reset",
            r"connection.*aborted",
            r"network.*unreachable",
            r"host.*unreachable",
            r"dns.*error",
            r"name.*resolution",
        ]

        # Non-retryable error patterns
        self.non_retryable_patterns = [
            r"permission.*denied",
            r"authorization.*failed",
            r"authentication.*failed",
            r"invalid.*parameter",
            r"validation.*error",
            r"schema.*error",
            r"file.*not.*found",
            r"directory.*not.*found",
            r"syntax.*error",
            r"import.*error",
            r"module.*not.*found",
            r"attribute.*error",
            r"key.*error",
            r"value.*error",
        ]

        logger.info("RetryManager initialized")

    def is_retryable_error(self, error: str, error_type: Optional[str] = None) -> bool:
        """Check if an error is retryable.

        Args:
            error: Error message
            error_type: Optional error type

        Returns:
            True if error is retryable
        """
        if not error:
            return False

        error_lower = error.lower()

        # Check error type first
        if error_type:
            retryable_types = {
                ErrorCategory.TRANSIENT,
                ErrorCategory.TIMEOUT,
                ErrorCategory.NETWORK,
                ErrorCategory.RESOURCE,
            }

            non_retryable_types = {
                ErrorCategory.PERMANENT,
                ErrorCategory.PERMISSION,
                ErrorCategory.VALIDATION,
            }

            if ErrorCategory(error_type) in non_retryable_types:
                return False
            if ErrorCategory(error_type) in retryable_types:
                return True

        # Check non-retryable patterns
        for pattern in self.non_retryable_patterns:
            if re.search(pattern, error_lower):
                logger.debug("Error matched non-retryable pattern: %s", pattern)
                return False

        # Check transient patterns
        for pattern in self.transient_error_patterns:
            if re.search(pattern, error_lower):
                logger.debug("Error matched retryable pattern: %s", pattern)
                return True

        # Check network patterns
        for pattern in self.network_error_patterns:
            if re.search(pattern, error_lower):
                logger.debug("Error matched network pattern: %s", pattern)
                return True

        # Default: conservatively retry unknown errors
        logger.debug("Error did not match any pattern, treating as retryable")
        return True

    def categorize_error(self, error: str, error_type: Optional[str] = None) -> str:
        """Categorize an error for retry logic.

        Args:
            error: Error message
            error_type: Optional error type hint

        Returns:
            Error category
        """
        if error_type:
            try:
                return ErrorCategory(error_type).value
            except ValueError:
                pass

        error_lower = error.lower()

        # Check for permission errors
        if re.search(r"permission|authorization|authentication", error_lower):
            return ErrorCategory.PERMISSION.value

        # Check for validation errors
        if re.search(r"invalid|validation|schema", error_lower):
            return ErrorCategory.VALIDATION.value

        # Check for timeout errors
        if re.search(r"timeout|timed out", error_lower):
            return ErrorCategory.TIMEOUT.value

        # Check for network errors
        for pattern in self.network_error_patterns:
            if re.search(pattern, error_lower):
                return ErrorCategory.NETWORK.value

        # Check for resource errors
        if re.search(r"memory|disk|cpu|resource", error_lower):
            return ErrorCategory.RESOURCE.value

        # Check for transient errors
        for pattern in self.transient_error_patterns:
            if re.search(pattern, error_lower):
                return ErrorCategory.TRANSIENT.value

        # Default categorization
        return ErrorCategory.UNKNOWN.value

    def calculate_retry_delay(
        self,
        attempt: int,
        base_delay: float = 1.0,
        max_delay: float = 60.0,
        backoff_factor: float = 2.0,
    ) -> float:
        """Calculate retry delay with exponential backoff.

        Args:
            attempt: Current attempt number (0-based)
            base_delay: Base delay in seconds
            max_delay: Maximum delay in seconds
            backoff_factor: Backoff multiplier

        Returns:
            Delay in seconds
        """
        delay = base_delay * (backoff_factor**attempt)
        return min(delay, max_delay)

    def get_retry_config(self, error_category: str) -> Dict[str, Any]:
        """Get retry configuration for an error category.

        Args:
            error_category: Error category

        Returns:
            Retry configuration
        """
        configs = {
            ErrorCategory.TRANSIENT.value: {
                "max_retries": 5,
                "base_delay": 1.0,
                "backoff_factor": 2.0,
                "max_delay": 30.0,
            },
            ErrorCategory.TIMEOUT.value: {
                "max_retries": 3,
                "base_delay": 2.0,
                "backoff_factor": 1.5,
                "max_delay": 20.0,
            },
            ErrorCategory.NETWORK.value: {
                "max_retries": 4,
                "base_delay": 1.0,
                "backoff_factor": 2.0,
                "max_delay": 30.0,
            },
            ErrorCategory.RESOURCE.value: {
                "max_retries": 2,
                "base_delay": 5.0,
                "backoff_factor": 1.0,
                "max_delay": 10.0,
            },
        }

        return configs.get(error_category, {"max_retries": 1, "base_delay": 1.0})

    def should_retry(self, attempt: int, max_retries: int) -> bool:
        """Check if another retry should be attempted.

        Args:
            attempt: Current attempt number (0-based)
            max_retries: Maximum number of retries

        Returns:
            True if should retry
        """
        return attempt < max_retries

    def add_custom_pattern(
        self, pattern: str, category: str, is_retryable: bool
    ) -> None:
        """Add a custom error pattern.

        Args:
            pattern: Regex pattern to match
            category: Error category for this pattern
            is_retryable: Whether errors matching this pattern are retryable
        """
        if is_retryable:
            self.transient_error_patterns.append(pattern)
        else:
            self.non_retryable_patterns.append(pattern)

        logger.info("Added custom pattern for category '%s': %s", category, pattern)

    def get_error_patterns(self) -> Dict[str, List[str]]:
        """Get all configured error patterns.

        Returns:
            Dictionary of patterns by category
        """
        return {
            "transient": self.transient_error_patterns[:],
            "network": self.network_error_patterns[:],
            "non_retryable": self.non_retryable_patterns[:],
        }


class RetryStatistics:
    """Tracks retry statistics for monitoring."""

    def __init__(self):
        """Initialize retry statistics."""
        self.total_attempts = 0
        self.successful_retries = 0
        self.failed_retries = 0
        self.retry_by_category: Dict[str, int] = {}
        self.total_delay_ms = 0

    def record_retry(self, error_category: str, success: bool, delay_ms: float) -> None:
        """Record a retry attempt.

        Args:
            error_category: Error category
            success: Whether retry succeeded
            delay_ms: Delay before retry in milliseconds
        """
        self.total_attempts += 1
        self.total_delay_ms += delay_ms

        if success:
            self.successful_retries += 1
        else:
            self.failed_retries += 1

        self.retry_by_category[error_category] = (
            self.retry_by_category.get(error_category, 0) + 1
        )

    def get_statistics(self) -> Dict[str, Any]:
        """Get retry statistics.

        Returns:
            Dictionary with statistics
        """
        total_retries = self.successful_retries + self.failed_retries
        success_rate = (
            self.successful_retries / total_retries if total_retries > 0 else 0
        )

        return {
            "total_attempts": self.total_attempts,
            "successful_retries": self.successful_retries,
            "failed_retries": self.failed_retries,
            "success_rate": success_rate,
            "retry_by_category": self.retry_by_category.copy(),
            "average_delay_ms": self.total_delay_ms / total_retries
            if total_retries > 0
            else 0,
        }

    def reset(self) -> None:
        """Reset statistics."""
        self.total_attempts = 0
        self.successful_retries = 0
        self.failed_retries = 0
        self.retry_by_category.clear()
        self.total_delay_ms = 0
