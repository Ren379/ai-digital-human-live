###############################################################################
#  Pydantic Schemas — Persona / Script / Knowledge / Events
###############################################################################

from pydantic import BaseModel, Field


# ── Persona ───────────────────────────────────────────────────────

class PersonaUpdate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    personality: str = Field(..., min_length=1)
    style: str = Field(..., min_length=1)
    knowledge_scope: str = Field(..., min_length=1)
    forbidden_topics: list[str] = Field(default_factory=list)


class PersonaResponse(BaseModel):
    id: int
    name: str
    personality: str
    style: str
    knowledge_scope: str
    forbidden_topics: list[str]
    updated_at: str | None = None


# ── Script ────────────────────────────────────────────────────────

class ScriptCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    type: str = Field(default="text", pattern="^(text|audio|video)$")
    content: str = Field(default="")
    tags: list[str] = Field(default_factory=list)


class ScriptUpdate(BaseModel):
    title: str | None = Field(None, min_length=1, max_length=200)
    content: str | None = None
    tags: list[str] | None = None
    enabled: bool | None = None


class ScriptResponse(BaseModel):
    id: int
    title: str
    type: str
    content: str
    file_path: str | None = None
    tags: list[str]
    enabled: bool
    play_count: int
    last_used_at: str | None = None
    created_at: str | None = None
    updated_at: str | None = None


# ── Knowledge ─────────────────────────────────────────────────────

class KnowledgeCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=300)
    content: str = Field(..., min_length=1)
    source_type: str = Field(default="text", pattern="^(text|file)$")


class KnowledgeResponse(BaseModel):
    id: int
    title: str
    content_preview: str
    source_type: str
    file_path: str | None = None
    chunk_count: int
    created_at: str | None = None


# ── Events / Livestream ───────────────────────────────────────────

class DanmakuEvent(BaseModel):
    platform: str
    sender: str
    content: str
    timestamp: float
    msg_type: str = "danmaku"


class LivestreamStartRequest(BaseModel):
    room_id: str = Field(default="")
    session_id: str = Field(..., min_length=1)
    platform: str = Field(default="bilibili")


class LivestreamStatusResponse(BaseModel):
    running: bool = False
    room_id: str = ""
    session_id: str = ""
    queue_high_count: int = 0
    queue_low_count: int = 0
    danmaku_count: int = 0
    is_speaking: bool = False


class LivetalkingSession(BaseModel):
    sessionid: str
    model: str = ""
    speaking: bool = False
    avatar_id: str = ""
    transport: str = ""


class LivetalkingSessionsResponse(BaseModel):
    sessions: list[LivetalkingSession] = Field(default_factory=list)
