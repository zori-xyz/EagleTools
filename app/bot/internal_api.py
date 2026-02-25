# bot/internal_api.py
from __future__ import annotations

import os
from datetime import date
from typing import Any, Literal

from fastapi import FastAPI, Header, HTTPException, Query
from pydantic import BaseModel


# =====================
# Config (env)
# =====================
BOT_API_KEY = os.getenv("BOT_API_KEY", "")
if not BOT_API_KEY:
    # можно оставить пустым для локалки, но лучше всегда задавать
    # raise RuntimeError("BOT_API_KEY is required")
    pass


# =====================
# Data models (response)
# =====================
Plan = Literal["free", "premium"]


class ProfilePayload(BaseModel):
    first_name: str | None = None
    last_name: str | None = None
    username: str | None = None
    # ВАЖНО: не возвращаем прямой photo_url через bot token.
    # Позже сделаем proxy endpoint на backend для фото по file_id.
    photo_url: str | None = None


class InternalProfileOut(BaseModel):
    plan: Plan
    limits: dict[str, int]              # {"daily_downloads": 10}
    usage: dict[str, int] | None = None # {"downloads_today": 3} - опционально
    referrals_count: int
    profile: ProfilePayload | None = None
    as_of: str                          # YYYY-MM-DD


# =====================
# Storage layer (plug your DB here)
# =====================
async def get_user_state_from_bot_db(telegram_id: int) -> dict[str, Any] | None:
    """
    TODO: заменить на реальную БД бота.

    Должно вернуть:
      {
        "plan": "free"|"premium",
        "referrals_count": int,
        "daily_limit": int | None,   # optional override
        "downloads_today": int | None,
        "profile": {"first_name":..,"last_name":..,"username":..,"photo_url":..} | None
      }

    Сейчас заглушка: всегда FREE + лимит 10.
    """
    _ = telegram_id

    return {
        "plan": "free",
        "referrals_count": 0,
        "daily_limit": 10,
        "downloads_today": None,
        "profile": None,
    }


# =====================
# FastAPI
# =====================
app = FastAPI(title="EagleTools Bot Internal API", version="0.1.0")


def require_key(x_bot_api_key: str | None) -> None:
    if not BOT_API_KEY:
        return  # allow if not set (local/dev)
    if not x_bot_api_key or x_bot_api_key != BOT_API_KEY:
        raise HTTPException(status_code=401, detail="unauthorized")


@app.get("/internal/health")
async def health():
    return {"ok": True}


@app.get("/internal/profile", response_model=InternalProfileOut)
async def internal_profile(
    telegram_id: int = Query(..., ge=1),
    x_bot_api_key: str | None = Header(default=None, alias="X-Bot-Api-Key"),
):
    require_key(x_bot_api_key)

    state = await get_user_state_from_bot_db(telegram_id)
    if state is None:
        raise HTTPException(status_code=404, detail="not_found")

    plan: Plan = "premium" if str(state.get("plan", "free")).lower() == "premium" else "free"

    daily_limit = state.get("daily_limit")
    if not isinstance(daily_limit, int) or daily_limit <= 0:
        daily_limit = 10

    referrals_count = int(state.get("referrals_count") or 0)
    downloads_today = state.get("downloads_today")

    profile_obj = state.get("profile")
    profile = ProfilePayload(**profile_obj) if isinstance(profile_obj, dict) else None

    usage = None
    if isinstance(downloads_today, int) and downloads_today >= 0:
        usage = {"downloads_today": downloads_today}

    return InternalProfileOut(
        plan=plan,
        limits={"daily_downloads": int(daily_limit)},
        usage=usage,
        referrals_count=referrals_count,
        profile=profile,
        as_of=date.today().isoformat(),
    )


# =====================
# Run:
#   uvicorn bot.internal_api:app --host 127.0.0.1 --port 9001 --reload
# =====================