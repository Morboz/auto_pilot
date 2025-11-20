"""Example usage of LLM Adapter Layer.

This example demonstrates how to use the LLM Adapter layer to work with
multiple LLM providers (OpenAI, Claude, Local) through a unified interface.
"""

import asyncio

from auto_pilot.llm import (
    GenerationParams,
    Message,
    StructuredGenerationParams,
    ToolDefinition,
    create_adapter_for_model,
)


async def example_openai():
    """Example: Using OpenAI adapter."""
    print("=" * 60)
    print("OpenAI Adapter Example")
    print("=" * 60)

    # Set your API key
    # os.environ["OPENAI_API_KEY"] = "your-openai-api-key"

    # Create adapter for OpenAI
    adapter = create_adapter_for_model(
        model="gpt-4",
        # api_key="your-api-key",  # Optional, uses env var
    )

    # Get model capabilities
    capabilities = await adapter.get_capabilities("gpt-4")
    print(f"Model capabilities: {capabilities}")

    # Simple text generation
    messages = [
        Message(role="system", content="You are a helpful assistant."),
        Message(role="user", content="What is the capital of France?"),
    ]

    params = GenerationParams(temperature=0.7)
    response = await adapter.generate("gpt-4", messages, params)

    print(f"\nResponse: {response.content}")
    print(f"Token usage: {response.usage.total_tokens} total")
    print(f"Model: {response.model}")


async def example_structured_output():
    """Example: Using structured output."""
    print("\n" + "=" * 60)
    print("Structured Output Example")
    print("=" * 60)

    adapter = create_adapter_for_model(model="gpt-4")

    messages = [
        Message(
            role="user",
            content="Extract the name and age from this text: John Doe is 30 years old",
        ),
    ]

    # Define JSON schema for structured output
    schema = {
        "type": "object",
        "properties": {
            "name": {"type": "string"},
            "age": {"type": "integer"},
        },
        "required": ["name", "age"],
    }

    params = StructuredGenerationParams(json_schema=schema, temperature=0.0)
    response = await adapter.structured_generate("gpt-4", messages, params)

    print(f"\nStructured response: {response.content}")
    print(f"Token usage: {response.usage.total_tokens} total")


async def example_tool_calling():
    """Example: Using tool calling."""
    print("\n" + "=" * 60)
    print("Tool Calling Example")
    print("=" * 60)

    adapter = create_adapter_for_model(model="gpt-4")

    # Define a tool
    tools = [
        ToolDefinition(
            name="get_weather",
            description="Get the current weather for a city",
            parameters={
                "type": "object",
                "properties": {
                    "city": {
                        "type": "string",
                        "description": "The city name",
                    }
                },
                "required": ["city"],
            },
        )
    ]

    messages = [
        Message(role="user", content="What's the weather like in London?"),
    ]

    # In a real implementation, you would:
    # 1. Call run_with_tools to get tool calls
    # 2. Execute the tools
    # 3. Insert results into the conversation
    # 4. Continue the conversation

    print(f"Tool defined: {tools[0].name}")
    print(f"Tool description: {tools[0].description}")


async def example_claude():
    """Example: Using Claude adapter."""
    print("\n" + "=" * 60)
    print("Claude Adapter Example")
    print("=" * 60)

    # Set your API key
    # os.environ["ANTHROPIC_API_KEY"] = "your-anthropic-api-key"

    # Create adapter for Claude
    adapter = create_adapter_for_model(model="claude-3-sonnet")

    capabilities = await adapter.get_capabilities("claude-3-sonnet")
    print(f"Model capabilities: {capabilities}")

    messages = [
        Message(role="user", content="Explain quantum computing in simple terms."),
    ]

    response = await adapter.generate("claude-3-sonnet", messages)

    print(f"\nResponse: {response.content}")
    print(f"Token usage: {response.usage.total_tokens} total")


async def example_local():
    """Example: Using Local adapter."""
    print("\n" + "=" * 60)
    print("Local Adapter Example")
    print("=" * 60)

    # Create adapter for a local model (e.g., Ollama, LM Studio)
    from auto_pilot.llm import ProviderFactory

    adapter = ProviderFactory.create_adapter(
        provider="local",
        base_url="http://localhost:11434",
        # api_key=None,  # Optional for local
    )

    capabilities = await adapter.get_capabilities("llama2")
    print(f"Model capabilities: {capabilities}")

    messages = [
        Message(role="user", content="Hello, how are you?"),
    ]

    response = await adapter.generate("llama2", messages)

    print(f"\nResponse: {response.content}")
    print(f"Token usage: {response.usage.total_tokens} total")


async def example_factory():
    """Example: Using the ProviderFactory directly."""
    print("\n" + "=" * 60)
    print("ProviderFactory Example")
    print("=" * 60)

    from auto_pilot.llm import LLMConfig, ProviderFactory

    # Create configuration
    config = LLMConfig(
        provider="openai",
        default_model="gpt-4",
        # api_key="your-api-key",
    )

    # Create adapter from config
    adapter = ProviderFactory.create_adapter_from_config(config)

    # Detect provider from model name
    provider = ProviderFactory.detect_provider("gpt-3.5-turbo")
    print(f"Detected provider for 'gpt-3.5-turbo': {provider}")

    provider = ProviderFactory.detect_provider("claude-3-opus")
    print(f"Detected provider for 'claude-3-opus': {provider}")


async def main():
    """Run all examples."""
    print("\n" + "=" * 60)
    print("LLM Adapter Layer - Usage Examples")
    print("=" * 60)
    print("\nNote: These examples require API keys to be set in environment variables")
    print("- OPENAI_API_KEY for OpenAI examples")
    print("- ANTHROPIC_API_KEY for Claude examples")
    print("\n" + "=" * 60)

    try:
        # Uncomment the examples you want to run
        # await example_openai()
        # await example_structured_output()
        # await example_tool_calling()
        # await example_claude()
        # await example_local()
        await example_factory()

        print("\n" + "=" * 60)
        print("Examples completed successfully!")
        print("=" * 60)

    except Exception as e:
        print(f"\nError: {e}")
        print("\nThis is expected if API keys are not configured.")


if __name__ == "__main__":
    asyncio.run(main())
