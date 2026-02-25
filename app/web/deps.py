from __future__ import annotations

import hashlib
import hmac
import json
from dataclasses import dataclass
from typing import Any
from urllib.parse import parse_qsl

from fastapi import Depends, Header, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.config import settings
from app.infra.db.schema import User
from app.infra.db.session import get_session


@dataclass(slots=True)
class TgWebAppUser:
    tg_id: int
    username: str | None = None
    first_name: str | None = None
    last_name: str | None = None
    photo_url: str | None = None
    language_code: str | None = None


# -------------------------
# Telegram WebApp initData
# -------------------------

def _get_telegram_secret() -> str:
    """
    Telegram WebApp signature secret:
      secret_key = sha256(bot_token)
    So we need bot token here (or an explicit configured secret == bot token).
    """
    for name in (
        "telegram_webapp_secret",  # preferred explicit
        "telegram_bot_token",
        "bot_token",
        "TELEGRAM_WEBAPP_SECRET",
        "TELEGRAM_BOT_TOKEN",
        "BOT_TOKEN",
    ):
        val = getattr(settings, name, None)
        if val:
            return str(val).strip()
    raise RuntimeError("Telegram token/secret is not configured (TELEGRAM_WEBAPP_SECRET or TELEGRAM_BOT_TOKEN).")


def _dev_tg_id() -> int | None:
    val = getattr(settings, "dev_tg_user_id", None) or getattr(settings, "DEV_TG_USER_ID", None)
    if val is None:
        return None
    try:
        return int(val)
    except Exception:
        raise HTTPException(status_code=500, detail="bad_dev_tg_user_id")


def _looks_like_initdata(raw: str) -> bool:
    raw = (raw or "").strip()
    return ("hash=" in raw) and ("auth_date=" in raw)


def _verify_init_data(init_data: str, token: str) -> dict[str, str]:
    """
    https://core.telegram.org/bots/webapps#validating-data-received-via-the-web-app

    - Parse query string into key/value pairs
    - Extract 'hash'
    - data_check_string = '\n'.join('k=v' sorted by k)
    - secret_key = sha256(bot_token)
    - computed_hash = hmac_sha256(secret_key, data_check_string)
    """
    try:
        pairs = parse_qsl(init_data, keep_blank_values=True)
    except Exception:
        raise HTTPException(status_code=401, detail="invalid_init_data")

    data = dict(pairs)
    received_hash = data.pop("hash", None)
    if not received_hash:
        raise HTTPException(status_code=401, detail="missing_hash")

    data_check_string = "\n".join(f"{k}={v}" for k, v in sorted(data.items()))
    secret_key = hashlib.sha256(token.encode("utf-8")).digest()
    computed_hash = hmac.new(secret_key, data_check_string.encode("utf-8"), hashlib.sha256).hexdigest()

    if not hmac.compare_digest(computed_hash, received_hash):
        raise HTTPException(status_code=401, detail="bad_signature")

    return data


def _parse_tg_user(data: dict[str, str]) -> TgWebAppUser:
    raw_user = data.get("user")
    if not raw_user:
        raise HTTPException(status_code=401, detail="missing_user")

    try:
        u: dict[str, Any] = json.loads(raw_user)
    except Exception:
        raise HTTPException(status_code=401, detail="bad_user_json")

    tg_id = u.get("id")
    if not isinstance(tg_id, int):
        raise HTTPException(status_code=401, detail="bad_user_id")

    return TgWebAppUser(
        tg_id=tg_id,
        username=u.get("username"),
        first_name=u.get("first_name"),
        last_name=u.get("last_name"),
        photo_url=u.get("photo_url"),
        language_code=u.get("language_code"),
    )


async def get_tg_user(
    x_tg_initdata: str | None = Header(default=None, alias="X-TG-INITDATA"),
) -> TgWebAppUser:
    raw = (x_tg_initdata or "").strip()
    dev_id = _dev_tg_id()

    # dev bypass: only if initData missing OR not похож на initData
    if dev_id is not None and (not raw or not _looks_like_initdata(raw)):
        return TgWebAppUser(tg_id=dev_id)

    if not raw:
        raise HTTPException(status_code=401, detail="missing_initdata")

    token = _get_telegram_secret()
    data = _verify_init_data(raw, token)
    return _parse_tg_user(data)


# -------------------------
# DB user resolver (tg_id)
# -------------------------

def _apply_profile_upsert(user: User, tg: TgWebAppUser) -> bool:
    """
    Update user profile fields if columns exist AND new value is not None/empty.
    Returns True if something changed.
    """
    changed = False

    def set_if_present(attr: str, value: str | None) -> None:
        nonlocal changed
        if value is None:
            return
        if isinstance(value, str) and not value.strip():
            return
        if not hasattr(user, attr):
            return
        cur = getattr(user, attr, None)
        if cur != value:
            setattr(user, attr, value)
            changed = True

    set_if_present("username", tg.username)
    set_if_present("first_name", tg.first_name)
    set_if_present("last_name", tg.last_name)
    set_if_present("photo_url", tg.photo_url)
    set_if_present("language_code", tg.language_code)

    return changed


async def get_current_user(
    session: AsyncSession = Depends(get_session),
    tg: TgWebAppUser = Depends(get_tg_user),
) -> User:
    """
    Strict auth dependency:
      - validates initData (or dev bypass)
      - resolves User by tg_id
      - creates if absent
      - upserts Telegram profile fields (if schema supports)
    """
    res = await session.execute(select(User).where(User.tg_id == int(tg.tg_id)))
    user = res.scalar_one_or_none()

    if user is None:
        user = User(tg_id=int(tg.tg_id))
        session.add(user)
        _apply_profile_upsert(user, tg)
        await session.commit()
        await session.refresh(user)
        return user

    changed = _apply_profile_upsert(user, tg)
    if changed:
        await session.commit()
        await session.refresh(user)

    return user