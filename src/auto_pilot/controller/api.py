"""API endpoints for task management."""

import asyncio
import uuid
from typing import Any, List, Optional

from fastapi import HTTPException, WebSocket, status

from auto_pilot.execution import (
    AgentExecutor,
    BaseExecutionCallback,
    ExecutionConfig,
    ExecutionEvent,
    StateManager,
    TaskInput,
)

from .models import (
    ApiResponse,
    TaskStartRequest,
    TaskStartResponse,
    TaskStatusResponse,
)


class TaskController:
    """Controller for managing agent task execution."""

    def __init__(
        self,
        llm_adapter: Any,
        state_manager: Optional[StateManager] = None,
    ):
        """Initialize Task Controller.

        Args:
            llm_adapter: LLM adapter for agents
            state_manager: Optional state manager (will create if not provided)
        """
        self.llm_adapter = llm_adapter
        self.state_manager = state_manager or StateManager()
        self.executor = AgentExecutor(
            llm_adapter=llm_adapter,
            state_manager=self.state_manager,
        )
        self._running_tasks: dict[str, bool] = {}
        self._websocket_connections: dict[str, List[WebSocket]] = {}

    async def start_task(
        self,
        agent_id: Optional[str],
        request: TaskStartRequest,
    ) -> TaskStartResponse:
        """Start a new task.

        Args:
            agent_id: Optional agent ID
            request: Task start request

        Returns:
            TaskStartResponse with task ID

        Raises:
            HTTPException: If task creation fails
        """
        task_id = str(uuid.uuid4())

        try:
            # Create task input
            task_input = TaskInput(
                task_id=task_id,
                user_input=request.input,
                agent_id=agent_id,
                config=request.config,
            )

            # Create execution config
            config = ExecutionConfig()
            if request.config:
                # Override defaults with provided config
                for key, value in request.config.items():
                    if hasattr(config, key):
                        setattr(config, key, value)

            # Start task in background
            self._running_tasks[task_id] = True

            # Add default WebSocket callback if connections exist
            if task_id in self._websocket_connections:
                self.executor.add_callback(
                    WebSocketStreamCallback(
                        task_id, self._websocket_connections[task_id]
                    )
                )

            # Run task
            asyncio.create_task(self._run_task(task_input, config))

            return TaskStartResponse(
                task_id=task_id,
                status="started",
                message="Task started successfully",
            )

        except Exception as e:
            self._running_tasks.pop(task_id, None)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to start task: {str(e)}",
            )

    async def pause_task(self, task_id: str) -> ApiResponse:
        """Pause a running task.

        Args:
            task_id: Task ID to pause

        Returns:
            ApiResponse

        Raises:
            HTTPException: If task not found or cannot pause
        """
        try:
            await self.executor.pause(task_id)
            return ApiResponse(
                success=True,
                message=f"Task {task_id} paused",
            )
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Failed to pause task: {str(e)}",
            )

    async def resume_task(self, task_id: str) -> ApiResponse:
        """Resume a paused task.

        Args:
            task_id: Task ID to resume

        Returns:
            ApiResponse

        Raises:
            HTTPException: If task not found or cannot resume
        """
        try:
            await self.executor.resume(task_id)
            return ApiResponse(
                success=True,
                message=f"Task {task_id} resumed",
            )
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Failed to resume task: {str(e)}",
            )

    async def stop_task(self, task_id: str) -> ApiResponse:
        """Stop a running task.

        Args:
            task_id: Task ID to stop

        Returns:
            ApiResponse

        Raises:
            HTTPException: If task not found or cannot stop
        """
        try:
            await self.executor.stop(task_id)
            return ApiResponse(
                success=True,
                message=f"Task {task_id} stopped",
            )
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Failed to stop task: {str(e)}",
            )

    async def get_task_status(self, task_id: str) -> TaskStatusResponse:
        """Get task status and details.

        Args:
            task_id: Task ID

        Returns:
            TaskStatusResponse

        Raises:
            HTTPException: If task not found
        """
        try:
            state = await self.state_manager.load_state(task_id)

            if not state:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Task {task_id} not found",
                )

            return TaskStatusResponse(
                task_id=state.task_id,
                status=state.status,
                user_input=state.user_input,
                current_step=state.current_step,
                max_steps=state.max_steps,
                final_output=state.final_output,
                error=state.error,
                created_at=state.created_at.isoformat(),
                updated_at=state.updated_at.isoformat(),
                steps=[step.dict() for step in state.steps],
                tool_calls=[call.dict() for call in state.tool_calls],
            )

        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to get task status: {str(e)}",
            )

    async def _run_task(self, task_input: TaskInput, config: ExecutionConfig) -> None:
        """Run a task in the background.

        Args:
            task_input: Task input
            config: Execution configuration
        """
        try:
            await self.executor.run(task_input, config=config)
        finally:
            self._running_tasks.pop(task_input.task_id, None)

    def add_websocket_connection(self, task_id: str, websocket: WebSocket) -> None:
        """Add a WebSocket connection for task streaming.

        Args:
            task_id: Task ID
            websocket: WebSocket connection
        """
        if task_id not in self._websocket_connections:
            self._websocket_connections[task_id] = []
        self._websocket_connections[task_id].append(websocket)

    def remove_websocket_connection(self, task_id: str, websocket: WebSocket) -> None:
        """Remove a WebSocket connection.

        Args:
            task_id: Task ID
            websocket: WebSocket connection
        """
        if task_id in self._websocket_connections:
            if websocket in self._websocket_connections[task_id]:
                self._websocket_connections[task_id].remove(websocket)

            # Clean up empty lists
            if not self._websocket_connections[task_id]:
                del self._websocket_connections[task_id]


class WebSocketStreamCallback(BaseExecutionCallback):
    """Callback for streaming task events via WebSocket."""

    def __init__(self, task_id: str, connections: List[WebSocket]):
        """Initialize callback.

        Args:
            task_id: Task ID
            connections: List of WebSocket connections
        """
        self.task_id = task_id
        self.connections = connections

    async def on_event(self, event: ExecutionEvent) -> None:
        """Send event to all WebSocket connections.

        Args:
            event: Execution event
        """
        message = {
            "event": event.type,
            "task_id": self.task_id,
            "data": event.data,
            "timestamp": event.timestamp.isoformat(),
        }

        # Send to all connected WebSockets
        disconnected = []
        for websocket in self.connections:
            try:
                await websocket.send_json(message)
            except Exception:
                disconnected.append(websocket)

        # Remove disconnected WebSockets
        for ws in disconnected:
            if ws in self.connections:
                self.connections.remove(ws)
