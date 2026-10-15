###############################################################################
#  MultiPlatformCollector — 平台弹幕聚合器（每次仅连一个平台）
###############################################################################

from app.services.danmaku.base import BaseDanmakuCollector, DanmakuMessage
from app.utils.logger import logger


class MultiPlatformCollector:
    """管理弹幕平台连接，单次只连一个平台"""

    def __init__(self):
        self._collector: BaseDanmakuCollector | None = None
        self._platform: str = ""
        self._callbacks: list = []

    def on_message(self, callback):
        """注册回调"""
        self._callbacks.append(callback)

    async def _forward(self, msg: DanmakuMessage):
        for cb in self._callbacks:
            try:
                await cb(msg)
            except Exception:
                pass

    async def connect(self, platform: str, room_id: str):
        """连接到指定平台直播间"""
        # 先断开已有连接
        await self.disconnect()

        if platform == "bilibili":
            from app.services.danmaku.bilibili import BilibiliCollector
            self._collector = BilibiliCollector(room_id)
        elif platform == "douyin":
            from app.services.danmaku.douyin import DouyinCollector
            self._collector = DouyinCollector(room_id)
        elif platform == "wxlive":
            from app.services.danmaku.wxlive import WxliveCollector
            self._collector = WxliveCollector(room_id)
        elif platform == "kuaishou":
            logger.warning("Kuaishou collector not yet implemented")
            return
        else:
            logger.error(f"Unknown platform: {platform}")
            return

        self._collector.on_message(self._forward)
        await self._collector.connect(room_id)
        self._platform = platform
        logger.info(f"Connected to {platform} room {room_id}")

    async def disconnect(self):
        """断开当前连接"""
        if self._collector:
            try:
                await self._collector.disconnect()
            except Exception as e:
                logger.warning(f"Disconnect error: {e}")
            self._collector = None
            self._platform = ""
            logger.info("Danmaku collector disconnected")
