#!/usr/bin/env python3
"""Integrated AutoPilot API Example.

This example demonstrates how to:
1. Initialize the LLM adapter
2. Set up the integrated FastAPI application
3. Use all features: Agents, Tools, Tasks, and Execution
"""

import asyncio

from auto_pilot.llm import (
    GenerationResponse,
    ModelCapabilities,
    TokenUsage,
)
from auto_pilot.main import app, init_llm_adapter


class ExampleLLMAdapter:
    """Example LLM adapter for demonstration purposes.

    In production, use:
        from auto_pilot.llm import create_adapter_for_model
        llm = create_adapter_for_model(
            model="claude-3",
            api_key="your-api-key"
        )
    """

    def __init__(self):
        self.call_count = 0

    async def get_capabilities(self, model: str) -> ModelCapabilities:
        """Get model capabilities."""
        return ModelCapabilities(
            supports_tools=True,
            supports_streaming=True,
            max_context_length=200000,
        )

    async def generate(self, model: str, messages, params=None):
        """Generate text response."""
        self.call_count += 1
        return GenerationResponse(
            content="I'll help you complete this task. Let me work through it step by step.",
            usage=TokenUsage(input_tokens=120, output_tokens=60),
            messages=[],
            model="example-model",
        )

    async def run_with_tools(self, model: str, messages, tools, params=None):
        """Generate response with tool support."""
        self.call_count += 1
        return GenerationResponse(
            content="I have successfully completed the task. The analysis is done and the task is complete.",
            usage=TokenUsage(input_tokens=180, output_tokens=90),
            messages=[],
            model="example-model",
            tool_calls=[],
        )


async def demo_rest_api():
    """Demonstrate REST API usage with integrated app."""
    print("=" * 70)
    print("Example: Integrated AutoPilot API with Execution Features")
    print("=" * 70)

    # Import test client
    from fastapi.testclient import TestClient

    # Create test client
    client = TestClient(app)

    # 1. Check API root
    print("\n1. Checking API root...")
    response = client.get("/")
    print(f"Status: {response.status_code}")
    print(f"Response: {response.json()}")

    # 2. Check health
    print("\n2. Checking health...")
    response = client.get("/health")
    print(f"Status: {response.status_code}")
    print(f"Response: {response.json()}")

    # 3. Start a task execution
    print("\n3. Starting task execution...")
    response = client.post(
        "/execution/agents/agent-123/tasks",
        json={
            "input": "Analyze the current codebase and provide insights",
            "config": {"max_steps": 10, "max_retries": 2},
            "tools": [
                {
                    "name": "search_file",
                    "description": "Search for files in the workspace",
                    "parameters": {
                        "type": "object",
                        "properties": {"filename": {"type": "string"}},
                    },
                }
            ],
        },
    )

    print(f"Status: {response.status_code}")
    result = response.json()
    print(f"Response: {result}")

    task_id = result.get("task_id")
    if task_id:
        # 4. Get task status
        print("\n4. Getting task status...")
        await asyncio.sleep(0.5)  # Wait for task to initialize

        response = client.get(f"/execution/tasks/{task_id}")
        print(f"Status: {response.status_code}")
        status = response.json()
        print(f"Status: {status.get('execution_status', status.get('db_status'))}")
        print(f"Current Step: {status.get('current_step', 'N/A')}")
        print(f"Final Output: {status.get('final_output', 'N/A')}")

    print("\n✅ Integration example completed!\n")


async def demo_websocket():
    """Demonstrate WebSocket streaming."""
    print("=" * 70)
    print("Example: WebSocket Streaming")
    print("=" * 70)

    from fastapi.testclient import TestClient

    client = TestClient(app)

    # Start a task
    print("\n1. Starting task...")
    response = client.post(
        "/execution/agents/agent-456/tasks",
        json={
            "input": "Process data with real-time streaming updates",
            "config": {"max_steps": 5},
        },
    )

    task_id = response.json()["task_id"]
    print(f"Task ID: {task_id}")

    # Connect to WebSocket
    print("\n2. Connecting to WebSocket...")
    with client.websocket_connect(f"/execution/tasks/{task_id}/stream") as websocket:
        print("3. Receiving streaming events...")
        event_count = 0
        for i in range(15):  # Try to receive up to 15 events
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


async def demo_all_features():
    """Demonstrate all features together."""
    print("=" * 70)
    print("Example: All Features Integration")
    print("=" * 70)

    from fastapi.testclient import TestClient

    client = TestClient(app)

    # Create an agent
    print("\n1. Creating agent...")
    response = client.post(
        "/agents/",
        json={"name": "Data Analysis Agent", "type": "analysis", "status": "active"},
    )
    print(f"Agent created: {response.status_code}")

    # Create a tool
    print("\n2. Creating tool...")
    response = client.post(
        "/tools/",
        json={
            "name": "File Reader",
            "description": "Read file contents",
            "version": "1.0.0",
        },
    )
    print(f"Tool created: {response.status_code}")

    # Start execution
    print("\n3. Starting execution...")
    response = client.post(
        "/execution/agents/agent-789/tasks",
        json={
            "input": "Complete a comprehensive analysis",
            "config": {"max_steps": 8, "max_retries": 3},
        },
    )
    task_id = response.json()["task_id"]
    print(f"Task ID: {task_id}")

    # Monitor with WebSocket
    print("\n4. Monitoring via WebSocket...")
    with client.websocket_connect(f"/execution/tasks/{task_id}/stream") as ws:
        for i in range(10):
            try:
                msg = ws.receive_json()
                print(f"   [{msg['event']}] ", end="")
                if msg["event"] == "step_started":
                    print(f"Step {msg['data'].get('step')}")
                elif msg["event"] == "llm_response":
                    print(f"LLM: {msg['data'].get('content', '')[:50]}...")
                elif msg["event"] == "finished":
                    print("Task completed!")
                    break
                ws.send_text("ping")
            except:
                break

    print("\n✅ All features demonstrated!\n")


async def main():
    """Main example function."""
    print("\n" + "🚀" * 20)
    print("AutoPilot Integrated API Example")
    print("🚀" * 20 + "\n")

    # Initialize LLM adapter
    print("Initializing LLM adapter...")
    llm = ExampleLLMAdapter()
    init_llm_adapter(llm)
    print("✅ LLM adapter initialized\n")

    await demo_rest_api()
    await asyncio.sleep(1)

    await demo_websocket()
    await asyncio.sleep(1)

    await demo_all_features()

    print("=" * 70)
    print("✅ All examples completed successfully!")
    print("=" * 70)
    print("\n📝 To run the actual server, use:")
    print("   uvicorn auto_pilot.main:app --host 0.0.0.0 --port 8000")
    print("\n📖 API Documentation available at: http://localhost:8000/docs")
    print("\n🔗 Key endpoints:")
    print("   • Agents: http://localhost:8000/agents")
    print("   • Tools: http://localhost:8000/tools")
    print("   • Tasks: http://localhost:8000/tasks")
    print("   • Execution: http://localhost:8000/execution")
    print("   • WebSocket: ws://localhost:8000/execution/tasks/{task_id}/stream")


if __name__ == "__main__":
    asyncio.run(main())
