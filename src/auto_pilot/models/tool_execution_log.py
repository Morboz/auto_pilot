from datetime import datetime
from typing import Optional
from uuid import UUID, uuid4

from sqlmodel import Field, SQLModel


class ToolExecutionLog(SQLModel, table=True):
    __tablename__ = "tool_execution_log"
    """工具执行日志表 - 记录每次工具调用的详细信息（用于审计）"""

    id: Optional[UUID] = Field(
        default_factory=uuid4, primary_key=True, description="执行记录唯一标识符"
    )
    task_id: Optional[UUID] = Field(
        default=None, index=True, description="关联的 Task ID (可选)"
    )
    tool_id: Optional[UUID] = Field(default=None, description="调用的 Tool ID (可选)")
    tool_name: str = Field(index=True, description="工具名称")
    input_params: Optional[str] = Field(
        default=None, description="调用参数（JSON 字符串）"
    )
    output: Optional[str] = Field(
        default=None, description="工具返回结果（JSON 字符串）"
    )
    error_message: Optional[str] = Field(
        default=None, description="错误信息（如工具调用失败）"
    )
    duration_ms: Optional[float] = Field(default=None, description="执行耗时（毫秒）")
    sandbox_enabled: bool = Field(default=True, description="是否启用 sandbox 执行")
    resource_usage: Optional[str] = Field(
        default=None, description="资源使用情况（JSON 字符串）"
    )
    created_at: datetime = Field(
        default_factory=datetime.utcnow, description="创建时间"
    )

    @property
    def success(self) -> bool:
        """是否执行成功"""
        return self.error_message is None
