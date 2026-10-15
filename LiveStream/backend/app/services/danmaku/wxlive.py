###############################################################################
#  WxliveCollector — 微信视频号弹幕采集
#
#  依赖 wxlivespy (https://github.com/fire4nt/wxlivespy)
#  wxlivespy 通过浏览器自动化登录视频号后台，监听弹幕/礼物/进场事件，
#  并以 HTTP POST 方式转发到本采集器。
#
#  架构:
#    视频号后台 → wxlivespy (Puppeteer) → POST /wxlive → 本采集器
#
#  本采集器启动一个独立的 aiohttp HTTP 服务器接收回调，
#  wxlivespy 配置中将转发地址设为 http://localhost:8000/forward
###############################################################################

import asyncio
import json
from aiohttp import web

from app.services.danmaku.base import BaseDanmakuCollector, DanmakuMessage
from app.utils.logger import logger


class WxliveCollector(BaseDanmakuCollector):
    """微信视频号弹幕采集器（HTTP 回调接收，配合 wxlivespy 使用）"""

    def __init__(self, room_id: str = "",
                 listen_host: str = "0.0.0.0",
                 listen_port: int = 8000):
        super().__init__()
        self._room_id = room_id
        self._listen_host = listen_host
        self._listen_port = listen_port
        self._running = False
        self._app: web.Application | None = None
        self._runner: web.AppRunner | None = None
        self._seq_list: list[str] = []  # 去重用
        self._max_seq = 30

    # ── HTTP 路由 ─────────────────────────────────────────────────

    async def _handle_wxlive(self, request: web.Request):
        """接收 wxlivespy 推送的弹幕/事件"""
        try:
            data = await request.json()
        except Exception:
            return web.json_response({"code": -1, "message": "invalid json"})

        logger.debug(f"Wxlive received: {json.dumps(data, ensure_ascii=False)[:300]}")

        events = data.get("events", [])
        if not events:
            return web.json_response({"code": -1, "message": "no events"})

        for evt in events:
            # seq 去重
            seq = evt.get("seq", "")
            if seq and seq in self._seq_list:
                continue
            if seq:
                self._seq_list.append(seq)
                if len(self._seq_list) > self._max_seq:
                    self._seq_list.pop(0)

            decoded_type = evt.get("decoded_type", "")
            nickname = evt.get("nickname", "未知")
            content = evt.get("content", "")

            if decoded_type == "comment":
                dm = DanmakuMessage(
                    platform="wxlive", sender=nickname, content=content,
                    msg_type="danmaku", raw_data=evt,
                )
                logger.info(f"[视频号弹幕] {nickname}: {content}")
                await self._dispatch(dm)

            elif decoded_type == "enter":
                dm = DanmakuMessage(
                    platform="wxlive", sender=nickname,
                    content="进入了直播间",
                    msg_type="enter", raw_data=evt,
                )
                logger.info(f"[视频号进场] {nickname}")
                await self._dispatch(dm)

            elif decoded_type == "gift":
                gift_name = evt.get("gift_name", "礼物")
                dm = DanmakuMessage(
                    platform="wxlive", sender=nickname,
                    content=f"{gift_name}",
                    msg_type="gift", raw_data=evt,
                )
                logger.info(f"[视频号礼物] {nickname}: {gift_name}")
                await self._dispatch(dm)

            # elif decoded_type == "like":
            #     dm = DanmakuMessage(
            #         platform="wxlive", sender=nickname,
            #         content="点赞了直播间",
            #         msg_type="danmaku", raw_data=evt,
            #     )
            #     logger.info(f"[视频号点赞] {nickname}")
            #     await self._dispatch(dm)

        return web.json_response({"code": 200, "message": "ok"})

    # ── 连接管理 ──────────────────────────────────────────────────

    async def connect(self, room_id: str):
        """启动 HTTP 服务器接收 wxlivespy 回调"""
        self._room_id = room_id
        self._running = True

        self._app = web.Application()
        self._app.router.add_post("/forward", self._handle_wxlive)
        # 兼容 wxlivespy 可能发到根路径
        self._app.router.add_post("/", self._handle_wxlive)

        self._runner = web.AppRunner(self._app)
        await self._runner.setup()
        site = web.TCPSite(self._runner, self._listen_host, self._listen_port)
        await site.start()

        logger.info(
            f"Wxlive collector listening on http://{self._listen_host}:{self._listen_port}/wxlive"
        )
        logger.info("Configure wxlivespy to forward to this address")

    async def disconnect(self):
        """停止 HTTP 服务器"""
        self._running = False
        if self._runner:
            await self._runner.cleanup()
            self._runner = None
            self._app = None
        self._seq_list.clear()
        logger.info("Wxlive collector disconnected")
