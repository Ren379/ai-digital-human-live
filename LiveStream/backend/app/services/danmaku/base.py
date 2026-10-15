###############################################################################
#  BaseDanmakuCollector — 弹幕采集抽象基类
#  参考: /Users/hengzhong/Study/ipcam/aigc/digital-human-livestream/danmaku_collector.py
###############################################################################

import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Callable, Awaitable


@dataclass
class DanmakuMessage:
    """统一的弹幕/事件消息格式"""
    platform: str              # "bilibili" | "douyin" | "kuaishou"
    sender: str                # 发送者昵称
    content: str               # 消息内容
    timestamp: float = field(default_factory=time.time)
    msg_type: str = "danmaku"  # "danmaku" | "gift" | "follow" | "enter"
    raw_data: dict = field(default_factory=dict)


EventCallback = Callable[[DanmakuMessage], Awaitable[None]]


class BaseDanmakuCollector(ABC):
    """弹幕采集器抽象基类"""

    def __init__(self):
        self._callbacks: list[EventCallback] = []

    def on_message(self, callback: EventCallback):
        """注册消息回调"""
        self._callbacks.append(callback)

    async def _dispatch(self, msg: DanmakuMessage):
        """分发消息给所有注册的回调"""
        for cb in self._callbacks:
            try:
                await cb(msg)
            except Exception:
                pass

    @abstractmethod
    async def connect(self, room_id: str):
        """连接到指定直播间"""
        ...

    @abstractmethod
    async def disconnect(self):
        """断开连接"""
        ...
