from datetime import datetime
from typing import Optional
from uuid import UUID, uuid4

from sqlmodel import Field, SQLModel


class Task(SQLModel, table=True):
    """任务表 - 存储每次用户触发的任务执行"""

    id: Optional[UUID] = Field(
        default_factory=uuid4,
        primary_key=True,
        index=True,
        description="Task 唯一标识符",
    )
    agent_id: UUID = Field(foreign_key="agent.id", description="使用的 Agent ID")
    input_text: str = Field(description="用户输入（如 '请分析 ETH 价格'）")
    status: str = Field(
        max_length=20,
        default="pending",
        index=True,
        description="任务状态（pending/running/failed/success）",
    )
    result_text: Optional[str] = Field(
        default=None, description="最终结果（文本或 JSON 字符串）"
    )
    meta: Optional[str] = Field(
        default=None, description="任务额外信息（JSON 字符串，如 riskLevel=high）"
    )
    created_at: datetime = Field(
        default_factory=datetime.utcnow, description="创建时间"
    )
    updated_at: datetime = Field(
        default_factory=datetime.utcnow, description="更新时间"
    )
