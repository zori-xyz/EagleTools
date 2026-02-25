from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Header, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.config import settings
from app.domain.services.quota import PREMIUM_DAILY_LIMIT, get_quota_state
from app.infra.db.schema import Referral, User
from app.infra.db.session import get_session

router = APIRouter(prefix="/api/internal", tags=["internal"])


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _ensure_aware_utc(dt: datetime | None) -> datetime | None:
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _http400(detail: str) -> HTTPException:
    return HTTPException(status_code=400, detail=detail)


def _http401() -> HTTPException:
    return HTTPException(status_code=401, detail="unauthorized")


async def _require_api_key(x_api_key: str | None = Header(default=None, alias="X-API-KEY")) -> None:
    expected = str(getattr(settings, "bot_api_key", "") or "")
    if not expected:
        # если ключ не задан — лучше закрыть доступ, чем случайно открыть
        raise _http401()
    if not x_api_key or x_api_key != expected:
        raise _http401()


class UserUpsertIn(BaseModel):
    tg_id: int = Field(..., ge=1)
    username: str | None = None
    first_name: str | None = None


class ReferralAcceptIn(BaseModel):
    inviter_tg_id: int = Field(..., ge=1)
    invited_tg_id: int = Field(..., ge=1)


class PremiumGrantIn(BaseModel):
    tg_id: int = Field(..., ge=1)
    days: int = Field(..., ge=1, le=3650)


@router.post("/users/upsert")
async def users_upsert(
    payload: UserUpsertIn,
    session: AsyncSession = Depends(get_session),
    _: None = Depends(_require_api_key),
):
    res = await session.execute(select(User).where(User.tg_id == payload.tg_id))
    user = res.scalar_one_or_none()

    if user is None:
        user = User(tg_id=payload.tg_id)
        session.add(user)

    # безопасно выставляем поля только если они есть в модели
    if payload.username is not None and hasattr(user, "username"):
        setattr(user, "username", payload.username)
    if payload.first_name is not None and hasattr(user, "first_name"):
        setattr(user, "first_name", payload.first_name)

    await session.commit()
    await session.refresh(user)

    out = {"id": int(user.id), "tg_id": int(user.tg_id)}
    if hasattr(user, "premium_until"):
        out["premium_until"] = _ensure_aware_utc(getattr(user, "premium_until", None)).isoformat() if getattr(user, "premium_until", None) else None
    if hasattr(user, "username"):
        out["username"] = getattr(user, "username", "") or ""
    if hasattr(user, "first_name"):
        out["first_name"] = getattr(user, "first_name", "") or ""

    return {"ok": True, "user": out}


@router.post("/referrals/accept")
async def referrals_accept(
    payload: ReferralAcceptIn,
    session: AsyncSession = Depends(get_session),
    _: None = Depends(_require_api_key),
):
    if payload.inviter_tg_id == payload.invited_tg_id:
        raise _http400("self_referral")

    q_inviter = await session.execute(select(User).where(User.tg_id == payload.inviter_tg_id))
    inviter = q_inviter.scalar_one_or_none()
    if inviter is None:
        raise _http400("inviter_not_found")

    q_invited = await session.execute(select(User).where(User.tg_id == payload.invited_tg_id))
    invited = q_invited.scalar_one_or_none()
    if invited is None:
        raise _http400("invited_not_found")

    # unique по invited_user_id
    q_exists = await session.execute(select(Referral).where(Referral.invited_user_id == invited.id))
    if q_exists.scalar_one_or_none() is not None:
        raise _http400("already_referred")

    ref = Referral(inviter_user_id=int(inviter.id), invited_user_id=int(invited.id))
    session.add(ref)
    await session.commit()

    return {"ok": True}


@router.post("/premium/grant")
async def premium_grant(
    payload: PremiumGrantIn,
    session: AsyncSession = Depends(get_session),
    _: None = Depends(_require_api_key),
):
    res = await session.execute(select(User).where(User.tg_id == payload.tg_id))
    user = res.scalar_one_or_none()
    if user is None:
        raise _http400("user_not_found")

    now = _utcnow()
    cur = _ensure_aware_utc(getattr(user, "premium_until", None))
    base = cur if (cur and cur > now) else now
    new_until = base + timedelta(days=int(payload.days))

    if hasattr(user, "premium_until"):
        setattr(user, "premium_until", new_until)

    # если есть поле plan — ставим premium
    if hasattr(user, "plan"):
        try:
            setattr(user, "plan", "premium")
        except Exception:
            pass

    await session.commit()
    await session.refresh(user)

    return {"ok": True, "premium_until": _ensure_aware_utc(getattr(user, "premium_until", None)).isoformat()}


@router.get("/stats")
async def stats(
    tg_id: int = Query(..., ge=1),
    session: AsyncSession = Depends(get_session),
    _: None = Depends(_require_api_key),
):
    res = await session.execute(select(User).where(User.tg_id == tg_id))
    user = res.scalar_one_or_none()
    if user is None:
        raise _http400("user_not_found")

    st = await get_quota_state(session, user)

    left_today = None if st.is_unlimited else max(0, st.daily_limit - st.used_today)

    return {
        "ok": True,
        "tg_id": int(tg_id),
        "plan": str(st.plan),
        "premium_until": _ensure_aware_utc(getattr(user, "premium_until", None)).isoformat() if getattr(user, "premium_until", None) else None,
        "daily_limit": int(st.daily_limit),
        "used_today": int(st.used_today),
        "left_today": left_today,
        "is_unlimited": bool(st.is_unlimited),
        "referrals": int(st.referrals),
    }