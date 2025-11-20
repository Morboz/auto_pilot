"""Example: Using Claude adapter with streaming tool calling (MiniMax compatible).

This example demonstrates streaming tool calling with MiniMax's Anthropic-compatible API,
showing how to handle real-time streaming responses while tools are being called.
Based on: https://platform.minimaxi.com/docs/guides/text-m2-function-call#anthropic-sdk
"""

import asyncio
from pathlib import Path

from dotenv import load_dotenv

from auto_pilot.llm.adapters.claude import ClaudeAdapter
from auto_pilot.llm.types import Message, StreamParams, ToolDefinition

# Load environment variables from .env file
env_path = Path(__file__).parent.parent / ".env"
load_dotenv(env_path)


async def simulate_tool_execution(tool_name: str, arguments: dict) -> str:
    """Simulate tool execution and return result."""
    # This is a mock implementation - in real scenarios, you'd call actual APIs
    print(f"\n  ⚙️  Executing {tool_name} with args: {arguments}")

    await asyncio.sleep(0.5)  # Simulate API delay

    if tool_name == "get_weather":
        location = arguments.get("location", "Unknown")
        return f"{location}的天气：晴朗，24°C，湿度65%，微风"

    elif tool_name == "get_stock_price":
        symbol = arguments.get("symbol", "Unknown")
        return f"{symbol}的股价：$150.25 (+2.3%)"

    elif tool_name == "search_news":
        query = arguments.get("query", "Unknown")
        return (
            f"关于'{query}'的最新新闻：1) AI技术突破... 2) 新产品发布... 3) 市场趋势..."
        )

    return "Tool executed successfully"


async def main():
    """Test ClaudeAdapter with streaming tool calling on MiniMax."""

    adapter = ClaudeAdapter()
    print(f"✓ Initialized adapter with base_url: {adapter.base_url}\n")

    # Define multiple tools
    tools = [
        ToolDefinition(
            name="get_weather",
            description="Get weather information for a location",
            parameters={
                "type": "object",
                "properties": {
                    "location": {
                        "type": "string",
                        "description": "City and state, e.g. San Francisco, US",
                    }
                },
                "required": ["location"],
            },
        ),
        ToolDefinition(
            name="get_stock_price",
            description="Get current stock price for a symbol",
            parameters={
                "type": "object",
                "properties": {
                    "symbol": {
                        "type": "string",
                        "description": "Stock ticker symbol, e.g. AAPL, TSLA",
                    }
                },
                "required": ["symbol"],
            },
        ),
        ToolDefinition(
            name="search_news",
            description="Search for latest news about a topic",
            parameters={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search query or topic"}
                },
                "required": ["query"],
            },
        ),
    ]

    print("🔧 Available tools:")
    for tool in tools:
        print(f"  - {tool.name}: {tool.description}")
    print()

    # Test scenario 1: Weather query
    print("=" * 80)
    print("Scenario 1: Weather Query with Streaming")
    print("=" * 80)

    messages = [
        Message(
            role="user",
            content=(
                "Please check the weather in San Francisco, US using the get_weather tool."
            ),
        )
    ]

    print(f"👤 User: {messages[0].content}\n")

    stream_params = StreamParams(
        max_tokens=1024,
        temperature=0.7,
    )

    try:
        print("=== Step 1: Model analyzes and calls tool (streaming) ===\n")
        print("💬 Claude (streaming):\n")

        # Track tool calls and assistant content
        detected_tool_calls = []
        accumulated_text = ""

        # Stream the response and detect tool calls in real-time
        async for chunk in adapter.stream_with_tools(
            model="MiniMax-M2",  # Use MiniMax model name
            messages=messages,
            tools=tools,
            params=stream_params,
        ):
            if chunk.type == "text":
                if isinstance(chunk.content, str):
                    # Accumulate text output
                    print(chunk.content, end="", flush=True)
                    accumulated_text += chunk.content
                elif isinstance(chunk.content, dict) and "usage" in chunk.content:
                    # Display usage stats at the end
                    usage = chunk.content["usage"]
                    inp = usage["input_tokens"]
                    out = usage["output_tokens"]
                    print(f"\n\n📊 Usage: Input={inp}, Output={out}")

            elif chunk.type == "tool_call":
                # Tool call detected during streaming
                tool_info = chunk.content
                detected_tool_calls.append(tool_info)
                print(f"\n\n🔧 [Tool Call] {tool_info['name']}")
                print(f"   Arguments: {tool_info['arguments']}\n")

        if not detected_tool_calls:
            print("\n⚠️  No tool calls detected. This might be an issue.")
            print("Let's try to see what the model said:")
            print(f"Accumulated text: {accumulated_text}")
            return

        print("\n=== Step 2: Execute tool(s) ===")

        # First, add the assistant's response with tool calls
        # Build raw_content with tool_use blocks (minimal format)
        tool_use_blocks = [
            {
                "type": "tool_use",
                "id": tc["id"],
                "name": tc["name"],
                "input": tc["arguments"],
            }
            for tc in detected_tool_calls
        ]
        messages.append(
            Message(
                role="assistant",
                content="",  # Empty content when using tools
                raw_content=tool_use_blocks,  # Store tool calls
            )
        )

        # Execute detected tools and add results
        for tool_call in detected_tool_calls:
            tool_name = tool_call.get("name")
            arguments = tool_call.get("arguments", {})
            tool_id = tool_call.get("id")  # Get the actual tool ID

            tool_result = await simulate_tool_execution(tool_name, arguments)
            print(f"  📊 Result: {tool_result}")

            # Add tool result to conversation
            messages.append(
                Message(
                    role="user",
                    type="tool_result",
                    content=tool_result,
                    tool_use_id=tool_id,  # Use the actual tool ID
                )
            )

        # Get final streaming response with tool results
        print("\n=== Step 3: Model generates final answer (streaming) ===\n")
        print("💬 Claude (streaming with context):\n")

        accumulated_text = ""
        async for chunk in adapter.stream_with_tools(
            model="MiniMax-M2",
            messages=messages,
            tools=tools,
            params=stream_params,
        ):
            if chunk.type == "text" and isinstance(chunk.content, str):
                print(chunk.content, end="", flush=True)
                accumulated_text += chunk.content
            elif isinstance(chunk.content, dict) and "usage" in chunk.content:
                usage = chunk.content["usage"]
                inp = usage["input_tokens"]
                out = usage["output_tokens"]
                print(f"\n\n📊 Usage: Input={inp}, Output={out}")

        print()  # Final newline

    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback

        traceback.print_exc()

    finally:
        await adapter.close()
        print("\n✅ Adapter closed")


if __name__ == "__main__":
    asyncio.run(main())
