"""State Manager for execution loop.

This module provides persistent state management for agent executions,
enabling pause/resume, recovery from failures, and audit logging.
"""

import os
from datetime import datetime
from typing import List, Optional

from .types import (
    AgentState,
    ExecutionStatus,
    ExecutionStep,
    TaskContext,
    ToolCallRecord,
)


class StateManager:
    """Manages persistent state for agent executions.

    Currently implements in-memory storage. Can be extended to support
    database persistence (PostgreSQL, Redis, etc.).
    """

    def __init__(self, storage_path: Optional[str] = None):
        """Initialize State Manager.

        Args:
            storage_path: Optional path for file-based storage
        """
        self._storage_path = storage_path
        self._states: dict[str, AgentState] = {}
        self._contexts: dict[str, TaskContext] = {}

    async def load_state(self, task_id: str) -> Optional[AgentState]:
        """Load agent state for a task.

        Args:
            task_id: The task ID

        Returns:
            AgentState if found, None otherwise
        """
        if task_id in self._states:
            return self._states[task_id]

        if self._storage_path and os.path.exists(self._storage_path):
            # TODO: Load from file storage
            pass

        return None

    async def save_state(self, task_id: str, state: AgentState) -> None:
        """Save agent state for a task.

        Args:
            task_id: The task ID
            state: The agent state to save
        """
        state.updated_at = datetime.now()
        self._states[task_id] = state

        if self._storage_path:
            # TODO: Save to file storage
            pass

    async def create_state(self, context: TaskContext) -> AgentState:
        """Create a new agent state.

        Args:
            context: The initial task context

        Returns:
            The newly created agent state
        """
        state = AgentState(
            task_id=context.task_id,
            agent_id=context.agent_id,
            status=ExecutionStatus.PENDING,
            user_input=context.user_input,
            current_step=0,
            max_steps=context.max_steps,
            max_retries=context.max_retries,
        )

        await self.save_state(context.task_id, state)
        self._contexts[context.task_id] = context
        return state

    async def append_step(self, task_id: str, step: ExecutionStep) -> None:
        """Append a step to the execution history.

        Args:
            task_id: The task ID
            step: The execution step to append
        """
        state = await self.load_state(task_id)
        if state:
            state.steps.append(step)
            await self.save_state(task_id, state)

    async def update_execution_status(self, task_id: str, status: ExecutionStatus) -> None:
        """Update the execution status.

        Args:
            task_id: The task ID
            status: The new status
        """
        state = await self.load_state(task_id)
        if state:
            state.status = status
            await self.save_state(task_id, state)

    async def record_tool_call(self, task_id: str, record: ToolCallRecord) -> None:
        """Record a tool call in history.

        Args:
            task_id: The task ID
            record: The tool call record
        """
        state = await self.load_state(task_id)
        if state:
            state.tool_calls.append(record)
            await self.save_state(task_id, state)

    async def update_current_step(self, task_id: str, step: int) -> None:
        """Update the current step number.

        Args:
            task_id: The task ID
            step: The new current step
        """
        state = await self.load_state(task_id)
        if state:
            state.current_step = step
            await self.save_state(task_id, state)

    async def set_final_output(self, task_id: str, output: str) -> None:
        """Set the final output for a completed task.

        Args:
            task_id: The task ID
            output: The final output
        """
        state = await self.load_state(task_id)
        if state:
            state.final_output = output
            await self.save_state(task_id, state)

    async def set_error(self, task_id: str, error: str) -> None:
        """Set an error for a failed task.

        Args:
            task_id: The task ID
            error: The error message
        """
        state = await self.load_state(task_id)
        if state:
            state.error = error
            await self.save_state(task_id, state)

    async def get_task_ids(self) -> List[str]:
        """Get all task IDs.

        Returns:
            List of task IDs
        """
        return list(self._states.keys())

    async def delete_state(self, task_id: str) -> None:
        """Delete a task state.

        Args:
            task_id: The task ID to delete
        """
        if task_id in self._states:
            del self._states[task_id]
        if task_id in self._contexts:
            del self._contexts[task_id]

    async def clear_all_states(self) -> None:
        """Clear all states (use with caution)."""
        self._states.clear()
        self._contexts.clear()

    async def get_context(self, task_id: str) -> Optional[TaskContext]:
        """Get task context.

        Args:
            task_id: The task ID

        Returns:
            TaskContext if found, None otherwise
        """
        return self._contexts.get(task_id)


class InMemoryStateManager(StateManager):
    """Simple in-memory state manager (alias for backward compatibility)."""

    pass
