from typing import Any, Dict, Optional

from pydantic import BaseModel


class ToolExecuteRequest(BaseModel):
    """Request schema for executing a tool."""

    arguments: Dict[str, Any]
    timeout: Optional[float] = 30.0


class ToolExecuteResponse(BaseModel):
    """Response schema for tool execution."""

    tool_name: str
    success: bool
    result: Optional[Any] = None
    error: Optional[str] = None
    execution_time_ms: Optional[float] = None
