#!/usr/bin/env python3
"""Example demonstrating the Controller module.

This example shows how to:
1. Create a FastAPI application with controller
2. Use REST API to manage tasks
3. Use WebSocket for real-time streaming
"""

import asyncio

from fastapi.testclient import TestClient

from auto_pilot.controller import create_app
from auto_pilot.llm import (
    GenerationResponse,
    ModelCapabilities,
    TokenUsage,
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
            content="I'll help you with this task. Let me process it step by step.",
            usage=TokenUsage(input_tokens=100, output_tokens=50),
            messages=[],
            model="example-model",
        )

    async def run_with_tools(self, model: str, messages, tools, params=None):
        self.call_count += 1
        return GenerationResponse(
            content="Task completed successfully. The analysis is done and the task is complete.",
            usage=TokenUsage(input_tokens=150, output_tokens=75),
            messages=[],
            model="example-model",
            tool_calls=[],
        )


async def example_rest_api():
    """Demonstrate REST API usage."""
    print("=" * 60)
    print("Example 1: REST API Usage")
    print("=" * 60)

    # Create LLM adapter
    llm = ExampleLLMAdapter()

    # Create FastAPI app
    app = create_app(llm_adapter=llm)

    # Create test client
    client = TestClient(app)

    # 1. Start a new task
    print("\n1. Starting a new task...")
    response = client.post(
        "/agents/agent-123/tasks",
        json={
            "input": "Analyze the sales data and provide insights",
            "agent_id": "agent-123",
            "config": {"max_steps": 10, "max_retries": 2},
        },
    )

    print(f"Response: {response.status_code}")
    result = response.json()
    print(f"Task ID: {result['task_id']}")
    print(f"Status: {result['status']}")

    task_id = result["task_id"]

    # 2. Get task status
    print("\n2. Getting task status...")
    response = client.get(f"/tasks/{task_id}")

    print(f"Response: {response.status_code}")
    status = response.json()
    print(f"Status: {status['status']}")
    print(f"Current Step: {status['current_step']}")
    print(f"User Input: {status['user_input']}")

    # 3. Wait a bit and check again
    await asyncio.sleep(0.5)

    print("\n3. Checking status again...")
    response = client.get(f"/tasks/{task_id}")
    status = response.json()
    print(f"Status: {status['status']}")
    print(f"Final Output: {status.get('final_output', 'N/A')}")

    # 4. Test pause (will fail if already finished)
    print("\n4. Attempting to pause task...")
    try:
        response = client.post(f"/tasks/{task_id}/pause")
        print(f"Response: {response.status_code}")
        result = response.json()
        print(f"Success: {result['success']}")
    except Exception as e:
        print(f"Task may have already finished: {e}")

    print("\n✅ REST API example completed!\n")


async def example_websocket():
    """Demonstrate WebSocket usage."""
    print("=" * 60)
    print("Example 2: WebSocket Usage")
    print("=" * 60)

    # Create LLM adapter
    llm = ExampleLLMAdapter()

    # Create FastAPI app
    app = create_app(llm_adapter=llm)

    # Create test client
    client = TestClient(app)

    # Start a task
    print("\n1. Starting a task with WebSocket streaming...")
    response = client.post(
        "/agents/agent-456/tasks",
        json={
            "input": "Process this data with streaming updates",
            "agent_id": "agent-456",
        },
    )

    task_id = response.json()["task_id"]
    print(f"Task ID: {task_id}")

    # Connect to WebSocket
    print("\n2. Connecting to WebSocket...")
    with client.websocket_connect(f"/tasks/{task_id}/stream") as websocket:
        # Receive events
        print("3. Receiving events...")
        event_count = 0
        for i in range(10):  # Try to receive up to 10 events
            try:
                message = websocket.receive_json()
                event_count += 1
                print(f"   Event {event_count}: {message['event']}")

                if message["event"] == "finished":
                    print(f"   Final output: {message['data'].get('final_output', 'N/A')}")
                    break

                # Send ping to keep connection alive
                websocket.send_text("ping")

            except Exception as e:
                print(f"   No more events: {e}")
                break

    print(f"\n✅ Received {event_count} WebSocket events!\n")


async def example_task_control():
    """Demonstrate task control operations."""
    print("=" * 60)
    print("Example 3: Task Control Operations")
    print("=" * 60)

    # Create LLM adapter
    llm = ExampleLLMAdapter()

    # Create FastAPI app
    app = create_app(llm_adapter=llm)
    client = TestClient(app)

    # Start a task
    print("\n1. Starting a task...")
    response = client.post("/agents/agent-789/tasks", json={"input": "Long running analysis task"})
    task_id = response.json()["task_id"]
    print(f"Task ID: {task_id}")

    # Try pause
    print("\n2. Pausing task...")
    response = client.post(f"/tasks/{task_id}/pause")
    print(f"Response: {response.json()}")

    # Try resume
    print("\n3. Resuming task...")
    response = client.post(f"/tasks/{task_id}/resume")
    print(f"Response: {response.json()}")

    # Try stop
    print("\n4. Stopping task...")
    response = client.post(f"/tasks/{task_id}/stop")
    print(f"Response: {response.json()}")

    # Check final status
    print("\n5. Checking final status...")
    response = client.get(f"/tasks/{task_id}")
    status = response.json()
    print(f"Final Status: {status['status']}")

    print("\n✅ Task control example completed!\n")


async def main():
    """Main example function."""
    print("\n🚀 Controller Module Example")
    print("This example demonstrates the REST API and WebSocket features.\n")

    await example_rest_api()
    await asyncio.sleep(1)

    await example_websocket()
    await asyncio.sleep(1)

    await example_task_control()

    print("=" * 60)
    print("✅ All examples completed successfully!")
    print("=" * 60)
    print("\nTo run the actual server, use:")
    print("  uvicorn auto_pilot.controller.app:create_app --host 0.0.0.0 --port 8000")
    print("\nAPI Documentation available at: http://localhost:8000/docs")


if __name__ == "__main__":
    asyncio.run(main())
