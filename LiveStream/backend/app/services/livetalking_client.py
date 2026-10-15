###############################################################################
#  LiveTalkingClient — LiveTalking HTTP + SSE 客户端
#
#  Session 选择流程:
#    1. 前端调用 GET /api/livetalking/sessions → 后端转发到 LiveTalking
#    2. 用户在 Dashboard 从下拉列表选择 sessionid
#    3. 启动直播时将 sessionid 传入
#
#  LiveTalking API（参考 docs/api.md）:
#    POST /human        — 发送文字（type: "echo" 直接 TTS）
#    POST /humanaudio   — 上传音频文件
#    POST /is_speaking  — 查询是否正在说话
#    POST /interrupt_talk — 打断
#    GET  /sse?sessionid=... — SSE 事件流（接收 status: start/end）
###############################################################################

import asyncio
import json
import os
from typing import Callable, Optional

import httpx
import aiohttp
from app.utils.logger import logger


class LiveTalkingClient:
    """管理与 LiveTalking 服务器的连接（HTTP + SSE）"""

    def __init__(self, base_url: str = "http://127.0.0.1:8010"):
        self.base_url = base_url.rstrip("/")
        self.session_id: Optional[str] = None
        self._http: Optional[httpx.AsyncClient] = None
        self._sse_task: Optional[asyncio.Task] = None
        self._playback_callbacks: list[Callable] = []
        self._running = False
        self._http = httpx.AsyncClient(timeout=30.0)

    # ── Session 管理 ──────────────────────────────────────────────

    async def fetch_sessions(self) -> list[dict]:
        """获取 LiveTalking 活跃 session 列表"""
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.get(f"{self.base_url}/api/admin/sessions")
                data = resp.json()
                if data.get("code") == 0:
                    sessions = data.get("data", {}).get("sessions", [])
                    logger.info(f"Fetched {len(sessions)} LiveTalking sessions")
                    return sessions
                else:
                    logger.warning(f"LiveTalking sessions API error: {data}")
                    return []
        except Exception as e:
            logger.error(f"Failed to fetch LiveTalking sessions: {e}")
            return []

    def set_session(self, session_id: str):
        """设置要使用的 session"""
        self.session_id = session_id
        logger.info(f"LiveTalking session set: {session_id}")

    # ── 连接 ──────────────────────────────────────────────────────

    async def connect(self):
        """建立 HTTP 客户端 + SSE 连接"""
        if not self.session_id:
            raise ValueError("session_id not set, call set_session() first")

        self._running = True

        # 启动 SSE 监听
        self._sse_task = asyncio.create_task(self._sse_connect())
        logger.info(f"LiveTalkingClient connected via SSE (session={self.session_id})")

    async def disconnect(self):
        """断开连接"""
        self._running = False

        if self._sse_task:
            self._sse_task.cancel()
            try:
                await self._sse_task
            except asyncio.CancelledError:
                pass
            self._sse_task = None

        # if self._http:
        #     await self._http.aclose()
        #     self._http = None

        self._playback_callbacks.clear()

        logger.info("LiveTalkingClient disconnected")

    # ── SSE 监听（播放状态）────────────────────────────────────────

    async def _sse_connect(self):
        """SSE 客户端：GET /sse?sessionid=... → 监听播放 start/end 事件"""
        sse_url = f"{self.base_url}/sse?sessionid={self.session_id}"

        retry_delay = 1
        max_retry_delay = 30

        while self._running:
            session = None
            try:
                session = aiohttp.ClientSession()
                # 使用 aiohttp 流式读取 SSE
                async with session.get(sse_url) as resp:
                    if resp.status != 200:
                        logger.error(f"SSE connection failed: HTTP {resp.status}")
                        break

                    logger.info(f"SSE connected: {sse_url}")
                    retry_delay = 1

                    # 逐行读取 SSE 流
                    async for line in resp.content:
                        if not self._running:
                            break
                        try:
                            text = line.decode("utf-8").strip()
                            if not text or text.startswith(":"):
                                continue  # SSE 注释行或空行
                            if text.startswith("data: "):
                                data_str = text[6:]  # 去掉 "data: " 前缀
                                data = json.loads(data_str)
                                status = data.get("status")
                                if status == "end":
                                    logger.info("LiveTalking playback ended (SSE)")
                                    for cb in self._playback_callbacks:
                                        try:
                                            if asyncio.iscoroutinefunction(cb):
                                                await cb()
                                            else:
                                                cb()
                                        except Exception as exc:
                                            logger.warning(f"Playback callback error: {exc}")
                                elif status == "start":
                                    logger.info(f"LiveTalking playback started (SSE): {data.get('text', '')[:50]}")
                        except json.JSONDecodeError:
                            pass
                        except Exception as e:
                            logger.warning(f"SSE line parse error: {e}")

            except asyncio.CancelledError:
                break
            except aiohttp.ClientError as e:
                logger.warning(f"SSE connection error: {e}")
            except Exception as e:
                logger.error(f"SSE unexpected error: {e}")
            finally:
                if session and not session.closed:
                    await session.close()

            if self._running:
                logger.info(f"SSE reconnecting in {retry_delay}s...")
                await asyncio.sleep(retry_delay)
                retry_delay = min(retry_delay * 2, max_retry_delay)

        logger.info("SSE listener stopped")

    # ── 发送 ──────────────────────────────────────────────────────

    async def send_text(self, text: str):
        """通过 /human 接口发送文字（echo 模式直接 TTS）"""
        if not self._http:
            raise RuntimeError("Not connected")

        resp = await self._http.post(
            f"{self.base_url}/human",
            json={
                "sessionid": self.session_id,
                "text": text,
                "type": "echo",
            },
        )
        data = resp.json()
        if data.get("code") != 0:
            logger.warning(f"LiveTalking /human returned error: {data}")
        return data

    async def send_audio(self, audio_path: str):
        """通过 /humanaudio 接口上传音频文件"""
        if not self._http:
            raise RuntimeError("Not connected")

        if not os.path.exists(audio_path):
            logger.error(f"Audio file not found: {audio_path}")
            return {"code": -1, "msg": "File not found"}

        with open(audio_path, "rb") as f:
            resp = await self._http.post(
                f"{self.base_url}/humanaudio",
                data={"sessionid": self.session_id},
                files={"file": (os.path.basename(audio_path), f)},
            )
        data = resp.json()
        return data

    async def convert_media(self, video_path: str) -> dict:
        """上传视频到 LiveTalking 转换（解压为帧序列+音频），返回 {media_path, ...}"""
        if not self._http:
            raise RuntimeError("Not connected")

        if not os.path.exists(video_path):
            raise FileNotFoundError(f"Video file not found: {video_path}")

        with open(video_path, "rb") as f:
            resp = await self._http.post(
                f"{self.base_url}/convert_custom_media",
                files={"file": (os.path.basename(video_path), f)},
            )
        data = resp.json()
        if data.get("code") != 0:
            logger.error(f"convert_custom_media failed: {data}")
            raise RuntimeError(f"Convert media failed: {data.get('msg', 'unknown')}")
        logger.info(f"Media converted: {data['data']['media_path']}")
        return data["data"]

    async def load_media(self, media_path: str):
        """加载预转换的媒体并播放"""
        if not self._http:
            raise RuntimeError("Not connected")

        resp = await self._http.post(
            f"{self.base_url}/load_custom_media",
            json={
                "sessionid": self.session_id,
                "media_path": media_path,
            },
        )
        data = resp.json()
        if data.get("code") != 0:
            logger.warning(f"load_custom_media error: {data}")
        return data

    async def interrupt(self):
        """打断当前说话"""
        if not self._http:
            return
        resp = await self._http.post(
            f"{self.base_url}/interrupt_talk",
            json={"sessionid": self.session_id},
        )
        return resp.json()

    async def is_speaking(self) -> bool:
        """查询数字人是否正在说话（轮询降级方案）"""
        if not self._http:
            return False
        try:
            resp = await self._http.post(
                f"{self.base_url}/is_speaking",
                json={"sessionid": self.session_id},
            )
            data = resp.json()
            return data.get("data", False)
        except Exception:
            return False

    # ── 回调 ──────────────────────────────────────────────────────

    def on_playback_ended(self, callback: Callable):
        """注册播放结束回调"""
        self._playback_callbacks.append(callback)
