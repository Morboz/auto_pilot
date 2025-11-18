from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from ..database import get_session
from ..models import Tool

router = APIRouter(prefix="/tools", tags=["tools"])


@router.get("/", response_model=list[Tool])
async def list_tools(session: AsyncSession = Depends(get_session)):
    """
    获取所有 Tool 列表
    """
    result = await session.execute(select(Tool))
    tools = result.scalars().all()
    return tools


@router.post("/", response_model=Tool, status_code=201)
async def create_tool(tool: Tool, session: AsyncSession = Depends(get_session)):
    """
    创建新的 Tool
    """
    session.add(tool)
    await session.commit()
    await session.refresh(tool)
    return tool


@router.get("/{tool_id}", response_model=Tool)
async def get_tool(tool_id: UUID, session: AsyncSession = Depends(get_session)):
    """
    根据 ID 获取 Tool
    """
    result = await session.execute(select(Tool).where(Tool.id == tool_id))
    tool = result.scalar_one_or_none()

    if tool is None:
        raise HTTPException(status_code=404, detail="Tool not found")

    return tool


@router.delete("/{tool_id}", status_code=204)
async def delete_tool(tool_id: UUID, session: AsyncSession = Depends(get_session)):
    """
    删除 Tool
    """
    result = await session.execute(select(Tool).where(Tool.id == tool_id))
    tool = result.scalar_one_or_none()

    if tool is None:
        raise HTTPException(status_code=404, detail="Tool not found")

    await session.delete(tool)
    await session.commit()
    return
