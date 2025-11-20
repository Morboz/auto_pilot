# LLM Adapter Layer

A unified interface layer for working with multiple LLM providers (OpenAI, Claude, local/self-hosted models) in the auto_pilot framework.

## Features

### Core Capabilities

1. **Unified Interface** - Work with any LLM provider through the same interface
2. **Text Generation** - Generate text responses with customizable parameters
3. **Structured Output** - Enforce JSON Schema validation on model outputs
4. **Tool Calling** - ReAct-style tool execution with schema-validated parameters
5. **Streaming** - Real-time response streaming for UI updates
6. **Token Tracking** - Monitor token usage for cost optimization
7. **Model Capabilities** - Dynamic feature detection per model

### Provider Support

- **OpenAI** - GPT-3.5, GPT-4, GPT-4 Turbo, etc.
- **Anthropic Claude** - Claude 3 Haiku, Sonnet, Opus
- **Local/Self-hosted** - Ollama, LM Studio, vLLM, OpenRouter, etc.

## Quick Start

### Installation

The adapter layer is included in the auto_pilot package. No additional installation required.

### Basic Usage

```python
from auto_pilot.llm import create_adapter_for_model, Message, GenerationParams

# Create an adapter for OpenAI
adapter = create_adapter_for_model(
    model="gpt-4",
    # api_key="your-api-key",  # Uses env var if not provided
)

# Generate text
messages = [
    Message(role="user", content="Hello, world!")
]

response = await adapter.generate(
    model="gpt-4",
    messages=messages,
    params=GenerationParams(temperature=0.7)
)

print(response.content)
print(f"Token usage: {response.usage}")
```

### Structured Output

```python
from auto_pilot.llm import StructuredGenerationParams

# Define JSON schema
schema = {
    "type": "object",
    "properties": {
        "name": {"type": "string"},
        "age": {"type": "integer"},
    },
    "required": ["name", "age"],
}

params = StructuredGenerationParams(
    json_schema=schema,
    temperature=0.0
)

response = await adapter.structured_generate(
    model="gpt-4",
    messages=messages,
    params=params
)

# Response content will be valid JSON matching the schema
data = json.loads(response.content)
```

### Tool Calling

```python
from auto_pilot.llm import ToolDefinition

# Define a tool
tools = [
    ToolDefinition(
        name="get_weather",
        description="Get the current weather for a city",
        parameters={
            "type": "object",
            "properties": {
                "city": {"type": "string"}
            },
            "required": ["city"],
        }
    )
]

# Execute with tools
response = await adapter.run_with_tools(
    model="gpt-4",
    messages=messages,
    tools=tools
)

# Check for tool calls
if response.tool_calls:
    for tool_call in response.tool_calls:
        print(f"Tool: {tool_call.name}")
        print(f"Arguments: {tool_call.arguments}")
```

### Streaming

```python
async for chunk in adapter.stream(
    model="gpt-4",
    messages=messages
):
    if chunk.type == "text":
        print(chunk.content, end="", flush=True)
```

### Multi-turn Conversations (ReAct Pattern)

```python
messages = [
    Message(role="system", content="You are a helpful assistant."),
    Message(role="user", content="I need to check the weather."),
    # Assistant thinks and decides to use a tool
    Message(role="assistant", type="thought", content="I should check the weather tool."),
    Message(role="assistant", type="tool_use", name="get_weather", content='{"city": "London"}'),
    # Tool result is inserted
    Message(role="tool", name="get_weather", content='{"weather": "sunny", "temp": 20}'),
    # Assistant continues reasoning
    Message(role="assistant", content="The weather in London is sunny with a temperature of 20°C."),
]
```

## API Reference

### Classes

#### `BaseLLMAdapter`

Abstract base class for all LLM adapters.

**Methods:**
- `generate(model, messages, params)` - Generate text response
- `structured_generate(model, messages, params)` - Generate structured output
- `run_with_tools(model, messages, tools, params)` - Execute tool calling
- `stream(model, messages, params)` - Stream text response
- `stream_with_tools(model, messages, tools, params)` - Stream with tool calls
- `get_capabilities(model)` - Get model capabilities
- `close()` - Clean up resources

#### `Message`

Unified message format for conversations.

**Fields:**
- `role: Literal["system", "user", "assistant", "tool"]` - Message role
- `content: Optional[str]` - Message content
- `type: Optional[Literal["thought", "tool_use", "tool_result"]]` - Message type for ReAct
- `name: Optional[str]` - Tool name (for tool messages)

#### `GenerationResponse`

Response from text generation.

**Fields:**
- `content: str` - Generated text
- `messages: List[Message]` - Updated conversation
- `usage: TokenUsage` - Token usage statistics
- `tool_calls: Optional[List[ToolCall]]` - Any tool calls made
- `model: str` - Model used

#### `TokenUsage`

Token usage tracking.

**Fields:**
- `input_tokens: int` - Tokens in the prompt
- `output_tokens: int` - Tokens in the response
- `total_tokens: int` - Total tokens (calculated property)

#### `ModelCapabilities`

Model capabilities description.

**Fields:**
- `supports_tools: bool` - Whether the model supports tool calling
- `supports_streaming: bool` - Whether the model supports streaming
- `supports_json_schema: bool` - Whether the model supports structured output
- `supports_images: bool` - Whether the model supports image input
- `max_context_length: Optional[int]` - Maximum context window

#### `ToolDefinition`

Definition of a tool for ReAct execution.

**Fields:**
- `name: str` - Tool name
- `description: str` - Tool description
- `parameters: Dict[str, Any]` - JSON Schema for tool arguments

#### `GenerationParams`

Parameters for text generation.

**Fields:**
- `temperature: float = 0.7` - Randomness control (0.0 to 2.0)
- `max_tokens: Optional[int] = None` - Maximum tokens to generate
- `top_p: float = 1.0` - Nucleus sampling parameter
- `frequency_penalty: float = 0.0` - Frequency penalty
- `presence_penalty: float = 0.0` - Presence penalty

#### `StructuredGenerationParams`

Parameters for structured output generation.

**Fields:**
- `json_schema: Dict[str, Any]` - JSON Schema for output
- `temperature: float = 0.0` - Temperature (typically 0 for structured output)
- `max_tokens: Optional[int] = None` - Maximum tokens
- `strict: bool = True` - Whether to enforce strict schema validation

#### `ToolExecutionParams`

Parameters for tool execution.

**Fields:**
- `tools: List[ToolDefinition]` - Available tools
- `tool_choice: Literal["auto", "none"] = "auto"` - Tool selection strategy
- `temperature: float = 0.0` - Temperature
- `max_tokens: Optional[int] = None` - Maximum tokens

#### `StreamParams`

Parameters for streaming responses.

**Fields:**
- `temperature: float = 0.7` - Temperature
- `max_tokens: Optional[int] = None` - Maximum tokens

#### `StreamOptions`

Options for streaming.

**Fields:**
- `include_usage: bool = False` - Whether to include usage in stream

#### `StreamingChunk`

A single chunk in a streaming response.

**Fields:**
- `type: Literal["text", "tool_call", "tool_result", "error"]` - Chunk type
- `content: Union[str, Dict[str, Any]]` - Chunk content
- `delta: bool = False` - Whether this is a delta update

### Factory Functions

#### `create_adapter_for_model(model, **kwargs)`

Create an adapter for a specific model. Automatically detects the provider.

```python
adapter = create_adapter_for_model(
    model="gpt-4",
    api_key="your-api-key",
    base_url="http://localhost:11434",  # For local providers
    timeout=60.0,
)
```

#### `ProviderFactory.create_adapter(provider, **kwargs)`

Create an adapter for a specific provider.

```python
from auto_pilot.llm import ProviderFactory

adapter = ProviderFactory.create_adapter(
    provider="openai",
    api_key="your-api-key",
    timeout=60.0,
)
```

#### `ProviderFactory.detect_provider(model)`

Detect the provider from a model name.

```python
provider = ProviderFactory.detect_provider("gpt-4")  # Returns "openai"
provider = ProviderFactory.detect_provider("claude-3-sonnet")  # Returns "claude"
```

### Provider-Specific Adapters

#### `OpenAIAdapter`

Adapter for OpenAI API.

```python
from auto_pilot.llm import OpenAIAdapter

adapter = OpenAIAdapter(
    api_key="your-api-key",
    base_url=None,  # Optional, for OpenAI-compatible APIs
    timeout=60.0,
)
```

#### `ClaudeAdapter`

Adapter for Anthropic Claude API.

```python
from auto_pilot.llm import ClaudeAdapter

adapter = ClaudeAdapter(
    api_key="your-api-key",
    base_url=None,  # Optional, for Claude-compatible APIs
    timeout=60.0,
)
```

#### `LocalAdapter`

Adapter for local/self-hosted models (OpenAI-compatible).

```python
from auto_pilot.llm import LocalAdapter

adapter = LocalAdapter(
    base_url="http://localhost:11434",  # Required
    api_key=None,  # Optional
    timeout=60.0,
)
```

## Error Handling

### Exception Hierarchy

All adapter errors inherit from `LLMAdapterError`:

- `ConfigurationError` - Configuration issues (missing API key, invalid config)
- `AuthenticationError` - Authentication failures (invalid API key)
- `RateLimitError` - Rate limit exceeded (can be retried)
- `ModelNotFoundError` - Model not available
- `InvalidRequestError` - Invalid request (malformed messages, exceeded context)
- `StreamingError` - Streaming errors
- `ToolExecutionError` - Tool execution errors
- `StructuredOutputError` - Structured output validation errors
- `ProviderError` - Generic provider errors (wraps provider-specific errors)

### Error Handling Example

```python
from auto_pilot.llm import (
    LLMAdapterError,
    AuthenticationError,
    RateLimitError,
)

try:
    response = await adapter.generate("gpt-4", messages)
except AuthenticationError as e:
    print(f"Authentication failed: {e.message}")
except RateLimitError as e:
    print(f"Rate limited. Retry after {e.retry_after} seconds")
except LLMAdapterError as e:
    print(f"LLM error: {e.message}")
    print(f"Error code: {e.error_code}")
```

## Configuration

### Environment Variables

- `OPENAI_API_KEY` - OpenAI API key
- `ANTHROPIC_API_KEY` - Anthropic API key

### Configuration File

```python
from auto_pilot.llm import LLMConfig, ProviderFactory

config = LLMConfig(
    provider="openai",
    default_model="gpt-4",
    api_key="your-api-key",
    timeout=60.0,
    max_retries=3,
)

adapter = ProviderFactory.create_adapter_from_config(config)
```

## Message Format Normalization

The adapter automatically converts between internal format and provider-specific formats.

### Internal Format

```python
Message(
    role="user",
    content="Hello",
    type=None,
    name=None,
)
```

### Provider-Specific Formats

**OpenAI:**
```python
{"role": "user", "content": "Hello"}
```

**Claude:**
```python
{"role": "user", "content": "Hello"}
```

The adapter handles the conversion automatically.

## Streaming

Streaming allows you to receive responses in real-time:

```python
async for chunk in adapter.stream("gpt-4", messages):
    if chunk.type == "text":
        print(chunk.content, end="")
    elif chunk.type == "tool_call":
        print(f"Tool call: {chunk.content}")
```

### Streaming Events

- `text` - Text content chunk
- `tool_call` - Tool call detected
- `tool_result` - Tool execution result
- `error` - Error occurred

## Testing

Run the test suite:

```bash
# Run all tests
pytest tests/test_llm_adapter.py -v

# Run with coverage
pytest tests/test_llm_adapter.py -v --cov=auto_pilot.llm
```

## Examples

See `examples/llm_adapter_usage.py` for comprehensive examples including:
- Basic text generation
- Structured output
- Tool calling
- Streaming
- Multi-turn conversations
- Different providers

## Architecture

### Design Patterns

1. **Adapter Pattern** - Unified interface over different providers
2. **Factory Pattern** - Centralized adapter creation
3. **Strategy Pattern** - Different generation strategies

### Class Diagram

```
BaseLLMAdapter (ABC)
    ├── OpenAIAdapter
    ├── ClaudeAdapter
    └── LocalAdapter

ProviderFactory
    ├── create_adapter()
    ├── create_adapter_from_config()
    ├── detect_provider()
    └── register_adapter()
```

## Best Practices

1. **Always use environment variables** for API keys
2. **Handle errors** gracefully with appropriate exception handling
3. **Monitor token usage** to control costs
4. **Use structured output** for predictable responses
5. **Cache capabilities** if querying frequently
6. **Close adapters** when done to free resources

## Troubleshooting

### Common Issues

**"API key is required"**
- Set the appropriate environment variable (`OPENAI_API_KEY`, `ANTHROPIC_API_KEY`)
- Or pass `api_key` parameter when creating the adapter

**"Model not found"**
- Check that the model name is correct
- Verify your API key has access to the model
- Ensure the model is available in your region

**"Rate limit exceeded"**
- The adapter will raise `RateLimitError`
- Implement exponential backoff for retries
- Consider using a different model or provider

**"Streaming stops unexpectedly"**
- Check network connectivity
- Verify timeout settings
- Handle `StreamingError` appropriately

## Contributing

When adding new providers:

1. Create a new adapter class inheriting from `BaseLLMAdapter`
2. Implement all required methods
3. Add tests
4. Register in `ProviderFactory._adapters`
5. Update documentation

## License

MIT License - see LICENSE file for details
