# AutoPilot Tool System

## Overview

The AutoPilot Tool System provides a modular, secure, and extensible framework for managing and executing tools within the AutoPilot agent framework. It implements the architecture specified in `docs/arch-spec.md` section 4.

## Architecture

The tool system consists of four main components:

### 1. Tool Registry

Central registry for managing tool definitions, metadata, and JSON schemas.

**Key Features:**
- Tool registration and discovery
- JSON Schema validation (Draft 2020-12)
- Version management and lifecycle
- Tool search and filtering

**Example:**
```python
from auto_pilot.tools import ToolRegistry, ToolDefinition, ToolMetadata

registry = ToolRegistry()

tool = ToolDefinition(
    metadata=ToolMetadata(
        name="read_file",
        description="Read file contents",
        version="1.0.0",
    ),
    parameters={
        "type": "object",
        "properties": {
            "path": {"type": "string"}
        },
        "required": ["path"]
    }
)

registry.register_tool(tool)
```

### 2. Tool Permissions

Fine-grained access control and security for tool execution.

**Key Features:**
- Filesystem access controls
- Network permissions
- Resource limits (CPU, memory, disk)
- Security policies
- Audit logging

**Example:**
```python
from auto_pilot.tools import PermissionManager, ToolPermissions
from auto_pilot.tools.types import FileSystemPermission, NetworkPermission, ResourceLimits

permissions = PermissionManager()

# Define restricted permissions
file_perms = ToolPermissions(
    filesystem=FileSystemPermission(
        allowed_paths=["/tmp", "/workspace"],
        denied_paths=["/etc", "/home"],
        operations=["read", "write"]
    ),
    network=NetworkPermission(enabled=False),
    resources=ResourceLimits(
        max_cpu_percent=50.0,
        max_memory_mb=256,
        max_execution_time_seconds=30.0
    )
)

permissions.set_tool_permissions("read_file", file_perms)
```

### 3. Tool Executor

Orchestrates tool execution with error handling, retries, and monitoring.

**Key Features:**
- Async execution support
- Intelligent retry logic
- Execution metrics and monitoring
- Timeout management
- Batch execution

**Example:**
```python
from auto_pilot.tools import ToolExecutor
from auto_pilot.tools.types import ExecutionContext

executor = ToolExecutor(
    registry=registry,
    permission_manager=permissions,
)

# Register implementation
executor.register_tool_implementation("read_file", read_file_func)

# Execute
context = ExecutionContext(task_id="task_123")
result = await executor.execute(
    tool_name="read_file",
    arguments={"path": "/tmp/file.txt"},
    context=context
)

if result.success:
    print(f"Result: {result.result}")
else:
    print(f"Error: {result.error}")
```

### 4. Tool Sandbox

Isolated execution environment with resource monitoring and output sanitization.

**Key Features:**
- Process-based isolation
- Resource usage monitoring
- Output sanitization
- Timeout enforcement
- Security enforcement

**Example:**
```python
from auto_pilot.tools import ToolSandbox
from auto_pilot.tools.types import SandboxConfig

sandbox = ToolSandbox()

result = await sandbox.execute(
    tool=tool_definition,
    implementation=tool_impl,
    arguments={"path": "/tmp/file.txt"},
    timeout=30.0
)
```

## Complete Example

```python
import asyncio
from auto_pilot.tools import create_tool_system

async def main():
    # Create complete system
    tool_system = create_tool_system()

    registry = tool_system["registry"]
    permissions = tool_system["permissions"]
    executor = tool_system["executor"]

    # Define and register tool
    tool = ToolDefinition(
        metadata=ToolMetadata(
            name="greet",
            description="Greet someone",
            version="1.0.0",
        ),
        parameters={
            "type": "object",
            "properties": {
                "name": {"type": "string"}
            },
        }
    )

    registry.register_tool(tool)

    # Define implementation
    def greet(name: str) -> str:
        return f"Hello, {name}!"

    executor.register_tool_implementation("greet", greet)

    # Execute
    result = await executor.execute(
        tool_name="greet",
        arguments={"name": "World"}
    )

    print(result.result)  # "Hello, World!"

asyncio.run(main())
```

## Component Integration

The components work together in the following flow:

```
User Request → Tool Registry → Permission Check → Sandbox Setup → Tool Execution → Result
                                      ↓                ↓              ↓
                               Permission Manager  Tool Sandbox  Executor
```

### Data Flow:

1. **Tool Registration**: Tools are registered with metadata and schemas
2. **Permission Assignment**: Permissions are configured for each tool
3. **Execution Request**: User requests tool execution
4. **Permission Validation**: Permissions are checked
5. **Sandbox Setup**: Execution environment is prepared
6. **Tool Execution**: Tool runs in sandboxed environment
7. **Result Processing**: Results are sanitized and returned
8. **Audit Logging**: Execution is logged for monitoring

## Error Handling and Retries

The executor includes intelligent retry logic:

```python
result = await executor.execute(
    tool_name="network_request",
    arguments={"url": "https://api.example.com"},
    retry_config={
        "max_retries": 3,
        "retry_delay": 1.0,
    }
)
```

Retryable errors:
- Timeout errors
- Network errors
- Temporary failures

Non-retryable errors:
- Permission denied
- Validation errors
- Schema errors

## Monitoring and Metrics

The executor collects execution metrics:

```python
metrics = executor.get_execution_metrics()

# Returns:
# {
#     "total_executions": 100,
#     "successful_executions": 95,
#     "failed_executions": 5,
#     "success_rate": 0.95,
#     "average_execution_time_ms": 123.5
# }
```

## Security Features

### 1. Access Control
- Whitelist-based filesystem access
- Network access controls
- Resource usage limits

### 2. Sandbox Isolation
- Process-based isolation
- Restricted environment variables
- Limited system calls

### 3. Output Sanitization
- Automatic PII removal
- Sensitive data redaction
- Configurable sanitization patterns

### 4. Audit Logging
- Complete execution history
- Permission checks logged
- Security events tracked

## Migration from Legacy ToolExecutor

The new architecture provides backward compatibility:

```python
# Old way (still works)
from auto_pilot.execution.tool_executor import ToolExecutor

# New way (recommended)
from auto_pilot.tools import ToolExecutor, create_tool_system
```

### Migration Steps:

1. Replace direct ToolExecutor imports with the new module
2. Register tools in the ToolRegistry instead of directly in executor
3. Optionally configure permissions for enhanced security
4. Update to new result format if needed

## Best Practices

### 1. Tool Design
- Use descriptive names and categories
- Provide comprehensive schema definitions
- Add proper metadata
- Tag tools appropriately

### 2. Security
- Define minimal required permissions
- Use whitelist approach for resources
- Enable sandboxing for untrusted tools
- Audit tool execution regularly

### 3. Performance
- Set appropriate timeouts
- Monitor resource usage
- Use batch execution for multiple tools
- Cache frequently used tool definitions

### 4. Error Handling
- Handle execution failures gracefully
- Use retry logic for transient errors
- Log errors for debugging
- Provide clear error messages

## Testing

Run the integration example:

```bash
uv run python examples/tools_integration.py
```

Run tests:

```bash
uv run pytest tests/test_tools/
```

## Future Enhancements

Planned improvements:
- Container-based sandboxing
- Distributed tool execution
- Tool marketplace integration
- Advanced monitoring dashboards
- Machine learning for error prediction

## API Reference

See the inline documentation in the source files:
- `src/auto_pilot/tools/registry/`
- `src/auto_pilot/tools/permissions/`
- `src/auto_pilot/tools/executor/`
- `src/auto_pilot/tools/sandbox/`
