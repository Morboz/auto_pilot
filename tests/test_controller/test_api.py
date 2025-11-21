"""Tests for TaskController API."""

import asyncio
from unittest.mock import MagicMock

import pytest

from auto_pilot.controller.api import TaskController
from auto_pilot.controller.models import TaskStartRequest


class MockLLMAdapter:
    """Mock LLM adapter for testing."""

    def __init__(self):
        self.call_count = 0

    async def get_capabilities(self, model: str):
        return MagicMock(supports_tools=True)

    async def generate(self, model: str, messages, params=None):
        self.call_count += 1
        return MagicMock(
            content="Test response",
            usage=MagicMock(),
            messages=[],
            model="test-model",
        )

    async def run_with_tools(self, model: str, messages, tools, params=None):
        self.call_count += 1
        return MagicMock(
            content="Task completed successfully",
            usage=MagicMock(),
            messages=[],
            model="test-model",
            tool_calls=[],
        )


@pytest.mark.asyncio
class TestTaskController:
    """Test TaskController."""

    async def test_start_task(self):
        """Test starting a new task."""
        llm = MockLLMAdapter()
        controller = TaskController(llm_adapter=llm)

        request = TaskStartRequest(
            input="Analyze data",
            agent_id="agent-1",
            config={"max_steps": 10},
        )

        response = await controller.start_task("agent-1", request)

        assert response.task_id is not None
        assert response.status == "started"
        assert "started" in response.message

    async def test_pause_task(self):
        """Test pausing a task."""
        llm = MockLLMAdapter()
        controller = TaskController(llm_adapter=llm)

        # Start a task first
        request = TaskStartRequest(input="Test task")
        response = await controller.start_task("agent-1", request)
        task_id = response.task_id

        # Pause it
        result = await controller.pause_task(task_id)

        assert result.success
        assert "paused" in result.message

    async def test_resume_task(self):
        """Test resuming a task."""
        llm = MockLLMAdapter()
        controller = TaskController(llm_adapter=llm)

        # Start a task
        request = TaskStartRequest(input="Test task")
        response = await controller.start_task("agent-1", request)
        task_id = response.task_id

        # Pause and resume
        await controller.pause_task(task_id)
        result = await controller.resume_task(task_id)

        assert result.success
        assert "resumed" in result.message

    async def test_stop_task(self):
        """Test stopping a task."""
        llm = MockLLMAdapter()
        controller = TaskController(llm_adapter=llm)

        # Start a task
        request = TaskStartRequest(input="Test task")
        response = await controller.start_task("agent-1", request)
        task_id = response.task_id

        # Stop it
        result = await controller.stop_task(task_id)

        assert result.success
        assert "stopped" in result.message

    async def test_get_task_status(self):
        """Test getting task status."""

        llm = MockLLMAdapter()
        controller = TaskController(llm_adapter=llm)

        # Create a task and wait for it to initialize
        request = TaskStartRequest(input="Test task")
        response = await controller.start_task("agent-1", request)
        task_id = response.task_id

        # Wait a bit for task to initialize
        await asyncio.sleep(0.1)

        # Get status
        status = await controller.get_task_status(task_id)

        assert status.task_id == task_id
        assert status.user_input == "Test task"
        # Task may have finished by the time we check
        assert status.status in ["pending", "running", "finished"]

    async def test_get_nonexistent_task_status(self):
        """Test getting status of non-existent task."""
        from fastapi import HTTPException

        llm = MockLLMAdapter()
        controller = TaskController(llm_adapter=llm)

        with pytest.raises(HTTPException) as exc_info:
            await controller.get_task_status("nonexistent")

        assert exc_info.value.status_code == 404
        assert "not found" in str(exc_info.value.detail)
