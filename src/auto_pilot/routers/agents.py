from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from ..database import get_session
from ..models import Agent

router = APIRouter(prefix="/agents", tags=["agents"])


@router.get("/", response_model=list[Agent])
async def list_agents(session: AsyncSession = Depends(get_session)):
    """
    获取所有 Agent 列表
    """
    result = await session.execute(select(Agent))
    agents = result.scalars().all()
    return agents


@router.post("/", response_model=Agent, status_code=201)
async def create_agent(agent: Agent, session: AsyncSession = Depends(get_session)):
    """
    创建新的 Agent
    """
    session.add(agent)
    await session.commit()
    await session.refresh(agent)
    return agent


@router.get("/{agent_id}", response_model=Agent)
async def get_agent(agent_id: UUID, session: AsyncSession = Depends(get_session)):
    """
    根据 ID 获取 Agent
    """
    result = await session.execute(select(Agent).where(Agent.id == agent_id))
    agent = result.scalar_one_or_none()

    if agent is None:
        raise HTTPException(status_code=404, detail="Agent not found")

    return agent


@router.delete("/{agent_id}", status_code=204)
async def delete_agent(agent_id: UUID, session: AsyncSession = Depends(get_session)):
    """
    删除 Agent
    """
    result = await session.execute(select(Agent).where(Agent.id == agent_id))
    agent = result.scalar_one_or_none()

    if agent is None:
        raise HTTPException(status_code=404, detail="Agent not found")

    await session.delete(agent)
    await session.commit()
    return
