"""Tests for execution types."""

from datetime import datetime

from auto_pilot.execution.types import (
    AgentState,
    EventType,
    ExecutionStatus,
    ExecutionStep,
    TaskInput,
    TaskOutput,
    ToolCallRecord,
)


class TestExecutionStatus:
    """Test ExecutionStatus enum."""

    def test_status_values(self):
        """Test all status values are correct."""
        assert ExecutionStatus.PENDING == "pending"
        assert ExecutionStatus.RUNNING == "running"
        assert ExecutionStatus.PAUSED == "paused"
        assert ExecutionStatus.WAITING == "waiting"
        assert ExecutionStatus.FINISHED == "finished"
        assert ExecutionStatus.FAILED == "failed"
        assert ExecutionStatus.STOPPED == "stopped"


class TestEventType:
    """Test EventType enum."""

    def test_event_types(self):
        """Test all event types exist."""
        assert EventType.STEP_STARTED == "step_started"
        assert EventType.STEP_COMPLETED == "step_completed"
        assert EventType.LLM_RESPONSE == "llm_response"
        assert EventType.TOOL_CALL_STARTED == "tool_call_started"
        assert EventType.TOOL_CALL_COMPLETED == "tool_call_completed"
        assert EventType.TOOL_RESULT == "tool_result"
        assert EventType.ERROR == "error"
        assert EventType.FINISHED == "finished"
        assert EventType.STATUS_CHANGED == "status_changed"


class TestExecutionStep:
    """Test ExecutionStep model."""

    def test_step_creation(self):
        """Test creating an execution step."""
        step = ExecutionStep(
            step_number=1,
            llm_response="This is my plan",
            tool_calls=[],
            is_final=False,
        )

        assert step.step_number == 1
        assert step.llm_response == "This is my plan"
        assert not step.is_final
        assert isinstance(step.timestamp, datetime)

    def test_step_with_tool_calls(self):
        """Test step with tool calls."""
        tool_calls = [{"name": "tool1", "arguments": {"arg1": "value1"}}]

        step = ExecutionStep(
            step_number=2,
            tool_calls=tool_calls,
        )

        assert len(step.tool_calls) == 1
        assert step.tool_calls[0]["name"] == "tool1"


class TestToolCallRecord:
    """Test ToolCallRecord model."""

    def test_record_creation(self):
        """Test creating a tool call record."""
        record = ToolCallRecord(
            tool_name="test_tool",
            arguments={"arg": "value"},
            result="success",
            success=True,
        )

        assert record.tool_name == "test_tool"
        assert record.arguments["arg"] == "value"
        assert record.result == "success"
        assert record.success
        assert isinstance(record.timestamp, datetime)


class TestTaskInput:
    """Test TaskInput model."""

    def test_input_creation(self):
        """Test creating a task input."""
        task_input = TaskInput(
            task_id="task-123",
            user_input="Do something",
            agent_id="agent-1",
        )

        assert task_input.task_id == "task-123"
        assert task_input.user_input == "Do something"
        assert task_input.agent_id == "agent-1"


class TestTaskOutput:
    """Test TaskOutput model."""

    def test_output_creation(self):
        """Test creating a task output."""
        output = TaskOutput(
            task_id="task-123",
            final_output="Task completed",
        )

        assert output.task_id == "task-123"
        assert output.final_output == "Task completed"
        assert output.total_steps == 0
        assert output.total_tool_calls == 0
        assert output.error is None


class TestAgentState:
    """Test AgentState model."""

    def test_state_creation(self):
        """Test creating an agent state."""
        state = AgentState(
            task_id="task-123",
            user_input="Do something",
        )

        assert state.task_id == "task-123"
        assert state.status == ExecutionStatus.PENDING
        assert state.current_step == 0
        assert state.max_steps == 50
        assert state.max_retries == 3
        assert state.messages == []
        assert state.tool_calls == []
        assert state.steps == []

    def test_state_with_steps(self):
        """Test state with execution history."""
        step = ExecutionStep(step_number=1)
        state = AgentState(
            task_id="task-123",
            user_input="Do something",
            steps=[step],
        )

        assert len(state.steps) == 1
        assert state.steps[0].step_number == 1
