"""Example: Using Claude adapter with compatible providers like MiniMax.

This example demonstrates how to use the ClaudeAdapter with Anthropic-compatible
providers by setting a custom base_url.
"""

import asyncio
from pathlib import Path

from dotenv import load_dotenv

from auto_pilot.llm.adapters.claude import ClaudeAdapter
from auto_pilot.llm.types import GenerationParams, Message

# Load environment variables from .env file
env_path = Path(__file__).parent.parent / ".env"
load_dotenv(env_path)


async def main():
    """Test ClaudeAdapter with a compatible provider."""

    # Method 1: Use environment variables (recommended)
    # Set ANTHROPIC_BASE_URL and ANTHROPIC_API_KEY in .env file
    adapter = ClaudeAdapter()

    # Method 2: Pass base_url explicitly
    # adapter = ClaudeAdapter(
    #     api_key="your-api-key",
    #     base_url="https://api.minimaxi.com/anthropic"
    # )

    print(f"Initialized adapter with base_url: {adapter.base_url}")

    # Test basic generation
    messages = [Message(role="user", content="Say 'Hello' in Chinese.")]

    params = GenerationParams(
        max_tokens=200,
        temperature=0.7,
    )

    try:
        # Test with claude-3-sonnet model
        response = await adapter.generate(
            model="claude-3-5-sonnet-20241022",
            messages=messages,
            params=params,
        )

        print("\n=== Generation Response ===")
        print(f"Content: {response.content!r}")
        print(f"Model: {response.model}")
        print(f"Usage: {response.usage}")
        print(f"Messages count: {len(response.messages)}")

        if response.content:
            print(f"\n✓ Success! Response: {response.content}")
        else:
            print("\n⚠ Warning: Response content is empty")
            print(f"Full response object: {response}")

    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback

        traceback.print_exc()

    finally:
        await adapter.close()


if __name__ == "__main__":
    asyncio.run(main())
