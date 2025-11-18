from datetime import datetime
from typing import Optional
from uuid import UUID, uuid4

from sqlmodel import Field, SQLModel


class Agent(SQLModel, table=True):
    """Agent 配置表 - 存储用户创建的自定义 Agent"""

    id: Optional[UUID] = Field(
        default_factory=uuid4,
        primary_key=True,
        index=True,
        description="Agent 唯一标识符",
    )
    name: str = Field(min_length=1, max_length=100, description="Agent 名称")
    model: str = Field(
        min_length=1,
        max_length=100,
        description="使用的模型名称（如 gpt-4、claude-3等）",
    )
    system_prompt: str = Field(description="Agent 的人格与指令")
    created_at: datetime = Field(
        default_factory=datetime.utcnow, description="创建时间"
    )
    updated_at: datetime = Field(
        default_factory=datetime.utcnow, description="更新时间"
    )
