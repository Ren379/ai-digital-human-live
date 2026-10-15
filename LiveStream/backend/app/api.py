###############################################################################
#  API Routes — 所有 REST + WebSocket 路由
###############################################################################

import os, uuid, json, asyncio
from datetime import datetime

from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException, WebSocket, WebSocketDisconnect
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_db
from app.models import Persona, Script, KnowledgeDocument
from app.schemas import (
    PersonaUpdate, PersonaResponse,
    ScriptCreate, ScriptUpdate, ScriptResponse,
    KnowledgeCreate, KnowledgeResponse,
    LivestreamStartRequest, LivestreamStatusResponse,
)
from app.utils.logger import logger

router = APIRouter()
UPLOAD_DIR = "data/uploads"

# ═══════════════════════════════════════════════════════════════════
#  Persona
# ═══════════════════════════════════════════════════════════════════

async def _get_or_create_persona(db: AsyncSession) -> Persona:
    result = await db.execute(select(Persona).limit(1))
    persona = result.scalar_one_or_none()
    if persona is None:
        persona = Persona(**Persona.default_dict())
        db.add(persona)
        await db.commit()
        await db.refresh(persona)
        logger.info("Created default persona")
    return persona


@router.get("/api/persona", response_model=PersonaResponse, tags=["persona"])
async def get_persona(db: AsyncSession = Depends(get_db)):
    persona = await _get_or_create_persona(db)
    return PersonaResponse(**persona.to_dict())


@router.put("/api/persona", response_model=PersonaResponse, tags=["persona"])
async def update_persona(data: PersonaUpdate, db: AsyncSession = Depends(get_db)):
    persona = await _get_or_create_persona(db)
    persona.name = data.name
    persona.personality = data.personality
    persona.style = data.style
    persona.knowledge_scope = data.knowledge_scope
    persona.forbidden_topics_list = data.forbidden_topics
    await db.commit()
    await db.refresh(persona)
    logger.info(f"Persona updated: {persona.name}")
    return PersonaResponse(**persona.to_dict())


# ═══════════════════════════════════════════════════════════════════
#  Settings
# ═══════════════════════════════════════════════════════════════════

from app.models import AppSettings


async def _get_settings(db: AsyncSession) -> AppSettings:
    result = await db.execute(select(AppSettings).limit(1))
    s = result.scalar_one_or_none()
    if s is None:
        s = AppSettings(**AppSettings.defaults())
        db.add(s)
        await db.commit()
        await db.refresh(s)
    return s


@router.get("/api/settings", tags=["settings"])
async def get_settings(db: AsyncSession = Depends(get_db)):
    s = await _get_settings(db)
    return {"code": 0, "data": s.to_dict()}


@router.put("/api/settings", tags=["settings"])
async def update_settings(data: dict, db: AsyncSession = Depends(get_db)):
    s = await _get_settings(db)
    allowed = set(AppSettings.defaults().keys())
    for k, v in data.items():
        if k in allowed and v is not None:
            setattr(s, k, v)
    await db.commit()
    logger.info("Settings updated")
    return {"code": 0, "data": s.to_dict()}


@router.post("/api/settings/reload", tags=["settings"])
async def reload_settings(db: AsyncSession = Depends(get_db)):
    """用 DB 中的最新配置重建 LLM 和 Embedding"""
    s = await _get_settings(db)
    # 同步到环境变量
    import os
    if s.llm_api_key:
        os.environ["OPENAI_API_KEY"] = s.llm_api_key
    if s.embedding_api_key:
        os.environ["EMBEDDING_API_KEY"] = s.embedding_api_key

    from app.main import app
    from app.services.llm_service import LLMService
    from app.services.livetalking_client import LiveTalkingClient

    # 重建 LLM service（传入 DB 中的最新配置）
    persona = await _get_or_create_persona(db)
    new_llm = LLMService(
        persona.to_dict(),
        llm_api_key=s.llm_api_key,
        llm_base_url=s.llm_base_url,
        llm_model=s.llm_model,
        embedding_api_key=s.embedding_api_key,
        embedding_base_url=s.embedding_base_url,
        embedding_model=s.embedding_model,
    )
    try:
        await new_llm.init_knowledge_base()
    except Exception as e:
        logger.warning(f"Knowledge base re-init skipped: {e}")
    app.state.llm_service = new_llm

    # 重建 LiveTalking client
    app.state.lt_client = LiveTalkingClient(base_url=s.livetalking_base_url)

    logger.info("Settings reloaded")
    return {"code": 0, "msg": "ok"}


# ═══════════════════════════════════════════════════════════════════
#  Scripts
# ═══════════════════════════════════════════════════════════════════

@router.get("/api/scripts", response_model=list[ScriptResponse], tags=["scripts"])
async def list_scripts(
    enabled_only: bool = False,
    type_filter: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    stmt = select(Script)
    if enabled_only:
        stmt = stmt.where(Script.enabled == True)
    if type_filter:
        stmt = stmt.where(Script.type == type_filter)
    stmt = stmt.order_by(Script.created_at.desc())
    result = await db.execute(stmt)
    return [ScriptResponse(**s.to_dict()) for s in result.scalars().all()]


@router.post("/api/scripts", response_model=ScriptResponse, tags=["scripts"])
async def create_script(data: ScriptCreate, db: AsyncSession = Depends(get_db)):
    script = Script(title=data.title, type=data.type, content=data.content, tags_list=data.tags)
    db.add(script)
    await db.commit()
    await db.refresh(script)
    logger.info(f"Script created: {script.title}")
    return ScriptResponse(**script.to_dict())


@router.put("/api/scripts/{script_id}", response_model=ScriptResponse, tags=["scripts"])
async def update_script(script_id: int, data: ScriptUpdate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Script).where(Script.id == script_id))
    script = result.scalar_one_or_none()
    if script is None:
        raise HTTPException(status_code=404, detail="Script not found")
    if data.title is not None:
        script.title = data.title
    if data.content is not None:
        script.content = data.content
    if data.tags is not None:
        script.tags_list = data.tags
    if data.enabled is not None:
        script.enabled = data.enabled
    await db.commit()
    await db.refresh(script)
    return ScriptResponse(**script.to_dict())


@router.delete("/api/scripts/{script_id}", tags=["scripts"])
async def delete_script(script_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Script).where(Script.id == script_id))
    script = result.scalar_one_or_none()
    if script is None:
        raise HTTPException(status_code=404, detail="Script not found")
    # 删除关联文件
    if script.file_path and os.path.isfile(script.file_path):
        try:
            os.remove(script.file_path)
        except Exception as e:
            logger.warning(f"Failed to delete script file: {e}")
    await db.delete(script)
    await db.commit()
    return {"code": 0, "msg": "ok"}


@router.post("/api/scripts/{script_id}/toggle", tags=["scripts"])
async def toggle_script(script_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Script).where(Script.id == script_id))
    script = result.scalar_one_or_none()
    if script is None:
        raise HTTPException(status_code=404, detail="Script not found")
    script.enabled = not script.enabled
    await db.commit()
    return {"code": 0, "enabled": script.enabled}


@router.post("/api/scripts/upload-file", tags=["scripts"])
async def upload_file(
    script_id: int = Form(...),
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Script).where(Script.id == script_id))
    script = result.scalar_one_or_none()
    if script is None:
        raise HTTPException(status_code=404, detail="Script not found")

    content = await file.read()
    os.makedirs(UPLOAD_DIR, exist_ok=True)

    if script.type == "video":
        # 视频：先存本地，再调 LiveTalking convert_custom_media 转换
        ext = os.path.splitext(file.filename or "video.mp4")[1]
        local_path = os.path.join(UPLOAD_DIR, f"{uuid.uuid4().hex}{ext}")
        with open(local_path, "wb") as f:
            f.write(content)

        from app.services.livetalking_client import LiveTalkingClient
        from app.main import app as main_app
        lt = main_app.state.lt_client or LiveTalkingClient(base_url=_settings.livetalking_base_url)
        result_data = await lt.convert_media(local_path)
        script.file_path = result_data["media_path"]  # 存 media_path，不是本地路径
        # 转换完成后删除本地临时视频文件
        try:
            os.remove(local_path)
        except Exception as e:
            logger.warning(f"Failed to remove temp video: {e}")
    else:
        ext = os.path.splitext(file.filename or "audio.wav")[1]
        local_path = os.path.join(UPLOAD_DIR, f"{uuid.uuid4().hex}{ext}")
        with open(local_path, "wb") as f:
            f.write(content)
        script.file_path = local_path

    await db.commit()
    await db.refresh(script)
    return {"code": 0, "file_path": script.file_path}


# ═══════════════════════════════════════════════════════════════════
#  Knowledge Base
# ═══════════════════════════════════════════════════════════════════

from app.config import load_settings
_settings = load_settings()


def _get_llm_service():
    """获取 LLM service（启动时已初始化，永远非空）"""
    from app.main import app
    return app.state.llm_service


@router.get("/api/knowledge/documents", response_model=list[KnowledgeResponse], tags=["knowledge"])
async def list_documents(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(KnowledgeDocument).order_by(KnowledgeDocument.created_at.desc()))
    docs = result.scalars().all()
    return [
        KnowledgeResponse(
            id=d.id, title=d.title,
            content_preview=d.content[:200] + "..." if len(d.content) > 200 else d.content,
            source_type=d.source_type, file_path=d.file_path,
            chunk_count=d.chunk_count,
            created_at=d.created_at.isoformat() if d.created_at else None,
        ) for d in docs
    ]


@router.post("/api/knowledge/documents", response_model=KnowledgeResponse, tags=["knowledge"])
async def create_document(data: KnowledgeCreate, db: AsyncSession = Depends(get_db)):
    doc = KnowledgeDocument(title=data.title, content=data.content, source_type=data.source_type)
    db.add(doc)
    await db.commit()
    await db.refresh(doc)

    # 增量同步到向量库
    llm = _get_llm_service()
    if llm and llm._knowledge_base:
        n = await llm._knowledge_base.add_document(doc.id, doc.title, doc.content)
        doc.chunk_count = n
        await db.commit()

    return KnowledgeResponse(
        id=doc.id, title=doc.title,
        content_preview=doc.content[:200] + "..." if len(doc.content) > 200 else doc.content,
        source_type=doc.source_type, chunk_count=doc.chunk_count,
        created_at=doc.created_at.isoformat() if doc.created_at else None,
    )


@router.post("/api/knowledge/documents/upload", tags=["knowledge"])
async def upload_document(
    title: str = Form(...),
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
):
    os.makedirs(_settings.knowledge_docs_path, exist_ok=True)
    ext = os.path.splitext(file.filename or "doc.txt")[1].lower()
    filename = f"{uuid.uuid4().hex}{ext}"
    filepath = os.path.join(_settings.knowledge_docs_path, filename)
    content = await file.read()
    with open(filepath, "wb") as f:
        f.write(content)

    # 根据文件类型解析文本
    if ext == ".pdf":
        try:
            from pypdf import PdfReader
            from io import BytesIO
            reader = PdfReader(BytesIO(content))
            text_content = "\n".join(
                page.extract_text() or "" for page in reader.pages
            )
        except Exception as e:
            logger.warning(f"PDF text extraction failed: {e}")
            text_content = f"[PDF 解析失败: {e}]"
    else:
        try:
            text_content = content.decode("utf-8")
        except UnicodeDecodeError:
            text_content = content.decode("latin-1", errors="replace")

    doc = KnowledgeDocument(title=title, content=text_content, source_type="file", file_path=filepath)
    db.add(doc)
    await db.commit()
    await db.refresh(doc)

    # 增量同步到向量库
    llm = _get_llm_service()
    if llm and llm._knowledge_base:
        n = await llm._knowledge_base.add_document(doc.id, doc.title, doc.content)
        doc.chunk_count = n
        await db.commit()

    return {"code": 0, "id": doc.id, "file_path": filepath, "chunk_count": doc.chunk_count}


@router.delete("/api/knowledge/documents/{doc_id}", tags=["knowledge"])
async def delete_document(doc_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(KnowledgeDocument).where(KnowledgeDocument.id == doc_id))
    doc = result.scalar_one_or_none()
    if doc is None:
        raise HTTPException(status_code=404, detail="Document not found")
    if doc.file_path and os.path.exists(doc.file_path):
        os.remove(doc.file_path)

    # 先从向量库删除
    llm = _get_llm_service()
    if llm and llm._knowledge_base:
        await llm._knowledge_base.delete_document(doc_id)

    await db.delete(doc)
    await db.commit()
    return {"code": 0, "msg": "ok"}


@router.post("/api/knowledge/rebuild", tags=["knowledge"])
async def rebuild_index():
    await _get_llm_service().rebuild_knowledge_base()
    return {"code": 0, "msg": "ok"}


# ═══════════════════════════════════════════════════════════════════
#  LiveTalking Sessions
# ═══════════════════════════════════════════════════════════════════

@router.get("/api/livetalking/sessions", tags=["livetalking"])
async def get_livetalking_sessions():
    """获取 LiveTalking 活跃 session 列表（供前端选择）"""
    from app.main import app
    sessions = await app.state.lt_client.fetch_sessions()
    return {"code": 0, "sessions": sessions}


# ═══════════════════════════════════════════════════════════════════
#  Livestream Control
# ═══════════════════════════════════════════════════════════════════

from app.services.play_queue import PlayQueue
from app.services.script_manager import ScriptManager
from app.services.danmaku.manager import MultiPlatformCollector
from app.services.danmaku.base import DanmakuMessage
from app.services.intent_service import IntentService
from app.services.live_analytics import LiveAnalytics


intent_service = IntentService()
live_analytics = LiveAnalytics()


async def _get_or_create_queue():
    """懒初始化播放队列（直播启动时）"""
    from app.main import app
    from app.database import async_session

    if app.state.play_queue is None:
        script_mgr = ScriptManager(async_session)
        queue = PlayQueue(script_manager=script_mgr)
        app.state.play_queue = queue
        app.state.script_manager = script_mgr

    return app.state.play_queue


@router.post("/api/livestream/start", tags=["livestream"])
async def start_livestream(req: LivestreamStartRequest):
    """启动直播：连接弹幕 + 连接数字人 + 启动队列"""
    from app.main import app
    from app.database import async_session

    llm = app.state.llm_service
    lt_client = app.state.lt_client
    queue = await _get_or_create_queue()

    # 每次队列变更自动广播到前端（put_high/put_low/get_next 内部触发）
    queue.set_on_change(lambda: _broadcast_queue_update(queue))

    # 1. 重新加载最新人设（前端可能刚改了 persona）
    async with async_session() as db:
        persona = await _get_or_create_persona(db)
        llm.persona = persona.to_dict()

    # 2. 连接 LiveTalking
    lt_client.set_session(req.session_id)
    await lt_client.connect()

    # ── 播放调度（SSE 主力 + 轮询兜底）──
    _playback_lock = asyncio.Lock()       # 防止重复出队

    async def do_send(item):
        """发送一条到 LiveTalking"""
        if item.type == "video" and item.content:
            await lt_client.load_media(item.content)
        elif item.type == "audio" and item.content:
            await lt_client.send_audio(item.content)
        else:
            await lt_client.send_text(item.content)
        if item.source == "script":
            live_analytics.record_script_play()
        await _broadcast_status({
            "type": "playback_started",
            "item_id": item.id,
            "source": item.source,
            "content_preview": item.content[:80],
        })

    async def try_play_next():
        """出队并发送（带锁，同一时刻只执行一次）"""
        if _playback_lock.locked():
            return
        async with _playback_lock:
            # 阻塞等待队列有数据
            while True:
                item = await queue.get_next()
                if item is not None:
                    break
                await asyncio.sleep(0.3)
            await do_send(item)

    # SSE 回调（主力）
    async def on_playback_end():
        await try_play_next()
    lt_client.on_playback_ended(on_playback_end)

    # 3. 连接弹幕平台
    app.state.collector = MultiPlatformCollector()

    async def on_danmaku(msg: DanmakuMessage):
        await _broadcast_event(msg)
        app.state._danmaku_count = getattr(app.state, '_danmaku_count', 0) + 1

        llm = app.state.llm_service
        if msg.msg_type == "danmaku" and llm:
            live_analytics.record_danmaku()
            intent = intent_service.classify(msg.content)
            reply = await llm.generate_reply(msg.content, msg.sender, intent=intent)
            if reply:
                from app.services.play_queue import QueueItem
                await queue.put_high(QueueItem(
                    type="text", content=reply, source="danmaku",
                    metadata={
                        "sender": msg.sender,
                        "original": msg.content,
                        "intent": intent,
                    },
                ))
                live_analytics.record_ai_reply(intent)
        elif msg.msg_type == "gift":
            from app.services.play_queue import QueueItem
            await queue.put_high(QueueItem(
                type="text", content=f"谢谢{msg.sender}的{msg.content}！", source="gift",
                metadata={"sender": msg.sender},
            ))
        elif msg.msg_type == "follow":
            from app.services.play_queue import QueueItem
            await queue.put_high(QueueItem(
                type="text", content=f"欢迎{msg.sender}关注直播间！", source="follow",
                metadata={"sender": msg.sender},
            ))

    app.state.collector.on_message(on_danmaku)
    # 保存 handler 引用供 mock 接口使用
    app.state._danmaku_handler = on_danmaku
    live_analytics.start()
    await app.state.collector.connect(req.platform, req.room_id)

    # 4. 启动队列自动补位
    await queue.start_auto_fill(min_size=_settings.queue_min_size, interval=_settings.queue_auto_fill_interval)

    # 5. 记录直播状态
    app.state._livestream_running = True
    app.state._room_id = req.room_id
    app.state._session_id = req.session_id
    app.state._danmaku_count = 0

    # 6. 首次触发：手动启动第一次出队播放
    asyncio.create_task(try_play_next())

    await _broadcast_status({"type": "status_change", "running": True, "room_id": req.room_id})
    logger.info(f"Livestream started: room={req.room_id}, session={req.session_id}")
    return {"code": 0, "msg": "ok"}


@router.get("/api/queue", tags=["queue"])
async def get_queue():
    """获取当前播放队列快照（HTTP 轮询降级方案）"""
    from app.main import app
    queue = app.state.play_queue
    if queue is None:
        return {"high": [], "low": []}
    return await queue.snapshot()


@router.post("/api/livestream/stop", tags=["livestream"])
async def stop_livestream():
    """停止直播"""
    from app.main import app

    # 停止弹幕
    if app.state.collector:
        try:
            await app.state.collector.disconnect()
        except Exception as e:
            logger.warning(f"Disconnect collector error: {e}")
        app.state.collector = None

    # 停止队列
    if app.state.play_queue:
        await app.state.play_queue.stop_auto_fill()
        await app.state.play_queue.clear()

    # 断开 LiveTalking（保留 session）
    if app.state.lt_client:
        await app.state.lt_client.disconnect()

    app.state._livestream_running = False
    live_analytics.stop()
    await _broadcast_status({"type": "status_change", "running": False})
    logger.info("Livestream stopped")
    return {"code": 0, "msg": "ok"}


@router.post("/api/mock/danmaku", tags=["mock"])
async def mock_danmaku(
    content: str = Form(default="主播好厉害！"),
    sender: str = Form(default="测试观众"),
    msg_type: str = Form(default="danmaku"),
):
    """模拟弹幕/礼物/关注事件（仅测试用）"""
    from app.main import app
    handler = getattr(app.state, '_danmaku_handler', None)
    if handler is None:
        raise HTTPException(status_code=400, detail="直播未启动，无法模拟弹幕")

    from app.services.danmaku.base import DanmakuMessage
    msg = DanmakuMessage(
        platform="mock",
        sender=sender,
        content=content,
        msg_type=msg_type,
    )
    await handler(msg)
    logger.info(f"Mock danmaku: [{msg_type}] {sender}: {content}")
    return {"code": 0, "msg": "ok"}


@router.get("/api/livestream/status", response_model=LivestreamStatusResponse, tags=["livestream"])
async def get_livestream_status():
    """获取直播状态"""
    from app.main import app
    queue = app.state.play_queue
    running = getattr(app.state, '_livestream_running', False)
    return LivestreamStatusResponse(
        running=running,
        room_id=getattr(app.state, '_room_id', ''),
        session_id=getattr(app.state, '_session_id', ''),
        queue_high_count=queue.high_length if queue else 0,
        queue_low_count=queue.low_length if queue else 0,
        danmaku_count=getattr(app.state, '_danmaku_count', 0),
        is_speaking=False,
    )


@router.get("/api/analytics/live/current", tags=["analytics"])
async def get_current_live_analytics():
    """获取当前直播场次的实时运营统计。"""
    return live_analytics.get_current()


@router.post("/api/livestream/interrupt", tags=["livestream"])
async def interrupt_livestream():
    """打断当前播放"""
    from app.main import app
    if app.state.lt_client:
        await app.state.lt_client.interrupt()
    return {"code": 0, "msg": "ok"}


# ═══════════════════════════════════════════════════════════════════
#  WebSocket（前端实时事件推送）
# ═══════════════════════════════════════════════════════════════════

_ws_clients: set[WebSocket] = set()


async def _broadcast_event(msg: DanmakuMessage):
    """广播弹幕事件给所有前端 WebSocket 客户端"""
    data = {
        "type": msg.msg_type,
        "platform": msg.platform,
        "sender": msg.sender,
        "content": msg.content,
        "timestamp": msg.timestamp,
    }
    await _broadcast(data)


async def _broadcast_queue_update(queue: PlayQueue):
    """广播队列更新"""
    snapshot = await queue.snapshot()
    await _broadcast({"type": "queue_update", "data": snapshot})


async def _broadcast_status(data: dict):
    """广播状态变更"""
    await _broadcast(data)


async def _broadcast(data: dict):
    """向所有已连接的 WebSocket 客户端发送消息"""
    dead: set[WebSocket] = set()
    for ws in _ws_clients:
        try:
            await ws.send_json(data)
        except Exception:
            dead.add(ws)
    _ws_clients.difference_update(dead)


@router.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    """前端 WebSocket 连接"""
    await ws.accept()
    _ws_clients.add(ws)
    logger.info(f"Frontend WS connected (total={len(_ws_clients)})")
    try:
        while True:
            # 仅保持连接存活，实际数据通过 _broadcast 发送
            data = await ws.receive_text()
    except WebSocketDisconnect:
        pass
    except Exception as e:
        logger.warning(f"WS error: {e}")
    finally:
        _ws_clients.discard(ws)
        logger.info(f"Frontend WS disconnected (total={len(_ws_clients)})")
