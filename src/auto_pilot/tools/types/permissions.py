"""Permission-related type definitions."""

from enum import Enum
from typing import Any, Dict, List, Set

from pydantic import BaseModel, Field


class PermissionLevel(str, Enum):
    """Permission levels for tool operations."""

    DENY = "deny"
    READ = "read"
    WRITE = "write"
    EXECUTE = "execute"
    FULL = "full"


class FileSystemPermission(BaseModel):
    """File system access permissions."""

    allowed_paths: List[str] = Field(default_factory=list)
    denied_paths: List[str] = Field(default_factory=list)
    operations: Set[str] = Field(default_factory=lambda: {"read", "write"})
    recursive_access: bool = True


class NetworkPermission(BaseModel):
    """Network access permissions."""

    enabled: bool = False
    allowed_hosts: List[str] = Field(default_factory=list)
    allowed_ports: List[int] = Field(default_factory=list)
    denied_hosts: List[str] = Field(default_factory=list)
    max_connections: int = 10


class ResourceLimits(BaseModel):
    """Resource usage limits for tool execution."""

    max_cpu_percent: float = 80.0
    max_memory_mb: int = 512
    max_disk_space_mb: int = 1024
    max_execution_time_seconds: float = 30.0
    max_processes: int = 5
    max_file_size_mb: int = 100


class SecurityPolicy(BaseModel):
    """Security policy for tool execution."""

    enable_sandbox: bool = True
    enable_output_sanitization: bool = True
    enable_audit_logging: bool = True
    allowed_imports: List[str] = Field(default_factory=list)
    blocked_imports: List[str] = Field(default_factory=list)
    environment_variables: Dict[str, str] = Field(default_factory=dict)


class ToolPermissions(BaseModel):
    """Complete permission set for a tool."""

    filesystem: FileSystemPermission = Field(default_factory=FileSystemPermission)
    network: NetworkPermission = Field(default_factory=NetworkPermission)
    resources: ResourceLimits = Field(default_factory=ResourceLimits)
    security: SecurityPolicy = Field(default_factory=SecurityPolicy)
    custom_permissions: Dict[str, Any] = Field(default_factory=dict)
