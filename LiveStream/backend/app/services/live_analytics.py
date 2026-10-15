###############################################################################
#  LiveAnalytics — 当前直播场次内存统计
###############################################################################

import time
from datetime import datetime, timezone


class LiveAnalytics:
    """维护当前直播场次统计；后端重启后数据清零。"""

    def __init__(self):
        self.running = False
        self.started_at: str | None = None
        self.duration_seconds = 0
        self.danmaku_count = 0
        self.ai_reply_count = 0
        self.auto_script_count = 0
        self.product_consultation_count = 0
        self.intent_consultation_count = 0
        self._started_monotonic: float | None = None

    def start(self):
        """开始新场次并重置全部实时统计。"""
        self.running = True
        self.started_at = datetime.now(timezone.utc).isoformat()
        self.duration_seconds = 0
        self.danmaku_count = 0
        self.ai_reply_count = 0
        self.auto_script_count = 0
        self.product_consultation_count = 0
        self.intent_consultation_count = 0
        self._started_monotonic = time.monotonic()

    def stop(self):
        """停止当前场次并冻结最后直播时长。"""
        self._refresh_duration()
        self.running = False
        self._started_monotonic = None

    def record_danmaku(self):
        if self.running:
            self.danmaku_count += 1

    def record_ai_reply(self, intent: str):
        if not self.running:
            return
        self.ai_reply_count += 1
        if intent in {"product_sales", "product_info"}:
            self.product_consultation_count += 1
        if intent in {"product_sales", "objection"}:
            self.intent_consultation_count += 1

    def record_script_play(self):
        if self.running:
            self.auto_script_count += 1

    def _refresh_duration(self):
        if self.running and self._started_monotonic is not None:
            self.duration_seconds = max(
                0, int(time.monotonic() - self._started_monotonic)
            )

    def get_current(self) -> dict:
        self._refresh_duration()
        return {
            "running": self.running,
            "started_at": self.started_at,
            "duration_seconds": self.duration_seconds,
            "danmaku_count": self.danmaku_count,
            "ai_reply_count": self.ai_reply_count,
            "auto_script_count": self.auto_script_count,
            "product_consultation_count": self.product_consultation_count,
            "intent_consultation_count": self.intent_consultation_count,
        }
