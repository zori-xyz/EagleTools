# app/domain/services/bot_api.py
from __future__ import annotations

from typing import Any

import httpx

from app.common.config import settings


async def bot_get_profile(telegram_id: int | None) -> dict[str, Any] | None:
    """
    Backend -> Bot (source of truth)

    Expected bot response example:
    {
      "plan": "free" | "premium",
      "limits": {"daily_downloads": 10},
      "usage": {"downloads_today": 3},  # optional
      "referrals_count": 2,
      "profile": {"first_name":"...", "last_name":"...", "username":"...", "photo_url":"..."}
    }
    """
    if not telegram_id:
        return None
    if not settings.bot_api_url:
        return None

    base = settings.bot_api_url.rstrip("/")
    url = f"{base}/internal/profile"

    headers: dict[str, str] = {}
    if settings.bot_api_key:
        headers["X-Bot-Api-Key"] = settings.bot_api_key

    async with httpx.AsyncClient(timeout=5.0) as client:
        r = await client.get(url, params={"telegram_id": telegram_id}, headers=headers)
        if r.status_code == 404:
            return None
        r.raise_for_status()
        data = r.json()
        return data if isinstance(data, dict) else None