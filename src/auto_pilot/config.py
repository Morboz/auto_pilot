from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """应用配置"""

    database_url: str = (
        "postgresql+asyncpg://postgres:x914259241@localhost:5432/auto_pilot"
    )
    debug: bool = False
    api_host: str = "0.0.0.0"
    api_port: int = 8000

    class Config:
        env_file = ".env"


# 创建全局设置实例
settings = Settings()
