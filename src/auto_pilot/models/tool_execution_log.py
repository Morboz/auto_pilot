from datetime import datetime
from typing import Optional
from uuid import UUID, uuid4

from sqlmodel import Field, SQLModel


class ToolExecutionLog(SQLModel, table=True):
    """工具执行日志表 - 记录每次工具调用的详细信息（用于审计）"""

    id: Optional[UUID] = Field(
        default_factory=uuid4, primary_key=True, description="执行记录唯一标识符"
    )
    task_id: UUID = Field(
        foreign_key="task.id", index=True, description="关联的 Task ID"
    )
    tool_id: UUID = Field(foreign_key="tool.id", description="调用的 Tool ID")
    input_params: Optional[str] = Field(
        default=None, description="调用参数（JSON 字符串）"
    )
    output: Optional[str] = Field(
        default=None, description="工具返回结果（JSON 字符串）"
    )
    error_message: Optional[str] = Field(
        default=None, description="错误信息（如工具调用失败）"
    )
    created_at: datetime = Field(
        default_factory=datetime.utcnow, description="创建时间"
    )
