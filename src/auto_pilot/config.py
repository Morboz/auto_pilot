from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """应用配置"""

    database_url: str = "postgresql+asyncpg://postgres:x914259241@localhost:5432/auto_pilot"
    debug: bool = False
    api_host: str = "0.0.0.0"
    api_port: int = 8000

    # Logging settings
    log_level: str = "INFO"
    log_json_format: bool = False

    # Optional LLM provider settings
    anthropic_api_key: str = ""
    anthropic_base_url: str = ""
    openai_api_key: str = ""
    openai_base_url: str = ""

    class Config:
        env_file = ".env"
        model_extra = "ignore"  # Allow extra fields from .env


# 创建全局设置实例
settings = Settings()
