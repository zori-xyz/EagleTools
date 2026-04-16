from __future__ import annotations

import base64
import hashlib
import hmac
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone  # timezone already imported

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.config import settings
from app.infra.db.schema import Referral, User


def _ref_secret() -> str:
    """
    Secret for signing referral codes.
    Prefer REF_SECRET in env; fallback to BOT_TOKEN.
    """
    for name in ("ref_secret", "REF_SECRET", "bot_token", "BOT_TOKEN", "TELEGRAM_BOT_TOKEN"):
        val = getattr(settings, name, None)
        if val:
            return str(val)
    raise RuntimeError("REF_SECRET/BOT_TOKEN not configured")


def make_ref_code(inviter_tg_id: int) -> str:
    """
    Creates signed short code encoding inviter tg_id.
    Used in deep-link: /start ref_<code>
    """
    payload = str(int(inviter_tg_id)).encode("utf-8")
    sig = hmac.new(_ref_secret().encode("utf-8"), payload, hashlib.sha256).digest()[:10]
    token = payload + b"." + sig
    return base64.urlsafe_b64encode(token).decode("ascii").rstrip("=")


def parse_ref_code(code: str) -> int | None:
    """
    Returns inviter_tg_id if signature ok, else None.
    """
    try:
        pad = "=" * (-len(code) % 4)
        raw = base64.urlsafe_b64decode((code + pad).encode("ascii"))
        payload, sig = raw.split(b".", 1)
        exp = hmac.new(_ref_secret().encode("utf-8"), payload, hashlib.sha256).digest()[:10]
        if not hmac.compare_digest(sig, exp):
            return None
        return int(payload.decode("utf-8"))
    except Exception:
        return None


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _is_premium_active(u: User) -> bool:
    if str(u.plan) != "premium":
        return False
    if u.premium_until is None:
        return True
    # FIX #5: PostgreSQL may return naive datetimes even for timezone=True columns
    # depending on asyncpg/SQLAlchemy configuration. Normalize to aware UTC before
    # comparing, same pattern as quota.py._as_aware_utc().
    pu = u.premium_until
    if pu.tzinfo is None:
        pu = pu.replace(tzinfo=timezone.utc)
    return pu > _now()


async def _get_or_create_user_by_tg(session: AsyncSession, tg_id: int) -> User:
    res = await session.execute(select(User).where(User.tg_id == tg_id))
    u = res.scalar_one_or_none()
    if u:
        return u
    u = User(tg_id=tg_id)
    session.add(u)
    await session.flush()  # assigns u.id
    return u


@dataclass(slots=True)
class ApplyReferralResult:
    ok: bool
    reason: str
    inviter_user_id: int | None = None
    invited_user_id: int | None = None
    inviter_referrals: int | None = None
    premium_extended_days: int = 0


async def apply_referral_start(
    session: AsyncSession,
    *,
    inviter_tg_id: int,
    invited_tg_id: int,
) -> ApplyReferralResult:
    """
    Applies referral when invited presses /start ref_<code>.

    Rules:
    - no self-ref
    - invited can be referred only once (Referral.invited_user_id unique + User.referred_by_id guard)
    - inviter.referrals_count increments once
    - if inviter premium: each 3 referrals -> +3 days premium
    """
    if inviter_tg_id == invited_tg_id:
        return ApplyReferralResult(ok=False, reason="self_ref")

    inviter = await _get_or_create_user_by_tg(session, inviter_tg_id)
    invited = await _get_or_create_user_by_tg(session, invited_tg_id)

    # already referred?
    if invited.referred_by_id is not None:
        return ApplyReferralResult(
            ok=False,
            reason="already_referred",
            inviter_user_id=inviter.id,
            invited_user_id=invited.id,
        )

    existing = await session.execute(select(Referral).where(Referral.invited_user_id == invited.id))
    if existing.scalar_one_or_none():
        return ApplyReferralResult(
            ok=False,
            reason="already_referred",
            inviter_user_id=inviter.id,
            invited_user_id=invited.id,
        )

    invited.referred_by_id = inviter.id
    session.add(Referral(inviter_user_id=inviter.id, invited_user_id=invited.id))

    inviter.referrals_count = int(inviter.referrals_count or 0) + 1

    extended = 0
    if _is_premium_active(inviter) and (inviter.referrals_count % 3 == 0):
        base = inviter.premium_until
        now = _now()
        if base is None or base < now:
            base = now
        inviter.premium_until = base + timedelta(days=3)
        extended = 3

    await session.commit()

    return ApplyReferralResult(
        ok=True,
        reason="applied",
        inviter_user_id=inviter.id,
        invited_user_id=invited.id,
        inviter_referrals=inviter.referrals_count,
        premium_extended_days=extended,
    )