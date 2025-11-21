"""Type definitions for Execution Loop module."""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class ExecutionStatus(str, Enum):
    """Agent execution status."""

    PENDING = "pending"  # Task created but not started
    RUNNING = "running"  # Currently executing
    PAUSED = "paused"  # Temporarily halted
    WAITING = "waiting"  # Waiting for tool response
    FINISHED = "finished"  # Completed successfully
    FAILED = "failed"  # Completed with errors
    STOPPED = "stopped"  # Manually stopped


class EventType(str, Enum):
    """Event types for execution callbacks."""

    STEP_STARTED = "step_started"
    STEP_COMPLETED = "step_completed"
    LLM_RESPONSE = "llm_response"
    TOOL_CALL_STARTED = "tool_call_started"
    TOOL_CALL_COMPLETED = "tool_call_completed"
    TOOL_RESULT = "tool_result"
    ERROR = "error"
    FINISHED = "finished"
    STATUS_CHANGED = "status_changed"


class ExecutionStep(BaseModel):
    """Represents a single execution step."""

    step_number: int
    llm_response: Optional[str] = None
    tool_calls: List[Dict[str, Any]] = Field(default_factory=list)
    tool_results: List[Dict[str, Any]] = Field(default_factory=list)
    is_final: bool = False
    timestamp: datetime = Field(default_factory=datetime.now)


class ToolCallRecord(BaseModel):
    """Record of a tool invocation."""

    tool_name: str
    arguments: Dict[str, Any]
    result: Optional[Any] = None
    success: bool = True
    error: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.now)
    duration_ms: Optional[float] = None


class TaskInput(BaseModel):
    """Input for starting a task."""

    task_id: str
    user_input: str
    agent_id: Optional[str] = None
    config: Optional[Dict[str, Any]] = None


class TaskOutput(BaseModel):
    """Output from a completed task."""

    task_id: str
    final_output: Optional[str] = None
    steps: List[ExecutionStep] = Field(default_factory=list)
    tool_calls: List[ToolCallRecord] = Field(default_factory=list)
    total_steps: int = 0
    total_tool_calls: int = 0
    error: Optional[str] = None


class ExecutionEvent(BaseModel):
    """Event for callback notifications."""

    type: EventType
    task_id: str
    data: Dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=datetime.now)


class TaskContext(BaseModel):
    """Context available during task execution."""

    task_id: str
    agent_id: Optional[str] = None
    user_input: str
    execution_status: ExecutionStatus = ExecutionStatus.PENDING
    current_step: int = 0
    max_steps: int = 50  # Prevent infinite loops
    max_retries: int = 3  # Retry attempts for failed operations


class ExecutionConfig(BaseModel):
    """Configuration for execution loop."""

    max_steps: int = 50
    max_retries: int = 3
    tool_timeout: Optional[float] = None
    step_delay: float = 0.0  # Delay between steps
    enable_streaming: bool = True
    auto_retry_errors: bool = True


class AgentState(BaseModel):
    """Complete state of an agent execution."""

    task_id: str
    agent_id: Optional[str] = None
    status: ExecutionStatus = ExecutionStatus.PENDING
    user_input: str = ""
    current_step: int = 0
    max_steps: int = 50
    max_retries: int = 3

    # Memory state (LLM-visible conversation context)
    messages: List[Dict[str, Any]] = Field(default_factory=list)

    # Tool call history
    tool_calls: List[ToolCallRecord] = Field(default_factory=list)

    # Execution history
    steps: List[ExecutionStep] = Field(default_factory=list)

    # Final output (when task completes)
    final_output: Optional[str] = None

    # Error tracking
    error: Optional[str] = None

    # Retry tracking
    retry_count: int = 0

    # Timestamps
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat(),
        }
