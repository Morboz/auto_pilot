from typing import Any, Dict, List

from fastapi import APIRouter, HTTPException

router = APIRouter(prefix="/tools", tags=["tools"])


@router.get("/", response_model=List[Dict[str, Any]])
async def list_tools():
    """
    获取所有内置工具列表

    注意：出于安全考虑，本系统仅支持内置工具，不支持动态注册外部工具
    """
    from ..main import _tool_system

    if not _tool_system or not _tool_system.get("registry"):
        raise HTTPException(status_code=503, detail="Tool system not initialized")

    registry = _tool_system["registry"]
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
async def get_tool(tool_name: str):
    """
    根据名称获取工具详情
    """
    from ..main import _tool_system

    if not _tool_system or not _tool_system.get("registry"):
        raise HTTPException(status_code=503, detail="Tool system not initialized")

    registry = _tool_system["registry"]
    tool_def = registry.get_tool(tool_name)

    if tool_def is None:
        raise HTTPException(status_code=404, detail=f"Tool '{tool_name}' not found")

    return {
        "name": tool_def.name,
        "description": tool_def.description,
        "parameters": tool_def.parameters,
        "metadata": tool_def.metadata,
    }


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
