"""Tests for controller models."""

from auto_pilot.controller.models import (
    ApiResponse,
    TaskControlRequest,
    TaskStartRequest,
    TaskStartResponse,
    TaskStatusResponse,
)


class TestTaskStartRequest:
    """Test TaskStartRequest model."""

    def test_create_request(self):
        """Test creating a task start request."""
        request = TaskStartRequest(
            input="Analyze data",
            agent_id="agent-1",
            config={"max_steps": 10},
        )

        assert request.input == "Analyze data"
        assert request.agent_id == "agent-1"
        assert request.config == {"max_steps": 10}

    def test_request_with_minimal_data(self):
        """Test creating request with minimal data."""
        request = TaskStartRequest(input="Simple task")

        assert request.input == "Simple task"
        assert request.agent_id is None
        assert request.config == {}


class TestTaskStartResponse:
    """Test TaskStartResponse model."""

    def test_create_response(self):
        """Test creating a task start response."""
        response = TaskStartResponse(
            task_id="task-123",
            status="started",
            message="Task created",
        )

        assert response.task_id == "task-123"
        assert response.status == "started"
        assert response.message == "Task created"


class TestTaskStatusResponse:
    """Test TaskStatusResponse model."""

    def test_create_status_response(self):
        """Test creating a task status response."""
        response = TaskStatusResponse(
            task_id="task-123",
            status="running",
            user_input="Analyze data",
            current_step=5,
            max_steps=50,
            created_at="2024-01-01T12:00:00",
            updated_at="2024-01-01T12:05:00",
        )

        assert response.task_id == "task-123"
        assert response.status == "running"
        assert response.current_step == 5
        assert response.final_output is None
        assert response.error is None


class TestApiResponse:
    """Test ApiResponse model."""

    def test_create_success_response(self):
        """Test creating a success API response."""
        response = ApiResponse(
            success=True,
            message="Operation completed",
        )

        assert response.success
        assert response.message == "Operation completed"
        assert response.data is None

    def test_create_response_with_data(self):
        """Test creating response with data."""
        response = ApiResponse(
            success=True,
            message="Data retrieved",
            data={"key": "value"},
        )

        assert response.success
        assert response.data == {"key": "value"}


class TestTaskControlRequest:
    """Test TaskControlRequest model."""

    def test_create_control_request(self):
        """Test creating a task control request."""
        request = TaskControlRequest(task_id="task-123")

        assert request.task_id == "task-123"
