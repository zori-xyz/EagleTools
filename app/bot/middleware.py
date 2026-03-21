# app/bot/middleware.py
from __future__ import annotations

import time
from collections import defaultdict
from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware
from aiogram.types import Message, TelegramObject


class RateLimitMiddleware(BaseMiddleware):
    """
    Простой in-memory rate limiter для бота.
    Лимит: max_calls запросов за window_sec секунд на пользователя.
    """

    def __init__(self, max_calls: int = 10, window_sec: int = 60) -> None:
        self.max_calls  = max_calls
        self.window_sec = window_sec
        self._buckets: dict[int, list[float]] = defaultdict(list)

    def _is_allowed(self, uid: int) -> bool:
        now    = time.monotonic()
        cutoff = now - self.window_sec
        bucket = [t for t in self._buckets[uid] if t > cutoff]
        self._buckets[uid] = bucket
        if len(bucket) >= self.max_calls:
            return False
        self._buckets[uid].append(now)
        return True

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        uid: int | None = None
        if hasattr(event, "from_user") and event.from_user:
            uid = event.from_user.id

        if uid is not None and not self._is_allowed(uid):
            if isinstance(event, Message):
                try:
                    await event.reply("⏳ Слишком много запросов — подожди минуту.")
                except Exception:
                    pass
            return  # блокируем

        return await handler(event, data)