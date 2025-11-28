"""Main module for the tool system package."""

from .executor import ExecutionContext, RetryManager, ToolExecutor
from .permissions import PermissionManager, PermissionValidator, SecurityPolicyEnforcer
from .registry import SchemaValidator, ToolRegistry
from .sandbox import OutputSanitizer, ResourceMonitor, ToolSandbox
from .types import (
    ExecutionContext,
    ExecutionResult,
    PermissionLevel,
    ResourceLimits,
    ResourceUsage,
    SandboxConfig,
    SandboxResult,
    SecurityPolicy,
    ToolDefinition,
    ToolMetadata,
    ToolPermissions,
    ToolSchema,
)

# Version information
__version__ = "0.1.0"

# Core components for easy access
__all__ = [
    # Types
    "ToolDefinition",
    "ToolMetadata",
    "ToolSchema",
    "ExecutionResult",
    "ExecutionContext",
    "ToolPermissions",
    "PermissionLevel",
    "ResourceLimits",
    "SecurityPolicy",
    "SandboxConfig",
    "SandboxResult",
    "ResourceUsage",
    # Registry
    "ToolRegistry",
    "SchemaValidator",
    # Permissions
    "PermissionManager",
    "SecurityPolicyEnforcer",
    "PermissionValidator",
    # Executor
    "ToolExecutor",
    "RetryManager",
    # Sandbox
    "ToolSandbox",
    "ResourceMonitor",
    "OutputSanitizer",
]


def create_tool_system():
    """Create a complete tool system with all components.

    Returns:
        Dictionary with initialized components
    """
    # Initialize components
    registry = ToolRegistry()
    permission_manager = PermissionManager()
    security_enforcer = SecurityPolicyEnforcer()
    sandbox = ToolSandbox()
    executor = ToolExecutor(
        registry=registry,
        permission_manager=permission_manager,
        security_enforcer=security_enforcer,
        sandbox=sandbox,
    )

    return {
        "registry": registry,
        "permissions": permission_manager,
        "security": security_enforcer,
        "sandbox": sandbox,
        "executor": executor,
    }
