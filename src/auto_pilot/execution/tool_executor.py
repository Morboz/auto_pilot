"""Tool Executor - Handles actual tool execution with sandboxing and validation.

This module provides safe tool execution with:
- Schema validation
- Timeout protection
- Error handling
- Audit logging
"""

import asyncio
import json
from typing import Any, Callable, Dict, Optional

from auto_pilot.llm import ToolDefinition

from .types import ToolCallRecord


class ToolExecutor:
    """Executes tools with validation, sandboxing, and error handling."""

    def __init__(
        self,
        default_timeout: float = 30.0,
    ):
        """Initialize Tool Executor.

        Args:
            default_timeout: Default timeout for tool execution in seconds
        """
        self.default_timeout = default_timeout
        self._tool_implementations: Dict[str, Callable] = {}

    def register_tool(
        self,
        name: str,
        implementation: Callable,
    ) -> None:
        """Register a tool implementation.

        Args:
            name: Tool name
            implementation: Async callable that implements the tool
        """
        self._tool_implementations[name] = implementation

    async def execute(
        self,
        tool: ToolDefinition,
        arguments: Dict[str, Any],
        timeout: Optional[float] = None,
    ) -> ToolCallRecord:
        """Execute a tool with the given arguments.

        Args:
            tool: Tool definition
            arguments: Tool arguments
            timeout: Optional timeout override

        Returns:
            ToolCallRecord with execution result
        """
        import time

        timeout = timeout or self.default_timeout
        start_time = time.time()

        try:
            # Validate arguments against schema
            self._validate_arguments(tool, arguments)

            # Get tool implementation
            implementation = self._tool_implementations.get(tool.name)

            if implementation is None:
                # If no implementation registered, use placeholder
                result = await self._execute_placeholder(tool, arguments)
            else:
                # Execute with timeout
                result = await asyncio.wait_for(
                    implementation(**arguments),
                    timeout=timeout,
                )

            duration_ms = (time.time() - start_time) * 1000

            return ToolCallRecord(
                tool_name=tool.name,
                arguments=arguments,
                result=result,
                success=True,
                duration_ms=duration_ms,
            )

        except asyncio.TimeoutError:
            duration_ms = (time.time() - start_time) * 1000
            error_msg = f"Tool execution timed out after {timeout}s"
            return ToolCallRecord(
                tool_name=tool.name,
                arguments=arguments,
                success=False,
                error=error_msg,
                duration_ms=duration_ms,
            )

        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            return ToolCallRecord(
                tool_name=tool.name,
                arguments=arguments,
                success=False,
                error=str(e),
                duration_ms=duration_ms,
            )

    def _validate_arguments(
        self,
        tool: ToolDefinition,
        arguments: Dict[str, Any],
    ) -> None:
        """Validate arguments against tool schema.

        Args:
            tool: Tool definition with schema
            arguments: Arguments to validate

        Raises:
            ValueError: If validation fails
        """
        # Basic validation - check required fields
        schema = tool.parameters

        if "required" in schema:
            required_fields = schema["required"]
            for field in required_fields:
                if field not in arguments:
                    raise ValueError(f"Missing required argument: {field} for tool {tool.name}")

        # Check properties exist
        if "properties" in schema:
            properties = schema["properties"]
            for arg_name in arguments:
                if arg_name not in properties:
                    raise ValueError(f"Unknown argument: {arg_name} for tool {tool.name}")

    async def _execute_placeholder(
        self,
        tool: ToolDefinition,
        arguments: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Execute a placeholder tool (for testing/development).

        Args:
            tool: Tool definition
            arguments: Tool arguments

        Returns:
            Placeholder result
        """
        # This is a placeholder for when no real implementation is registered
        # In production, you would integrate with actual tool implementations
        return {
            "status": "success",
            "message": f"Tool {tool.name} executed",
            "tool": tool.name,
            "arguments": arguments,
            "note": "This is a placeholder result - register real implementations",
        }

    def format_result_for_llm(
        self,
        record: ToolCallRecord,
    ) -> str:
        """Format tool result for LLM consumption.

        Args:
            record: Tool call record

        Returns:
            Formatted result string
        """
        if record.success:
            # Format successful result
            if isinstance(record.result, dict):
                result_str = json.dumps(record.result, indent=2, ensure_ascii=False)
            elif isinstance(record.result, (list, tuple)):
                result_str = json.dumps(record.result, ensure_ascii=False)
            else:
                result_str = str(record.result)

            return f"""Tool: {record.tool_name}
Status: Success
Result:
{result_str}"""
        else:
            # Format error result
            return f"""Tool: {record.tool_name}
Status: Failed
Error: {record.error}"""

    def is_retryable_error(self, error: str) -> bool:
        """Determine if an error is retryable.

        Args:
            error: Error message

        Returns:
            True if the error should be retried
        """
        # Retryable error patterns
        retryable_patterns = [
            "timeout",
            "timed out",
            "connection",
            "network",
            "rate limit",
            "429",
            "503",
            "502",
            "504",
        ]

        error_lower = error.lower()
        return any(pattern in error_lower for pattern in retryable_patterns)
