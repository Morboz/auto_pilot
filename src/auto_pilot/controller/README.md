# Controller Module

This module provides REST API and WebSocket interfaces for managing and monitoring agent task executions in the auto_pilot framework.

## Overview

The Controller module serves as the external interface for:
- Starting, pausing, resuming, and stopping tasks
- Querying task status and history
- Real-time event streaming via WebSocket

## API Endpoints

### REST API

#### Start Task
```http
POST /agents/{agent_id}/tasks
Content-Type: application/json

{
  "input": "Analyze the sales data and create a summary",
  "agent_id": "agent-123",
  "config": {
    "max_steps": 50,
    "max_retries": 3
  }
}
```

Response:
```json
{
  "task_id": "uuid-string",
  "status": "started",
  "message": "Task started successfully"
}
```

#### Get Task Status
```http
GET /tasks/{task_id}
```

Response:
```json
{
  "task_id": "uuid-string",
  "status": "running",
  "user_input": "Analyze the sales data...",
  "current_step": 5,
  "max_steps": 50,
  "final_output": null,
  "error": null,
  "created_at": "2024-01-01T12:00:00",
  "updated_at": "2024-01-01T12:05:00",
  "steps": [...],
  "tool_calls": [...]
}
```

#### Pause Task
```http
POST /tasks/{task_id}/pause
```

Response:
```json
{
  "success": true,
  "message": "Task paused"
}
```

#### Resume Task
```http
POST /tasks/{task_id}/resume
```

Response:
```json
{
  "success": true,
  "message": "Task resumed"
}
```

#### Stop Task
```http
POST /tasks/{task_id}/stop
```

Response:
```json
{
  "success": true,
  "message": "Task stopped"
}
```

### WebSocket

Connect to WebSocket for real-time event streaming:

```javascript
const ws = new WebSocket('ws://localhost:8000/tasks/{task_id}/stream');

ws.onmessage = (event) => {
  const message = JSON.parse(event.data);
  console.log('Event:', message.event);
  console.log('Data:', message.data);
};

// Send periodic pings to keep connection alive
setInterval(() => {
  ws.send('ping');
}, 30000);
```

#### WebSocket Events

**step_started**
```json
{
  "event": "step_started",
  "task_id": "uuid-string",
  "data": { "step": 5 },
  "timestamp": "2024-01-01T12:05:00"
}
```

**llm_response**
```json
{
  "event": "llm_response",
  "task_id": "uuid-string",
  "data": { "content": "I will analyze the data..." },
  "timestamp": "2024-01-01T12:05:00"
}
```

**tool_call_started**
```json
{
  "event": "tool_call_started",
  "task_id": "uuid-string",
  "data": {
    "tool_name": "read_file",
    "arguments": { "filepath": "sales.csv" }
  },
  "timestamp": "2024-01-01T12:05:00"
}
```

**tool_result**
```json
{
  "event": "tool_result",
  "task_id": "uuid-string",
  "data": {
    "tool_name": "read_file",
    "result": "CSV content..."
  },
  "timestamp": "2024-01-01T12:05:00"
}
```

**finished**
```json
{
  "event": "finished",
  "task_id": "uuid-string",
  "data": {
    "final_output": "Analysis complete. Summary: ..."
  },
  "timestamp": "2024-01-01T12:10:00"
}
```

**error**
```json
{
  "event": "error",
  "task_id": "uuid-string",
  "data": {
    "error": "Tool execution failed",
    "error_type": "ToolError",
    "step": 5
  },
  "timestamp": "2024-01-01T12:05:00"
}
```

## Usage Example

```python
from fastapi import FastAPI
from auto_pilot.controller import create_app
from auto_pilot.llm import create_adapter_for_model
from auto_pilot.execution import StateManager

# Create LLM adapter
llm = create_adapter_for_model(
    model="claude-3",
    api_key="your-api-key"
)

# Create optional state manager
state_manager = StateManager()

# Create FastAPI app
app = create_app(
    llm_adapter=llm,
    state_manager=state_manager,
    cors_origins=["http://localhost:3000"]  # Your frontend URL
)

# Run with uvicorn
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
```

## Architecture

```
┌─────────────┐
│   Client    │
└──────┬──────┘
       │ HTTP/WebSocket
       ▼
┌──────────────────┐
│  FastAPI App     │
│  - REST Routes   │
│  - WebSocket     │
└──────┬───────────┘
       │
       ▼
┌──────────────────┐
│ TaskController   │
│ - Start/Pause    │
│ - Resume/Stop    │
│ - Get Status     │
│ - Stream Events  │
└──────┬───────────┘
       │
       ▼
┌──────────────────┐
│  AgentExecutor   │
│  - Plan → Act    │
│  - Observe       │
│  - Re-plan       │
└──────────────────┘
```

## Features

### ✅ Implemented

- **Task Management**: Start, pause, resume, stop tasks
- **Status Monitoring**: Real-time task status and history
- **Event Streaming**: WebSocket-based real-time updates
- **RESTful API**: Standard REST endpoints
- **CORS Support**: Configurable cross-origin support
- **Error Handling**: Comprehensive error responses
- **WebSocket Management**: Automatic connection cleanup

### 🔄 Extensible

- **Authentication**: Can add API key/JWT auth
- **Rate Limiting**: Can add rate limiting middleware
- **Database Persistence**: StateManager can be extended
- **Multi-Agent Support**: Controller supports multiple agents

## Testing

Run tests with:

```bash
uv run pytest tests/test_controller/ -v
```

## Integration

The Controller integrates with:
- ✅ **AgentExecutor** - Core execution engine
- ✅ **StateManager** - Persistent state
- ✅ **LLM Adapter** - Language model interface
- ✅ **Tool Registry** - Tool execution (future)

## Production Deployment

### Using Uvicorn

```bash
uvicorn auto_pilot.controller.app:create_app \
    --host 0.0.0.0 \
    --port 8000 \
    --reload
```

### Using Docker

```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY . .

RUN pip install -r requirements.txt

EXPOSE 8000

CMD ["uvicorn", "auto_pilot.controller.app:create_app", "--host", "0.0.0.0", "--port", "8000"]
```

## Environment Variables

- `API_KEY`: Optional API key for authentication
- `CORS_ORIGINS`: Comma-separated list of allowed origins
- `LOG_LEVEL`: Logging level (DEBUG, INFO, WARNING, ERROR)

## Future Enhancements

1. **Authentication**: Add API key or JWT authentication
2. **Rate Limiting**: Add request rate limiting
3. **Metrics**: Add Prometheus metrics endpoint
4. **Task Queue**: Add task queue with Celery/Redis
5. **Load Balancing**: Support multiple executor instances
6. **Database Integration**: PostgreSQL/Redis persistence
