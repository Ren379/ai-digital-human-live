###############################################################################
#  ScriptManager — 话术随机选取
###############################################################################

import random
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.models import Script
from app.services.play_queue import QueueItem
from app.utils.logger import logger


class ScriptManager:
    """话术库管理 + 随机选取（避免短期重复）"""

    def __init__(self, db_session_factory):
        self._db_factory = db_session_factory
        self._recent_picks: list[int] = []
        self._max_recent = 5

    async def random_pick(self) -> QueueItem | None:
        async with self._db_factory() as session:
            stmt = select(Script).where(Script.enabled == True).order_by(Script.play_count.asc())
            result = await session.execute(stmt)
            scripts = result.scalars().all()

            if not scripts:
                logger.warning("No active scripts available for auto-fill")
                return None

            candidates = [s for s in scripts if s.id not in self._recent_picks]
            if not candidates:
                candidates = scripts
                self._recent_picks.clear()

            total_plays = sum(s.play_count + 1 for s in candidates)
            if total_plays == 0:
                weights = [1] * len(candidates)
            else:
                max_play = max(s.play_count for s in candidates) + 2
                weights = [max_play - s.play_count for s in candidates]

            chosen = random.choices(candidates, weights=weights, k=1)[0]
            chosen.play_count += 1
            chosen.last_used_at = datetime.now()
            await session.commit()

            self._recent_picks.append(chosen.id)
            if len(self._recent_picks) > self._max_recent:
                self._recent_picks.pop(0)

            item = QueueItem(
                type=chosen.type,
                content=chosen.content if chosen.type == "text" else (chosen.file_path or ""),
                source="script",
                level="low",
                metadata={"script_id": chosen.id, "title": chosen.title},
            )
            logger.info(f"Auto-fill picked script: [{chosen.id}] {chosen.title}")
            return item
