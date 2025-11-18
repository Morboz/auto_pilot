import os
from typing import Generator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool
from sqlmodel import SQLModel

# 数据库连接配置
DATABASE_URL = os.getenv(
    "DATABASE_URL", "postgresql+asyncpg://postgres:x914259241@localhost:5432/auto_pilot"
)

# 创建异步数据库引擎
engine = create_async_engine(
    DATABASE_URL,
    echo=False,
    poolclass=NullPool,  # 适合 Serverless 或单连接场景
    pool_pre_ping=True,
    connect_args={
        "server_settings": {
            "jit": "off"  # 可选：禁用 JIT 编译以提高兼容性
        }
    },
)

# 创建异步会话工厂
AsyncSessionLocal = async_sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)


async def create_db_and_tables() -> None:
    """创建所有数据库表"""
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)


async def get_session() -> Generator[AsyncSession, None, None]:
    """
    获取数据库会话的依赖注入函数
    使用方式: async with get_session() as session:
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def close_db_connection() -> None:
    """关闭数据库连接"""
    await engine.dispose()
