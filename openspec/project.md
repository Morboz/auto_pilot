# Project Context

## Purpose
The auto_pilot project is a backend service for an AI Agent framework similar to Claude Code. It provides a comprehensive system for executing autonomous AI agents through a Plan-Act-Observe loop, with support for:

- **Agent Runtime Service**: Manages the execution lifecycle of AI agents with LLM integration
- **Tool Registry System**: Provides a plugin-based tool architecture for extensibility
- **Workspace Storage**: Isolated filesystem environments per agent
- **Web UI Integration**: Real-time dashboard and interaction layer
- **Audit & Logging**: Complete event tracking and audit trails

The goal is to create a production-ready, extensible framework for building autonomous AI agents that can perform complex tasks through tool execution.

## Tech Stack
- **Python 3.11+**: Primary language (minimum version 3.11)
- **FastAPI**: Web framework for RESTful APIs and WebSocket support
- **Ruff**: Linting and formatting tool
- **pytest**: Testing framework with coverage support
- **pytest-cov**: Coverage plugin for pytest
- **pre-commit**: Git hooks for code quality enforcement
- **hatchling**: Build system for Python packaging
- **WebSocket**: Real-time communication for UI updates
- **LLM Providers**: OpenAI, Claude, and local LLM support

## Project Conventions

### Code Style
- **Linting**: Ruff with rules E (errors), W (warnings), F (flakes), I (isort)
- **Line Length**: 88 characters
- **Formatting**: Ruff-format with double quotes, space indentation
- **Import Sorting**: isort with `auto_pilot` as a known first-party module
- **Line Endings**: Auto-detect (cross-platform support)
- **Magic Trailing Comma**: Disabled
- **Pre-commit Hooks**: Automatically fix linting issues before commit
- **Naming Conventions**: Follow PEP 8 standards enforced by Ruff

### Architecture Patterns
Based on the component architecture in `arch-spec.md`:

1. **Microservices Architecture**:
   - API Gateway (REST + WebSocket)
   - Agent Runtime Service (core execution engine)
   - Tool Registry Service (plugin management)
   - Workspace Storage Service (isolated filesystem)
   - Event/Audit Log Store

2. **Agent Execution Loop**:
   ```
   Plan → Act → Observe → (repeat)
   ```
   - LLM generates plans
   - Tool execution with schema validation
   - Result observation and feedback
   - Iteration until completion

3. **Tool System**:
   - Registry-based plugin architecture
   - Schema validation for all tool inputs
   - Sandbox execution environment
   - Permission system for tool restrictions

4. **Workspace Isolation**:
   - Per-agent filesystem sandbox
   - Allowed paths whitelist
   - Versioning and snapshots support

### Testing Strategy
- **Test Framework**: pytest with strict marker enforcement
- **Test Structure**:
  - Location: `tests/` directory
  - Pattern: `test_*.py` and `*_test.py` files
  - Functions: `test_*` prefix
  - Classes: `Test*` prefix
- **Coverage**: pytest-cov for measuring test coverage
- **Options**: `-ra -q --strict-markers` for detailed output
- **Quality Gates**: All tests must pass, coverage tracked
- **Version Testing**: Dedicated test for package version verification

### Git Workflow
- **Pre-commit Hooks**:
  - Ruff linting and formatting (auto-fix enabled)
  - Trailing whitespace removal
  - End-of-file fixer
  - YAML validation
  - Large file detection
  - Merge conflict detection
- **Automated Formatting**: All code auto-formatted via pre-commit
- **Branch Strategy**: Standard git workflow (specific strategy not yet defined)
- **Commit Standards**: Code quality enforced via automated hooks

## Domain Context
This is an **AI Agent Execution Framework** that enables:

- **Autonomous Task Execution**: Agents can independently plan and execute complex tasks
- **Tool Plugin Architecture**: Extensible system where tools can be registered and invoked
- **Sandboxed Execution**: Safe execution environment with path restrictions and permissions
- **Real-time Monitoring**: WebSocket-based live updates of agent execution
- **LLM Integration**: Support for multiple LLM providers (OpenAI, Claude, local)
- **Workspace Management**: Isolated file systems for each agent instance
- **Complete Audit Trail**: All agent actions, tool calls, and decisions logged

Key concepts:
- **Agent**: An autonomous entity that executes tasks through the Plan-Act-Observe loop
- **Tool**: A callable function with schema validation, executed in a sandbox
- **Plan**: LLM-generated step-by-step instructions for task completion
- **Workspace**: Isolated filesystem where agents can read/write files
- **Runtime**: The core execution engine managing agent lifecycle

## Important Constraints
1. **Security**:
   - All tool executions must be sandboxed
   - Workspace paths must be restricted via whitelist
   - Tool permissions must be enforced
   - All actions logged for audit

2. **Isolation**:
   - Each agent operates in isolated workspace
   - Tool executions cannot escape sandbox
   - Resource usage monitoring required

3. **Reliability**:
   - Tool execution must have timeout protection
   - Error handling and retry logic required
   - Graceful degradation on failures

4. **Scalability**:
   - Support multiple concurrent agents
   - WebSocket connections for real-time updates
   - Efficient workspace management

5. **Extensibility**:
   - Plugin-based tool registry
   - Multiple LLM provider support
   - Modular architecture for new features

## External Dependencies
1. **LLM Providers**:
   - OpenAI API
   - Anthropic Claude API
   - Local LLM support via API

2. **Build & Dev Tools**:
   - hatchling (Python build backend)
   - ruff (linting and formatting)
   - pre-commit hooks

3. **Testing Framework**:
   - pytest (test framework)
   - pytest-cov (coverage reporting)

4. **Future Dependencies** (based on arch-spec.md):
   - WebSocket server for real-time communication
   - File system monitoring for workspace events
   - Database for audit logs and event storage
   - Containerization for tool sandbox (optional)
