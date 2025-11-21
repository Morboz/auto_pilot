"""Execution Loop module for auto_pilot Agent Runtime.

This module implements the core execution loop that orchestrates:
- Plan → Act → Observe → Re-plan cycle
- State management and persistence
- Event callbacks for real-time streaming
- Error handling and retry logic
"""

from .callbacks import (
    BaseExecutionCallback,
    CallbackManager,
    WebSocketCallback,
)
from .executor import AgentExecutor
from .state_manager import AgentState, StateManager
from .types import (
    EventType,
    ExecutionConfig,
    ExecutionEvent,
    ExecutionStatus,
    ExecutionStep,
    TaskContext,
    TaskInput,
    TaskOutput,
    ToolCallRecord,
)

__all__ = [
    # Core classes
    "AgentExecutor",
    "StateManager",
    "AgentState",
    # Types
    "ExecutionConfig",
    "ExecutionStep",
    "TaskInput",
    "TaskOutput",
    "ExecutionEvent",
    "EventType",
    "ExecutionStatus",
    "TaskContext",
    "ToolCallRecord",
    # Callbacks
    "BaseExecutionCallback",
    "CallbackManager",
    "WebSocketCallback",
]
