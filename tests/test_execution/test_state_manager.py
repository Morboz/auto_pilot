"""Tests for state manager."""

import pytest

from auto_pilot.execution.state_manager import StateManager
from auto_pilot.execution.types import (
    ExecutionStatus,
    ExecutionStep,
    TaskContext,
    ToolCallRecord,
)


@pytest.mark.asyncio
class TestStateManager:
    """Test StateManager."""

    async def test_create_state(self):
        """Test creating a new state."""
        state_manager = StateManager()

        context = TaskContext(
            task_id="task-1",
            user_input="Do something",
        )

        state = await state_manager.create_state(context)

        assert state.task_id == "task-1"
        assert state.status == ExecutionStatus.PENDING
        assert state.user_input == "Do something"
        assert state.current_step == 0

    async def test_load_state(self):
        """Test loading existing state."""
        state_manager = StateManager()

        context = TaskContext(task_id="task-2", user_input="Test")
        await state_manager.create_state(context)

        loaded = await state_manager.load_state("task-2")

        assert loaded is not None
        assert loaded.task_id == "task-2"

    async def test_load_nonexistent_state(self):
        """Test loading non-existent state returns None."""
        state_manager = StateManager()

        loaded = await state_manager.load_state("nonexistent")

        assert loaded is None

    async def test_update_status(self):
        """Test updating execution status."""
        state_manager = StateManager()

        context = TaskContext(task_id="task-3", user_input="Test")
        await state_manager.create_state(context)

        await state_manager.update_execution_status("task-3", ExecutionStatus.RUNNING)

        state = await state_manager.load_state("task-3")
        assert state.status == ExecutionStatus.RUNNING

    async def test_append_step(self):
        """Test appending a step."""
        state_manager = StateManager()

        context = TaskContext(task_id="task-4", user_input="Test")
        await state_manager.create_state(context)

        step = ExecutionStep(
            step_number=1,
            llm_response="My plan",
        )

        await state_manager.append_step("task-4", step)

        state = await state_manager.load_state("task-4")
        assert len(state.steps) == 1
        assert state.steps[0].llm_response == "My plan"

    async def test_record_tool_call(self):
        """Test recording a tool call."""
        state_manager = StateManager()

        context = TaskContext(task_id="task-5", user_input="Test")
        await state_manager.create_state(context)

        record = ToolCallRecord(
            tool_name="test_tool",
            arguments={"arg": "value"},
            result="success",
        )

        await state_manager.record_tool_call("task-5", record)

        state = await state_manager.load_state("task-5")
        assert len(state.tool_calls) == 1
        assert state.tool_calls[0].tool_name == "test_tool"

    async def test_update_current_step(self):
        """Test updating current step."""
        state_manager = StateManager()

        context = TaskContext(task_id="task-6", user_input="Test")
        await state_manager.create_state(context)

        await state_manager.update_current_step("task-6", 5)

        state = await state_manager.load_state("task-6")
        assert state.current_step == 5

    async def test_set_final_output(self):
        """Test setting final output."""
        state_manager = StateManager()

        context = TaskContext(task_id="task-7", user_input="Test")
        await state_manager.create_state(context)

        await state_manager.set_final_output("task-7", "Task completed")

        state = await state_manager.load_state("task-7")
        assert state.final_output == "Task completed"

    async def test_set_error(self):
        """Test setting error."""
        state_manager = StateManager()

        context = TaskContext(task_id="task-8", user_input="Test")
        await state_manager.create_state(context)

        await state_manager.set_error("task-8", "Something went wrong")

        state = await state_manager.load_state("task-8")
        assert state.error == "Something went wrong"

    async def test_get_task_ids(self):
        """Test getting all task IDs."""
        state_manager = StateManager()

        await state_manager.create_state(
            TaskContext(task_id="task-9", user_input="Test1")
        )
        await state_manager.create_state(
            TaskContext(task_id="task-10", user_input="Test2")
        )

        ids = await state_manager.get_task_ids()
        assert "task-9" in ids
        assert "task-10" in ids

    async def test_delete_state(self):
        """Test deleting a state."""
        state_manager = StateManager()

        context = TaskContext(task_id="task-11", user_input="Test")
        await state_manager.create_state(context)

        assert await state_manager.load_state("task-11") is not None

        await state_manager.delete_state("task-11")

        assert await state_manager.load_state("task-11") is None
