"""Tests for Tool Permissions component."""

from pathlib import Path

import pytest

from auto_pilot.tools.permissions import PermissionManager, PermissionValidator
from auto_pilot.tools.types.permissions import (
    FileSystemPermission,
    NetworkPermission,
    ResourceLimits,
    ToolPermissions,
)


class TestPermissionManager:
    """Test PermissionManager class."""

    def test_initialization(self):
        """Test permission manager initialization."""
        manager = PermissionManager()
        assert manager is not None

    def test_set_tool_permissions(self):
        """Test setting tool permissions."""
        manager = PermissionManager()

        permissions = ToolPermissions()
        manager.set_tool_permissions("test_tool", permissions)

        retrieved = manager.get_tool_permissions("test_tool")
        assert retrieved is not None

    def test_get_tool_permissions_default(self):
        """Test getting default permissions for unconfigured tool."""
        manager = PermissionManager()

        permissions = manager.get_tool_permissions("unknown_tool")
        assert permissions is not None
        assert isinstance(permissions, ToolPermissions)

    def test_check_filesystem_access_allowed(self):
        """Test filesystem access check - allowed."""
        manager = PermissionManager()

        perms = ToolPermissions(
            filesystem=FileSystemPermission(
                allowed_paths=[str(Path("/tmp").resolve())],
                operations=["read", "write"],
            )
        )
        manager.set_tool_permissions("test_tool", perms)

        assert (
            manager.check_filesystem_access("test_tool", "/tmp/file.txt", "read")
            is True
        )

    def test_check_filesystem_access_denied(self):
        """Test filesystem access check - denied."""
        manager = PermissionManager()

        perms = ToolPermissions(
            filesystem=FileSystemPermission(
                allowed_paths=["/tmp"],
                denied_paths=["/etc"],
                operations=["read"],
            )
        )
        manager.set_tool_permissions("test_tool", perms)

        # Denied path
        assert (
            manager.check_filesystem_access("test_tool", "/etc/passwd", "read") is False
        )

        # Operation not allowed
        assert (
            manager.check_filesystem_access("test_tool", "/tmp/file.txt", "write")
            is False
        )

    def test_check_network_access_disabled(self):
        """Test network access check when disabled."""
        manager = PermissionManager()

        perms = ToolPermissions(network=NetworkPermission(enabled=False))
        manager.set_tool_permissions("test_tool", perms)

        assert manager.check_network_access("test_tool", "example.com", 80) is False

    def test_check_network_access_allowed(self):
        """Test network access check - allowed."""
        manager = PermissionManager()

        perms = ToolPermissions(
            network=NetworkPermission(
                enabled=True,
                allowed_hosts=["api.openai.com"],
                allowed_ports=[80, 443],
            )
        )
        manager.set_tool_permissions("test_tool", perms)

        assert manager.check_network_access("test_tool", "api.openai.com", 443) is True

    def test_check_resource_limits(self):
        """Test resource limits check."""
        manager = PermissionManager()

        perms = ToolPermissions(
            resources=ResourceLimits(
                max_cpu_percent=80.0,
                max_memory_mb=512,
            )
        )
        manager.set_tool_permissions("test_tool", perms)

        # Within limits
        usage = {"cpu_percent": 50.0, "memory_mb": 256}
        assert manager.check_resource_limits("test_tool", usage) is True

    def test_create_restricted_permissions(self):
        """Test creating restricted permissions."""
        manager = PermissionManager()
        perms = manager.create_restricted_permissions()

        assert perms.network.enabled is False
        assert len(perms.filesystem.allowed_paths) == 0

    def test_create_trusted_permissions(self):
        """Test creating trusted permissions."""
        manager = PermissionManager()
        perms = manager.create_trusted_permissions()

        assert perms.network.enabled is True
        assert len(perms.filesystem.allowed_paths) > 0


class TestPermissionValidator:
    """Test PermissionValidator class."""

    def test_initialization(self):
        """Test validator initialization."""
        validator = PermissionValidator()
        assert validator is not None

    def test_validate_permissions(self):
        """Test validating permissions."""
        validator = PermissionValidator()

        perms = ToolPermissions()
        assert validator.validate_permissions(perms) is True

    def test_validate_invalid_permissions(self):
        """Test validating invalid permissions."""
        validator = PermissionValidator()

        perms = ToolPermissions()
        perms.resources.max_memory_mb = -1  # Invalid

        with pytest.raises(ValueError):
            validator.validate_permissions(perms)

    def test_validate_filesystem_permissions(self):
        """Test validating filesystem permissions."""
        validator = PermissionValidator()

        fs_perms = FileSystemPermission(
            operations=["read", "write", "invalid_op"]  # Invalid operation
        )

        perms = ToolPermissions(filesystem=fs_perms)

        with pytest.raises(ValueError):
            validator.validate_permissions(perms)

    def test_validate_network_permissions(self):
        """Test validating network permissions."""
        validator = PermissionValidator()

        net_perms = NetworkPermission(
            allowed_ports=[-1, 99999]  # Invalid ports
        )

        perms = ToolPermissions(network=net_perms)

        with pytest.raises(ValueError):
            validator.validate_permissions(perms)

    def test_validate_resource_limits(self):
        """Test validating resource limits."""
        validator = PermissionValidator()

        limits = ResourceLimits(
            max_cpu_percent=150.0,  # Invalid > 100
        )

        perms = ToolPermissions(resources=limits)

        with pytest.raises(ValueError):
            validator.validate_permissions(perms)

    def test_check_permission_compatibility(self):
        """Test checking permission compatibility."""
        validator = PermissionValidator()

        perms1 = ToolPermissions()
        perms2 = ToolPermissions()

        # Same permissions should be compatible
        assert validator.check_permission_compatibility(perms1, perms2) is True

    def test_validate_access_request(self):
        """Test validating access request."""
        validator = PermissionValidator()

        perms = ToolPermissions(
            filesystem=FileSystemPermission(
                operations=["read"],
            )
        )

        assert (
            validator.validate_access_request(
                perms, "filesystem", "/tmp/test.txt", "read"
            )
            is True
        )

    def test_generate_permission_summary(self):
        """Test generating permission summary."""
        validator = PermissionValidator()

        perms = ToolPermissions()
        summary = validator.generate_permission_summary(perms)

        assert "filesystem_access" in summary
        assert "network_access" in summary
        assert "resource_limits" in summary
        assert "security_features" in summary
