###############################################################################
#  BilibiliCollector — B 站弹幕采集
#  参考: /Users/hengzhong/Study/ipcam/aigc/digital-human-livestream/danmaku_collector.py
###############################################################################

import asyncio
import time
import json
from bilibili_api import live

from app.services.danmaku.base import BaseDanmakuCollector, DanmakuMessage
from app.utils.logger import logger


class BilibiliCollector(BaseDanmakuCollector):
    """B 站直播间弹幕/礼物/关注事件采集器，基于 WebSocket"""

    def __init__(self, room_id: str = ""):
        super().__init__()
        self._room_id = int(room_id) if room_id else 0
        self._live_danmaku: live.LiveDanmaku | None = None
        self._running = False

    # ── 事件处理器 ────────────────────────────────────────────────

    async def _on_danmaku(self, event: dict):
        """处理弹幕 DANMU_MSG"""
        try:
            info = event.get("data", {}).get("info", [])
            if len(info) < 3:
                return
            content = info[1]  # 弹幕文字
            sender_info = info[2]
            sender = sender_info[1] if len(sender_info) > 1 else "未知"

            msg = DanmakuMessage(
                platform="bilibili",
                sender=sender,
                content=str(content),
                msg_type="danmaku",
                raw_data=event.get("data", {}),
            )
            logger.info(f"[B站弹幕] {sender}: {content}")
            await self._dispatch(msg)
        except Exception as e:
            logger.warning(f"Parse danmaku error: {e}")

    async def _on_gift(self, event: dict):
        """处理礼物 SEND_GIFT"""
        try:
            data = event.get("data", {}).get("data", {})
            sender = data.get("uname", "未知")
            gift_name = data.get("giftName", "礼物")
            num = data.get("num", 1)
            content = f"{gift_name} x{num}"

            msg = DanmakuMessage(
                platform="bilibili",
                sender=sender,
                content=content,
                msg_type="gift",
                raw_data=data,
            )
            logger.info(f"[B站礼物] {sender}: {content}")
            await self._dispatch(msg)
        except Exception as e:
            logger.warning(f"Parse gift error: {e}")

    async def _on_interact(self, event: dict):
        """处理互动 INTERACT_WORD（关注/进入直播间）"""
        try:
            data = event.get("data", {}).get("data", {})
            # INTERACT_WORD 可能带有 pb_decoded
            pb = data.get("pb_decoded", {})
            if pb and isinstance(pb, dict):
                sender = pb.get("uname", "未知")
                msg_type_id = pb.get("msg_type", 0)
            else:
                sender = data.get("uname", "未知")
                msg_type_id = data.get("msg_type", 0)

            if not sender:
                return

            if msg_type_id == 2:
                msg_type = "follow"
                content = "关注了直播间"
            else:
                msg_type = "enter"
                content = "进入了直播间"

            msg = DanmakuMessage(
                platform="bilibili",
                sender=sender,
                content=content,
                msg_type=msg_type,
                raw_data=data,
            )
            logger.info(f"[B站互动] {sender}: {content}")
            await self._dispatch(msg)
        except Exception as e:
            logger.warning(f"Parse interact error: {e}")

    # ── 连接管理 ──────────────────────────────────────────────────

    async def connect(self, room_id: str):
        """连接 B 站直播间"""
        self._room_id = int(room_id)
        self._running = True

        self._live_danmaku = live.LiveDanmaku(
            room_display_id=self._room_id,
            max_retry=10,
            retry_after=5,
        )

        # 注册事件监听
        self._live_danmaku.add_event_listener("DANMU_MSG", self._on_danmaku)
        self._live_danmaku.add_event_listener("SEND_GIFT", self._on_gift)
        self._live_danmaku.add_event_listener("INTERACT_WORD", self._on_interact)

        try:
            await self._live_danmaku.connect()
            logger.info(f"Bilibili collector connected to room {self._room_id}")
        except Exception as e:
            logger.error(f"Bilibili connect failed: {e}")
            self._running = False
            raise

    async def disconnect(self):
        """断开连接"""
        self._running = False
        if self._live_danmaku:
            try:
                await self._live_danmaku.disconnect()
            except Exception:
                pass
            self._live_danmaku = None
        logger.info("Bilibili collector disconnected")
