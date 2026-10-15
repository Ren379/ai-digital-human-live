###############################################################################
#  应用配置 — 非业务参数（数据库、路径、队列等基础设施）
#
#  LLM / Embedding / LiveTalking 等业务参数请在前端「系统配置」页面修改，
#  存储在 DB 的 app_settings 表中，重启后生效。
###############################################################################

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """基础设施配置（.env 或环境变量）"""

    # ── Database ──
    database_url: str = "sqlite+aiosqlite:///data/livestream.db"

    # ── Queue ──
    queue_min_size: int = 2
    queue_auto_fill_interval: float = 3.0

    # ── Memory ──
    memory_window_size: int = 10

    # ── Knowledge Base ──
    knowledge_docs_path: str = "data/knowledge"
    chroma_persist_path: str = "data/chroma_db"

    # ── App ──
    app_host: str = "0.0.0.0"
    app_port: int = 8020
    cors_origins: str = "*"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"  # 忽略 .env 中的旧字段（已迁移到 DB）


def load_settings() -> Settings:
    return Settings()
