from typing import Any, Dict, Optional
from uuid import UUID, uuid4

from sqlmodel import JSON, Column, Field, SQLModel


class AgentTool(SQLModel, table=True):
    __tablename__ = "agent_tool"
    """Agent-Tool 关联表 - 多对多关系 + 权限配置"""

    id: Optional[UUID] = Field(
        default_factory=uuid4, primary_key=True, description="关联记录唯一标识符"
    )
    agent_id: UUID = Field(foreign_key="agent.id", description="关联的 Agent ID")
    tool_id: UUID = Field(foreign_key="tool.id", description="关联的 Tool ID")

    # Tool 权限配置（JSON格式），可选，为 null 时使用默认权限
    permissions: Optional[Dict[str, Any]] = Field(
        default=None,
        sa_column=Column(JSON, nullable=True),
        description="Tool 权限配置（JSON），为 null 时使用默认权限",
    )
