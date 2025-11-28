"""Enhanced Tool Executor for orchestrating tool execution."""

import asyncio
import logging
import time
from typing import Any, Callable, Dict, List, Optional

from ..permissions import PermissionManager, SecurityPolicyEnforcer
from ..registry import ToolRegistry
from ..sandbox import ToolSandbox
from ..types.base import ExecutionContext, ExecutionResult, ToolDefinition
from .context import ExecutionContextManager
from .metrics import ExecutionMetrics
from .retry import RetryManager

logger = logging.getLogger(__name__)


class ToolExecutor:
    """Enhanced tool executor that coordinates with registry, permissions, and sandbox."""

    def __init__(
        self,
        registry: Optional[ToolRegistry] = None,
        permission_manager: Optional[PermissionManager] = None,
        security_enforcer: Optional[SecurityPolicyEnforcer] = None,
        sandbox: Optional[ToolSandbox] = None,
        default_timeout: float = 30.0,
        enable_metrics: bool = True,
    ):
        """Initialize the enhanced tool executor.

        Args:
            registry: Tool registry for tool definitions
            permission_manager: Permission manager for access control
            security_enforcer: Security policy enforcer
            sandbox: Tool sandbox for isolated execution
            default_timeout: Default execution timeout
            enable_metrics: Whether to collect execution metrics
        """
        self.registry = registry or ToolRegistry()
        self.permission_manager = permission_manager or PermissionManager()
        self.security_enforcer = security_enforcer or SecurityPolicyEnforcer()
        self.sandbox = sandbox or ToolSandbox()
        self.default_timeout = default_timeout
        self.enable_metrics = enable_metrics

        self.context_manager = ExecutionContextManager()
        self.retry_manager = RetryManager()
        self.metrics = ExecutionMetrics() if enable_metrics else None

        # Tool implementations storage
        self._tool_implementations: Dict[str, Callable] = {}

        logger.info("Enhanced ToolExecutor initialized")

    def register_tool_implementation(
        self, tool_name: str, implementation: Callable
    ) -> None:
        """Register a tool implementation.

        Args:
            tool_name: Name of the tool
            implementation: Async callable that implements the tool
        """
        self._tool_implementations[tool_name] = implementation
        logger.info("Tool implementation registered for '%s'", tool_name)

    async def execute(
        self,
        tool_name: str,
        arguments: Dict[str, Any],
        context: Optional[ExecutionContext] = None,
        timeout: Optional[float] = None,
        retry_config: Optional[Dict[str, Any]] = None,
    ) -> ExecutionResult:
        """Execute a tool with the given arguments.

        Args:
            tool_name: Name of the tool to execute
            arguments: Tool arguments
            context: Execution context
            timeout: Optional timeout override
            retry_config: Optional retry configuration

        Returns:
            Execution result
        """
        start_time = time.time()
        timeout = timeout or self.default_timeout
        context = context or ExecutionContext(task_id=f"task_{int(start_time)}")

        try:
            # Get tool definition from registry
            tool_definition = self.registry.get_tool(tool_name)
            if not tool_definition:
                return ExecutionResult.error_result(
                    error=f"Tool '{tool_name}' not found in registry",
                    error_type="tool_not_found",
                    execution_time_ms=(time.time() - start_time) * 1000,
                )

            # Validate arguments against schema
            try:
                self.registry.validate_tool_parameters(tool_name, arguments)
            except ValueError as e:
                return ExecutionResult.error_result(
                    error=f"Parameter validation failed: {str(e)}",
                    error_type="validation_error",
                    execution_time_ms=(time.time() - start_time) * 1000,
                )

            # Get tool permissions
            permissions = self.permission_manager.get_tool_permissions(tool_name)

            # Create execution context
            execution_context = self.context_manager.create_context(
                tool_name=tool_name,
                arguments=arguments,
                context=context,
                permissions=permissions,
            )

            # Execute with retry logic
            result = await self._execute_with_retry(
                tool_definition=tool_definition,
                arguments=arguments,
                execution_context=execution_context,
                timeout=timeout,
                retry_config=retry_config,
            )

            # Update metrics
            if self.metrics:
                self.metrics.record_execution(tool_name, result)

            # Audit execution
            self.security_enforcer.audit_execution(
                tool_name=tool_name,
                execution_context=execution_context,
                permissions=permissions,
                result={"success": result.success, "error_type": result.error_type},
            )

            return result

        except Exception as e:
            logger.error(
                "Unexpected error during tool execution: %s", str(e), exc_info=True
            )
            return ExecutionResult.error_result(
                error=f"Unexpected error: {str(e)}",
                error_type="internal_error",
                execution_time_ms=(time.time() - start_time) * 1000,
            )

    async def _execute_with_retry(
        self,
        tool_definition: ToolDefinition,
        arguments: Dict[str, Any],
        execution_context: Dict[str, Any],
        timeout: float,
        retry_config: Optional[Dict[str, Any]],
    ) -> ExecutionResult:
        """Execute tool with retry logic.

        Args:
            tool_definition: Tool definition
            arguments: Tool arguments
            execution_context: Execution context
            timeout: Execution timeout
            retry_config: Retry configuration

        Returns:
            Execution result
        """
        max_retries = retry_config.get("max_retries", 3) if retry_config else 3
        retry_delay = retry_config.get("retry_delay", 1.0) if retry_config else 1.0

        for attempt in range(max_retries + 1):
            try:
                result = await self._execute_single(
                    tool_definition=tool_definition,
                    arguments=arguments,
                    execution_context=execution_context,
                    timeout=timeout,
                )

                if result.success:
                    return result

                # Check if error is retryable
                if not self.retry_manager.is_retryable_error(
                    result.error, result.error_type
                ):
                    return result

                if attempt < max_retries:
                    logger.info(
                        "Retrying tool execution (attempt %d/%d)",
                        attempt + 2,
                        max_retries + 1,
                    )
                    await asyncio.sleep(
                        retry_delay * (2**attempt)
                    )  # Exponential backoff

            except asyncio.TimeoutError:
                if attempt < max_retries:
                    logger.info(
                        "Tool execution timed out, retrying (attempt %d/%d)",
                        attempt + 2,
                        max_retries + 1,
                    )
                    await asyncio.sleep(retry_delay * (2**attempt))
                else:
                    return ExecutionResult.error_result(
                        error=f"Tool execution timed out after {timeout}s and {max_retries} retries",
                        error_type="timeout_error",
                        execution_time_ms=timeout * 1000,
                    )

            except Exception as e:
                error_type = self.retry_manager.categorize_error(str(e))
                if (
                    not self.retry_manager.is_retryable_error(str(e), error_type)
                    or attempt >= max_retries
                ):
                    return ExecutionResult.error_result(
                        error=str(e),
                        error_type=error_type,
                        execution_time_ms=execution_context.get("execution_time_ms", 0),
                    )

                logger.info(
                    "Retrying after error (attempt %d/%d): %s",
                    attempt + 2,
                    max_retries + 1,
                    str(e),
                )
                await asyncio.sleep(retry_delay * (2**attempt))

        return ExecutionResult.error_result(
            error=f"Tool execution failed after {max_retries + 1} attempts",
            error_type="max_retries_exceeded",
            execution_time_ms=execution_context.get("execution_time_ms", 0),
        )

    async def _execute_single(
        self,
        tool_definition: ToolDefinition,
        arguments: Dict[str, Any],
        execution_context: Dict[str, Any],
        timeout: float,
    ) -> ExecutionResult:
        """Execute a tool once (single attempt).

        Args:
            tool_definition: Tool definition
            arguments: Tool arguments
            execution_context: Execution context
            timeout: Execution timeout

        Returns:
            Execution result
        """
        start_time = time.time()
        tool_name = tool_definition.name

        try:
            # Check if sandbox execution is enabled
            if execution_context.get("enable_sandbox", True):
                result = await self._execute_in_sandbox(
                    tool_definition=tool_definition,
                    arguments=arguments,
                    execution_context=execution_context,
                    timeout=timeout,
                )
            else:
                result = await self._execute_directly(
                    tool_definition=tool_definition,
                    arguments=arguments,
                    execution_context=execution_context,
                    timeout=timeout,
                )

            execution_time_ms = (time.time() - start_time) * 1000
            result.execution_time_ms = execution_time_ms

            return result

        except asyncio.TimeoutError:
            execution_time_ms = (time.time() - start_time) * 1000
            return ExecutionResult.error_result(
                error=f"Tool execution timed out after {timeout}s",
                error_type="timeout_error",
                execution_time_ms=execution_time_ms,
            )

        except Exception as e:
            execution_time_ms = (time.time() - start_time) * 1000
            logger.error("Tool execution error: %s", str(e), exc_info=True)
            return ExecutionResult.error_result(
                error=str(e),
                error_type="execution_error",
                execution_time_ms=execution_time_ms,
            )

    async def _execute_in_sandbox(
        self,
        tool_definition: ToolDefinition,
        arguments: Dict[str, Any],
        execution_context: Dict[str, Any],
        timeout: float,
    ) -> ExecutionResult:
        """Execute tool in sandbox environment.

        Args:
            tool_definition: Tool definition
            arguments: Tool arguments
            execution_context: Execution context
            timeout: Execution timeout

        Returns:
            Execution result
        """
        # Get tool implementation
        implementation = self._tool_implementations.get(tool_definition.name)
        if not implementation:
            return ExecutionResult.error_result(
                error=f"No implementation found for tool '{tool_definition.name}'",
                error_type="implementation_not_found",
            )

        # Execute in sandbox
        sandbox_result = await self.sandbox.execute(
            tool=tool_definition,
            implementation=implementation,
            arguments=arguments,
            permissions=execution_context.get("permissions"),
            timeout=timeout,
        )

        if sandbox_result.success:
            return ExecutionResult.success_result(
                result=sandbox_result.result,
                resource_usage=sandbox_result.resource_usage.model_dump(),
            )
        else:
            return ExecutionResult.error_result(
                error=sandbox_result.error_message,
                error_type="sandbox_error",
                resource_usage=sandbox_result.resource_usage.model_dump(),
            )

    async def _execute_directly(
        self,
        tool_definition: ToolDefinition,
        arguments: Dict[str, Any],
        execution_context: Dict[str, Any],
        timeout: float,
    ) -> ExecutionResult:
        """Execute tool directly without sandbox (for trusted tools).

        Args:
            tool_definition: Tool definition
            arguments: Tool arguments
            execution_context: Execution context
            timeout: Execution timeout

        Returns:
            Execution result
        """
        tool_name = tool_definition.name
        implementation = self._tool_implementations.get(tool_name)

        if not implementation:
            return ExecutionResult.error_result(
                error=f"No implementation found for tool '{tool_name}'",
                error_type="implementation_not_found",
            )

        try:
            # Execute with timeout
            result = await asyncio.wait_for(
                implementation(**arguments),
                timeout=timeout,
            )

            return ExecutionResult.success_result(result=result)

        except asyncio.TimeoutError:
            raise

        except Exception as e:
            return ExecutionResult.error_result(
                error=str(e),
                error_type="execution_error",
            )

    def format_result_for_llm(self, result: ExecutionResult) -> str:
        """Format execution result for LLM consumption.

        Args:
            result: Execution result

        Returns:
            Formatted result string
        """
        if result.success:
            # Format successful result
            if isinstance(result.result, dict):
                import json

                result_str = json.dumps(result.result, indent=2, ensure_ascii=False)
            elif isinstance(result.result, (list, tuple)):
                import json

                result_str = json.dumps(result.result, ensure_ascii=False)
            else:
                result_str = str(result.result)

            return f"""Tool Execution Result:
Status: Success
Execution Time: {result.execution_time_ms:.2f}ms
Result:
{result_str}"""
        else:
            # Format error result
            return f"""Tool Execution Result:
Status: Failed
Error Type: {result.error_type or 'unknown'}
Error: {result.error}
Execution Time: {result.execution_time_ms:.2f}ms"""

    def get_execution_metrics(self) -> Optional[Dict[str, Any]]:
        """Get execution metrics.

        Returns:
            Execution metrics if enabled, None otherwise
        """
        if not self.metrics:
            return None

        return self.metrics.get_metrics()

    def clear_metrics(self) -> None:
        """Clear execution metrics."""
        if self.metrics:
            self.metrics.clear()

    async def execute_batch(
        self,
        executions: List[Dict[str, Any]],
        context: Optional[ExecutionContext] = None,
        max_concurrent: int = 5,
    ) -> List[ExecutionResult]:
        """Execute multiple tools concurrently.

        Args:
            executions: List of execution configurations
            context: Shared execution context
            max_concurrent: Maximum concurrent executions

        Returns:
            List of execution results
        """
        semaphore = asyncio.Semaphore(max_concurrent)

        async def execute_single(exec_config: Dict[str, Any]) -> ExecutionResult:
            async with semaphore:
                return await self.execute(
                    tool_name=exec_config["tool_name"],
                    arguments=exec_config["arguments"],
                    context=context,
                    timeout=exec_config.get("timeout"),
                )

        # Execute all tools concurrently
        tasks = [execute_single(exec_config) for exec_config in executions]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Handle exceptions
        processed_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                processed_results.append(
                    ExecutionResult.error_result(
                        error=f"Batch execution error: {str(result)}",
                        error_type="batch_error",
                    )
                )
            else:
                processed_results.append(result)

        return processed_results
