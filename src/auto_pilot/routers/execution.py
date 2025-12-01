"""Execution router - Task execution and monitoring endpoints."""

import json
import uuid
from typing import List, Optional
from uuid import UUID

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Request,
    WebSocket,
    WebSocketDisconnect,
    status,
)
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from auto_pilot.database import get_session
from auto_pilot.execution import (
    AgentExecutor,
    BaseExecutionCallback,
    ExecutionConfig,
    ExecutionEvent,
    StateManager,
    TaskInput,
)
from auto_pilot.llm import BaseLLMAdapter, ToolDefinition
from auto_pilot.models import Agent as AgentModel
from auto_pilot.models import Task

router = APIRouter(prefix="/execution", tags=["execution"])


def get_llm_adapter(request: Request) -> BaseLLMAdapter:
    """Get LLM adapter instance from app state."""
    if (
        not hasattr(request.app.state, "llm_adapter")
        or request.app.state.llm_adapter is None
    ):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="LLM adapter not initialized",
        )
    return request.app.state.llm_adapter


def get_state_manager(request: Request) -> StateManager:
    """Get state manager instance from app state."""
    if not hasattr(request.app.state, "state_manager"):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="State manager not initialized",
        )
    return request.app.state.state_manager


def get_executor(
    llm_adapter: BaseLLMAdapter = Depends(get_llm_adapter),
    state_manager: StateManager = Depends(get_state_manager),
) -> AgentExecutor:
    """Create executor instance with dependencies."""
    return AgentExecutor(
        llm_adapter=llm_adapter,
        state_manager=state_manager,
    )


class WebSocketStreamCallback(BaseExecutionCallback):
    """Callback for streaming execution events via WebSocket."""

    def __init__(self, task_id: str, websocket: WebSocket):
        self.task_id = task_id
        self.websocket = websocket

    async def on_event(self, event: ExecutionEvent) -> None:
        """Send event to WebSocket."""
        message = {
            "event": event.type,
            "task_id": self.task_id,
            "data": event.data,
            "timestamp": event.timestamp.isoformat(),
        }
        try:
            await self.websocket.send_json(message)
        except Exception:
            # WebSocket disconnected
            pass


@router.post("/agents/{agent_id}/tasks", status_code=status.HTTP_201_CREATED)
async def start_execution(
    agent_id: str,
    request: dict,
    executor: AgentExecutor = Depends(get_executor),
    session: AsyncSession = Depends(get_session),
):
    """Start a new task execution.

    Args:
        agent_id: Agent ID (UUID)
        request: Task request containing:
            - input: User input/task description
            - config: Optional execution configuration
            - tools: Optional list of tools available to the agent
    """
    try:
        # Validate agent_id format
        try:
            agent_uuid = UUID(agent_id)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid agent_id format. Must be a valid UUID.",
            )

        # Generate task_id
        task_uuid = uuid.uuid4()
        task_id = str(task_uuid)

        # Create task input
        task_input = TaskInput(
            task_id=task_id,
            user_input=request.get("input", ""),
            agent_id=agent_id,
            config=request.get("config"),
        )

        # Create execution config
        config = ExecutionConfig()
        if request.get("config"):
            for key, value in request["config"].items():
                if hasattr(config, key):
                    setattr(config, key, value)

        # Convert tools if provided
        tools = None
        if request.get("tools"):
            tools = [ToolDefinition(**tool_data) for tool_data in request["tools"]]

        # Check if agent exists, if not create a default one
        result = await session.execute(select(Task).where(Task.agent_id == agent_uuid))
        agent_exists = await session.execute(
            select(AgentModel).where(AgentModel.id == agent_uuid)
        )
        agent_record = agent_exists.scalar_one_or_none()

        if not agent_record:
            # Create a default agent for this execution
            agent_record = AgentModel(
                id=agent_uuid,
                name=f"Agent {agent_id[:8]}",
                model="execution-agent",
                system_prompt="You are an autonomous execution agent.",
            )
            session.add(agent_record)
            await session.commit()

        # Create database task record
        db_task = Task(
            id=task_uuid,
            agent_id=agent_uuid,
            input_text=request.get("input", ""),
            status="running",
        )
        session.add(db_task)
        await session.commit()
        await session.refresh(db_task)

        # Start execution in background
        import asyncio

        asyncio.create_task(
            _execute_task_wrapper(executor, task_input, tools, config, session, task_id)
        )

        return {
            "task_id": task_id,
            "status": "started",
            "message": "Task execution started successfully",
        }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to start task: {str(e)}",
        )


@router.post("/tasks/{task_id}/pause")
async def pause_execution(
    task_id: str,
    executor: AgentExecutor = Depends(get_executor),
    session: AsyncSession = Depends(get_session),
):
    """Pause a running task execution.

    Args:
        task_id: Task ID to pause
    """
    try:
        await executor.pause(task_id)

        # Update database record
        from sqlalchemy import text

        await session.execute(
            text("UPDATE task SET status = 'paused' WHERE id = :task_id"),
            {"task_id": task_id},
        )
        await session.commit()

        return {
            "success": True,
            "message": f"Task {task_id} paused",
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to pause task: {str(e)}",
        )


@router.post("/tasks/{task_id}/resume")
async def resume_execution(
    task_id: str,
    executor: AgentExecutor = Depends(get_executor),
    session: AsyncSession = Depends(get_session),
):
    """Resume a paused task execution.

    Args:
        task_id: Task ID to resume
    """
    try:
        await executor.resume(task_id)

        # Update database record
        from sqlalchemy import text

        await session.execute(
            text("UPDATE task SET status = 'running' WHERE id = :task_id"),
            {"task_id": task_id},
        )
        await session.commit()

        return {
            "success": True,
            "message": f"Task {task_id} resumed",
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to resume task: {str(e)}",
        )


@router.post("/tasks/{task_id}/stop")
async def stop_execution(
    task_id: str,
    executor: AgentExecutor = Depends(get_executor),
    session: AsyncSession = Depends(get_session),
):
    """Stop a running task execution.

    Args:
        task_id: Task ID to stop
    """
    try:
        await executor.stop(task_id)

        # Update database record
        from sqlalchemy import text

        await session.execute(
            text("UPDATE task SET status = 'stopped' WHERE id = :task_id"),
            {"task_id": task_id},
        )
        await session.commit()

        return {
            "success": True,
            "message": f"Task {task_id} stopped",
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to stop task: {str(e)}",
        )


@router.get("/tasks/{task_id}")
async def get_execution_status(
    task_id: str,
    session: AsyncSession = Depends(get_session),
    state_manager: StateManager = Depends(get_state_manager),
):
    """Get task execution status and details.

    Args:
        task_id: Task ID

    Returns:
        Detailed task status including execution state, steps, and tool calls
    """
    try:
        # Get execution state
        state = await state_manager.load_state(task_id)

        # Get database record
        from sqlalchemy import text

        result = await session.execute(
            text("SELECT * FROM task WHERE id = :task_id"), {"task_id": task_id}
        )
        db_task = result.fetchone()

        if not state and not db_task:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Task {task_id} not found",
            )

        # Combine database and execution state
        response = {
            "task_id": task_id,
            "db_status": db_task.status if db_task else "unknown",
        }

        if state:
            response.update(
                {
                    "execution_status": state.status,
                    "user_input": state.user_input,
                    "current_step": state.current_step,
                    "max_steps": state.max_steps,
                    "final_output": state.final_output,
                    "error": state.error,
                    "created_at": state.created_at.isoformat()
                    if state.created_at
                    else None,
                    "updated_at": state.updated_at.isoformat()
                    if state.updated_at
                    else None,
                    "steps": [step.model_dump() for step in state.steps],
                    "tool_calls": [call.model_dump() for call in state.tool_calls],
                }
            )

        return response

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get task status: {str(e)}",
        )


@router.websocket("/tasks/{task_id}/stream")
async def websocket_execution_stream(
    websocket: WebSocket,
    task_id: str,
    executor: AgentExecutor = Depends(get_executor),
):
    """WebSocket endpoint for real-time execution streaming.

    Args:
        websocket: WebSocket connection
        task_id: Task ID to stream
        executor: Executor instance
    """
    await websocket.accept()

    # Create callback for this connection
    callback = WebSocketStreamCallback(task_id, websocket)
    executor.add_callback(callback)

    try:
        # Keep connection alive
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        # Remove callback on disconnect
        executor.remove_callback(callback)
    except Exception as e:
        await websocket.close(code=1011, reason=str(e))
        executor.remove_callback(callback)


async def _execute_task_wrapper(
    executor: AgentExecutor,
    task_input: TaskInput,
    tools: Optional[List[ToolDefinition]],
    config: ExecutionConfig,
    session: AsyncSession,
    task_id: str,
):
    """Wrapper for executing task with proper cleanup."""
    try:
        output = await executor.run(
            task_input, tools=tools, config=config, session=session
        )

        # Update database record with final result
        from sqlalchemy import text

        await session.execute(
            text(
                "UPDATE task SET status = 'completed', "
                "result_text = :result WHERE id = :task_id"
            ),
            {
                "task_id": task_id,
                "result": json.dumps(
                    {
                        "final_output": output.final_output,
                        "total_steps": output.total_steps,
                        "total_tool_calls": output.total_tool_calls,
                    }
                ),
            },
        )
        await session.commit()

    except Exception as e:
        # Update database record with error
        from sqlalchemy import text

        await session.execute(
            text("UPDATE task SET status = 'failed', meta = :meta WHERE id = :task_id"),
            {
                "task_id": task_id,
                "meta": json.dumps({"error": str(e)}),
            },
        )
        await session.commit()
