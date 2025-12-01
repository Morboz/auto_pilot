"""API models for Controller module."""

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class TaskStartRequest(BaseModel):
    """Request model for starting a new task."""

    input: str = Field(..., description="The user input for the task")
    agent_id: Optional[str] = Field(None, description="Optional agent ID")
    config: Optional[Dict[str, Any]] = Field(
        default_factory=dict, description="Optional execution configuration"
    )


class TaskStartResponse(BaseModel):
    """Response model for task start."""

    task_id: str = Field(..., description="The ID of the created task")
    status: str = Field(..., description="Task status")
    message: Optional[str] = Field(None, description="Optional message")


class TaskStatusResponse(BaseModel):
    """Response model for task status."""

    task_id: str = Field(..., description="Task ID")
    status: str = Field(..., description="Current status")
    user_input: str = Field(..., description="User input for the task")
    current_step: int = Field(..., description="Current execution step")
    max_steps: int = Field(..., description="Maximum steps allowed")
    final_output: Optional[str] = Field(None, description="Final output if completed")
    error: Optional[str] = Field(None, description="Error message if failed")
    created_at: str = Field(..., description="Creation timestamp")
    updated_at: str = Field(..., description="Last update timestamp")
    steps: List[Dict[str, Any]] = Field(default_factory=list, description="Execution steps")
    tool_calls: List[Dict[str, Any]] = Field(default_factory=list, description="Tool call history")


class ApiResponse(BaseModel):
    """Generic API response."""

    success: bool = Field(..., description="Whether the request succeeded")
    message: Optional[str] = Field(None, description="Response message")
    data: Optional[Any] = Field(None, description="Response data")


class TaskControlRequest(BaseModel):
    """Request model for task control operations."""

    task_id: str = Field(..., description="Task ID to control")
