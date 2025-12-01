"""Permission validation utilities."""

import logging
from typing import Any, Dict

from auto_pilot.tools.types.permissions import ToolPermissions

logger = logging.getLogger(__name__)


class PermissionValidator:
    """Validates permissions and access requests."""

    def __init__(self):
        """Initialize the permission validator."""
        logger.info("PermissionValidator initialized")

    def validate_permissions(self, permissions: ToolPermissions) -> bool:
        """Validate that permissions are well-formed and consistent.

        Args:
            permissions: Permissions to validate

        Returns:
            True if permissions are valid

        Raises:
            ValueError: If permissions are invalid
        """
        # Validate filesystem permissions
        self._validate_filesystem_permissions(permissions.filesystem)

        # Validate network permissions
        self._validate_network_permissions(permissions.network)

        # Validate resource limits
        self._validate_resource_limits(permissions.resources)

        # Validate security policy
        self._validate_security_policy(permissions.security)

        logger.debug("Permissions validation passed")
        return True

    def validate_access_request(
        self,
        permissions: ToolPermissions,
        access_type: str,
        resource: str,
        operation: str,
    ) -> bool:
        """Validate a specific access request.

        Args:
            permissions: Tool permissions
            access_type: Type of access (filesystem, network, etc.)
            resource: Resource being accessed
            operation: Operation being performed

        Returns:
            True if access is valid

        Raises:
            ValueError: If access is invalid
        """
        if access_type == "filesystem":
            return self._validate_filesystem_access(permissions.filesystem, resource, operation)
        elif access_type == "network":
            return self._validate_network_access(permissions.network, resource, operation)
        else:
            raise ValueError(f"Unknown access type: {access_type}")

    def _validate_filesystem_permissions(self, fs_perm) -> None:
        """Validate filesystem permissions.

        Args:
            fs_perm: Filesystem permission configuration

        Raises:
            ValueError: If permissions are invalid
        """
        # Validate operations
        valid_operations = {"read", "write", "execute", "delete"}
        for op in fs_perm.operations:
            if op not in valid_operations:
                raise ValueError(f"Invalid filesystem operation: {op}")

        # Validate paths
        for path in fs_perm.allowed_paths + fs_perm.denied_paths:
            if not isinstance(path, str):
                raise ValueError(f"Invalid path type: {type(path)}")

        logger.debug("Filesystem permissions validation passed")

    def _validate_network_permissions(self, net_perm) -> None:
        """Validate network permissions.

        Args:
            net_perm: Network permission configuration

        Raises:
            ValueError: If permissions are invalid
        """
        # Validate ports
        for port in net_perm.allowed_ports:
            if not isinstance(port, int) or port < 0 or port > 65535:
                raise ValueError(f"Invalid port number: {port}")

        # Validate hosts
        for host in net_perm.allowed_hosts + net_perm.denied_hosts:
            if not isinstance(host, str):
                raise ValueError(f"Invalid host type: {type(host)}")

        logger.debug("Network permissions validation passed")

    def _validate_resource_limits(self, resource_limits) -> None:
        """Validate resource limits.

        Args:
            resource_limits: Resource limits configuration

        Raises:
            ValueError: If limits are invalid
        """
        # Validate CPU percentage
        if resource_limits.max_cpu_percent < 0 or resource_limits.max_cpu_percent > 100:
            raise ValueError(f"Invalid CPU percentage: {resource_limits.max_cpu_percent}")

        # Validate memory (must be positive)
        if resource_limits.max_memory_mb <= 0:
            raise ValueError(f"Invalid memory limit: {resource_limits.max_memory_mb}")

        # Validate disk space (must be positive)
        if resource_limits.max_disk_space_mb <= 0:
            raise ValueError(f"Invalid disk space limit: {resource_limits.max_disk_space_mb}")

        # Validate execution time (must be positive)
        if resource_limits.max_execution_time_seconds <= 0:
            raise ValueError(
                f"Invalid execution time limit: {resource_limits.max_execution_time_seconds}"
            )

        logger.debug("Resource limits validation passed")

    def _validate_security_policy(self, security_policy) -> None:
        """Validate security policy.

        Args:
            security_policy: Security policy configuration

        Raises:
            ValueError: If policy is invalid
        """
        # Validate imports
        for import_name in security_policy.allowed_imports + security_policy.blocked_imports:
            if not isinstance(import_name, str):
                raise ValueError(f"Invalid import name type: {type(import_name)}")

        # Validate environment variables
        for var_name, var_value in security_policy.environment_variables.items():
            if not isinstance(var_name, str):
                raise ValueError(f"Invalid environment variable name: {type(var_name)}")
            if not isinstance(var_value, str):
                raise ValueError(f"Invalid environment variable value: {type(var_value)}")

        logger.debug("Security policy validation passed")

    def _validate_filesystem_access(self, fs_perm, resource: str, operation: str) -> bool:
        """Validate filesystem access request.

        Args:
            fs_perm: Filesystem permissions
            resource: Path being accessed
            operation: Operation being performed

        Returns:
            True if access is valid

        Raises:
            ValueError: If access is invalid
        """
        # Check operation
        if operation not in fs_perm.operations:
            raise ValueError(f"Operation '{operation}' not allowed by filesystem permissions")

        # Check path (simplified validation)
        if not isinstance(resource, str):
            raise ValueError(f"Invalid resource path type: {type(resource)}")

        logger.debug(f"Filesystem access validation passed for {operation} on {resource}")
        return True

    def _validate_network_access(self, net_perm, resource: str, operation: str) -> bool:
        """Validate network access request.

        Args:
            net_perm: Network permissions
            resource: Network resource being accessed
            operation: Operation being performed

        Returns:
            True if access is valid

        Raises:
            ValueError: If access is invalid
        """
        if not net_perm.enabled:
            raise ValueError("Network access is disabled")

        # Validate resource format (simplified)
        if not isinstance(resource, str):
            raise ValueError(f"Invalid network resource type: {type(resource)}")

        logger.debug("Network access validation passed for %s on %s", operation, resource)
        return True

    def check_permission_compatibility(
        self,
        requested_permissions: ToolPermissions,
        existing_permissions: ToolPermissions,
    ) -> bool:
        """Check if requested permissions are compatible with existing ones.

        Args:
            requested_permissions: Permissions being requested
            existing_permissions: Existing permissions to check against

        Returns:
            True if permissions are compatible

        Raises:
            ValueError: If permissions are incompatible
        """
        # Check if requested permissions are more restrictive
        # This is a simplified check - in practice, this could be more complex

        # Check filesystem permissions
        if not self._is_filesystem_compatible(
            requested_permissions.filesystem, existing_permissions.filesystem
        ):
            raise ValueError("Filesystem permissions are incompatible")

        # Check network permissions
        if not self._is_network_compatible(
            requested_permissions.network, existing_permissions.network
        ):
            raise ValueError("Network permissions are incompatible")

        logger.debug("Permission compatibility check passed")
        return True

    def _is_filesystem_compatible(self, requested, existing) -> bool:
        """Check filesystem permission compatibility.

        Args:
            requested: Requested filesystem permissions
            existing: Existing filesystem permissions

        Returns:
            True if compatible
        """
        # Simplified compatibility check
        # In practice, this would check path overlaps, etc.
        return True

    def _is_network_compatible(self, requested, existing) -> bool:
        """Check network permission compatibility.

        Args:
            requested: Requested network permissions
            existing: Existing network permissions

        Returns:
            True if compatible
        """
        # Simplified compatibility check
        if not existing.enabled and requested.enabled:
            return False
        return True

    def generate_permission_summary(self, permissions: ToolPermissions) -> Dict[str, Any]:
        """Generate a human-readable summary of permissions.

        Args:
            permissions: Permissions to summarize

        Returns:
            Dictionary with permission summary
        """
        return {
            "filesystem_access": {
                "allowed_paths": len(permissions.filesystem.allowed_paths),
                "denied_paths": len(permissions.filesystem.denied_paths),
                "operations": list(permissions.filesystem.operations),
            },
            "network_access": {
                "enabled": permissions.network.enabled,
                "allowed_hosts": len(permissions.network.allowed_hosts),
                "allowed_ports": len(permissions.network.allowed_ports),
            },
            "resource_limits": {
                "max_cpu_percent": permissions.resources.max_cpu_percent,
                "max_memory_mb": permissions.resources.max_memory_mb,
                "max_execution_time_seconds": permissions.resources.max_execution_time_seconds,
            },
            "security_features": {
                "sandbox_enabled": permissions.security.enable_sandbox,
                "output_sanitization": permissions.security.enable_output_sanitization,
                "audit_logging": permissions.security.enable_audit_logging,
            },
        }
