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


def _get_bot_token() -> str:
    for name in (
        "telegram_webapp_secret",  # prefer explicit secret
        "telegram_bot_token",
        "bot_token",
        "TELEGRAM_WEBAPP_SECRET",
        "TELEGRAM_BOT_TOKEN",
        "BOT_TOKEN",
    ):
        val = getattr(settings, name, None)
        if val:
            return str(val).strip()
    raise RuntimeError("Telegram secret/token is not configured (TELEGRAM_WEBAPP_SECRET or TELEGRAM_BOT_TOKEN).")


def _dev_tg_id() -> int | None:
    val = getattr(settings, "dev_tg_user_id", None)
    if val is None:
        return None
    try:
        return int(val)
    except Exception:
        raise HTTPException(status_code=500, detail="bad_dev_tg_user_id")


def _looks_like_initdata(s: str) -> bool:
    # Реальное initData почти всегда содержит hash= и auth_date=
    s = (s or "").strip()
    return ("hash=" in s) and ("auth_date=" in s)


def _verify_telegram_init_data(init_data: str, secret: str) -> dict[str, str]:
    try:
        pairs = parse_qsl(init_data, keep_blank_values=True)
    except Exception:
        raise HTTPException(status_code=401, detail="invalid_init_data")

    data = dict(pairs)
    received_hash = data.pop("hash", None)
    if not received_hash:
        raise HTTPException(status_code=401, detail="missing_hash")

    data_check_string = "\n".join(f"{k}={v}" for k, v in sorted(data.items()))

    secret_key = hashlib.sha256(secret.encode("utf-8")).digest()
    computed_hash = hmac.new(secret_key, data_check_string.encode("utf-8"), hashlib.sha256).hexdigest()

    if not hmac.compare_digest(computed_hash, received_hash):
        raise HTTPException(status_code=401, detail="bad_signature")

    return data


def _parse_user(data: dict[str, str]) -> TgWebAppUser:
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
    """
    Auth gate dependency.
    Dev-bypass:
      - if DEV_TG_USER_ID is set AND initData missing OR not похож на initData -> пропускаем
      - если initData похоже на настоящее -> валидируем
    """
    raw = (x_tg_initdata or "").strip()
    dev_id = _dev_tg_id()

    if dev_id is not None and (not raw or not _looks_like_initdata(raw)):
        return TgWebAppUser(tg_id=dev_id)

    if not raw:
        raise HTTPException(status_code=401, detail="missing_initdata")

    secret = _get_bot_token()
    data = _verify_telegram_init_data(raw, secret)
    return _parse_user(data)


async def get_current_user(
    session: AsyncSession = Depends(get_session),
    x_tg_initdata: str | None = Header(default=None, alias="X-TG-INITDATA"),
) -> User | None:
    """
    DB user resolver.

    Dev-bypass:
      - если DEV_TG_USER_ID задан и initData отсутствует/мусорный -> возвращаем/создаём dev user в БД
    """
    raw = (x_tg_initdata or "").strip()
    dev_id = _dev_tg_id()

    if dev_id is not None and (not raw or not _looks_like_initdata(raw)):
        tg_id = dev_id
        username = ""
        first_name = ""
    else:
        if not raw:
            return None
        secret = _get_bot_token()
        data = _verify_telegram_init_data(raw, secret)
        tg = _parse_user(data)
        tg_id = tg.tg_id
        username = tg.username or ""
        first_name = tg.first_name or ""

    res = await session.execute(select(User).where(User.tg_id == tg_id))
    user = res.scalar_one_or_none()

    if user is None:
        user = User(tg_id=tg_id)
        # если в модели есть поля username/first_name — заполним, иначе пропустим
        if hasattr(user, "username"):
            setattr(user, "username", username)
        if hasattr(user, "first_name"):
            setattr(user, "first_name", first_name)

        session.add(user)
        await session.commit()
        await session.refresh(user)

    return user