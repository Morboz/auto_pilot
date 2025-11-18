from datetime import datetime
from typing import Optional
from uuid import UUID, uuid4

from sqlmodel import Field, SQLModel


class Tool(SQLModel, table=True):
    """工具注册表 - 存储可用的 Tool 定义"""

    id: Optional[UUID] = Field(
        default_factory=uuid4,
        primary_key=True,
        index=True,
        description="Tool 唯一标识符",
    )
    name: str = Field(
        min_length=1,
        max_length=100,
        index=True,
        description="工具名称（如 HTTP GET、SQL Query等）",
    )
    type: str = Field(
        max_length=50, description="工具类型（如 http、sql、web3、js、custom）"
    )
    description: str = Field(description="工具详细说明")
    schema: Optional[str] = Field(default=None, description="工具参数 JSON Schema")
    created_at: datetime = Field(
        default_factory=datetime.utcnow, description="创建时间"
    )
    updated_at: datetime = Field(
        default_factory=datetime.utcnow, description="更新时间"
    )
