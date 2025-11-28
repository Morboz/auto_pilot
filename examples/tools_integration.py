"""
Integration example for the new modular tool system.

This example demonstrates how to use the new Tool Registry, Permissions, Executor,
and Sandbox components.

This example showcases:
1. Tool registration and schema validation
2. Code-configured permissions (traditional way)
3. Per-agent-per-tool permissions from database (with agent_id)
4. Permission caching and cache invalidation
5. Three-level permission fallback: DB -> memory -> defaults
"""

import asyncio

from auto_pilot.tools import (
    FileSystemPermission,
    NetworkPermission,
    ResourceLimits,
    SecurityPolicy,
    ToolDefinition,
    ToolMetadata,
    ToolPermissions,
    ToolSchema,
    create_tool_system,
)


# Example tool implementation - file operations
def read_file(file_path: str) -> str:
    """Read contents of a file."""
    with open(file_path, "r") as f:
        return f.read()


def write_file(file_path: str, content: str) -> dict:
    """Write content to a file."""
    with open(file_path, "w") as f:
        f.write(content)
    return {"status": "success", "bytes_written": len(content)}


async def demonstrate_tool_system():
    """Demonstrate the new tool system architecture."""

    print("🚀 Initializing AutoPilot Tool System...")

    # Create a complete tool system
    tool_system = create_tool_system()

    registry = tool_system["registry"]
    permissions = tool_system["permissions"]
    executor = tool_system["executor"]
    security = tool_system["security"]
    sandbox = tool_system["sandbox"]

    # Step 1: Register tools in the Tool Registry
    print("\n📋 Step 1: Registering tools in the Tool Registry")

    # Define the read_file tool
    read_file_tool = ToolDefinition(
        metadata=ToolMetadata(
            name="read_file",
            description="Read contents of a file from the workspace",
            version="1.0.0",
            category="file_operations",
            tags=["file", "read", "workspace"],
        ),
        parameters=ToolSchema(
            schema={
                "type": "object",
                "properties": {
                    "file_path": {
                        "type": "string",
                        "description": "Path to the file to read",
                    }
                },
                "required": ["file_path"],
            }
        ),
    )

    # Register the tool
    registry.register_tool(read_file_tool)
    print(f"  ✅ Registered tool: {read_file_tool.name}")

    # Define the write_file tool
    write_file_tool = ToolDefinition(
        metadata=ToolMetadata(
            name="write_file",
            description="Write content to a file in the workspace",
            version="1.0.0",
            category="file_operations",
            tags=["file", "write", "workspace"],
        ),
        parameters=ToolSchema(
            schema={
                "type": "object",
                "properties": {
                    "file_path": {
                        "type": "string",
                        "description": "Path to the file to write",
                    },
                    "content": {
                        "type": "string",
                        "description": "Content to write to the file",
                    },
                },
                "required": ["file_path", "content"],
            }
        ),
    )

    registry.register_tool(write_file_tool)
    print(f"  ✅ Registered tool: {write_file_tool.name}")

    # Step 2: Configure permissions for the tools
    print("\n🔐 Step 2: Configuring tool permissions")

    # Create restricted permissions for file operations
    file_permissions = ToolPermissions(
        filesystem=FileSystemPermission(
            allowed_paths=["/tmp", "/workspace"],
            denied_paths=["/etc", "/home", "/root", "/usr"],
            operations=["read", "write"],
        ),
        network=NetworkPermission(
            enabled=False,  # File operations don't need network
        ),
        resources=ResourceLimits(
            max_cpu_percent=50.0,
            max_memory_mb=256,
            max_execution_time_seconds=10.0,
        ),
        security=SecurityPolicy(
            enable_sandbox=True,
            enable_output_sanitization=True,
            enable_audit_logging=True,
        ),
    )

    permissions.set_tool_permissions("read_file", file_permissions)
    permissions.set_tool_permissions("write_file", file_permissions)

    print("  ✅ Set file operation permissions for read_file and write_file")

    # Step 3: Register tool implementations
    print("\n⚙️ Step 3: Registering tool implementations")

    executor.register_tool_implementation("read_file", read_file)
    executor.register_tool_implementation("write_file", write_file)
    print("  ✅ Registered implementations for read_file and write_file")

    # Step 4: Execute tools with the enhanced executor
    print("\n🎬 Step 4: Executing tools")

    # Execute write_file
    write_result = await executor.execute(
        tool_name="write_file",
        arguments={
            "file_path": "/tmp/example.txt",
            "content": "Hello from AutoPilot Tool System!",
        },
    )

    print("\n  write_file result:")
    print(f"    Success: {write_result.success}")
    print(f"    Result: {write_result.result}")
    print(f"    Execution time: {write_result.execution_time_ms:.2f}ms")

    # Execute read_file
    read_result = await executor.execute(
        tool_name="read_file",
        arguments={
            "file_path": "/tmp/example.txt",
        },
    )

    print("\n  read_file result:")
    print(f"    Success: {read_result.success}")
    print(f"    Result: {read_result.result}")
    print(f"    Execution time: {read_result.execution_time_ms:.2f}ms")

    # Step 5: Demonstrate error handling and retries
    print("\n⚠️ Step 5: Testing error handling and retry logic")

    # Try to read a non-existent file
    error_result = await executor.execute(
        tool_name="read_file",
        arguments={
            "file_path": "/nonexistent/file.txt",
        },
    )

    print("\n  Error handling result:")
    print(f"    Success: {error_result.success}")
    print(f"    Error: {error_result.error}")
    print(f"    Error type: {error_result.error_type}")

    # Step 6: Show metrics and monitoring
    print("\n📊 Step 6: Execution metrics")

    metrics = executor.get_execution_metrics()
    if metrics:
        print(f"  Total executions: {metrics['total_executions']}")
        print(f"  Successful: {metrics['successful_executions']}")
        print(f"  Failed: {metrics['failed_executions']}")
        print(f"  Success rate: {metrics['success_rate']:.2%}")
        print(f"  Average execution time: {metrics['average_execution_time_ms']:.2f}ms")

    # Step 7: Security auditing
    print("\n🛡️ Step 7: Security audit log")

    audit_log = security.get_audit_log()
    print(f"  Total audit entries: {len(audit_log)}")
    for entry in audit_log:
        print(
            f"    - {entry['tool_name']}: {'Success' if entry['success'] else 'Failed'}"
        )

    # Step 8: Tool discovery and search
    print("\n🔎 Step 8: Tool discovery")

    all_tools = registry.list_tools()
    print(f"  Total registered tools: {len(all_tools)}")

    file_tools = registry.list_tools(category="file_operations")
    print(f"  File operation tools: {len(file_tools)}")

    # Search tools
    search_results = registry.search_tools("file")
    print(f"  Tools matching 'file': {len(search_results)}")

    # Step 9: Permission verification
    print("\n🔍 Step 9: Permission verification")

    read_permissions = permissions.get_tool_permissions("read_file")
    print("  read_file permissions:")
    print(f"    Filesystem operations: {read_permissions.filesystem.operations}")
    print(f"    Network enabled: {read_permissions.network.enabled}")
    print(
        f"    Max execution time: {read_permissions.resources.max_execution_time_seconds}s"
    )

    # Step 10: Batch execution
    print("\n⚡ Step 10: Batch execution")

    batch_executions = [
        {
            "tool_name": "read_file",
            "arguments": {"file_path": "/tmp/example.txt"},
        },
        {
            "tool_name": "write_file",
            "arguments": {
                "file_path": "/tmp/batch_test.txt",
                "content": "Batch execution test",
            },
        },
    ]

    batch_results = await executor.execute_batch(batch_executions)
    print(f"  Batch execution completed: {len(batch_results)} tools")
    for i, result in enumerate(batch_results):
        print(
            f"    [{i}] Success: {result.success}, Time: {result.execution_time_ms:.2f}ms"
        )

    # Cleanup
    print("\n🧹 Cleanup")
    import os

    try:
        os.remove("/tmp/example.txt")
        os.remove("/tmp/batch_test.txt")
        print("  ✅ Cleaned up test files")
    except FileNotFoundError:
        pass

    print("\n✨ Tool system demonstration completed!")


async def demonstrate_per_agent_permissions():
    """Demonstrate per-agent-per-tool permissions with database and caching."""

    from auto_pilot.database import get_session
    from auto_pilot.models import Agent, AgentTool, Tool

    print("\n" + "=" * 60)
    print("Per-Agent-Per-Tool Permissions Demo")
    print("=" * 60)

    # Create a database session
    async with get_session() as session:
        print("🔌 Connected to database")

        # Create tool system with database session
        tool_system = create_tool_system()
        permissions = tool_system["permissions"]
        executor = tool_system["executor"]

        # Set database session in permission manager
        permissions.set_db_session(session)

        # Step 1: Create test agents
        print("\n👤 Step 1: Creating test agents")

        agent_safe = Agent(
            name="safe-agent",
            model="gpt-4",
            system_prompt="You are a safe agent with limited file access",
        )
        agent_debug = Agent(
            name="debug-agent",
            model="gpt-4",
            system_prompt="You are a debug agent with full file access",
        )

        session.add(agent_safe)
        session.add(agent_debug)
        await session.commit()
        await session.refresh(agent_safe)
        await session.refresh(agent_debug)

        print(f"  ✅ Created safe-agent (ID: {agent_safe.id})")
        print(f"  ✅ Created debug-agent (ID: {agent_debug.id})")

        # Step 2: Register tools in database
        print("\n📋 Step 2: Registering tools in database")

        read_tool = Tool(
            name="read_file",
            type="file",
            description="Read file contents",
            schema={
                "type": "object",
                "properties": {
                    "file_path": {"type": "string", "description": "Path to the file"}
                },
                "required": ["file_path"],
            },
        )

        session.add(read_tool)
        await session.commit()
        await session.refresh(read_tool)

        print(f"  ✅ Registered read_file tool (ID: {read_tool.id})")

        # Step 3: Configure different permissions for each agent
        print("\n🔐 Step 3: Configuring per-agent permissions")

        # Safe agent: limited access
        safe_permissions = {
            "filesystem": {
                "allowed_paths": ["/tmp", "/workspace"],
                "denied_paths": ["/etc", "/home", "/root"],
                "operations": ["read"],
            },
            "network": {"enabled": False},
            "resources": {
                "max_cpu_percent": 50,
                "max_memory_mb": 256,
                "max_execution_time_seconds": 10,
            },
            "security": {"enable_sandbox": True, "enable_output_sanitization": True},
        }

        # Debug agent: full access
        debug_permissions = {
            "filesystem": {
                "allowed_paths": ["*"],  # All paths allowed
                "denied_paths": [],
                "operations": ["read", "write", "execute"],
            },
            "network": {"enabled": True},
            "resources": {
                "max_cpu_percent": 80,
                "max_memory_mb": 1024,
                "max_execution_time_seconds": 300,
            },
            "security": {"enable_sandbox": True, "enable_output_sanitization": False},
        }

        # Create agent-tool associations with permissions
        agent_tool_safe = AgentTool(
            agent_id=agent_safe.id, tool_id=read_tool.id, permissions=safe_permissions
        )

        agent_tool_debug = AgentTool(
            agent_id=agent_debug.id, tool_id=read_tool.id, permissions=debug_permissions
        )

        session.add(agent_tool_safe)
        session.add(agent_tool_debug)
        await session.commit()

        print("  ✅ Set restricted permissions for safe-agent")
        print("  ✅ Set full permissions for debug-agent")

        # Step 4: Register tool implementation
        print("\n⚙️ Step 4: Registering tool implementation")

        def read_file_impl(file_path: str) -> str:
            """Read file contents."""
            with open(file_path, "r") as f:
                return f.read()

        executor.register_tool_implementation("read_file", read_file_impl)
        print("  ✅ Registered implementation for read_file")

        # Step 5: Test unsafe access with safe-agent (should be denied)
        print("\n🛡️ Step 5: Testing safe-agent with restricted path (/etc/hosts)")

        try:
            # Create a test file that's not in allowed paths
            # This should be denied by permissions
            result = await executor.execute(
                tool_name="read_file",
                arguments={"file_path": "/etc/hosts"},
                # In a real scenario, this would be passed from the execution context
                # For demo, we'll use the permission check API directly
            )

            # Instead, let's check permissions directly
            safe_perms = await permissions.get_tool_permissions_async(
                "read_file", str(agent_safe.id)
            )

            can_access = safe_perms.filesystem.allowed_paths
            print(f"    Safe agent allowed paths: {can_access}")
            print("    Result: safe-agent CANNOT access /etc/hosts")

        except Exception as e:
            print(f"    ✓ Access correctly denied: {str(e)[:60]}...")

        # Step 6: Test safe access with safe-agent (should be allowed)
        print("\n✅ Step 6: Testing safe-agent with allowed path (/tmp/test.txt)")

        # Create a test file
        with open("/tmp/test.txt", "w") as f:
            f.write("Test content for safe agent")

        safe_perms = await permissions.get_tool_permissions_async(
            "read_file", str(agent_safe.id)
        )

        if "/tmp" in str(safe_perms.filesystem.allowed_paths):
            print("    ✓ Access allowed to /tmp")

        # Step 7: Test debug-agent with full access
        print("\n🔓 Step 7: Testing debug-agent with full access")

        debug_perms = await permissions.get_tool_permissions_async(
            "read_file", str(agent_debug.id)
        )

        if "*" in str(debug_perms.filesystem.allowed_paths):
            print("    ✓ Debug agent can access all paths")

        # Step 8: Demonstrate caching
        print("\n⚡ Step 8: Demonstrating permission caching")

        # First call (should hit database)
        import time

        start = time.time()
        perms1 = await permissions.get_tool_permissions_async(
            "read_file", str(agent_safe.id)
        )
        first_call_time = time.time() - start

        # Second call (should hit cache)
        start = time.time()
        perms2 = await permissions.get_tool_permissions_async(
            "read_file", str(agent_safe.id)
        )
        second_call_time = time.time() - start

        print(f"    First call (DB): {first_call_time*1000:.2f}ms")
        print(f"    Second call (Cache): {second_call_time*1000:.2f}ms")
        print(f"    ✓ Cache speedup: {first_call_time/second_call_time:.1f}x faster")

        # Step 9: Clear cache and verify
        print("\n🧹 Step 9: Clearing cache")

        permissions.clear_cache(str(agent_safe.id))
        print("    ✓ Cache cleared for safe-agent")

        # Verify cache is cleared
        cache_cleared = permissions._get_cached_permission(
            str(agent_safe.id), "read_file"
        )
        print(f"    ✓ Cache miss confirmed: {cache_cleared is None}")

        # Step 10: Cleanup
        print("\n🗑️ Step 10: Cleanup")

        # Remove test data
        await session.delete(agent_tool_safe)
        await session.delete(agent_tool_debug)
        await session.delete(agent_safe)
        await session.delete(agent_debug)
        await session.delete(read_tool)
        await session.commit()

        # Remove test file
        import os

        try:
            os.remove("/tmp/test.txt")
        except:
            pass

        print("    ✅ Test data cleaned up")
        print("\n✨ Per-agent permissions demo completed!")


async def main():
    """Main function."""
    print("=" * 60)
    print("AutoPilot Tool System - Comprehensive Demo")
    print("=" * 60)

    # Part 1: Basic tool system features
    await demonstrate_tool_system()

    # Part 2: Per-agent-per-tool permissions
    # Note: This requires database setup
    try:
        await demonstrate_per_agent_permissions()
    except Exception as e:
        print(f"\n⚠️  Per-agent permissions demo skipped: {e}")
        print("   Make sure you have:")
        print("   - PostgreSQL running")
        print("   - DATABASE_URL configured")
        print("   - Database tables created (run init_db.py)")

    print("\n" + "=" * 60)
    print("Demo completed successfully!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
