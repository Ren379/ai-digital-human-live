###############################################################################
#  FastAPI 主入口
#
#  启动方式：
#    cd backend && python -m app.main
#    uvicorn app.main:app --port 8020
#    python backend/app/main.py  （项目根目录也支持）
###############################################################################

import sys, os

# 确保 backend/ 在 sys.path 中（支持从任意目录启动）
_backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _backend_dir not in sys.path:
    sys.path.insert(0, _backend_dir)

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import load_settings
from app.database import init_db, async_session
from app.utils.logger import logger

settings = load_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期：启动时初始化所有服务，关闭时清理资源"""
    logger.info("Starting LiveStream backend...")
    await init_db()
    logger.info("Database initialized")

    # 1. 加载 DB Settings（优先于 .env / 默认值）
    from app.models import Persona, AppSettings
    from sqlalchemy import select

    async with async_session() as db:
        # Persona
        result = await db.execute(select(Persona).limit(1))
        persona = result.scalar_one_or_none()
        if persona is None:
            persona = Persona(**Persona.default_dict())
            db.add(persona)
            await db.commit()
            await db.refresh(persona)
            logger.info("Created default persona")
        persona_dict = persona.to_dict()

        # AppSettings（DB 存储的配置，首次自动创建）
        result = await db.execute(select(AppSettings).limit(1))
        db_settings = result.scalar_one_or_none()
        if db_settings is None:
            db_settings = AppSettings(**AppSettings.defaults())
            db.add(db_settings)
            await db.commit()
            await db.refresh(db_settings)
            logger.info("Created default app settings")
        s = db_settings  # shorthand

    # 同步 key 到环境变量（LangChain / OpenAI SDK 从环境变量读取）
    import os
    if s.llm_api_key:
        os.environ["OPENAI_API_KEY"] = s.llm_api_key
    if s.embedding_api_key:
        os.environ["EMBEDDING_API_KEY"] = s.embedding_api_key

    # 2. 初始化 LLMService（使用 DB 中的配置）
    from app.services.llm_service import LLMService

    app.state.llm_service = LLMService(
        persona_dict,
        llm_api_key=s.llm_api_key,
        llm_base_url=s.llm_base_url,
        llm_model=s.llm_model,
        embedding_api_key=s.embedding_api_key,
        embedding_base_url=s.embedding_base_url,
        embedding_model=s.embedding_model,
    )
    try:
        await app.state.llm_service.init_knowledge_base()
    except Exception as e:
        logger.warning(f"Knowledge base init skipped: {e}")
    logger.info(f"LLM service initialized: model={s.llm_model}")

    # 3. 初始化 LiveTalking 客户端
    from app.services.livetalking_client import LiveTalkingClient

    app.state.lt_client = LiveTalkingClient(base_url=s.livetalking_base_url)
    logger.info(f"LiveTalking client initialized: {s.livetalking_base_url}")

    # 4. 播放队列和弹幕采集器在直播启动时懒初始化
    app.state.play_queue = None
    app.state.collector = None

    yield

    logger.info("Shutting down LiveStream backend...")
    if app.state.collector:
        try:
            await app.state.collector.disconnect()
        except Exception:
            pass


app = FastAPI(
    title="LiveStream",
    description="数字人直播控制系统",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins.split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 设置默认 state（lifespan 启动后会被覆盖）
app.state.llm_service = None
app.state.lt_client = None
app.state.play_queue = None
app.state.collector = None


@app.get("/api/health")
async def health_check():
    return {"status": "ok", "version": "0.1.0"}


# 注册所有路由
from app.api import router
app.include_router(router)

# 生产模式：托管前端编译产物
import os as _os
_frontend_dist = _os.path.join(_backend_dir, "..", "frontend", "dist")
if _os.path.isdir(_frontend_dist):
    from fastapi.staticfiles import StaticFiles
    app.mount("/", StaticFiles(directory=_frontend_dist, html=True), name="frontend")
    logger.info(f"Serving frontend from: {_frontend_dist}")


if __name__ == "__main__":
    import uvicorn
    logger.info(f"Starting backend on {settings.app_host}:{settings.app_port}")
    logger.info(f"API docs: http://localhost:{settings.app_port}/docs")
    uvicorn.run(
        "app.main:app",
        host=settings.app_host,
        port=settings.app_port,
        reload=True,
    )
