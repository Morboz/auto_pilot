"""Tool Sandbox for isolated execution."""

import asyncio
import inspect
import logging
import time
from typing import Any, Callable, Dict, List, Optional, Tuple

from ..types.base import ToolDefinition
from ..types.permissions import ResourceLimits, ToolPermissions
from ..types.sandbox import ResourceUsage, SandboxConfig, SandboxResult

logger = logging.getLogger(__name__)


class ToolSandbox:
    """Isolated execution environment for tools."""

    def __init__(self, config: Optional[SandboxConfig] = None):
        """Initialize tool sandbox.

        Args:
            config: Sandbox configuration
        """
        self.config = config or SandboxConfig()
        self.active_sandboxes: Dict[str, Any] = {}
        logger.info("ToolSandbox initialized")

    async def execute(
        self,
        tool: ToolDefinition,
        arguments: Dict[str, Any],
        implementation: Callable,
        timeout: float = 30.0,
        permissions: Optional[ToolPermissions] = None,
    ) -> SandboxResult:
        """Execute a tool in sandboxed environment.

        Args:
            tool: Tool definition
            arguments: Tool arguments
            implementation: Tool implementation function
            timeout: Execution timeout in seconds
            permissions: Security permissions

        Returns:
            Sandbox execution result
        """
        sandbox_id = f"{tool.name}_{int(time.time())}"
        start_time = time.time()

        try:
            # Validate permissions
            if permissions and not self._validate_permissions(permissions):
                return SandboxResult(
                    success=False,
                    error_message="Invalid permissions configuration",
                    exit_code=-1,
                )

            # Execute with monitoring
            before_stats = self._get_resource_stats()

            # Run implementation with timeout
            result = await self._run_with_timeout(
                implementation=implementation,
                arguments=arguments,
                timeout=timeout,
            )

            # Calculate resource usage
            after_stats = self._get_resource_stats()
            resource_usage = self._calculate_usage(before_stats, after_stats)

            execution_time = time.time() - start_time

            return SandboxResult(
                success=True,
                result=result,
                execution_time_ms=execution_time * 1000,
                resource_usage=resource_usage,
                exit_code=0,
            )

        except asyncio.TimeoutError:
            execution_time = time.time() - start_time
            logger.warning(
                "Tool '%s' execution timed out after %ss", tool.name, timeout
            )
            return SandboxResult(
                success=False,
                error_message=f"Execution timed out after {timeout}s",
                execution_time_ms=execution_time * 1000,
                exit_code=-1,
            )

        except Exception as e:
            execution_time = time.time() - start_time
            logger.error("Sandbox execution error: %s", str(e), exc_info=True)
            return SandboxResult(
                success=False,
                error_message=str(e),
                execution_time_ms=execution_time * 1000,
                exit_code=1,
            )

    async def _run_with_timeout(
        self,
        implementation: Callable,
        arguments: Dict[str, Any],
        timeout: float,
    ) -> Any:
        """Run implementation with timeout.

        Args:
            implementation: Function to execute
            arguments: Function arguments
            timeout: Timeout in seconds

        Returns:
            Execution result

        Raises:
            asyncio.TimeoutError: If execution times out
        """
        if inspect.iscoroutinefunction(implementation):
            return await asyncio.wait_for(implementation(**arguments), timeout=timeout)

        loop = asyncio.get_event_loop()
        return await asyncio.wait_for(
            loop.run_in_executor(None, lambda: implementation(**arguments)),
            timeout=timeout,
        )

    def _validate_permissions(self, permissions: ToolPermissions) -> bool:
        """Validate permissions.

        Args:
            permissions: Permissions to validate

        Returns:
            True if valid
        """
        try:
            # Basic validation - in production this would be more comprehensive
            if permissions.resources.max_execution_time_seconds <= 0:
                return False
            if permissions.resources.max_memory_mb <= 0:
                return False
            return True
        except Exception:
            return False

    def _get_resource_stats(self) -> Dict[str, float]:
        """Get current resource statistics.

        Returns:
            Resource statistics
        """
        try:
            import psutil

            process = psutil.Process()
            memory_info = process.memory_info()

            return {
                "cpu_percent": psutil.cpu_percent(interval=None),
                "memory_mb": memory_info.rss / (1024 * 1024),  # Convert to MB
                "disk_read_mb": psutil.disk_io_counters().read_bytes / (1024 * 1024),
                "disk_write_mb": psutil.disk_io_counters().write_bytes / (1024 * 1024),
                "timestamp": time.time(),
            }
        except Exception as e:
            logger.debug("Could not get resource stats: %s", e)
            return {"timestamp": time.time()}

    def _calculate_usage(
        self,
        before: Dict[str, float],
        after: Dict[str, float],
    ) -> ResourceUsage:
        """Calculate resource usage between two snapshots.

        Args:
            before: Before execution stats
            after: After execution stats

        Returns:
            Resource usage
        """
        execution_time = after["timestamp"] - before["timestamp"]

        return ResourceUsage(
            cpu_percent=after.get("cpu_percent", 0) - before.get("cpu_percent", 0),
            memory_mb=after.get("memory_mb", 0),
            disk_read_mb=after.get("disk_read_mb", 0) - before.get("disk_read_mb", 0),
            disk_write_mb=after.get("disk_write_mb", 0)
            - before.get("disk_write_mb", 0),
            execution_time_seconds=execution_time,
            peak_memory_mb=after.get("memory_mb", 0),
        )


class ResourceMonitor:
    """Monitors system resources during execution."""

    def __init__(self):
        """Initialize resource monitor."""
        self.monitoring = False
        self.measurements: List[Dict[str, Any]] = []
        logger.info("ResourceMonitor initialized")

    def start_monitoring(self) -> None:
        """Start resource monitoring."""
        self.monitoring = True
        self.measurements = []
        logger.info("Resource monitoring started")

    def stop_monitoring(self) -> Dict[str, Any]:
        """Stop monitoring and return statistics.

        Returns:
            Monitoring statistics
        """
        self.monitoring = False
        stats = self.get_statistics()
        logger.info("Resource monitoring stopped")
        return stats

    def record_measurement(self) -> None:
        """Record a resource measurement."""
        if not self.monitoring:
            return

        try:
            measurement = self._get_measurement()
            self.measurements.append(measurement)
        except Exception as e:
            logger.debug("Failed to record measurement: %s", e)

    def _get_measurement(self) -> Dict[str, float]:
        """Get a resource measurement.

        Returns:
            Measurement dictionary
        """
        try:
            import psutil

            process = psutil.Process()
            memory_info = process.memory_info()
            cpu_percent = process.cpu_percent(interval=0.1)

            return {
                "timestamp": time.time(),
                "cpu_percent": cpu_percent,
                "memory_mb": memory_info.rss / (1024 * 1024),
            }
        except Exception:
            return {"timestamp": time.time(), "cpu_percent": 0, "memory_mb": 0}

    def get_statistics(self) -> Dict[str, Any]:
        """Get monitoring statistics.

        Returns:
            Statistics dictionary
        """
        if not self.measurements:
            return {"measurements": 0}

        cpu_values = [m["cpu_percent"] for m in self.measurements]
        memory_values = [m["memory_mb"] for m in self.measurements]

        return {
            "measurements": len(self.measurements),
            "avg_cpu_percent": sum(cpu_values) / len(cpu_values) if cpu_values else 0,
            "max_cpu_percent": max(cpu_values) if cpu_values else 0,
            "avg_memory_mb": sum(memory_values) / len(memory_values)
            if memory_values
            else 0,
            "max_memory_mb": max(memory_values) if memory_values else 0,
        }

    def check_limits(self, limits: ResourceLimits) -> Tuple[bool, Optional[str]]:
        """Check if current usage is within limits.

        Args:
            limits: Resource limits

        Returns:
            Tuple of (within_limits, violation_message)
        """
        try:
            import psutil

            # Check memory
            memory = psutil.virtual_memory()
            memory_usage_mb = memory.used / (1024 * 1024)

            if memory_usage_mb > limits.max_memory_mb:
                return (
                    False,
                    f"Memory usage {memory_usage_mb:.1f}MB exceeds limit {limits.max_memory_mb}MB",
                )

            # Check CPU
            cpu_percent = psutil.cpu_percent(interval=0.1)
            if cpu_percent > limits.max_cpu_percent:
                return (
                    False,
                    f"CPU usage {cpu_percent:.1f}% exceeds limit {limits.max_cpu_percent}%",
                )

            return True, None
        except Exception as e:
            logger.debug("Could not check resource limits: %s", e)
            return True, None


class OutputSanitizer:
    """Sanitizes tool output for security."""

    def __init__(self):
        """Initialize output sanitizer."""
        self.sensitive_patterns = [
            # File paths
            (r"/[^\s]*", "[FILE_PATH]"),
            # IP addresses
            (r"\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b", "[IP_ADDRESS]"),
            # Email addresses
            (r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b", "[EMAIL]"),
            # API keys
            (r"\b[a-zA-Z0-9-_]{32,}\b", "[API_KEY]"),
            # Passwords
            (r"password\s*[:=]\s*[^\s]+", "password=[REDACTED]"),
            (r"pwd\s*[:=]\s*[^\s]+", "pwd=[REDACTED]"),
            # Connection strings
            (r"(\w+://)[^\s]+", r"\1[REDACTED]"),
        ]
        logger.info("OutputSanitizer initialized")

    def sanitize(
        self, output: str, permissions: Optional[ToolPermissions] = None
    ) -> str:
        """Sanitize output.

        Args:
            output: Output to sanitize
            permissions: Permissions (for configuration)

        Returns:
            Sanitized output
        """
        if not output:
            return output

        # Check if sanitization is enabled
        if permissions and not permissions.security.enable_output_sanitization:
            return output

        sanitized = output
        for pattern, replacement in self.sensitive_patterns:
            try:
                import re

                sanitized = re.sub(pattern, replacement, sanitized, flags=re.IGNORECASE)
            except Exception as e:
                logger.debug("Pattern sanitization failed: %s", e)

        return sanitized

    def add_pattern(self, pattern: str, replacement: str) -> None:
        """Add a custom sanitization pattern.

        Args:
            pattern: Regex pattern
            replacement: Replacement string
        """
        self.sensitive_patterns.append((pattern, replacement))
        logger.info("Added custom sanitization pattern: %s", pattern)

    def get_patterns(self) -> List[Tuple[str, str]]:
        """Get all sanitization patterns.

        Returns:
            List of (pattern, replacement) tuples
        """
        return self.sensitive_patterns.copy()
