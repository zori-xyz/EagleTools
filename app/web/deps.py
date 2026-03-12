# app/web/deps.py
from __future__ import annotations

import hashlib
import hmac
import json
import time
from urllib.parse import parse_qsl, unquote

from fastapi import Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.config import settings
from app.infra.db.models.user import User
from app.infra.db.session import get_session

# ──────────────────────────────────────────────
# Telegram initData validation
# https://core.telegram.org/bots/webapps#validating-data-received-via-the-mini-app
# ──────────────────────────────────────────────

_MAX_AGE_SEC = 86_400  # 24 h


def _make_secret(bot_token: str) -> bytes:
    return hmac.new(b"WebAppData", bot_token.encode(), hashlib.sha256).digest()


def _verify_init_data(init_data: str, bot_token: str, *, max_age: int = _MAX_AGE_SEC) -> dict:
    """
    Validate Telegram WebApp initData string.
    Returns parsed fields dict on success.
    Raises HTTPException(401) on any failure.
    """
    if not init_data:
        raise HTTPException(status_code=401, detail="missing_init_data")

    params = dict(parse_qsl(init_data, keep_blank_values=True))
    received_hash = params.pop("hash", None)
    if not received_hash:
        raise HTTPException(status_code=401, detail="missing_hash")

    # Check timestamp freshness
    auth_date = params.get("auth_date", "0")
    try:
        if time.time() - int(auth_date) > max_age:
            raise HTTPException(status_code=401, detail="init_data_expired")
    except ValueError:
        raise HTTPException(status_code=401, detail="invalid_auth_date")

    # Build data-check string (sorted, key=value, newline-separated)
    data_check = "\n".join(
        f"{k}={v}"
        for k, v in sorted(params.items())
    )

    secret = _make_secret(bot_token)
    expected = hmac.new(secret, data_check.encode(), hashlib.sha256).hexdigest()

    if not hmac.compare_digest(expected, received_hash):
        raise HTTPException(status_code=401, detail="invalid_hash")

    return params


def _parse_user_from_params(params: dict) -> dict:
    """Extract and parse the 'user' JSON field from initData params."""
    raw = params.get("user", "")
    if not raw:
        raise HTTPException(status_code=401, detail="missing_user_field")
    try:
        return json.loads(unquote(raw))
    except Exception:
        raise HTTPException(status_code=401, detail="invalid_user_field")


# ──────────────────────────────────────────────
# DB upsert — saves profile info on every open
# ──────────────────────────────────────────────

async def _upsert_user(session: AsyncSession, tg_data: dict) -> User:
    """
    Get or create user by tg_id.
    Always updates first_name / last_name / username / language_code.
    photo_url is NOT available from initData — it stays as-is in DB.
    """
    tg_id = int(tg_data["id"])

    result = await session.execute(select(User).where(User.tg_id == tg_id))
    user = result.scalar_one_or_none()

    first_name = str(tg_data.get("first_name", "") or "").strip()
    last_name   = str(tg_data.get("last_name",  "") or "").strip()
    username    = str(tg_data.get("username",    "") or "").strip()
    lang        = str(tg_data.get("language_code", "") or "").strip()

    if user is None:
        user = User(tg_id=tg_id)
        session.add(user)

    # Always refresh profile fields
    if first_name:
        user.first_name    = first_name
    if last_name:
        user.last_name     = last_name
    if username:
        user.username      = username
    if lang:
        user.language_code = lang

    await session.commit()
    await session.refresh(user)
    return user


# ──────────────────────────────────────────────
# FastAPI dependency
# ──────────────────────────────────────────────

async def get_tg_user(
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> User:
    """
    FastAPI dependency.
    Reads X-TG-INITDATA header, validates it, upserts user in DB.
    """
    init_data = request.headers.get("X-TG-INITDATA", "").strip()

    # DEV MODE: bypass auth with a fixed tg_id from .env
    if not init_data and settings.debug and settings.dev_tg_user_id:
        result = await session.execute(
            select(User).where(User.tg_id == settings.dev_tg_user_id)
        )
        user = result.scalar_one_or_none()
        if user is None:
            user = User(tg_id=settings.dev_tg_user_id, first_name="Dev", username="devuser")
            session.add(user)
            await session.commit()
            await session.refresh(user)
        return user

    params = _verify_init_data(init_data, settings.effective_webapp_secret)
    tg_data = _parse_user_from_params(params)
    return await _upsert_user(session, tg_data)


# Alias used in app.py
get_current_user = get_tg_user