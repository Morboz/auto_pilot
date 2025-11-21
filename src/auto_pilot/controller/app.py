"""FastAPI application for Controller module."""

from typing import Any, Optional

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, status
from fastapi.middleware.cors import CORSMiddleware

from ..execution import StateManager
from .api import TaskController
from .models import (
    ApiResponse,
    TaskStartRequest,
    TaskStartResponse,
    TaskStatusResponse,
)


def create_app(
    llm_adapter: Any,
    state_manager: Optional[StateManager] = None,
    cors_origins: Optional[list[str]] = None,
) -> FastAPI:
    """Create FastAPI application.

    Args:
        llm_adapter: LLM adapter for agents
        state_manager: Optional state manager
        cors_origins: Optional list of CORS origins

    Returns:
        FastAPI application
    """
    # Create FastAPI app
    app = FastAPI(
        title="auto_pilot Agent Runtime API",
        description="REST API and WebSocket interface for managing agent executions",
        version="1.0.0",
    )

    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins or ["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Create controller
    controller = TaskController(
        llm_adapter=llm_adapter,
        state_manager=state_manager,
    )

    # Store controller in app state
    app.state.controller = controller

    @app.get("/")
    async def root():
        """Root endpoint."""
        return {
            "name": "auto_pilot Agent Runtime API",
            "version": "1.0.0",
            "status": "running",
        }

    @app.get("/health")
    async def health_check():
        """Health check endpoint."""
        return {"status": "healthy"}

    @app.post(
        "/agents/{agent_id}/tasks",
        response_model=TaskStartResponse,
        status_code=status.HTTP_201_CREATED,
    )
    async def start_task(
        agent_id: str,
        request: TaskStartRequest,
    ):
        """Start a new task for an agent.

        Args:
            agent_id: Agent ID
            request: Task start request

        Returns:
            TaskStartResponse with task ID
        """
        return await controller.start_task(agent_id, request)

    @app.get("/tasks/{task_id}", response_model=TaskStatusResponse)
    async def get_task_status(task_id: str):
        """Get task status and details.

        Args:
            task_id: Task ID

        Returns:
            TaskStatusResponse
        """
        return await controller.get_task_status(task_id)

    @app.post(
        "/tasks/{task_id}/pause",
        response_model=ApiResponse,
        status_code=status.HTTP_200_OK,
    )
    async def pause_task(task_id: str):
        """Pause a running task.

        Args:
            task_id: Task ID

        Returns:
            ApiResponse
        """
        return await controller.pause_task(task_id)

    @app.post(
        "/tasks/{task_id}/resume",
        response_model=ApiResponse,
        status_code=status.HTTP_200_OK,
    )
    async def resume_task(task_id: str):
        """Resume a paused task.

        Args:
            task_id: Task ID

        Returns:
            ApiResponse
        """
        return await controller.resume_task(task_id)

    @app.post(
        "/tasks/{task_id}/stop",
        response_model=ApiResponse,
        status_code=status.HTTP_200_OK,
    )
    async def stop_task(task_id: str):
        """Stop a running task.

        Args:
            task_id: Task ID

        Returns:
            ApiResponse
        """
        return await controller.stop_task(task_id)

    @app.websocket("/tasks/{task_id}/stream")
    async def websocket_stream(websocket: WebSocket, task_id: str):
        """WebSocket endpoint for real-time task streaming.

        Args:
            websocket: WebSocket connection
            task_id: Task ID to stream
        """
        await websocket.accept()
        controller = websocket.app.state.controller

        # Add connection
        controller.add_websocket_connection(task_id, websocket)

        try:
            # Keep connection alive
            while True:
                await websocket.receive_text()
        except WebSocketDisconnect:
            # Remove connection on disconnect
            controller.remove_websocket_connection(task_id, websocket)
        except Exception as e:
            # Handle errors
            await websocket.close(code=1011, reason=str(e))
            controller.remove_websocket_connection(task_id, websocket)

    return app
