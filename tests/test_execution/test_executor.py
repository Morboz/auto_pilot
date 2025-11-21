"""Tests for agent executor."""

import asyncio
from unittest.mock import AsyncMock, patch

import pytest

from auto_pilot.execution.callbacks import BaseExecutionCallback
from auto_pilot.execution.executor import AgentExecutor
from auto_pilot.execution.tool_executor import ToolExecutor
from auto_pilot.execution.types import (
    ExecutionConfig,
    TaskContext,
    TaskInput,
    ToolCallRecord,
)
from auto_pilot.llm import (
    GenerationResponse,
    ModelCapabilities,
    TokenUsage,
    ToolDefinition,
)
from auto_pilot.llm.errors import (
    AuthenticationError,
    ConfigurationError,
    RateLimitError,
)


class MockLLMAdapter:
    """Mock LLM adapter for testing."""

    def __init__(self):
        self.call_count = 0

    async def get_capabilities(self, model: str) -> ModelCapabilities:
        return ModelCapabilities(
            supports_tools=True,
            supports_streaming=True,
        )

    def get_capabilities_sync(self, model: str) -> ModelCapabilities:
        """Synchronous version for testing."""
        return ModelCapabilities(
            supports_tools=True,
            supports_streaming=True,
        )

    async def generate(self, model: str, messages, params=None):
        self.call_count += 1
        return GenerationResponse(
            content="I'll help you with this task.",
            usage=TokenUsage(),
            messages=[],
            model="test-model",
        )

    async def run_with_tools(self, model: str, messages, tools, params=None):
        self.call_count += 1
        return GenerationResponse(
            content="I'll use the available tools to complete this task.",
            usage=TokenUsage(),
            messages=[],
            model="test-model",
            tool_calls=[],
        )


class TestAgentExecutor:
    """Test AgentExecutor."""

    @pytest.mark.asyncio
    async def test_basic_execution(self):
        """Test basic task execution."""
        llm = MockLLMAdapter()
        executor = AgentExecutor(llm_adapter=llm)

        task_input = TaskInput(
            task_id="test-task-1",
            user_input="Complete a simple task",
        )

        output = await executor.run(task_input)

        assert output.task_id == "test-task-1"
        assert output.error is None
        assert llm.call_count > 0

    @pytest.mark.asyncio
    async def test_execution_with_tools(self):
        """Test execution with available tools."""
        llm = MockLLMAdapter()
        # Patch get_capabilities to return sync version
        llm.get_capabilities = llm.get_capabilities_sync

        executor = AgentExecutor(llm_adapter=llm)

        tools = [
            ToolDefinition(
                name="test_tool",
                description="A test tool",
                parameters={"type": "object"},
            )
        ]

        task_input = TaskInput(
            task_id="test-task-2",
            user_input="Use test_tool to complete this",
        )

        output = await executor.run(task_input, tools=tools)

        assert output.task_id == "test-task-2"
        assert output.error is None
        assert llm.call_count > 0

    @pytest.mark.asyncio
    async def test_stop_task(self):
        """Test stopping a running task."""
        llm = MockLLMAdapter()
        llm.get_capabilities = llm.get_capabilities_sync
        executor = AgentExecutor(llm_adapter=llm)

        task_input = TaskInput(
            task_id="test-task-3",
            user_input="Long running task",
        )

        # Start task in background
        task = asyncio.create_task(executor.run(task_input))

        # Give it a moment to start
        await asyncio.sleep(0.01)

        # Stop it
        await executor.stop("test-task-3")

        assert not executor._running_tasks.get("test-task-3", False)

        # Cancel the task
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass

    @pytest.mark.asyncio
    async def test_pause_and_resume(self):
        """Test pausing and resuming a task."""
        llm = MockLLMAdapter()
        llm.get_capabilities = llm.get_capabilities_sync
        executor = AgentExecutor(llm_adapter=llm)

        task_input = TaskInput(
            task_id="test-task-4",
            user_input="Paused task",
        )

        # Start task in background
        task = asyncio.create_task(executor.run(task_input))

        # Give it a moment to start
        await asyncio.sleep(0.01)

        # Pause
        await executor.pause("test-task-4")

        # Resume
        await executor.resume("test-task-4")

        # Should be running again
        assert executor._running_tasks.get("test-task-4", False)

        # Cancel the task
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass

    @pytest.mark.asyncio
    async def test_custom_config(self):
        """Test execution with custom config."""
        llm = MockLLMAdapter()
        executor = AgentExecutor(llm_adapter=llm)

        config = ExecutionConfig(
            max_steps=10,
            max_retries=2,
            auto_retry_errors=True,
        )

        task_input = TaskInput(
            task_id="test-task-5",
            user_input="Custom config task",
        )

        output = await executor.run(task_input, config=config)

        assert output.task_id == "test-task-5"
        assert output.error is None

    @pytest.mark.asyncio
    async def test_callback_system(self):
        """Test event callback system."""
        llm = MockLLMAdapter()
        llm.get_capabilities = llm.get_capabilities_sync
        executor = AgentExecutor(llm_adapter=llm)

        events = []

        class TestCallback(BaseExecutionCallback):
            async def on_event(self, event):
                events.append(("event", event.type))

            async def on_step_started(self, task_id: str, step: int):
                events.append(("step_started", step))

            async def on_finished(self, task_id: str, output: str):
                events.append(("finished", output))

            async def on_status_changed(self, task_id: str, status: str):
                events.append(("status_changed", status))

        callback = TestCallback()
        executor.add_callback(callback)

        task_input = TaskInput(
            task_id="test-task-6",
            user_input="Callback test",
        )

        output = await executor.run(task_input)

        assert len(events) > 0
        assert ("finished", output.final_output) in events


class TestToolIntegration:
    """Test tool execution integration with executor."""

    @pytest.mark.asyncio
    async def test_invoke_tool_with_tool_executor(self):
        """Test _invoke_tool uses ToolExecutor correctly."""
        llm = MockLLMAdapter()
        tool_executor = ToolExecutor()

        # Register a test tool
        async def test_tool_impl(param1: str):
            return {"result": f"processed_{param1}"}

        tool_executor.register_tool("test_tool", test_tool_impl)

        executor = AgentExecutor(
            llm_adapter=llm,
            tool_executor=tool_executor,
        )

        tool = ToolDefinition(
            name="test_tool",
            description="A test tool",
            parameters={
                "type": "object",
                "properties": {"param1": {"type": "string"}},
                "required": ["param1"],
            },
        )

        result = await executor._invoke_tool(tool, {"param1": "test"})

        assert result == {"result": "processed_test"}

    @pytest.mark.asyncio
    async def test_invoke_tool_raises_on_error(self):
        """Test _invoke_tool raises exception on tool failure."""
        llm = MockLLMAdapter()
        tool_executor = ToolExecutor()

        # Register a failing tool
        async def failing_tool(**kwargs):
            raise ValueError("Tool failed")

        tool_executor.register_tool("failing_tool", failing_tool)

        executor = AgentExecutor(
            llm_adapter=llm,
            tool_executor=tool_executor,
        )

        tool = ToolDefinition(
            name="failing_tool",
            description="A failing tool",
            parameters={"type": "object"},
        )

        with pytest.raises(Exception) as exc_info:
            await executor._invoke_tool(tool, {})

        assert "Tool failed" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_add_tool_results_to_messages(self):
        """Test tool results are added to state messages."""
        llm = MockLLMAdapter()
        executor = AgentExecutor(llm_adapter=llm)

        # Create a task and state
        from auto_pilot.execution.types import TaskContext

        task_id = "test-tool-results"

        context = TaskContext(
            task_id=task_id,
            user_input="Test tool results",
        )

        # Initialize state
        state = await executor.state_manager.create_state(context=context)

        # Add some tool calls to state
        tool_record = ToolCallRecord(
            tool_name="test_tool",
            arguments={"param": "value"},
            result={"status": "success"},
            success=True,
        )

        await executor.state_manager.record_tool_call(task_id, tool_record)

        # Add tool results to messages
        await executor._add_tool_results_to_messages(task_id)

        # Verify messages were added
        updated_state = await executor.state_manager.load_state(task_id)

        # Should have at least one message with tool result
        tool_result_messages = [
            msg for msg in updated_state.messages if msg.get("type") == "tool_result"
        ]

        assert len(tool_result_messages) > 0
        assert "test_tool" in tool_result_messages[0]["content"]


class TestRetryLogic:
    """Test retry logic with exponential backoff."""

    @pytest.mark.asyncio
    async def test_retry_on_rate_limit_error(self):
        """Test retry logic for rate limit errors."""
        llm = MockLLMAdapter()
        executor = AgentExecutor(llm_adapter=llm)

        task_id = "test-retry"
        error = RateLimitError("Rate limit exceeded", retry_after=1)

        config = ExecutionConfig(max_retries=2, auto_retry_errors=True)

        # Create state
        context = TaskContext(task_id=task_id, user_input="Test retry")
        state = await executor.state_manager.create_state(context=context)
        state = await executor.state_manager.load_state(task_id)

        # Mock asyncio.sleep to avoid actual waiting
        with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
            # Should not raise, will sleep and update retry count
            await executor._handle_error_with_retry(task_id, error, state, config)

            # Verify sleep was called with exponential backoff
            assert mock_sleep.called
            call_args = mock_sleep.call_args[0][0]
            assert call_args >= 1.0  # Base delay

    @pytest.mark.asyncio
    async def test_no_retry_on_auth_error(self):
        """Test no retry for authentication errors."""
        llm = MockLLMAdapter()
        executor = AgentExecutor(llm_adapter=llm)

        task_id = "test-no-retry"
        error = AuthenticationError("Invalid API key")

        config = ExecutionConfig(max_retries=3, auto_retry_errors=True)

        context = TaskContext(task_id=task_id, user_input="Test")
        state = await executor.state_manager.create_state(context=context)
        state = await executor.state_manager.load_state(task_id)

        # Should raise immediately without retry
        with pytest.raises(AuthenticationError):
            await executor._handle_error_with_retry(task_id, error, state, config)

    @pytest.mark.asyncio
    async def test_no_retry_on_config_error(self):
        """Test no retry for configuration errors."""
        llm = MockLLMAdapter()
        executor = AgentExecutor(llm_adapter=llm)

        task_id = "test-config-error"
        error = ConfigurationError("Missing configuration")

        config = ExecutionConfig(max_retries=3, auto_retry_errors=True)

        context = TaskContext(task_id=task_id, user_input="Test")
        state = await executor.state_manager.create_state(context=context)
        state = await executor.state_manager.load_state(task_id)

        with pytest.raises(ConfigurationError):
            await executor._handle_error_with_retry(task_id, error, state, config)

    @pytest.mark.asyncio
    async def test_retry_exhausted(self):
        """Test retry limit is respected."""
        llm = MockLLMAdapter()
        executor = AgentExecutor(llm_adapter=llm)

        task_id = "test-retry-exhausted"
        error = RateLimitError("Rate limit exceeded")

        config = ExecutionConfig(max_retries=2, auto_retry_errors=True)

        context = TaskContext(task_id=task_id, user_input="Test")
        state = await executor.state_manager.create_state(context=context)
        state = await executor.state_manager.load_state(task_id)

        # Set retry count to max
        state.retry_count = 2

        # Should raise because retries exhausted
        with pytest.raises(RateLimitError):
            await executor._handle_error_with_retry(task_id, error, state, config)

    @pytest.mark.asyncio
    async def test_exponential_backoff_calculation(self):
        """Test exponential backoff delay calculation."""
        llm = MockLLMAdapter()
        executor = AgentExecutor(llm_adapter=llm)

        task_id = "test-backoff"
        error = RateLimitError("Rate limit")
        config = ExecutionConfig(max_retries=5)

        context = TaskContext(task_id=task_id, user_input="Test")
        state = await executor.state_manager.create_state(context=context)

        delays = []

        with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
            # Test retry count 0, 1, 2
            for retry_count in range(3):
                state = await executor.state_manager.load_state(task_id)
                state.retry_count = retry_count
                await executor.state_manager.save_state(task_id, state)

                await executor._handle_error_with_retry(task_id, error, state, config)

                if mock_sleep.called:
                    delays.append(mock_sleep.call_args[0][0])
                    mock_sleep.reset_mock()

        # Verify delays increase exponentially
        # Base formula: min(1.0 * (2^retry_count), 60.0) + jitter
        for i, delay in enumerate(delays[:-1]):
            # Each delay should be roughly double the previous (accounting for jitter)
            # We just check it's increasing
            assert delays[i + 1] > delays[i] * 0.9  # Allow some variance for jitter

    @pytest.mark.asyncio
    async def test_retry_on_timeout_error(self):
        """Test retry logic for timeout errors."""
        llm = MockLLMAdapter()
        executor = AgentExecutor(llm_adapter=llm)

        task_id = "test-timeout-retry"
        error = asyncio.TimeoutError("Request timed out")

        config = ExecutionConfig(max_retries=2)

        context = TaskContext(task_id=task_id, user_input="Test")
        state = await executor.state_manager.create_state(context=context)
        state = await executor.state_manager.load_state(task_id)

        with patch("asyncio.sleep", new_callable=AsyncMock):
            # Should not raise on first retry
            await executor._handle_error_with_retry(task_id, error, state, config)

            # Verify retry count was incremented
            updated_state = await executor.state_manager.load_state(task_id)
            assert hasattr(updated_state, "retry_count")
            assert updated_state.retry_count == 1
