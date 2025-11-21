# Execution Loop Module

This module implements the core autonomous execution engine for the auto_pilot agent system, based on the ReAct pattern (Reasoning + Acting).

## Overview

The Execution Loop module provides the infrastructure for agents to autonomously execute tasks through a Plan → Act → Observe → Re-plan cycle, similar to Claude Code.

## Key Components

### 1. AgentExecutor

The core class that orchestrates task execution:

```python
from auto_pilot.execution import AgentExecutor, TaskInput, ExecutionConfig
from auto_pilot.llm import create_adapter_for_model

# Create LLM adapter
llm = create_adapter_for_model(model="claude-3", api_key="...")

# Create executor
executor = AgentExecutor(llm_adapter=llm)

# Define tools
tools = [
    ToolDefinition(
        name="check_balance",
        description="Check wallet balance",
        parameters={...}
    )
]

# Start task
task_input = TaskInput(
    task_id="task-123",
    user_input="Check my wallet balance and rebalance if needed"
)

output = await executor.run(task_input, tools=tools)
print(output.final_output)
```

### 2. StateManager

Manages persistent state for tasks:

- Execution status (running, paused, stopped, etc.)
- Conversation history
- Tool call history
- Step-by-step execution trace

```python
from auto_pilot.execution import StateManager

state_manager = StateManager()

# Load state
state = await state_manager.load_state(task_id)

# Update status
await state_manager.update_execution_status(task_id, ExecutionStatus.RUNNING)
```

### 3. Callback System

Real-time event streaming for UI and monitoring:

```python
from auto_pilot.execution import BaseExecutionCallback, ExecutionEvent, EventType

class MyCallback(BaseExecutionCallback):
    async def on_event(self, event: ExecutionEvent) -> None:
        print(f"Event: {event.type} - {event.data}")

executor.add_callback(MyCallback())
```

## Execution Flow

```
1. Initialize Task
   ↓
2. Generate Plan (LLM)
   ↓
3. Execute Tool Calls (if any)
   ↓
4. Observe Results
   ↓
5. Re-plan (if not final)
   ↓
6. Repeat until completion
```

## Features

### ✅ Implemented

- **Plan → Act → Observe → Re-plan Loop**: Core execution cycle
- **Tool Calling**: Support for LLM tool invocation
- **State Persistence**: In-memory state management
- **Event Callbacks**: Real-time event streaming
- **Error Handling**: Basic error handling with retry support
- **Max Steps Protection**: Prevents infinite loops
- **Status Tracking**: Running, paused, stopped, finished, failed

### 🔄 Extensible

- **Tool Registry Integration**: Placeholder for actual tool execution
- **Database Persistence**: Currently in-memory, can be extended
- **Retry Logic**: Basic framework, needs customization
- **Advanced Error Recovery**: Can be enhanced

## Usage Examples

### Basic Task Execution

```python
from auto_pilot.execution import AgentExecutor, TaskInput, ExecutionConfig
from auto_pilot.llm import create_adapter_for_model

llm = create_adapter_for_model(model="claude-3", api_key="...")

executor = AgentExecutor(llm_adapter=llm)

task = TaskInput(
    task_id="analyze-123",
    user_input="Analyze the sales data in sales.csv and create a summary"
)

output = await executor.run(task)
print(f"Result: {output.final_output}")
```

### With Custom Config

```python
config = ExecutionConfig(
    max_steps=100,
    max_retries=3,
    auto_retry_errors=True,
    step_delay=0.5,
)

output = await executor.run(task, config=config)
```

### With Real-time Callbacks

```python
from auto_pilot.execution import BaseExecutionCallback, ExecutionEvent

class LoggingCallback(BaseExecutionCallback):
    async def on_step_started(self, task_id: str, step: int) -> None:
        print(f"Step {step} started")

    async def on_tool_call_started(self, task_id: str, tool_name: str, args: dict) -> None:
        print(f"Calling tool: {tool_name}")

    async def on_finished(self, task_id: str, output: str) -> None:
        print(f"Task completed: {output}")

executor.add_callback(LoggingCallback())
```

## Architecture

See `/docs/P3-2-execution-loop.md` for detailed design documentation.

## Testing

Run tests with:

```bash
uv run pytest tests/test_execution/ -v
```

## Future Enhancements

1. **Tool Registry Integration**: Connect to actual tool execution system
2. **Database Persistence**: Add PostgreSQL/Redis support
3. **Advanced Retry Strategies**: Exponential backoff, circuit breakers
4. **Checkpointing**: Save state periodically for recovery
5. **Resource Limits**: CPU/memory constraints for tools
6. **Streaming UI**: WebSocket integration for real-time updates
