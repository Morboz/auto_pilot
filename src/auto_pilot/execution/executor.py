"""Agent Executor - Core execution loop implementation.

This module implements the core Plan → Act → Observe → Re-plan cycle
that drives autonomous agent behavior, similar to Claude Code.
"""

import asyncio
import json
import random
from typing import Any, Dict, List, Optional

from auto_pilot.llm import BaseLLMAdapter, Message, ToolDefinition
from auto_pilot.llm.errors import (
    AuthenticationError,
    ConfigurationError,
    RateLimitError,
)
from auto_pilot.models import ToolExecutionLog

from ..logger import get_logger
from .callbacks import BaseExecutionCallback, CallbackManager
from .state_manager import StateManager
from .tool_executor import ToolExecutor
from .types import (
    AgentState,
    ExecutionConfig,
    ExecutionStatus,
    ExecutionStep,
    TaskContext,
    TaskInput,
    TaskOutput,
    ToolCallRecord,
)

logger = get_logger(__name__)


class AgentExecutor:
    """Main executor for agent task execution.

    Implements the core ReAct loop:
    1. Generate Plan (LLM)
    2. Execute Tool (if needed)
    3. Observe Result
    4. Re-plan (if needed)
    """

    def __init__(
        self,
        llm_adapter: BaseLLMAdapter,
        state_manager: Optional[StateManager] = None,
        callback_manager: Optional[CallbackManager] = None,
        tool_executor: Optional[ToolExecutor] = None,
    ):
        """Initialize Agent Executor.

        Args:
            llm_adapter: LLM adapter for generating responses
            state_manager: State manager for persistence
            callback_manager: Callback manager for events
            tool_executor: Tool executor for executing tools
        """
        self.llm_adapter = llm_adapter
        self.state_manager = state_manager or StateManager()
        self.callback_manager = callback_manager or CallbackManager()
        self.tool_executor = tool_executor or ToolExecutor()
        self._running_tasks: dict[str, bool] = {}

    def add_callback(self, callback: BaseExecutionCallback) -> None:
        """Add an event callback.

        Args:
            callback: The callback to add
        """
        self.callback_manager.add_callback(callback)

    def remove_callback(self, callback: BaseExecutionCallback) -> None:
        """Remove an event callback.

        Args:
            callback: The callback to remove
        """
        self.callback_manager.remove_callback(callback)

    async def run(
        self,
        task_input: TaskInput,
        tools: Optional[List[ToolDefinition]] = None,
        config: Optional[ExecutionConfig] = None,
        session: Optional[Any] = None,
    ) -> TaskOutput:
        """Execute a task from start to finish.

        Args:
            task_input: Input for the task
            tools: Available tools for the task
            config: Execution configuration
            session: Optional database session for saving execution logs

        Returns:
            TaskOutput with results
        """
        config = config or ExecutionConfig()

        # Initialize context
        context = TaskContext(
            task_id=task_input.task_id,
            agent_id=task_input.agent_id,
            user_input=task_input.user_input,
            max_steps=config.max_steps,
            max_retries=config.max_retries,
        )

        # Create state
        await self.state_manager.create_state(context)
        await self.state_manager.update_execution_status(
            task_input.task_id, ExecutionStatus.RUNNING
        )
        await self.callback_manager.emit_status_changed(
            task_input.task_id, ExecutionStatus.RUNNING
        )

        self._running_tasks[task_input.task_id] = True

        try:
            # Execute the main loop
            await self._execute_loop(task_input.task_id, tools or [], config, session)

            # Task completed successfully
            await self.state_manager.update_execution_status(
                task_input.task_id, ExecutionStatus.FINISHED
            )
            await self.callback_manager.emit_status_changed(
                task_input.task_id, ExecutionStatus.FINISHED
            )

            # Get final state
            final_state = await self.state_manager.load_state(task_input.task_id)
            final_output = final_state.final_output if final_state else None

            await self.callback_manager.emit_finished(task_input.task_id, final_output)

            return TaskOutput(
                task_id=task_input.task_id,
                final_output=final_output,
                steps=final_state.steps if final_state else [],
                tool_calls=final_state.tool_calls if final_state else [],
                total_steps=final_state.current_step if final_state else 0,
                total_tool_calls=len(final_state.tool_calls) if final_state else 0,
            )

        except asyncio.CancelledError:
            # Task was cancelled
            await self.state_manager.update_execution_status(
                task_input.task_id, ExecutionStatus.STOPPED
            )
            await self.callback_manager.emit_status_changed(
                task_input.task_id, ExecutionStatus.STOPPED
            )
            raise

        except Exception as e:
            # Task failed with error
            await self.state_manager.update_execution_status(
                task_input.task_id, ExecutionStatus.FAILED
            )
            await self.state_manager.set_error(task_input.task_id, str(e))
            await self.callback_manager.emit_error(
                task_input.task_id, e, context.current_step
            )
            await self.callback_manager.emit_status_changed(
                task_input.task_id, ExecutionStatus.FAILED
            )

            return TaskOutput(
                task_id=task_input.task_id,
                error=str(e),
                steps=context.steps if hasattr(context, "steps") else [],
            )

        finally:
            if task_input.task_id in self._running_tasks:
                del self._running_tasks[task_input.task_id]

    async def _execute_loop(
        self,
        task_id: str,
        tools: List[ToolDefinition],
        config: ExecutionConfig,
        session: Optional[Any] = None,
    ) -> None:
        """Execute the main Plan → Act → Observe → Re-plan loop.

        Args:
            task_id: The task ID
            tools: Available tools
            config: Execution configuration
            session: Optional database session for saving execution logs
        """
        state = await self.state_manager.load_state(task_id)
        if not state:
            raise ValueError(f"State not found for task {task_id}")

        # Main execution loop
        while self._is_running(task_id):
            # Check if we've exceeded max steps
            if state.current_step >= config.max_steps:
                await self._handle_max_steps_exceeded(task_id, state)
                break

            # Generate plan using LLM
            try:
                step, is_final = await self._generate_plan(
                    task_id,
                    tools,
                    config,
                )

                await self.state_manager.append_step(task_id, step)
                await self.state_manager.update_current_step(
                    task_id, state.current_step + 1
                )

                await self.callback_manager.emit_step_started(
                    task_id, state.current_step + 1
                )

                # Check if this is the final step
                if is_final:
                    await self._handle_final_step(task_id, step)
                    break

                # Execute any tool calls and add results to messages
                if step.tool_calls:
                    await self._execute_tool_calls(
                        task_id,
                        step.tool_calls,
                        tools,
                        config,
                        session,
                    )

                    # Add tool results to state messages for next LLM call
                    await self._add_tool_results_to_messages(task_id)

                await self.callback_manager.emit_step_completed(
                    task_id, state.current_step + 1
                )

                # Delay between steps if configured
                if config.step_delay > 0:
                    await asyncio.sleep(config.step_delay)

                # Reload state for next iteration
                state = await self.state_manager.load_state(task_id)

            except Exception as e:
                await self.callback_manager.emit_error(task_id, e, state.current_step)
                if config.auto_retry_errors:
                    await self._handle_error_with_retry(task_id, e, state, config)
                else:
                    raise

    async def _generate_plan(
        self,
        task_id: str,
        tools: List[ToolDefinition],
        config: ExecutionConfig,
    ) -> tuple[ExecutionStep, bool]:
        """Generate a plan using the LLM.

        Args:
            task_id: The task ID
            tools: Available tools
            config: Execution configuration

        Returns:
            Tuple of (ExecutionStep, is_final)
        """
        state = await self.state_manager.load_state(task_id)
        if not state:
            raise ValueError(f"State not found for task {task_id}")

        # Build messages for LLM
        messages = self._build_messages(state)

        # Try tool calling first
        if tools:
            # Use tool calling
            response = await self.llm_adapter.run_with_tools(
                model="",  # Use default model
                messages=messages,
                tools=tools,
                params=None,
            )

            await self.callback_manager.emit_llm_response(task_id, response.content)

            # Check if LLM indicates task is done
            is_final = self._check_if_final(response.content)

            # Extract tool calls
            tool_calls = []
            if response.tool_calls:
                for tool_call in response.tool_calls:
                    tool_calls.append(
                        {
                            "name": tool_call.name,
                            "arguments": tool_call.arguments,
                            "id": tool_call.id,
                        }
                    )

            step = ExecutionStep(
                step_number=state.current_step + 1,
                llm_response=response.content,
                tool_calls=tool_calls,
                is_final=is_final,
            )

            # Update state with new messages
            state.messages.append(
                {
                    "role": "assistant",
                    "content": response.content,
                    "tool_calls": tool_calls if tool_calls else None,
                }
            )

            await self.state_manager.save_state(task_id, state)

            return step, is_final

        else:
            # Simple text generation without tools
            response = await self.llm_adapter.generate(
                model="",
                messages=messages,
                params=None,
            )

            await self.callback_manager.emit_llm_response(task_id, response.content)

            is_final = self._check_if_final(response.content)

            step = ExecutionStep(
                step_number=state.current_step + 1,
                llm_response=response.content,
                tool_calls=[],
                is_final=is_final,
            )

            # Update state
            state.messages.append(
                {
                    "role": "assistant",
                    "content": response.content,
                }
            )

            await self.state_manager.save_state(task_id, state)

            return step, is_final

    def _build_messages(self, state: AgentState) -> List[Message]:
        """Build message list from state for LLM.

        Args:
            state: The current agent state

        Returns:
            List of messages
        """
        messages = []

        # Add system message if not already present
        if not state.messages or state.messages[0].get("role") != "system":
            messages.append(
                Message(
                    role="system",
                    content=f"""You are an autonomous agent that can execute tasks.

Task: {state.user_input}

You can:
- Call tools to perform actions
- Provide direct answers
- Indicate when you're done with the task

To indicate completion, simply state that the task is complete in your response.
""",
                )
            )

        # Add conversation history
        for msg in state.messages:
            messages.append(
                Message(
                    role=msg["role"],
                    content=msg.get("content"),
                    tool_use_id=msg.get("tool_use_id"),
                    name=msg.get("name"),
                )
            )

        # Add recent tool results
        for tool_call in state.tool_calls[-5:]:  # Last 5 tool calls
            messages.append(
                Message(
                    role="tool",
                    name=tool_call.tool_name,
                    content=str(tool_call.result),
                )
            )

        return messages

    async def _execute_tool_calls(
        self,
        task_id: str,
        tool_calls: List[Dict[str, Any]],
        tools: List[ToolDefinition],
        config: ExecutionConfig,
        session: Optional[Any] = None,
    ) -> None:
        """Execute tool calls and record results.

        Args:
            task_id: The task ID
            tool_calls: List of tool calls to execute
            tools: Available tools
            config: Execution configuration
            session: Optional database session for saving execution logs
        """
        for tool_call_data in tool_calls:
            if not self._is_running(task_id):
                break

            tool_name = tool_call_data["name"]
            arguments = tool_call_data["arguments"]

            await self.callback_manager.emit_tool_call_started(
                task_id,
                tool_name,
                arguments,
            )

            try:
                # Find tool definition
                tool_def = next((t for t in tools if t.name == tool_name), None)

                if not tool_def:
                    raise ValueError(f"Tool {tool_name} not found")

                # Execute tool
                result = await self._invoke_tool(tool_def, arguments)
                duration = result.duration_ms if result.duration_ms else 0

                await self.callback_manager.emit_tool_result(
                    task_id,
                    tool_name,
                    result.result if result.success else None,
                )

                # Record tool call
                record = ToolCallRecord(
                    tool_name=tool_name,
                    arguments=arguments,
                    result=result.result if result.success else None,
                    success=result.success,
                    duration_ms=duration,
                    error=result.error if not result.success else None,
                )

                await self.state_manager.record_tool_call(task_id, record)
                await self.callback_manager.emit_tool_call_completed(
                    task_id,
                    record,
                )

                # Save to database if session is provided
                if session:
                    await self._save_tool_execution_to_db(
                        session, task_id, tool_def, result
                    )

            except Exception as e:
                await self.callback_manager.emit_error(task_id, e)

                # Record failed tool call
                record = ToolCallRecord(
                    tool_name=tool_name,
                    arguments=arguments,
                    success=False,
                    error=str(e),
                )

                await self.state_manager.record_tool_call(task_id, record)
                await self.callback_manager.emit_tool_call_completed(
                    task_id,
                    record,
                )

                # Re-raise if not auto-retry
                if not config.auto_retry_errors:
                    raise

    async def _invoke_tool(
        self,
        tool: ToolDefinition,
        arguments: Dict[str, Any],
    ) -> Any:
        """Invoke a tool using the tool executor.

        Args:
            tool: The tool definition
            arguments: Tool arguments

        Returns:
            Tool execution result
        """
        # Use tool executor to run the tool with validation and sandboxing
        record = await self.tool_executor.execute(
            tool=tool,
            arguments=arguments,
        )

        if not record.success:
            raise Exception(record.error)

        return record.result

    def _check_if_final(self, content: str) -> bool:
        """Check if LLM response indicates task completion.

        Args:
            content: LLM response content

        Returns:
            True if task appears complete
        """
        final_indicators = [
            "task is complete",
            "task completed",
            "finished",
            "done",
            "complete",
        ]

        content_lower = content.lower()
        return any(indicator in content_lower for indicator in final_indicators)

    async def _handle_final_step(
        self,
        task_id: str,
        step: ExecutionStep,
    ) -> None:
        """Handle final step of execution.

        Args:
            task_id: The task ID
            step: The final step
        """
        # Extract final answer from LLM response
        final_answer = step.llm_response or ""

        await self.state_manager.set_final_output(task_id, final_answer)

    async def _handle_max_steps_exceeded(
        self,
        task_id: str,
        state: AgentState,
    ) -> None:
        """Handle case where max steps is exceeded.

        Args:
            task_id: The task ID
            state: Current state
        """
        await self.state_manager.set_error(
            task_id, f"Maximum steps ({state.max_steps}) exceeded"
        )

    async def _handle_error_with_retry(
        self,
        task_id: str,
        error: Exception,
        state: AgentState,
        config: ExecutionConfig,
    ) -> None:
        """Handle error with exponential backoff retry logic.

        Args:
            task_id: The task ID
            error: The error that occurred
            state: Current state
            config: Execution configuration
        """
        # Check if error is retryable
        is_retryable = isinstance(
            error,
            (
                RateLimitError,
                asyncio.TimeoutError,
                ConnectionError,
            ),
        )

        # Don't retry authentication or configuration errors
        if isinstance(error, (AuthenticationError, ConfigurationError)):
            raise error

        # Check retry count
        retry_count = getattr(state, "retry_count", 0)

        if not is_retryable or retry_count >= config.max_retries:
            raise error

        # Calculate exponential backoff delay
        base_delay = 1.0  # 1 second
        max_delay = 60.0  # 60 seconds
        delay = min(base_delay * (2**retry_count), max_delay)

        # Add jitter to avoid thundering herd
        jitter = random.uniform(0, delay * 0.1)
        delay = delay + jitter

        # Log retry attempt
        retry_msg = (
            f"Retrying after {delay:.2f}s "
            f"(attempt {retry_count + 1}/{config.max_retries}): {error}"
        )
        await self.callback_manager.emit_error(
            task_id,
            Exception(retry_msg),
            state.current_step,
        )

        # Wait before retry
        await asyncio.sleep(delay)

        # Increment retry count
        state.retry_count = retry_count + 1  # type: ignore
        await self.state_manager.save_state(task_id, state)

    async def _add_tool_results_to_messages(
        self,
        task_id: str,
    ) -> None:
        """Add recent tool results to state messages for LLM context.

        Args:
            task_id: The task ID
        """
        state = await self.state_manager.load_state(task_id)
        if not state:
            return

        # Get recent tool calls that haven't been added to messages yet
        # We'll add the last few tool results
        recent_tool_calls = state.tool_calls[-3:]  # Last 3 tool calls

        for tool_call in recent_tool_calls:
            # Format tool result for LLM
            result_text = self.tool_executor.format_result_for_llm(tool_call)

            # Add as tool result message
            state.messages.append(
                {
                    "role": "user",
                    "content": result_text,
                    "type": "tool_result",
                }
            )

        await self.state_manager.save_state(task_id, state)

    def _is_running(self, task_id: str) -> bool:
        """Check if a task is still running.

        Args:
            task_id: The task ID

        Returns:
            True if task is running
        """
        return self._running_tasks.get(task_id, False)

    async def _save_tool_execution_to_db(
        self,
        session: Any,
        task_id: str,
        tool: ToolDefinition,
        execution_result: ToolCallRecord,
    ) -> None:
        """Save tool execution result to database.

        Args:
            session: Database session
            task_id: The task ID
            tool: Tool definition
            execution_result: Tool execution result
        """
        from uuid import UUID

        try:
            # Convert task_id to UUID if it's a string
            task_uuid = UUID(task_id) if isinstance(task_id, str) else task_id

            # Create tool execution log
            log = ToolExecutionLog(
                task_id=task_uuid,
                tool_name=tool.name,
                input_params=json.dumps(execution_result.arguments),
                output=json.dumps(execution_result.result)
                if execution_result.success and execution_result.result
                else None,
                error_message=execution_result.error
                if not execution_result.success
                else None,
                duration_ms=execution_result.duration_ms,
                sandbox_enabled=True,  # TODO: Make this configurable
                resource_usage=None,  # TODO: Capture resource usage from sandbox
            )

            session.add(log)
            await session.commit()

        except Exception as e:
            # Log error but don't fail the task
            logger.error("Failed to save tool execution log: %s", e)

    async def stop(self, task_id: str) -> None:
        """Stop a running task.

        Args:
            task_id: The task ID to stop
        """
        if task_id in self._running_tasks:
            self._running_tasks[task_id] = False

        await self.state_manager.update_execution_status(
            task_id, ExecutionStatus.STOPPED
        )
        await self.callback_manager.emit_status_changed(
            task_id, ExecutionStatus.STOPPED
        )

    async def pause(self, task_id: str) -> None:
        """Pause a running task.

        Args:
            task_id: The task ID to pause
        """
        if task_id in self._running_tasks:
            self._running_tasks[task_id] = False

        await self.state_manager.update_execution_status(
            task_id, ExecutionStatus.PAUSED
        )
        await self.callback_manager.emit_status_changed(task_id, ExecutionStatus.PAUSED)

    async def resume(self, task_id: str) -> None:
        """Resume a paused task.

        Args:
            task_id: The task ID to resume
        """
        self._running_tasks[task_id] = True

        await self.state_manager.update_execution_status(
            task_id, ExecutionStatus.RUNNING
        )
        await self.callback_manager.emit_status_changed(
            task_id, ExecutionStatus.RUNNING
        )
