import json
from typing import Any, Dict, List
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_session
from ..logger import get_logger
from ..models import ToolExecutionLog
from ..schemas.tools import ToolExecuteRequest, ToolExecuteResponse

logger = get_logger(__name__)


router = APIRouter(prefix="/tools", tags=["tools"])


async def get_tool_system(request: Request):
    """
    依赖：获取工具系统

    Returns:
        包含 registry 和 executor 的工具系统字典

    Raises:
        HTTPException: 如果工具系统未初始化
    """
    if not hasattr(
        request.app.state, "tool_system"
    ) or not request.app.state.tool_system.get("registry"):
        raise HTTPException(status_code=503, detail="Tool system not initialized")

    return request.app.state.tool_system


@router.get("/", response_model=List[Dict[str, Any]])
async def list_tools(tool_system=Depends(get_tool_system)):
    """
    获取所有内置工具列表

    注意：出于安全考虑，本系统仅支持内置工具，不支持动态注册外部工具

    Args:
        tool_system: 工具系统依赖
    """
    registry = tool_system["registry"]
    tools = []

    for tool_name, tool_def in registry._tools.items():
        tools.append(
            {
                "name": tool_def.name,
                "description": tool_def.description,
                "parameters": tool_def.parameters,
                "metadata": tool_def.metadata,
            }
        )

    return tools


@router.post("/")
async def create_tool():
    """
    创建新工具（已禁用）

    出于安全考虑，本系统不支持动态注册外部工具。
    所有工具都是内置的，在系统启动时自动加载。
    """
    raise HTTPException(
        status_code=403,
        detail="Tool registration is disabled for security reasons. "
        "Only built-in tools are available.",
    )


@router.get("/{tool_name}", response_model=Dict[str, Any])
async def get_tool(tool_name: str, tool_system=Depends(get_tool_system)):
    """
    根据名称获取工具详情

    Args:
        tool_name: 工具名称
        tool_system: 工具系统依赖
    """
    registry = tool_system["registry"]
    tool_def = registry.get_tool(tool_name)

    if tool_def is None:
        raise HTTPException(status_code=404, detail=f"Tool '{tool_name}' not found")

    return {
        "name": tool_def.name,
        "description": tool_def.description,
        "parameters": tool_def.parameters,
        "metadata": tool_def.metadata,
    }


@router.post("/{tool_name}/execute", response_model=ToolExecuteResponse)
async def execute_tool(
    tool_name: str,
    request: ToolExecuteRequest,
    session: AsyncSession = Depends(get_session),
    tool_system=Depends(get_tool_system),
):
    """
    执行一个工具（用于调试和手动测试）

    Args:
        tool_name: 工具名称
        request: 包含工具参数和超时配置
        session: 数据库会话
        tool_system: 工具系统依赖

    Returns:
        工具执行结果
    """
    registry = tool_system["registry"]
    executor = tool_system["executor"]

    # Get tool definition
    tool_def = registry.get_tool(tool_name)
    if not tool_def:
        raise HTTPException(status_code=404, detail=f"Tool '{tool_name}' not found")

    try:
        # Execute tool
        result = await executor.execute(
            tool_name=tool_name,
            arguments=request.arguments,
            timeout=request.timeout,
        )

        # Save execution to database
        try:
            # Create a dummy task_id since this is a direct tool execution
            task_id = uuid4()

            log = ToolExecutionLog(
                task_id=task_id,
                tool_name=tool_name,
                input_params=json.dumps(request.arguments),
                output=json.dumps(result.result)
                if result.success and result.result
                else None,
                error_message=result.error if not result.success else None,
                duration_ms=result.execution_time_ms,
                sandbox_enabled=True,
                resource_usage=json.dumps(result.resource_usage)
                if result.resource_usage
                else None,
            )

            session.add(log)
            await session.commit()
            logger.info("✅ Tool execution log saved to DB with id: %s", log.id)
        except Exception as db_error:
            # Don't fail the request if DB logging fails
            logger.error(
                "❌ Failed to save tool execution log: %s", db_error, exc_info=True
            )

        return ToolExecuteResponse(
            tool_name=tool_name,
            success=result.success,
            result=result.result,
            error=result.error,
            execution_time_ms=result.execution_time_ms,
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to execute tool: {str(e)}")


@router.delete("/{tool_name}")
async def delete_tool(tool_name: str):
    """
    删除工具（已禁用）

    出于安全考虑，内置工具无法删除。
    """
    raise HTTPException(
        status_code=403,
        detail="Cannot delete built-in tools. "
        "Tool management is restricted for security reasons.",
    )
