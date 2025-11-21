from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI

from .config import settings
from .database import close_db_connection, create_db_and_tables
from .llm import BaseLLMAdapter
from .routers import agents, execution, tasks, tools

# Global LLM adapter instance
_llm_adapter: Optional[BaseLLMAdapter] = None


def init_llm_adapter(adapter: BaseLLMAdapter):
    """Initialize the global LLM adapter.

    Args:
        adapter: Configured LLM adapter instance
    """
    global _llm_adapter
    _llm_adapter = adapter
    execution.set_llm_adapter(adapter)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    应用生命周期管理
    启动时初始化数据库，关闭时清理连接
    """
    # 启动时执行
    print("🚀 正在启动 AutoPilot API...")
    print(f"📊 连接数据库: {settings.database_url}")
    await create_db_and_tables()
    print("✅ 数据库就绪")

    # Check if LLM adapter is initialized
    if _llm_adapter is None:
        print(
            "⚠️  LLM adapter not initialized. Call init_llm_adapter() to enable execution features."
        )

    yield

    # 关闭时执行
    print("\n🔌 正在关闭数据库连接...")
    await close_db_connection()
    print("✅ 应用已关闭")


# 创建 FastAPI 应用实例
app = FastAPI(
    title="AutoPilot API",
    description="自主任务执行 Agent 框架 - 支持自主任务执行的 LLM Agent 平台",
    version="0.1.0",
    lifespan=lifespan,
)

# 注册路由
app.include_router(agents.router)
app.include_router(tools.router)
app.include_router(tasks.router)
app.include_router(execution.router)


# 健康检查端点
@app.get("/health")
async def health_check():
    """健康检查端点"""
    return {
        "status": "healthy",
        "database": "connected",
        "execution": "enabled" if _llm_adapter else "disabled",
    }


# API 路由
@app.get("/")
async def read_root():
    return {
        "message": "欢迎使用 AutoPilot API",
        "version": "0.1.0",
        "docs": "/docs",
        "health": "/health",
        "execution_docs": "/docs#tag/execution",
        "endpoints": {
            "agents": "/agents",
            "tools": "/tools",
            "tasks": "/tasks",
            "execution": "/execution",
        },
        "features": {
            "task_execution": _llm_adapter is not None,
            "websocket_streaming": True,
        },
    }
