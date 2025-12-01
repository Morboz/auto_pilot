from contextlib import asynccontextmanager

from fastapi import FastAPI, Request

from .config import settings
from .database import close_db_connection, create_db_and_tables
from .execution.state_manager import StateManager
from .llm import BaseLLMAdapter
from .logger import get_logger, setup_logging
from .routers import agents, execution, tasks, tools
from .tools import create_tool_system
from .tools.builtin import BuiltinToolLoader

logger = get_logger(__name__)


def init_llm_adapter(adapter: BaseLLMAdapter):
    """Initialize the global LLM adapter.

    Args:
        adapter: Configured LLM adapter instance
    """
    app.state.llm_adapter = adapter


def get_tool_executor(request: Request):
    """Get the global tool executor instance.

    Returns:
        ToolExecutor instance or None if not initialized
    """
    return getattr(request.app.state, "tool_executor", None)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    应用生命周期管理
    启动时初始化数据库，关闭时清理连接
    """
    # 初始化日志
    setup_logging()

    # 启动时执行
    logger.info("🚀 正在启动 AutoPilot API...")
    logger.info("📊 连接数据库: %s", settings.database_url)
    await create_db_and_tables()
    logger.info("✅ 数据库就绪")

    # Initialize tool system
    logger.info("🔧 正在初始化工具系统...")
    tool_system = create_tool_system()
    app.state.tool_system = tool_system
    app.state.tool_executor = tool_system["executor"]
    logger.info("✅ 工具系统就绪")

    # Initialize state manager
    app.state.state_manager = StateManager()

    # Load builtin tools
    logger.info("📦 加载内置工具...")
    loader = BuiltinToolLoader(
        registry=app.state.tool_system["registry"],
        executor=app.state.tool_executor,
    )
    loader.load_builtin_tools()
    logger.info("✅ 已加载 %d 个工具", len(app.state.tool_system["registry"].list_tools()))

    yield

    # 关闭时执行
    logger.info("🛑 正在关闭 AutoPilot API...")
    await close_db_connection()
    logger.info("👋 再见!")


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
async def health_check(request: Request):
    """健康检查端点"""
    tool_count = 0
    if hasattr(request.app.state, "tool_system") and request.app.state.tool_system.get("registry"):
        tool_count = len(request.app.state.tool_system["registry"]._tools)

    return {
        "status": "healthy",
        "database": "connected",
        "execution": "enabled" if getattr(request.app.state, "llm_adapter", None) else "disabled",
        "tool_system": "enabled" if hasattr(request.app.state, "tool_system") else "disabled",
        "builtin_tools_loaded": tool_count,
    }


# API 路由
@app.get("/")
async def read_root(request: Request):
    # Get tool count
    tool_count = 0
    if hasattr(request.app.state, "tool_system") and request.app.state.tool_system.get("registry"):
        tool_count = len(request.app.state.tool_system["registry"]._tools)

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
            "task_execution": getattr(request.app.state, "llm_adapter", None) is not None,
            "websocket_streaming": True,
            "builtin_tools": tool_count,
        },
    }
