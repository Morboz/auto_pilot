"""Example demonstrating the built-in tools system.

This example shows how the built-in tools are automatically loaded
at startup and how to use them through the tool executor.
"""

import asyncio

from auto_pilot.tools import create_tool_system
from auto_pilot.tools.builtin import BuiltinToolLoader


async def main():
    """Demonstrate built-in tools usage."""
    print("=" * 80)
    print("Built-in Tools System Demo")
    print("=" * 80)

    # Step 1: Create tool system
    print("\n1. Creating tool system...")
    tool_system = create_tool_system()
    registry = tool_system["registry"]
    executor = tool_system["executor"]
    print("✓ Tool system created")

    # Step 2: Load built-in tools
    print("\n2. Loading built-in tools...")
    loader = BuiltinToolLoader(registry=registry, executor=executor)
    tool_count = loader.load_builtin_tools()
    print(f"✓ Loaded {tool_count} built-in tools:")
    for tool_name in loader.get_loaded_tools():
        print(f"   - {tool_name}")

    # Step 3: List all available tools
    print("\n3. Available tools:")
    for tool_name, tool_def in registry._tools.items():
        print(f"\n   Tool: {tool_name}")
        print(f"   Description: {tool_def.description}")
        print(f"   Category: {tool_def.metadata.category or 'N/A'}")

    # Step 4: Execute calculator tool
    print("\n" + "=" * 80)
    print("4. Testing Calculator Tool")
    print("=" * 80)

    result = await executor.execute(
        tool_name="calculator",
        arguments={"expression": "2 + 2 * 10"},
    )

    print("\nExpression: 2 + 2 * 10")
    print(f"Result: {result.result}")
    print(f"Success: {result.success}")
    print(f"Execution time: {result.execution_time_ms:.2f}ms")

    # Step 5: Execute file operations (demonstrative - would need real file)
    print("\n" + "=" * 80)
    print("5. Testing File Write Tool")
    print("=" * 80)

    result = await executor.execute(
        tool_name="file_write",
        arguments={
            "file_path": "/tmp/test_autopilot.txt",
            "content": "Hello from AutoPilot built-in tools!",
            "create_dirs": True,
        },
    )

    print("\nFile write result:")
    print(f"Success: {result.success}")
    if result.success:
        print(f"Path: {result.result.get('path')}")
        print(f"Bytes written: {result.result.get('bytes_written')}")
    else:
        print(f"Error: {result.error}")

    # Step 6: Read the file back
    print("\n" + "=" * 80)
    print("6. Testing File Read Tool")
    print("=" * 80)

    result = await executor.execute(
        tool_name="file_read",
        arguments={"file_path": "/tmp/test_autopilot.txt"},
    )

    print("\nFile read result:")
    print(f"Success: {result.success}")
    if result.success:
        print(f"Content: {result.result.get('content')}")
        print(f"Size: {result.result.get('size')} bytes")
    else:
        print(f"Error: {result.error}")

    # Step 7: Test HTTP GET (example with a public API)
    print("\n" + "=" * 80)
    print("7. Testing HTTP GET Tool")
    print("=" * 80)

    result = await executor.execute(
        tool_name="http_get",
        arguments={
            "url": "https://api.github.com/repos/python/cpython",
            "timeout": 10,
        },
    )

    print("\nHTTP GET result:")
    print(f"Success: {result.success}")
    if result.success:
        print(f"Status code: {result.result.get('status_code')}")
        content = result.result.get("content", "")
        print(f"Content length: {len(content)} bytes")
        print(f"Content preview: {content[:100]}...")
    else:
        print(f"Error: {result.error}")

    # Step 8: Get execution metrics
    print("\n" + "=" * 80)
    print("8. Execution Metrics")
    print("=" * 80)

    metrics = executor.get_execution_metrics()
    if metrics:
        print("\nMetrics summary:")
        print(f"Total Executions: {metrics.get('total_executions', 0)}")
        print(f"Successful: {metrics.get('successful_executions', 0)}")
        print(f"Failed: {metrics.get('failed_executions', 0)}")
        print(f"Success Rate: {metrics.get('success_rate', 0):.1%}")
        print(
            f"Avg Execution Time: "
            f"{metrics.get('average_execution_time_ms', 0):.2f}ms"
        )

    print("\n" + "=" * 80)
    print("Demo completed!")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(main())
