from typing import Optional
from uuid import UUID, uuid4

from sqlmodel import Field, SQLModel


class AgentTool(SQLModel, table=True):
    """Agent-Tool 关联表 - 多对多关系"""

    id: Optional[UUID] = Field(
        default_factory=uuid4, primary_key=True, description="关联记录唯一标识符"
    )
    agent_id: UUID = Field(foreign_key="agent.id", description="关联的 Agent ID")
    tool_id: UUID = Field(foreign_key="tool.id", description="关联的 Tool ID")
