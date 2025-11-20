"""Example: Using Claude adapter with tool calling (MiniMax compatible).

This example demonstrates tool calling with MiniMax's Anthropic-compatible API.
Based on: https://platform.minimaxi.com/docs/guides/text-m2-function-call#anthropic-sdk
"""

import asyncio
from pathlib import Path

from dotenv import load_dotenv

from auto_pilot.llm.adapters.claude import ClaudeAdapter
from auto_pilot.llm.types import Message, ToolDefinition, ToolExecutionParams

# Load environment variables from .env file
env_path = Path(__file__).parent.parent / ".env"
load_dotenv(env_path)


async def main():
    """Test ClaudeAdapter with tool calling on MiniMax."""

    adapter = ClaudeAdapter()
    print(f"Initialized adapter with base_url: {adapter.base_url}\n")

    # Define a simple tool (following MiniMax's format)
    tools = [
        ToolDefinition(
            name="get_weather",
            description=(
                "Get weather of a location, " "the user should supply a location first."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "location": {
                        "type": "string",
                        "description": "The city and state, e.g. San Francisco, US",
                    }
                },
                "required": ["location"],
            },
        )
    ]

    # Test tool calling
    messages = [
        Message(
            role="user",
            content=(
                "Please use the get_weather tool to check the weather "
                "in San Francisco, US."
            ),
        )
    ]

    print(f"👤 User: {messages[0].content}")

    params = ToolExecutionParams(
        tools=tools,
        max_tokens=4096,
        temperature=0.7,
    )

    try:
        print("\n=== Step 1: Model analyzes and calls tool ===")
        response = await adapter.run_with_tools(
            model="MiniMax-M2",  # Use MiniMax model name
            messages=messages,
            tools=tools,
            params=params,
        )

        print(f"\n💬 Model: {response.content!r}")
        print(f"📊 Usage: {response.usage}")

        if response.tool_calls:
            print("\n✓ Tool calls detected:")
            for tool_call in response.tool_calls:
                print(f"  🔧 Tool: {tool_call.name}")
                print(f"     Arguments: {tool_call.arguments}")

                # Simulate tool execution
                print("\n=== Step 2: Execute tool ===")
                tool_result = "24℃, sunny"
                print(f"  📊 Tool result: {tool_result}")

                # Add tool result to conversation
                # According to MiniMax docs, we need tool_use_id
                messages = response.messages  # Use updated messages from response
                messages.append(
                    Message(
                        role="user",  # Tool results are sent as user messages
                        type="tool_result",
                        content=tool_result,
                        tool_use_id=tool_call.id,  # Critical: must match
                    )
                )

                # Get final response
                print("\n=== Step 3: Model generates final answer ===")
                final_response = await adapter.run_with_tools(
                    model="MiniMax-M2",  # Use MiniMax model name
                    messages=messages,
                    tools=tools,
                    params=params,
                )

                print(f"\n💬 Final answer: {final_response.content}")
                print(f"📊 Usage: {final_response.usage}")
        else:
            print("\n⚠ No tool calls in response")
            print(f"   Direct answer: {response.content}")

    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback

        traceback.print_exc()

    finally:
        await adapter.close()


if __name__ == "__main__":
    asyncio.run(main())
