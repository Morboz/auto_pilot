"""Type definitions for LLM Adapter layer."""

from typing import Any, Dict, List, Literal, Optional, Union

from pydantic import BaseModel, Field


class Message(BaseModel):
    """Unified message format for internal use.

    Represents a message in a conversation with support for ReAct patterns.
    """

    role: Literal["system", "user", "assistant", "tool"]
    content: Optional[str] = None
    type: Optional[Literal["thought", "tool_use", "tool_result"]] = None
    name: Optional[str] = None  # tool name for tool messages
    tool_use_id: Optional[str] = None  # ID for tool_use/tool_result tracking
    # Raw content blocks (for preserving Claude's multi-block format)
    raw_content: Optional[Any] = None


class ToolCall(BaseModel):
    """Represents a tool call in the ReAct pattern."""

    type: Literal["tool_call"]
    name: str
    arguments: Dict[str, Any]
    id: Optional[str] = None  # Tool call ID for tracking (e.g., Claude's tool_use_id)


class ToolResult(BaseModel):
    """Represents the result of a tool execution."""

    type: Literal["tool_result"]
    name: str
    result: Any
    success: bool = True
    error: Optional[str] = None


class TokenUsage(BaseModel):
    """Tracks token usage for cost monitoring."""

    input_tokens: int = 0
    output_tokens: int = 0

    @property
    def total_tokens(self) -> int:
        """Calculate total tokens."""
        return self.input_tokens + self.output_tokens


class ModelCapabilities(BaseModel):
    """Describes the capabilities of a specific model."""

    supports_tools: bool = False
    supports_streaming: bool = False
    supports_json_schema: bool = False
    supports_images: bool = False
    max_context_length: Optional[int] = None


class GenerationResponse(BaseModel):
    """Response from text generation."""

    content: str
    messages: List[Message]
    usage: TokenUsage
    tool_calls: Optional[List[ToolCall]] = None
    model: str


class StreamingChunk(BaseModel):
    """A single chunk in a streaming response."""

    type: Literal["text", "tool_call", "tool_result", "error"]
    content: Union[str, Dict[str, Any]]
    delta: bool = False


class GenerationParams(BaseModel):
    """Parameters for text generation."""

    temperature: float = 0.7
    max_tokens: Optional[int] = None
    top_p: float = 1.0
    frequency_penalty: float = 0.0
    presence_penalty: float = 0.0


class StructuredGenerationParams(BaseModel):
    """Parameters for structured generation with JSON Schema."""

    json_schema: Dict[str, Any] = Field(
        ..., description="JSON Schema for structured output"
    )
    temperature: float = 0.0
    max_tokens: Optional[int] = None
    strict: bool = True


class ToolDefinition(BaseModel):
    """Definition of a tool for the ReAct pattern."""

    name: str
    description: str
    parameters: Dict[str, Any]  # JSON Schema for tool arguments


class ToolExecutionParams(BaseModel):
    """Parameters for tool execution."""

    tools: List[ToolDefinition]
    tool_choice: Literal["auto", "none"] = "auto"
    temperature: float = 0.0
    max_tokens: Optional[int] = None


class StreamParams(BaseModel):
    """Parameters for streaming responses."""

    temperature: float = 0.7
    max_tokens: Optional[int] = None


class StreamOptions(BaseModel):
    """Options for streaming."""

    include_usage: bool = False
