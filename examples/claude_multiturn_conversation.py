"""示例：使用Claude adapter进行多轮对话。

本示例演示如何使用ClaudeAdapter与支持Anthropic API的提供商（如MiniMax）
进行连续的多轮对话，保持对话上下文。
"""

import asyncio
from pathlib import Path

from dotenv import load_dotenv

from auto_pilot.llm.adapters.claude import ClaudeAdapter
from auto_pilot.llm.types import GenerationParams, Message

# 加载.env文件中的环境变量
env_path = Path(__file__).parent.parent / ".env"
load_dotenv(env_path)


async def main():
    """测试ClaudeAdapter多轮对话功能."""

    # 方法1：使用环境变量（推荐）
    # 在.env文件中设置 ANTHROPIC_BASE_URL 和 ANTHROPIC_API_KEY
    adapter = ClaudeAdapter()

    # 方法2：直接传递参数
    # adapter = ClaudeAdapter(
    #     api_key="your-api-key",
    #     base_url="https://api.minimaxi.com/anthropic"
    # )

    print(f"✓ 初始化adapter，base_url: {adapter.base_url}\n")

    # 初始化对话历史
    conversation_history = []

    # 第一轮：用户介绍自己
    print("=" * 60)
    print("第1轮对话")
    print("=" * 60)

    user_message_1 = Message(role="user", content="你好！我的名字是张三，我是一名软件工程师。")
    print(f"👤 用户: {user_message_1.content}")

    conversation_history.append(user_message_1)

    params = GenerationParams(
        max_tokens=500,
        temperature=0.7,
    )

    try:
        response_1 = await adapter.generate(
            model="claude-3-5-sonnet-20241022",  # 或使用 "MiniMax-M2" 用于MiniMax
            messages=conversation_history,
            params=params,
        )

        print(f"\n💬 Claude: {response_1.content}")
        print(f"📊 使用情况: {response_1.usage}")

        # 将助手的回复添加到对话历史
        assistant_message_1 = Message(role="assistant", content=response_1.content)
        conversation_history.append(assistant_message_1)

        # 第二轮：询问个人信息
        print("\n" + "=" * 60)
        print("第2轮对话")
        print("=" * 60)

        user_message_2 = Message(role="user", content="我很喜欢编程，你知道我喜欢什么编程语言吗？")
        print(f"👤 用户: {user_message_2.content}")

        conversation_history.append(user_message_2)

        response_2 = await adapter.generate(
            model="claude-3-5-sonnet-20241022",
            messages=conversation_history,
            params=params,
        )

        print(f"\n💬 Claude: {response_2.content}")
        print(f"📊 使用情况: {response_2.usage}")

        assistant_message_2 = Message(role="assistant", content=response_2.content)
        conversation_history.append(assistant_message_2)

        # 第三轮：基于之前的对话继续
        print("\n" + "=" * 60)
        print("第3轮对话")
        print("=" * 60)

        user_message_3 = Message(
            role="user",
            content="是的，我最喜欢Python！那你能给我推荐几个Python项目吗？",
        )
        print(f"👤 用户: {user_message_3.content}")

        conversation_history.append(user_message_3)

        response_3 = await adapter.generate(
            model="claude-3-5-sonnet-20241022",
            messages=conversation_history,
            params=params,
        )

        print(f"\n💬 Claude: {response_3.content}")
        print(f"📊 使用情况: {response_3.usage}")

        # 第四轮：更复杂的请求
        print("\n" + "=" * 60)
        print("第4轮对话")
        print("=" * 60)

        user_message_4 = Message(
            role="user",
            content="这些项目听起来不错！作为一个软件工程师，你觉得我应该如何提升我的Python技能？",
        )
        print(f"👤 用户: {user_message_4.content}")

        conversation_history.append(user_message_4)

        response_4 = await adapter.generate(
            model="claude-3-5-sonnet-20241022",
            messages=conversation_history,
            params=params,
        )

        print(f"\n💬 Claude: {response_4.content}")
        print(f"📊 使用情况: {response_4.usage}")

        # 展示对话历史统计
        print("\n" + "=" * 60)
        print("对话总结")
        print("=" * 60)
        print(f"✓ 总轮数: {len([msg for msg in conversation_history if msg.role == 'user'])}")
        print(f"✓ 消息总数: {len(conversation_history)}")
        print(f"✓ 对话参与者: {', '.join(set(msg.role for msg in conversation_history))}")

        # 可选：保存对话历史到文件
        save_conversation_to_file(conversation_history)

    except Exception as e:
        print(f"\n✗ 错误: {e}")
        import traceback

        traceback.print_exc()

    finally:
        await adapter.close()
        print("\n✓ 适配器已关闭")


def save_conversation_to_file(
    conversation_history: list[Message], filename: str = "conversation_log.txt"
):
    """将对话历史保存到文件."""
    try:
        filepath = Path(__file__).parent / filename

        with open(filepath, "w", encoding="utf-8") as f:
            f.write("多轮对话记录\n")
            f.write("=" * 60 + "\n\n")

            for i, message in enumerate(conversation_history, 1):
                role = "👤 用户" if message.role == "user" else "💬 Claude"
                f.write(f"{i}. {role}:\n")
                f.write(f"{message.content}\n\n")

            f.write("=" * 60 + "\n")
            f.write(f"总消息数: {len(conversation_history)}\n")

        print(f"✓ 对话历史已保存到: {filepath}")

    except Exception as e:
        print(f"⚠ 保存对话历史时出错: {e}")


if __name__ == "__main__":
    asyncio.run(main())
