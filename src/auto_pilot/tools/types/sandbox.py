"""Sandbox-related type definitions."""

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class ResourceUsage(BaseModel):
    """Resource usage metrics for sandbox execution."""

    cpu_percent: float = 0.0
    memory_mb: float = 0.0
    disk_read_mb: float = 0.0
    disk_write_mb: float = 0.0
    network_sent_mb: float = 0.0
    network_received_mb: float = 0.0
    peak_memory_mb: float = 0.0
    execution_time_seconds: float = 0.0


class SandboxConfig(BaseModel):
    """Configuration for tool sandbox execution."""

    sandbox_type: str = "process"  # process, container, vm
    working_directory: str = "/tmp/sandbox"
    environment_variables: Dict[str, str] = Field(default_factory=dict)
    allowed_binaries: List[str] = Field(default_factory=list)
    blocked_system_calls: List[str] = Field(default_factory=list)
    enable_networking: bool = False
    enable_gui: bool = False
    shared_memory_mb: int = 64
    max_processes: int = 5
    user_id: int = 1000
    group_id: int = 1000


class SandboxResult(BaseModel):
    """Result from sandboxed execution."""

    success: bool
    result: Optional[Any] = None
    exit_code: int = 0
    stdout: str = ""
    stderr: str = ""
    error_message: Optional[str] = None
    execution_time_ms: float = 0.0
    resource_usage: ResourceUsage = Field(default_factory=ResourceUsage)
    created_files: List[str] = Field(default_factory=list)
    modified_files: List[str] = Field(default_factory=list)
    timestamp: datetime = Field(default_factory=datetime.now)
