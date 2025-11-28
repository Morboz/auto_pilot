"""数据库初始化工具"""

import asyncio

from .database import AsyncSessionLocal, engine
from .logger import get_logger
from .models import Agent, AgentTool, Task, TaskLog, Tool, ToolExecutionLog

logger = get_logger(__name__)


async def init_database(drop_first: bool = False) -> None:
    """
    初始化数据库

    Args:
        drop_first: 如果为 True，将先删除所有表，然后重新创建
    """
    from .database import create_db_and_tables

    logger.info("🚀 正在初始化数据库...")

    async with engine.begin() as conn:
        if drop_first:
            logger.info("⚠️  删除现有表...")
            await conn.run_sync(ToolExecutionLog.__table__.drop)
            await conn.run_sync(TaskLog.__table__.drop)
            await conn.run_sync(Task.__table__.drop)
            await conn.run_sync(AgentTool.__table__.drop)
            await conn.run_sync(Tool.__table__.drop)
            await conn.run_sync(Agent.__table__.drop)
            logger.info("✅ 现有表已删除")

    logger.info("📦 创建新表...")
    await create_db_and_tables()
    logger.info("✅ 所有表创建成功")

    # 创建一些示例数据
    await create_sample_data()
    logger.info("✨ 数据库初始化完成！")


async def create_sample_data() -> None:
    """创建示例数据"""
    async with AsyncSessionLocal() as session:
        # 创建示例 Agent
        sample_agent = Agent(
            name="数据分析助手",
            model="claude-3-opus",
            system_prompt="你是一个专业的数据分析师，擅长处理和分析各种数据。",
        )

        # 创建示例 Tool
        http_tool = Tool(
            name="HTTP GET",
            type="http",
            description="通过 HTTP GET 请求获取外部 API 数据",
            schema='{"url": "string", "headers": "object"}',
        )

        sql_tool = Tool(
            name="SQL Query",
            type="sql",
            description="执行 SQL 查询操作数据库",
            schema='{"query": "string", "params": "object"}',
        )

        session.add(sample_agent)
        session.add(http_tool)
        session.add(sql_tool)
        await session.commit()
        await session.refresh(sample_agent)
        await session.refresh(http_tool)
        await session.refresh(sql_tool)

        # 创建 Agent-Tool 关联
        agent_tool1 = AgentTool(agent_id=sample_agent.id, tool_id=http_tool.id)
        agent_tool2 = AgentTool(agent_id=sample_agent.id, tool_id=sql_tool.id)
        session.add(agent_tool1)
        session.add(agent_tool2)
        await session.commit()

        logger.info("   📄 创建示例 Agent: %s", sample_agent.name)
        logger.info("   🛠️  创建示例 Tool: %s, %s", http_tool.name, sql_tool.name)


if __name__ == "__main__":
    asyncio.run(init_database(drop_first=True))
