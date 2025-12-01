"""Base type definitions for tool system components."""

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class ToolMetadata(BaseModel):
    """Metadata for tool definitions."""

    name: str
    description: str
    version: str = "1.0.0"
    category: Optional[str] = None
    author: Optional[str] = None
    tags: List[str] = Field(default_factory=list)
    deprecated: bool = False
    deprecated_message: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)


class ToolSchema(BaseModel):
    """JSON schema wrapper for tool parameters."""

    schema_dict: Dict[str, Any] = Field(alias="schema")
    schema_version: str = "https://json-schema.org/draft/2020-12/schema"

    class Config:
        allow_population_by_field_name = True


class ToolDefinition(BaseModel):
    """Enhanced tool definition with metadata and schema."""

    metadata: ToolMetadata
    parameters: ToolSchema
    required_permissions: Optional[List[str]] = None
    resource_limits: Optional[Dict[str, Any]] = None
    execution_config: Optional[Dict[str, Any]] = None

    @property
    def name(self) -> str:
        """Get tool name from metadata."""
        return self.metadata.name

    @property
    def description(self) -> str:
        """Get tool description from metadata."""
        return self.metadata.description


class ExecutionContext(BaseModel):
    """Context for tool execution."""

    task_id: str
    agent_id: Optional[str] = None
    workspace_path: Optional[str] = None
    execution_timeout: float = 30.0
    enable_sandbox: bool = True
    retry_count: int = 0
    max_retries: int = 3
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ExecutionResult(BaseModel):
    """Result of tool execution."""

    success: bool
    result: Optional[Any] = None
    error: Optional[str] = None
    error_type: Optional[str] = None
    execution_time_ms: float = 0.0
    resource_usage: Optional[Dict[str, Any]] = None
    timestamp: datetime = Field(default_factory=datetime.now)

    @classmethod
    def success_result(
        cls, result: Any, execution_time_ms: float = 0.0, **kwargs
    ) -> "ExecutionResult":
        """Create a successful execution result."""
        return cls(success=True, result=result, execution_time_ms=execution_time_ms, **kwargs)

    @classmethod
    def error_result(
        cls,
        error: str,
        error_type: Optional[str] = None,
        execution_time_ms: float = 0.0,
        **kwargs,
    ) -> "ExecutionResult":
        """Create an error execution result."""
        return cls(
            success=False,
            error=error,
            error_type=error_type,
            execution_time_ms=execution_time_ms,
            **kwargs,
        )
