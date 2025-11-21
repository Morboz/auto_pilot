#!/usr/bin/env python3
"""Example demonstrating the execution loop module.

This example shows how to:
1. Create an agent executor
2. Define tools for the agent to use
3. Run a task with real-time event callbacks
4. Handle pause/resume/stop operations
"""

import asyncio

from auto_pilot.execution import (
    AgentExecutor,
    BaseExecutionCallback,
    ExecutionConfig,
    ExecutionEvent,
    TaskInput,
)


# Example callback for real-time event handling
class LoggingCallback(BaseExecutionCallback):
    """Logs all execution events for demonstration purposes."""

    def __init__(self):
        self.events = []

    async def on_event(self, event: ExecutionEvent) -> None:
        self.events.append(event)
        print(f"[EVENT] {event.type}: {event.data}")

    async def on_step_started(self, task_id: str, step: int) -> None:
        print(f"\n🔄 Step {step} started")

    async def on_llm_response(self, task_id: str, content: str) -> None:
        print(f"🧠 LLM: {content[:100]}...")

    async def on_tool_call_started(
        self, task_id: str, tool_name: str, arguments: dict
    ) -> None:
        print(f"🛠️  Calling tool: {tool_name} with args {arguments}")

    async def on_finished(self, task_id: str, final_output: str) -> None:
        print("\n✅ Task completed!")
        print(f"Final output: {final_output}")


async def main():
    """Main example function."""

    # Import a mock LLM adapter for demonstration
    # In production, you would use: from auto_pilot.llm import create_adapter_for_model
    from auto_pilot.llm import (
        GenerationResponse,
        ModelCapabilities,
        TokenUsage,
        ToolDefinition,
    )

    class ExampleLLMAdapter:
        """Example LLM adapter for demonstration."""

        def __init__(self):
            self.call_count = 0

        async def get_capabilities(self, model: str) -> ModelCapabilities:
            return ModelCapabilities(
                supports_tools=True,
                supports_streaming=True,
            )

        async def generate(self, model: str, messages, params=None):
            self.call_count += 1
            return GenerationResponse(
                content="I'll help you with this task. Let me think about it step by step.",
                usage=TokenUsage(input_tokens=100, output_tokens=50),
                messages=[],
                model="example-model",
            )

        async def run_with_tools(self, model: str, messages, tools, params=None):
            self.call_count += 1
            return GenerationResponse(
                content="I have completed the task successfully. The task is complete.",
                usage=TokenUsage(input_tokens=150, output_tokens=75),
                messages=[],
                model="example-model",
                tool_calls=[],
            )

    # Create LLM adapter
    llm = ExampleLLMAdapter()

    # Create executor with callbacks
    executor = AgentExecutor(llm_adapter=llm)
    callback = LoggingCallback()
    executor.add_callback(callback)

    # Define tools available to the agent
    tools = [
        ToolDefinition(
            name="search_file",
            description="Search for a file in the workspace",
            parameters={
                "type": "object",
                "properties": {
                    "filename": {
                        "type": "string",
                        "description": "The filename to search for",
                    }
                },
                "required": ["filename"],
            },
        ),
        ToolDefinition(
            name="read_file",
            description="Read the contents of a file",
            parameters={
                "type": "object",
                "properties": {
                    "filepath": {
                        "type": "string",
                        "description": "The path to the file",
                    }
                },
                "required": ["filepath"],
            },
        ),
    ]

    # Example 1: Run a simple task
    print("=" * 60)
    print("Example 1: Running a simple task")
    print("=" * 60)

    task_input = TaskInput(
        task_id="task-001",
        user_input="Analyze the codebase and provide a summary of its structure",
    )

    output = await executor.run(task_input, tools=tools)

    print("\n📊 Task Summary:")
    print(f"  Task ID: {output.task_id}")
    print(f"  Total Steps: {output.total_steps}")
    print(f"  Total Tool Calls: {output.total_tool_calls}")
    print(f"  Final Output: {output.final_output}")
    print(f"  Total Events: {len(callback.events)}")

    # Example 2: Run with custom configuration
    print("\n" + "=" * 60)
    print("Example 2: Running with custom configuration")
    print("=" * 60)

    config = ExecutionConfig(
        max_steps=10,
        max_retries=2,
        auto_retry_errors=True,
        step_delay=0.5,  # Add delay between steps for demonstration
    )

    task_input2 = TaskInput(
        task_id="task-002",
        user_input="Find all Python files and count their lines",
    )

    callback2 = LoggingCallback()
    executor.add_callback(callback2)

    output2 = await executor.run(task_input2, tools=tools, config=config)

    print("\n📊 Task Summary:")
    print(f"  Task ID: {output2.task_id}")
    print(f"  Total Steps: {output2.total_steps}")
    print(f"  Total Events: {len(callback2.events)}")

    # Example 3: Demonstrate pause/resume
    print("\n" + "=" * 60)
    print("Example 3: Demonstrating pause/resume (simulated)")
    print("=" * 60)

    task_input3 = TaskInput(
        task_id="task-003",
        user_input="A long-running analysis task",
    )

    # In a real scenario, you would start the task in the background
    # and then pause/resume it while it's running
    print("In a real scenario, you would:")
    print("  1. Start task: executor.run(task_input3)")
    print("  2. While running: await executor.pause('task-003')")
    print("  3. Pause it: await executor.pause('task-003')")
    print("  4. Resume it: await executor.resume('task-003')")
    print("  5. Stop it: await executor.stop('task-003')")

    print("\n✅ All examples completed successfully!")


if __name__ == "__main__":
    print("🚀 Execution Loop Example")
    print("This example demonstrates the core execution loop module.\n")

    asyncio.run(main())
