"""Direct example using Anthropic SDK with MiniMax.

This demonstrates the correct way to handle tool calling with MiniMax
according to their official documentation.
"""

import asyncio
import json
from pathlib import Path

from anthropic import AsyncAnthropic
from dotenv import load_dotenv

# Load environment variables
env_path = Path(__file__).parent.parent / ".env"
load_dotenv(env_path)


async def main():
    """Test tool calling with direct Anthropic SDK."""

    # Initialize client
    client = AsyncAnthropic()

    # Define tool
    tools = [
        {
            "name": "get_weather",
            "description": (
                "Get weather of a location, " "the user should supply a location first."
            ),
            "input_schema": {
                "type": "object",
                "properties": {
                    "location": {
                        "type": "string",
                        "description": "The city and state, e.g. San Francisco, US",
                    }
                },
                "required": ["location"],
            },
        }
    ]

    # Step 1: Initial user message
    messages = [{"role": "user", "content": "How's the weather in San Francisco?"}]
    print(f"👤 User: {messages[0]['content']}\n")

    # Step 2: Model analyzes and calls tool
    print("=== Step 1: Model analyzes and calls tool ===")
    response = await client.messages.create(
        model="MiniMax-M2",
        max_tokens=4096,
        messages=messages,
        tools=tools,
    )

    print(f"Response type: {response.stop_reason}")
    print(f"Content blocks: {len(response.content)}")

    tool_use_blocks = []
    for block in response.content:
        print(f"  Block type: {block.type}")
        if block.type == "thinking":
            print(f"    💭 Thinking: {block.thinking[:100]}...")
        elif block.type == "text":
            print(f"    💬 Text: {block.text}")
        elif block.type == "tool_use":
            tool_use_blocks.append(block)
            print(f"    🔧 Tool: {block.name}")
            print(f"       Args: {json.dumps(block.input, ensure_ascii=False)}")
            print(f"       ID: {block.id}")

    # Step 3: Execute tool and add result
    if tool_use_blocks:
        # ⚠️ CRITICAL: Must append complete response.content
        messages.append({"role": "assistant", "content": response.content})

        # Execute tool (simulated)
        print("\n=== Step 2: Execute tool ===")
        tool_result = "24℃, sunny"
        print(f"📊 Tool result: {tool_result}")

        # Add tool result
        messages.append(
            {
                "role": "user",
                "content": [
                    {
                        "type": "tool_result",
                        "tool_use_id": tool_use_blocks[0].id,
                        "content": tool_result,
                    }
                ],
            }
        )

        # Step 4: Get final response
        print("\n=== Step 3: Model generates final answer ===")
        final_response = await client.messages.create(
            model="MiniMax-M2",
            max_tokens=4096,
            messages=messages,
            tools=tools,
        )

        for block in final_response.content:
            if block.type == "thinking":
                print(f"💭 Thinking: {block.thinking[:100]}...")
            elif block.type == "text":
                print(f"💬 Final answer: {block.text}")

        print(f"\n📊 Usage: {final_response.usage}")

    await client.close()


if __name__ == "__main__":
    asyncio.run(main())
