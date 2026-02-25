from __future__ import annotations

import asyncio
from dataclasses import dataclass


class QueueFull(Exception):
    pass


@dataclass(frozen=True)
class QueueTicket:
    position: int
    release: callable


class UserQueue:
    """
    Per-user semaphore + bounded waiting list.

    - max_in_flight: сколько задач одновременно (у нас 1, чтобы не лагало ffmpeg/stt)
    - max_queue: максимум ожидающих + выполняемых (у нас 3)
    """
    def __init__(self, *, max_in_flight: int = 1, max_queue: int = 3) -> None:
        self._sem = asyncio.Semaphore(max_in_flight)
        self._max_queue = max_queue
        self._lock = asyncio.Lock()
        self._in_system = 0  # executing + waiting

    async def acquire(self) -> QueueTicket:
        async with self._lock:
            if self._in_system >= self._max_queue:
                raise QueueFull()
            self._in_system += 1
            # позиция: 1 = либо сразу выполняется, либо первый в ожидании
            position = self._in_system

        await self._sem.acquire()

        def _release() -> None:
            self._sem.release()

        return QueueTicket(position=position, release=_release)

    async def done(self) -> None:
        async with self._lock:
            if self._in_system > 0:
                self._in_system -= 1

    async def size(self) -> int:
        async with self._lock:
            return self._in_system