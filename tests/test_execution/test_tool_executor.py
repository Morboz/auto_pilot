"""Tests for ToolExecutor."""

import asyncio

import pytest

from auto_pilot.execution.tool_executor import ToolExecutor
from auto_pilot.execution.types import ToolCallRecord
from auto_pilot.llm import ToolDefinition


class TestToolExecutor:
    """Test ToolExecutor functionality."""

    def test_initialization(self):
        """Test ToolExecutor initialization."""
        executor = ToolExecutor(default_timeout=30.0)
        assert executor.default_timeout == 30.0
        assert len(executor._tool_implementations) == 0

    def test_register_tool(self):
        """Test tool registration."""
        executor = ToolExecutor()

        async def test_tool_impl(**kwargs):
            return {"result": "success"}

        executor.register_tool("test_tool", test_tool_impl)
        assert "test_tool" in executor._tool_implementations

    @pytest.mark.asyncio
    async def test_execute_placeholder_tool(self):
        """Test executing a tool without registered implementation."""
        executor = ToolExecutor()

        tool = ToolDefinition(
            name="unregistered_tool",
            description="A tool without implementation",
            parameters={
                "type": "object",
                "properties": {"param1": {"type": "string"}},
            },
        )

        record = await executor.execute(
            tool=tool,
            arguments={"param1": "value1"},
        )

        assert record.tool_name == "unregistered_tool"
        assert record.success is True
        assert "placeholder" in str(record.result).lower()

    @pytest.mark.asyncio
    async def test_execute_registered_tool(self):
        """Test executing a registered tool."""
        executor = ToolExecutor()

        async def calculator(**kwargs):
            x = kwargs.get("x", 0)
            y = kwargs.get("y", 0)
            return {"result": x + y}

        executor.register_tool("calculator", calculator)

        tool = ToolDefinition(
            name="calculator",
            description="Simple calculator",
            parameters={
                "type": "object",
                "properties": {
                    "x": {"type": "number"},
                    "y": {"type": "number"},
                },
                "required": ["x", "y"],
            },
        )

        record = await executor.execute(
            tool=tool,
            arguments={"x": 5, "y": 3},
        )

        assert record.tool_name == "calculator"
        assert record.success is True
        assert record.result == {"result": 8}
        assert record.error is None

    @pytest.mark.asyncio
    async def test_execute_with_timeout(self):
        """Test tool execution timeout."""
        executor = ToolExecutor(default_timeout=0.1)

        async def slow_tool(**kwargs):
            await asyncio.sleep(1.0)  # Longer than timeout
            return {"result": "done"}

        executor.register_tool("slow_tool", slow_tool)

        tool = ToolDefinition(
            name="slow_tool",
            description="A slow tool",
            parameters={"type": "object"},
        )

        record = await executor.execute(tool=tool, arguments={})

        assert record.tool_name == "slow_tool"
        assert record.success is False
        assert "timed out" in record.error.lower()

    @pytest.mark.asyncio
    async def test_execute_with_error(self):
        """Test tool execution with error."""
        executor = ToolExecutor()

        async def error_tool(**kwargs):
            raise ValueError("Something went wrong")

        executor.register_tool("error_tool", error_tool)

        tool = ToolDefinition(
            name="error_tool",
            description="A tool that raises error",
            parameters={"type": "object"},
        )

        record = await executor.execute(tool=tool, arguments={})

        assert record.tool_name == "error_tool"
        assert record.success is False
        assert "Something went wrong" in record.error

    @pytest.mark.asyncio
    async def test_validate_arguments_missing_required(self):
        """Test argument validation with missing required field."""
        executor = ToolExecutor()

        tool = ToolDefinition(
            name="test_tool",
            description="Test tool",
            parameters={
                "type": "object",
                "properties": {"required_param": {"type": "string"}},
                "required": ["required_param"],
            },
        )

        record = await executor.execute(
            tool=tool,
            arguments={},  # Missing required_param
        )

        assert record.success is False
        assert "Missing required argument" in record.error

    @pytest.mark.asyncio
    async def test_validate_arguments_unknown_field(self):
        """Test argument validation with unknown field."""
        executor = ToolExecutor()

        tool = ToolDefinition(
            name="test_tool",
            description="Test tool",
            parameters={
                "type": "object",
                "properties": {"known_param": {"type": "string"}},
            },
        )

        record = await executor.execute(
            tool=tool,
            arguments={"unknown_param": "value"},  # Unknown field
        )

        assert record.success is False
        assert "Unknown argument" in record.error

    def test_format_result_for_llm_success(self):
        """Test formatting successful result for LLM."""
        executor = ToolExecutor()

        record = ToolCallRecord(
            tool_name="test_tool",
            arguments={"param": "value"},
            result={"status": "success", "data": [1, 2, 3]},
            success=True,
        )

        formatted = executor.format_result_for_llm(record)

        assert "test_tool" in formatted
        assert "Success" in formatted
        assert "status" in formatted
        assert "data" in formatted

    def test_format_result_for_llm_failure(self):
        """Test formatting failed result for LLM."""
        executor = ToolExecutor()

        record = ToolCallRecord(
            tool_name="test_tool",
            arguments={"param": "value"},
            success=False,
            error="Connection timeout",
        )

        formatted = executor.format_result_for_llm(record)

        assert "test_tool" in formatted
        assert "Failed" in formatted
        assert "Connection timeout" in formatted

    def test_format_result_with_string(self):
        """Test formatting string result."""
        executor = ToolExecutor()

        record = ToolCallRecord(
            tool_name="test_tool",
            arguments={},
            result="Simple string result",
            success=True,
        )

        formatted = executor.format_result_for_llm(record)

        assert "Simple string result" in formatted

    def test_format_result_with_list(self):
        """Test formatting list result."""
        executor = ToolExecutor()

        record = ToolCallRecord(
            tool_name="test_tool",
            arguments={},
            result=[1, 2, 3, 4, 5],
            success=True,
        )

        formatted = executor.format_result_for_llm(record)

        assert "[1, 2, 3, 4, 5]" in formatted

    def test_is_retryable_error_timeout(self):
        """Test retryable error detection for timeout."""
        executor = ToolExecutor()

        assert executor.is_retryable_error("Connection timeout")
        assert executor.is_retryable_error("Request timed out")

    def test_is_retryable_error_network(self):
        """Test retryable error detection for network errors."""
        executor = ToolExecutor()

        assert executor.is_retryable_error("Network connection failed")
        assert executor.is_retryable_error("Connection reset by peer")

    def test_is_retryable_error_rate_limit(self):
        """Test retryable error detection for rate limits."""
        executor = ToolExecutor()

        assert executor.is_retryable_error("Rate limit exceeded")
        assert executor.is_retryable_error("HTTP 429 Too Many Requests")
        assert executor.is_retryable_error("503 Service Unavailable")

    def test_is_retryable_error_non_retryable(self):
        """Test non-retryable errors."""
        executor = ToolExecutor()

        assert not executor.is_retryable_error("Invalid authentication")
        assert not executor.is_retryable_error("Permission denied")
        assert not executor.is_retryable_error("Resource not found")

    @pytest.mark.asyncio
    async def test_execute_with_custom_timeout(self):
        """Test tool execution with custom timeout."""
        executor = ToolExecutor(default_timeout=10.0)

        async def medium_slow_tool(**kwargs):
            await asyncio.sleep(0.2)
            return {"result": "done"}

        executor.register_tool("medium_slow_tool", medium_slow_tool)

        tool = ToolDefinition(
            name="medium_slow_tool",
            description="A medium slow tool",
            parameters={"type": "object"},
        )

        # Should succeed with custom timeout
        record = await executor.execute(
            tool=tool,
            arguments={},
            timeout=1.0,  # Custom timeout
        )

        assert record.success is True

    @pytest.mark.asyncio
    async def test_execute_multiple_tools_sequentially(self):
        """Test executing multiple tools sequentially."""
        executor = ToolExecutor()

        results = []

        async def tool1(**kwargs):
            results.append("tool1")
            return {"result": 1}

        async def tool2(**kwargs):
            results.append("tool2")
            return {"result": 2}

        executor.register_tool("tool1", tool1)
        executor.register_tool("tool2", tool2)

        tool_def_1 = ToolDefinition(
            name="tool1", description="Tool 1", parameters={"type": "object"}
        )

        tool_def_2 = ToolDefinition(
            name="tool2", description="Tool 2", parameters={"type": "object"}
        )

        record1 = await executor.execute(tool_def_1, {})
        record2 = await executor.execute(tool_def_2, {})

        assert record1.success is True
        assert record2.success is True
        assert results == ["tool1", "tool2"]
