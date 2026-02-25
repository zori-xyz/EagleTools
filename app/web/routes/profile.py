# app/web/routes/profile.py
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.config import settings
from app.domain.services.quota import get_quota_state
from app.infra.db.schema import User
from app.infra.db.session import get_session
from app.web.deps import get_current_user

router = APIRouter(tags=["profile"])


def _dt_to_utc_aware(dt: datetime | None) -> datetime | None:
    """
    Normalize DB datetimes to timezone-aware UTC so we can compare safely.
    - if dt is naive: assume it's UTC
    - if dt is aware: convert to UTC
    """
    if not dt:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _iso(dt: datetime | None) -> str | None:
    dt2 = _dt_to_utc_aware(dt)
    return dt2.isoformat() if dt2 else None


def _bot_username() -> str | None:
    v = (settings.bot_username or "").strip()
    if not v:
        return None
    return v.lstrip("@")


def _ref_link_for(tg_id: int) -> str:
    bot = _bot_username()
    if not bot:
        return ""
    # payload format must match bot /start parser and internal referrals/accept usage:
    # ref_<inviter_tg_id>
    return f"https://t.me/{bot}?start=ref_{tg_id}"


def _premium_active(user: User) -> bool:
    now = datetime.now(timezone.utc)
    pu = _dt_to_utc_aware(getattr(user, "premium_until", None))
    return bool(pu and pu > now)


def _ui_name(user: User) -> str:
    # requirement: only name, no фамилия
    first_name = str(getattr(user, "first_name", "") or "").strip()
    if first_name:
        return first_name
    username = str(getattr(user, "username", "") or "").strip()
    if username:
        return username
    return "User"


def _ui_username(user: User) -> str:
    return str(getattr(user, "username", "") or "").strip()


def _ui_photo_url(user: User) -> str:
    return str(getattr(user, "photo_url", "") or "").strip()


@router.get("/profile")
async def profile(
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
) -> dict[str, Any]:
    st = await get_quota_state(session, user)

    daily_limit = int(getattr(st, "daily_limit", 0) or 0)
    used_today = int(getattr(st, "used_today", 0) or 0)
    referrals = int(getattr(st, "referrals", 0) or 0)

    # is_unlimited:
    # - prefer QuotaState flag if exists
    # - fallback to premium_until check
    st_unlimited = getattr(st, "is_unlimited", None)
    is_unlimited = bool(st_unlimited) if st_unlimited is not None else _premium_active(user)

    left_today = None if is_unlimited else max(0, daily_limit - used_today)
    premium_until = _iso(getattr(user, "premium_until", None))

    # show referral link for everyone (free + premium)
    ref_link = _ref_link_for(int(getattr(user, "tg_id", 0)))

    # invites left until next reward (example: +3 days per 3 invites)
    reward_need = (3 - (referrals % 3)) % 3 if referrals > 0 else 0

    return {
        # --- UI поля для Mini App ---
        "user_name": _ui_name(user),
        "user_username": _ui_username(user),
        "user_photo_url": _ui_photo_url(user),

        # --- текущая логика (сохранена) ---
        "plan": "premium" if is_unlimited else "free",
        "premium_until": premium_until,
        "daily_limit": daily_limit,
        "used_today": used_today,
        "left_today": left_today,
        "is_unlimited": is_unlimited,
        "referrals": referrals,
        "ref_link": ref_link,
        "reward_need": reward_need,
    }


@router.get("/me")
async def me(user: User = Depends(get_current_user)) -> dict[str, Any]:
    return {
        "ok": True,
        "user": {
            "id": int(getattr(user, "id")),
            "tg_id": int(getattr(user, "tg_id")),
            "username": str(getattr(user, "username", "") or ""),
            "first_name": str(getattr(user, "first_name", "") or ""),
            "last_name": str(getattr(user, "last_name", "") or ""),
            "photo_url": str(getattr(user, "photo_url", "") or ""),
            "language_code": str(getattr(user, "language_code", "") or ""),
            "plan": "premium" if _premium_active(user) else "free",
            "premium_until": _iso(getattr(user, "premium_until", None)),
        },
    }