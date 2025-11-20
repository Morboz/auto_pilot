"""示例：使用Claude adapter进行流式响应。

本示例演示如何使用ClaudeAdapter的流式响应功能，
包括基本流式响应和带工具调用的流式响应。
"""

import asyncio
import time
from pathlib import Path

from dotenv import load_dotenv

from auto_pilot.llm.adapters.claude import ClaudeAdapter
from auto_pilot.llm.types import (
    Message,
    StreamOptions,
    StreamParams,
    ToolDefinition,
)

# 加载.env文件中的环境变量
env_path = Path(__file__).parent.parent / ".env"
load_dotenv(env_path)


async def basic_streaming_example():
    """演示基本流式响应."""
    print("=" * 80)
    print("示例 1: 基本流式响应")
    print("=" * 80)

    adapter = ClaudeAdapter()
    print(f"✓ 初始化adapter，base_url: {adapter.base_url}\n")

    messages = [
        Message(
            role="user",
            content="请讲一个关于机器人的简短故事，边讲边输出，让我看到流式效果。",
        )
    ]

    print(f"👤 用户: {messages[0].content}\n")
    print("💬 Claude (流式输出):\n")

    # 使用流式参数
    stream_params = StreamParams(
        max_tokens=500,
        temperature=0.8,
    )

    # 流式选项：包含使用统计
    stream_options = StreamOptions(
        include_usage=True,
    )

    try:
        start_time = time.time()

        # 收集所有流式块
        full_content = ""
        async for chunk in adapter.stream(
            model="claude-3-5-sonnet-20241022",  # 或使用 "MiniMax-M2" 用于MiniMax
            messages=messages,
            params=stream_params,
            options=stream_options,
        ):
            if chunk.type == "text":
                if isinstance(chunk.content, str):
                    # 实时输出文本块
                    print(chunk.content, end="", flush=True)
                    full_content += chunk.content
                elif isinstance(chunk.content, dict) and "usage" in chunk.content:
                    # 显示使用统计
                    print("\n\n📊 流式响应完成！")
                    usage = chunk.content["usage"]
                    print(f"   输入tokens: {usage['input_tokens']}")
                    print(f"   输出tokens: {usage['output_tokens']}")

            elif chunk.type == "error":
                print(f"\n\n✗ 流式错误: {chunk.content}")

        elapsed_time = time.time() - start_time
        print(f"\n\n⏱ 总耗时: {elapsed_time:.2f}秒")
        print(f"✓ 完整响应长度: {len(full_content)} 字符")

    except Exception as e:
        print(f"\n✗ 错误: {e}")
        import traceback

        traceback.print_exc()

    finally:
        await adapter.close()
        print("\n✓ 适配器已关闭\n")


async def streaming_with_tools_example():
    """演示带工具调用的流式响应."""
    print("\n" + "=" * 80)
    print("示例 2: 流式响应 + 工具调用")
    print("=" * 80)

    adapter = ClaudeAdapter()
    print("✓ 初始化adapter\n")

    # 定义工具
    tools = [
        ToolDefinition(
            name="get_weather",
            description="获取指定城市的天气信息",
            parameters={
                "type": "object",
                "properties": {
                    "location": {
                        "type": "string",
                        "description": "城市名称，例如：北京、上海",
                    },
                    "unit": {
                        "type": "string",
                        "description": "温度单位，C或F",
                        "enum": ["C", "F"],
                    },
                },
                "required": ["location"],
            },
        ),
        ToolDefinition(
            name="calculate",
            description="执行数学计算",
            parameters={
                "type": "object",
                "properties": {
                    "expression": {
                        "type": "string",
                        "description": "数学表达式，例如：2 + 2 * 3",
                    }
                },
                "required": ["expression"],
            },
        ),
    ]

    messages = [
        Message(
            role="user",
            content="请帮我计算一下 15 * 23 + 7 的结果，然后告诉我北京的天气怎么样？",
        )
    ]

    print(f"👤 用户: {messages[0].content}\n")
    print("💬 Claude (流式输出):\n")

    stream_params = StreamParams(
        max_tokens=1000,
        temperature=0.7,
    )

    try:
        start_time = time.time()
        tool_calls_detected = []

        async for chunk in adapter.stream_with_tools(
            model="claude-3-5-sonnet-20241022",
            messages=messages,
            tools=tools,
            params=stream_params,
        ):
            if chunk.type == "text":
                if isinstance(chunk.content, str):
                    print(chunk.content, end="", flush=True)
                elif isinstance(chunk.content, dict) and "usage" in chunk.content:
                    print("\n\n📊 流式响应完成！")
                    usage = chunk.content["usage"]
                    print(f"   输入tokens: {usage['input_tokens']}")
                    print(f"   输出tokens: {usage['output_tokens']}")

            elif chunk.type == "tool_call":
                tool_calls_detected.append(chunk.content)
                print(f"\n\n🔧 [检测到工具调用] {chunk.content}\n")

        elapsed_time = time.time() - start_time

        # 如果有工具调用，模拟执行
        if tool_calls_detected:
            print("\n" + "=" * 80)
            print("工具执行模拟")
            print("=" * 80)

            for tool_call in tool_calls_detected:
                tool_name = tool_call.get("name")
                arguments = tool_call.get("arguments", {})

                print(f"\n🔧 执行工具: {tool_name}")
                print(f"   参数: {arguments}")

                # 模拟工具执行结果
                if tool_name == "calculate":
                    expression = arguments.get("expression", "")
                    try:
                        # 安全计算（仅限演示）
                        result = eval(expression)
                        print(f"   结果: {result}")
                    except:
                        print("   结果: 计算错误")
                elif tool_name == "get_weather":
                    location = arguments.get("location", "未知")
                    print(f"   结果: {location}的天气：晴朗，25°C")

        print(f"\n⏱ 总耗时: {elapsed_time:.2f}秒")

    except Exception as e:
        print(f"\n✗ 错误: {e}")
        import traceback

        traceback.print_exc()

    finally:
        await adapter.close()
        print("\n✓ 适配器已关闭\n")


async def conversation_streaming_example():
    """演示多轮对话中的流式响应."""
    print("\n" + "=" * 80)
    print("示例 3: 多轮对话中的流式响应")
    print("=" * 80)

    adapter = ClaudeAdapter()
    print("✓ 初始化adapter\n")

    conversation_history = []

    questions = [
        "你好，请用一句话介绍一下你自己。",
        "你能帮我写一个Python函数来计算斐波那契数列吗？",
        "这个函数的时间复杂度是多少？如何优化？",
    ]

    for i, question in enumerate(questions, 1):
        print(f"\n{'=' * 80}")
        print(f"第 {i} 轮对话")
        print("=" * 80)

        user_message = Message(role="user", content=question)
        print(f"👤 用户: {question}\n")
        print("💬 Claude (流式输出):\n")

        # 添加到对话历史
        conversation_history.append(user_message)

        stream_params = StreamParams(
            max_tokens=400,
            temperature=0.7,
        )

        try:
            start_time = time.time()
            response_content = ""

            async for chunk in adapter.stream(
                model="claude-3-5-sonnet-20241022",
                messages=conversation_history,
                params=stream_params,
            ):
                if chunk.type == "text" and isinstance(chunk.content, str):
                    print(chunk.content, end="", flush=True)
                    response_content += chunk.content

            elapsed_time = time.time() - start_time

            # 添加助手回复到对话历史
            assistant_message = Message(role="assistant", content=response_content)
            conversation_history.append(assistant_message)

            print(f"\n\n⏱ 本轮耗时: {elapsed_time:.2f}秒")

        except Exception as e:
            print(f"\n✗ 错误: {e}")
            break

    print("\n" + "=" * 80)
    print("对话总结")
    print("=" * 80)
    print(f"✓ 总轮数: {len(questions)}")
    print(f"✓ 总消息数: {len(conversation_history)}")
    print("✓ 对话保持了上下文连贯性")

    await adapter.close()
    print("\n✓ 适配器已关闭\n")


async def main():
    """运行所有流式响应示例."""
    try:
        # 示例 1: 基本流式响应
        await basic_streaming_example()

        # 等待一秒
        await asyncio.sleep(1)

        # 示例 2: 流式响应 + 工具调用
        await streaming_with_tools_example()

        # 等待一秒
        await asyncio.sleep(1)

        # 示例 3: 多轮对话中的流式响应
        await conversation_streaming_example()

    except Exception as e:
        print(f"\n✗ 整体错误: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    print("🚀 开始运行流式响应示例\n")
    asyncio.run(main())
    print("\n✅ 所有示例运行完成！")
