"""Callback system for execution loop events.

This module provides a flexible callback system for receiving real-time
events from the execution loop, enabling features like WebSocket streaming.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

from auto_pilot.logger import get_logger

from .types import EventType, ExecutionEvent, ToolCallRecord

logger = get_logger(__name__)


class BaseExecutionCallback(ABC):
    """Base class for execution event callbacks."""

    @abstractmethod
    async def on_event(self, event: ExecutionEvent) -> None:
        """Called for each execution event.

        Args:
            event: The execution event
        """
        pass

    async def on_step_started(self, task_id: str, step: int) -> None:
        """Called when a step starts."""
        await self.on_event(
            ExecutionEvent(
                type=EventType.STEP_STARTED, task_id=task_id, data={"step": step}
            )
        )

    async def on_step_completed(self, task_id: str, step: int) -> None:
        """Called when a step completes."""
        await self.on_event(
            ExecutionEvent(
                type=EventType.STEP_COMPLETED, task_id=task_id, data={"step": step}
            )
        )

    async def on_llm_response(self, task_id: str, content: str) -> None:
        """Called when LLM responds."""
        await self.on_event(
            ExecutionEvent(
                type=EventType.LLM_RESPONSE, task_id=task_id, data={"content": content}
            )
        )

    async def on_tool_call_started(
        self, task_id: str, tool_name: str, arguments: Dict[str, Any]
    ) -> None:
        """Called when a tool call starts."""
        await self.on_event(
            ExecutionEvent(
                type=EventType.TOOL_CALL_STARTED,
                task_id=task_id,
                data={"tool_name": tool_name, "arguments": arguments},
            )
        )

    async def on_tool_call_completed(
        self, task_id: str, record: ToolCallRecord
    ) -> None:
        """Called when a tool call completes."""
        await self.on_event(
            ExecutionEvent(
                type=EventType.TOOL_CALL_COMPLETED,
                task_id=task_id,
                data={"record": record},
            )
        )

    async def on_tool_result(self, task_id: str, tool_name: str, result: Any) -> None:
        """Called with tool execution result."""
        await self.on_event(
            ExecutionEvent(
                type=EventType.TOOL_RESULT,
                task_id=task_id,
                data={"tool_name": tool_name, "result": result},
            )
        )

    async def on_error(
        self, task_id: str, error: Exception, step: Optional[int] = None
    ) -> None:
        """Called when an error occurs."""
        await self.on_event(
            ExecutionEvent(
                type=EventType.ERROR,
                task_id=task_id,
                data={
                    "error": str(error),
                    "error_type": type(error).__name__,
                    "step": step,
                },
            )
        )

    async def on_finished(
        self, task_id: str, final_output: Optional[str] = None
    ) -> None:
        """Called when task finishes."""
        await self.on_event(
            ExecutionEvent(
                type=EventType.FINISHED,
                task_id=task_id,
                data={"final_output": final_output},
            )
        )

    async def on_status_changed(self, task_id: str, status: str) -> None:
        """Called when execution status changes."""
        await self.on_event(
            ExecutionEvent(
                type=EventType.STATUS_CHANGED, task_id=task_id, data={"status": status}
            )
        )


class CallbackManager:
    """Manages multiple callbacks for execution events."""

    def __init__(self) -> None:
        self._callbacks: List[BaseExecutionCallback] = []

    def add_callback(self, callback: BaseExecutionCallback) -> None:
        """Add a callback to be notified of events.

        Args:
            callback: The callback to add
        """
        self._callbacks.append(callback)

    def remove_callback(self, callback: BaseExecutionCallback) -> None:
        """Remove a callback.

        Args:
            callback: The callback to remove
        """
        if callback in self._callbacks:
            self._callbacks.remove(callback)

    async def emit_event(self, event: ExecutionEvent) -> None:
        """Emit an event to all callbacks.

        Args:
            event: The event to emit
        """
        for callback in self._callbacks:
            try:
                await callback.on_event(event)
            except Exception as e:
                # Log error but don't let it crash the execution loop
                logger.error("Error in callback %s: %s", callback, e)

    async def emit_step_started(self, task_id: str, step: int) -> None:
        for callback in self._callbacks:
            await callback.on_step_started(task_id, step)

    async def emit_step_completed(self, task_id: str, step: int) -> None:
        for callback in self._callbacks:
            await callback.on_step_completed(task_id, step)

    async def emit_llm_response(self, task_id: str, content: str) -> None:
        for callback in self._callbacks:
            await callback.on_llm_response(task_id, content)

    async def emit_tool_call_started(
        self, task_id: str, tool_name: str, arguments: Dict[str, Any]
    ) -> None:
        for callback in self._callbacks:
            await callback.on_tool_call_started(task_id, tool_name, arguments)

    async def emit_tool_call_completed(
        self, task_id: str, record: ToolCallRecord
    ) -> None:
        for callback in self._callbacks:
            await callback.on_tool_call_completed(task_id, record)

    async def emit_tool_result(self, task_id: str, tool_name: str, result: Any) -> None:
        for callback in self._callbacks:
            await callback.on_tool_result(task_id, tool_name, result)

    async def emit_error(
        self, task_id: str, error: Exception, step: Optional[int] = None
    ) -> None:
        for callback in self._callbacks:
            await callback.on_error(task_id, error, step)

    async def emit_finished(
        self, task_id: str, final_output: Optional[str] = None
    ) -> None:
        for callback in self._callbacks:
            await callback.on_finished(task_id, final_output)

    async def emit_status_changed(self, task_id: str, status: str) -> None:
        for callback in self._callbacks:
            await callback.on_status_changed(task_id, status)


class WebSocketCallback(BaseExecutionCallback):
    """Example callback for WebSocket streaming.

    This is a placeholder implementation that could be extended to
    integrate with actual WebSocket connections.
    """

    def __init__(self, websocket=None):
        self.websocket = websocket

    async def on_event(self, event: ExecutionEvent) -> None:
        """Send event to WebSocket client."""
        if self.websocket:
            await self.websocket.send_json(event.dict())

    def set_websocket(self, websocket):
        """Update the WebSocket connection."""
        self.websocket = websocket
