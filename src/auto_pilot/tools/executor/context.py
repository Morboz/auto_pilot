"""Execution context management for tool execution."""

import logging
import uuid
from datetime import datetime
from typing import Any, Dict, Optional

from auto_pilot.tools.types.base import ExecutionContext
from auto_pilot.tools.types.permissions import ToolPermissions

logger = logging.getLogger(__name__)


class ExecutionContextManager:
    """Manages execution contexts for tool execution."""

    def __init__(self):
        """Initialize the execution context manager."""
        self._contexts: Dict[str, Dict[str, Any]] = {}
        logger.info("ExecutionContextManager initialized")

    def create_context(
        self,
        tool_name: str,
        arguments: Dict[str, Any],
        context: ExecutionContext,
        permissions: ToolPermissions,
    ) -> Dict[str, Any]:
        """Create an execution context for tool execution.

        Args:
            tool_name: Name of the tool
            arguments: Tool arguments
            context: Base execution context
            permissions: Tool permissions

        Returns:
            Complete execution context
        """
        execution_id = str(uuid.uuid4())

        execution_context = {
            "execution_id": execution_id,
            "tool_name": tool_name,
            "arguments": arguments,
            "task_id": context.task_id,
            "agent_id": context.agent_id,
            "workspace_path": context.workspace_path,
            "execution_timeout": context.execution_timeout,
            "enable_sandbox": context.enable_sandbox,
            "permissions": permissions,
            "start_time": datetime.now(),
            "retry_count": context.retry_count,
            "max_retries": context.max_retries,
            "metadata": context.metadata.copy(),
        }

        # Store context
        self._contexts[execution_id] = execution_context

        logger.info("Created execution context %s for tool '%s'", execution_id, tool_name)
        return execution_context

    def get_context(self, execution_id: str) -> Optional[Dict[str, Any]]:
        """Get execution context by ID.

        Args:
            execution_id: Execution context ID

        Returns:
            Execution context or None if not found
        """
        return self._contexts.get(execution_id)

    def update_context(self, execution_id: str, updates: Dict[str, Any]) -> bool:
        """Update execution context.

        Args:
            execution_id: Execution context ID
            updates: Updates to apply

        Returns:
            True if context was updated
        """
        if execution_id not in self._contexts:
            return False

        self._contexts[execution_id].update(updates)
        logger.debug("Updated execution context %s", execution_id)
        return True

    def complete_context(
        self, execution_id: str, result: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Complete execution context with result.

        Args:
            execution_id: Execution context ID
            result: Execution result

        Returns:
            Completed context or None if not found
        """
        context = self._contexts.get(execution_id)
        if not context:
            return None

        context["end_time"] = datetime.now()
        context["result"] = result
        context["execution_time_ms"] = (
            context["end_time"] - context["start_time"]
        ).total_seconds() * 1000

        logger.info("Completed execution context %s", execution_id)
        return context

    def cleanup_context(self, execution_id: str) -> bool:
        """Clean up execution context.

        Args:
            execution_id: Execution context ID

        Returns:
            True if context was cleaned up
        """
        if execution_id in self._contexts:
            del self._contexts[execution_id]
            logger.debug("Cleaned up execution context %s", execution_id)
            return True
        return False

    def get_active_contexts(self) -> Dict[str, Dict[str, Any]]:
        """Get all active execution contexts.

        Returns:
            Dictionary of active contexts
        """
        return self._contexts.copy()

    def get_context_stats(self) -> Dict[str, int]:
        """Get execution context statistics.

        Returns:
            Dictionary with statistics
        """
        return {
            "active_contexts": len(self._contexts),
            "total_created": len(self._contexts),  # Simplified for now
        }

    def clear_all_contexts(self) -> None:
        """Clear all execution contexts."""
        count = len(self._contexts)
        self._contexts.clear()
        logger.info("Cleared %d execution contexts", count)


class ExecutionEnvironment:
    """Represents the execution environment for a tool."""

    def __init__(self, context: Dict[str, Any]):
        """Initialize execution environment.

        Args:
            context: Execution context
        """
        self.context = context
        self.tool_name = context["tool_name"]
        self.arguments = context["arguments"]
        self.permissions = context["permissions"]
        self.workspace_path = context.get("workspace_path")

    def get_allowed_paths(self) -> list:
        """Get allowed file system paths.

        Returns:
            List of allowed paths
        """
        return self.permissions.filesystem.allowed_paths

    def get_environment_variables(self) -> Dict[str, str]:
        """Get environment variables for execution.

        Returns:
            Dictionary of environment variables
        """
        return self.permissions.security.environment_variables.copy()

    def is_network_enabled(self) -> bool:
        """Check if network access is enabled.

        Returns:
            True if network is enabled
        """
        return self.permissions.network.enabled

    def get_resource_limits(self) -> Dict[str, Any]:
        """Get resource limits for execution.

        Returns:
            Dictionary of resource limits
        """
        return {
            "max_cpu_percent": self.permissions.resources.max_cpu_percent,
            "max_memory_mb": self.permissions.resources.max_memory_mb,
            "max_execution_time_seconds": self.permissions.resources.max_execution_time_seconds,
        }

    def create_sandbox_config(self) -> Dict[str, Any]:
        """Create sandbox configuration.

        Returns:
            Sandbox configuration dictionary
        """
        return {
            "working_directory": self.workspace_path or "/tmp/sandbox",
            "environment_variables": self.get_environment_variables(),
            "enable_networking": self.is_network_enabled(),
            "resource_limits": self.get_resource_limits(),
            "allowed_paths": self.get_allowed_paths(),
        }
