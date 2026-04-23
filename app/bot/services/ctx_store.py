# app/bot/services/ctx_store.py
"""
Redis-backed per-user context store for the smart router.

Persists URL / file_id across bot restarts so that inline button callbacks
still work after a redeploy (within 30-minute TTL).

Falls back silently if Redis is unavailable — in-memory dict in smart_router
will handle the same-session case.
"""
from __future__ import annotations

import json
import logging
from typing import Any

from app.common.config import settings

log = logging.getLogger(__name__)

_CTX_TTL = 1800    # 30 minutes
_PANEL_TTL = 1800


def _get_redis():
    """Lazily create an async Redis client; returns None if not configured."""
    url = settings.effective_redis_url
    if not url:
        return None
    try:
        import redis.asyncio as aioredis  # type: ignore
        return aioredis.from_url(url, decode_responses=True)
    except Exception as e:
        log.debug("Redis unavailable: %s", e)
        return None


async def ctx_set(uid: int, data: dict) -> None:
    """
    Persist context for uid.  Message objects are serialised to plain data
    (file_id + filename) so they survive process restart.
    """
    r = _get_redis()
    if r is None:
        return
    serializable: dict[str, Any] = {}
    for k, v in data.items():
        if k == "orig_msg":
            # Flatten to file_id + filename for JSON storage
            try:
                from aiogram.types import Message as _Msg  # local import to avoid cycles
                if isinstance(v, _Msg):
                    if v.voice:
                        serializable["file_id"] = v.voice.file_id
                        serializable["filename"] = "voice.ogg"
                    elif v.audio:
                        serializable["file_id"] = v.audio.file_id
                        serializable["filename"] = v.audio.file_name or "audio"
                    elif v.video:
                        serializable["file_id"] = v.video.file_id
                        serializable["filename"] = "video.mp4"
                    elif v.document:
                        serializable["file_id"] = v.document.file_id
                        serializable["filename"] = v.document.file_name or "file"
            except Exception:
                pass
        else:
            serializable[k] = v
    try:
        async with r:
            await r.setex(f"bot:ctx:{uid}", _CTX_TTL, json.dumps(serializable))
    except Exception as e:
        log.debug("ctx_set failed uid=%s: %s", uid, e)


async def ctx_get(uid: int) -> dict:
    """Return stored context or empty dict."""
    r = _get_redis()
    if r is None:
        return {}
    try:
        async with r:
            raw = await r.get(f"bot:ctx:{uid}")
        if not raw:
            return {}
        return json.loads(raw)
    except Exception as e:
        log.debug("ctx_get failed uid=%s: %s", uid, e)
        return {}


async def ctx_del(uid: int) -> None:
    r = _get_redis()
    if r is None:
        return
    try:
        async with r:
            await r.delete(f"bot:ctx:{uid}")
    except Exception as e:
        log.debug("ctx_del failed uid=%s: %s", uid, e)
