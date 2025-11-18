from datetime import datetime
from typing import Optional
from uuid import UUID, uuid4

from sqlmodel import Field, SQLModel


class TaskLog(SQLModel, table=True):
    """任务日志表 - 存储 ReAct 风格的 thought/action/observation 步骤"""

    id: Optional[UUID] = Field(
        default_factory=uuid4, primary_key=True, description="日志记录唯一标识符"
    )
    task_id: UUID = Field(
        foreign_key="task.id", index=True, description="关联的 Task ID"
    )
    step_number: int = Field(description="步骤编号（递增）")
    type: str = Field(
        max_length=20, description="日志类型（thought/action/observation）"
    )
    content: str = Field(description="具体内容（文本或 JSON 字符串）")
    created_at: datetime = Field(
        default_factory=datetime.utcnow, description="创建时间"
    )
