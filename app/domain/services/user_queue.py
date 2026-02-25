from __future__ import annotations

import asyncio
from collections import deque
from dataclasses import dataclass
from typing import Awaitable, Callable, Deque, Dict, Optional


class QueueFull(RuntimeError):
    pass


@dataclass
class JobView:
    pending_pos: int  # 1..N среди pending
    pending_total: int
    has_running: bool
    total: int  # running + pending


@dataclass
class _Job:
    uid: int
    runner: Callable[[], Awaitable[None]]


class UserQueue:
    """
    Очередь задач PER-USER.
    - max_total: ограничение на (running + pending) на одного юзера
    - sequential: задачи одного юзера выполняются строго по очереди
    - on_change: коллбек при изменении состояния очереди для uid
    """

    def __init__(
        self,
        *,
        max_total: int = 3,
        on_change: Optional[Callable[[int], Awaitable[None]]] = None,
    ) -> None:
        self._max_total = max_total
        self._on_change = on_change

        self._locks: Dict[int, asyncio.Lock] = {}
        self._queues: Dict[int, Deque[_Job]] = {}
        self._running: Dict[int, bool] = {}

    def set_on_change(self, cb: Optional[Callable[[int], Awaitable[None]]]) -> None:
        self._on_change = cb

    def _get_lock(self, uid: int) -> asyncio.Lock:
        lock = self._locks.get(uid)
        if lock is None:
            lock = asyncio.Lock()
            self._locks[uid] = lock
        return lock

    def _get_q(self, uid: int) -> Deque[_Job]:
        q = self._queues.get(uid)
        if q is None:
            q = deque()
            self._queues[uid] = q
        return q

    def _pending_count(self, uid: int) -> int:
        q = self._queues.get(uid)
        return len(q) if q else 0

    def _has_running(self, uid: int) -> bool:
        return bool(self._running.get(uid))

    def size_total(self, uid: int) -> int:
        return self._pending_count(uid) + (1 if self._has_running(uid) else 0)

    def view_for_new_job(self, uid: int) -> JobView:
        """
        Вью для job, который только что добавили в конец pending.
        pending_pos = pending_total (последний).
        """
        pending_total = self._pending_count(uid)
        has_running = self._has_running(uid)
        total = pending_total + (1 if has_running else 0)
        return JobView(
            pending_pos=pending_total if pending_total > 0 else 1,
            pending_total=pending_total,
            has_running=has_running,
            total=total,
        )

    def view_current(self, uid: int) -> JobView:
        pending_total = self._pending_count(uid)
        has_running = self._has_running(uid)
        total = pending_total + (1 if has_running else 0)
        return JobView(
            pending_pos=1,
            pending_total=pending_total,
            has_running=has_running,
            total=total,
        )

    async def enqueue(self, *, uid: int, runner: Callable[[], Awaitable[None]]) -> JobView:
        """
        Добавляет задачу. Возвращает JobView.
        Может поднять QueueFull.
        """
        lock = self._get_lock(uid)
        async with lock:
            total = self.size_total(uid)
            if total >= self._max_total:
                raise QueueFull("queue_full")

            q = self._get_q(uid)
            q.append(_Job(uid=uid, runner=runner))

            if not self._has_running(uid):
                self._running[uid] = True
                asyncio.create_task(self._worker(uid))

            view = self.view_for_new_job(uid)

        await self._notify(uid)
        return view

    async def _notify(self, uid: int) -> None:
        cb = self._on_change
        if cb is None:
            return
        try:
            await cb(uid)
        except Exception:
            # не ломаем очередь из-за UI
            pass

    async def _worker(self, uid: int) -> None:
        lock = self._get_lock(uid)
        try:
            while True:
                async with lock:
                    q = self._get_q(uid)
                    if not q:
                        self._running[uid] = False
                        break
                    job = q.popleft()

                await self._notify(uid)

                try:
                    await job.runner()
                except Exception:
                    # runner сам покажет ошибку пользователю; тут не падаем
                    pass

                await self._notify(uid)

        finally:
            async with lock:
                self._running[uid] = False
            await self._notify(uid)