from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from ..database import get_session
from ..models import Task

router = APIRouter(prefix="/tasks", tags=["tasks"])


@router.get("/", response_model=list[Task])
async def list_tasks(session: AsyncSession = Depends(get_session)):
    """
    获取所有 Task 列表
    """
    result = await session.execute(select(Task))
    tasks = result.scalars().all()
    return tasks


@router.post("/", response_model=Task, status_code=201)
async def create_task(task: Task, session: AsyncSession = Depends(get_session)):
    """
    创建新的 Task
    """
    session.add(task)
    await session.commit()
    await session.refresh(task)
    return task


@router.get("/{task_id}", response_model=Task)
async def get_task(task_id: UUID, session: AsyncSession = Depends(get_session)):
    """
    根据 ID 获取 Task
    """
    result = await session.execute(select(Task).where(Task.id == task_id))
    task = result.scalar_one_or_none()

    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")

    return task


@router.delete("/{task_id}", status_code=204)
async def delete_task(task_id: UUID, session: AsyncSession = Depends(get_session)):
    """
    删除 Task
    """
    result = await session.execute(select(Task).where(Task.id == task_id))
    task = result.scalar_one_or_none()

    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")

    await session.delete(task)
    await session.commit()
    return
