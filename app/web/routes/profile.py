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
    # IMPORTANT: payload format must match bot /start parser and internal referrals/accept usage
    # We use inviter_tg_id directly: ref_<inviter_tg_id>
    return f"https://t.me/{bot}?start=ref_{tg_id}"


def _premium_active(user: User | None) -> bool:
    if not user:
        return False
    now = datetime.now(timezone.utc)
    pu = _dt_to_utc_aware(getattr(user, "premium_until", None))
    return bool(pu and pu > now)


@router.get("/profile")
async def profile(
    session: AsyncSession = Depends(get_session),
    user: User | None = Depends(get_current_user),
) -> dict[str, Any]:
    st = await get_quota_state(session, user)

    plan = str(getattr(st, "plan", "free") or "free")
    daily_limit = int(getattr(st, "daily_limit", 0) or 0)
    used_today = int(getattr(st, "used_today", 0) or 0)
    referrals = int(getattr(st, "referrals", 0) or 0)

    # is_unlimited:
    # - prefer QuotaState flag if exists
    # - fallback to premium_until check
    st_unlimited = getattr(st, "is_unlimited", None)
    is_unlimited = bool(st_unlimited) if st_unlimited is not None else _premium_active(user)

    left_today = None if is_unlimited else max(0, daily_limit - used_today)
    premium_until = _iso(getattr(user, "premium_until", None)) if user else None

    # Policy:
    # - show referral link for everyone (free + premium). Premium can also invite; harmless to show.
    ref_link = _ref_link_for(int(getattr(user, "tg_id", 0))) if user else ""

    # Optional: how many invites left until next reward (example: +3 days per 3 invites)
    reward_need = (3 - (referrals % 3)) % 3 if referrals > 0 else 0

    return {
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
async def me(user: User | None = Depends(get_current_user)) -> dict[str, Any]:
    if not user:
        return {"ok": True, "user": None}

    return {
        "ok": True,
        "user": {
            "id": int(getattr(user, "id")),
            "tg_id": int(getattr(user, "tg_id")),
            "username": str(getattr(user, "username", "") or ""),
            "first_name": str(getattr(user, "first_name", "") or ""),
            "plan": "premium" if _premium_active(user) else "free",
            "premium_until": _iso(getattr(user, "premium_until", None)),
        },
    }