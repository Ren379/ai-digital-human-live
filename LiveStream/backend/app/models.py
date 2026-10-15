###############################################################################
#  ORM 模型 — Persona / Script / KnowledgeDocument
###############################################################################

import json
from datetime import datetime
from sqlalchemy import String, Text, Integer, Boolean, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base


# ── Persona（单行配置）────────────────────────────────────────────

class Persona(Base):
    __tablename__ = "persona"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), default="小助手")
    personality: Mapped[str] = mapped_column(Text, default="热情友好")
    style: Mapped[str] = mapped_column(Text, default="轻松活泼")
    knowledge_scope: Mapped[str] = mapped_column(Text, default="日常闲聊")
    forbidden_topics: Mapped[str] = mapped_column(Text, default="[]")
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )

    @property
    def forbidden_topics_list(self) -> list[str]:
        return json.loads(self.forbidden_topics) if self.forbidden_topics else []

    @forbidden_topics_list.setter
    def forbidden_topics_list(self, value: list[str]):
        self.forbidden_topics = json.dumps(value, ensure_ascii=False)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "personality": self.personality,
            "style": self.style,
            "knowledge_scope": self.knowledge_scope,
            "forbidden_topics": self.forbidden_topics_list,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    @classmethod
    def default_dict(cls) -> dict:
        """返回默认 Persona 属性；forbidden_topics 存 JSON 字符串（ORM 列是 Text 类型）"""
        return {
            "name": "小助手",
            "personality": "热情友好、耐心细致、幽默风趣",
            "style": "轻松活泼，喜欢用简短的句子，偶尔加入网络流行语",
            "knowledge_scope": "日常闲聊、生活百科、娱乐八卦",
            "forbidden_topics": "[]",
        }


# ── Script（话术）─────────────────────────────────────────────────

class Script(Base):
    __tablename__ = "script"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(200), default="")
    type: Mapped[str] = mapped_column(String(20), default="text")
    content: Mapped[str] = mapped_column(Text, default="")
    file_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    tags: Mapped[str] = mapped_column(Text, default="[]")
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    play_count: Mapped[int] = mapped_column(Integer, default=0)
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )

    @property
    def tags_list(self) -> list[str]:
        return json.loads(self.tags) if self.tags else []

    @tags_list.setter
    def tags_list(self, value: list[str]):
        self.tags = json.dumps(value, ensure_ascii=False)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "title": self.title,
            "type": self.type,
            "content": self.content,
            "file_path": self.file_path,
            "tags": self.tags_list,
            "enabled": self.enabled,
            "play_count": self.play_count,
            "last_used_at": self.last_used_at.isoformat() if self.last_used_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


# ── AppSettings（前端可配置的系统参数，单行）─────────────────────

class AppSettings(Base):
    __tablename__ = "app_settings"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    livetalking_base_url: Mapped[str] = mapped_column(String(300), default="http://127.0.0.1:8010")
    llm_api_key: Mapped[str] = mapped_column(String(300), default="")
    llm_base_url: Mapped[str] = mapped_column(String(300), default="https://dashscope.aliyuncs.com/compatible-mode/v1")
    llm_model: Mapped[str] = mapped_column(String(100), default="qwen-plus")
    embedding_api_key: Mapped[str] = mapped_column(String(300), default="")
    embedding_base_url: Mapped[str] = mapped_column(String(300), default="https://dashscope.aliyuncs.com/compatible-mode/v1")
    embedding_model: Mapped[str] = mapped_column(String(100), default="text-embedding-v4")

    def to_dict(self) -> dict:
        return {c.name: getattr(self, c.name) for c in self.__table__.columns
                if c.name not in ('id',)}

    @classmethod
    def defaults(cls) -> dict:
        return {
            "livetalking_base_url": "http://127.0.0.1:8010",
            "llm_api_key": "",
            "llm_base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
            "llm_model": "qwen-plus",
            "embedding_api_key": "",
            "embedding_base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
            "embedding_model": "text-embedding-v4",
        }


# ── KnowledgeDocument（知识库文档）────────────────────────────────

class KnowledgeDocument(Base):
    __tablename__ = "knowledge_document"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(300))
    content: Mapped[str] = mapped_column(Text, default="")
    source_type: Mapped[str] = mapped_column(String(20), default="text")
    file_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    chunk_count: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    def to_dict(self) -> dict:
        c = self.content
        return {
            "id": self.id,
            "title": self.title,
            "content": c[:200] + "..." if len(c) > 200 else c,
            "source_type": self.source_type,
            "file_path": self.file_path,
            "chunk_count": self.chunk_count,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
