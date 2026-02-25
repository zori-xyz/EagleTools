# app/domain/services/quota.py
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timezone

from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.infra.db.schema import Referral, UsageDaily, User

# ----------------------------
# Public constants (compat)
# ----------------------------
FREE_DAILY_LIMIT = 10
REF_BONUS_PER_INVITE = 5

# internal.py expects this name
PREMIUM_DAILY_LIMIT = 1_000_000_000  # effectively unlimited


class QuotaExceeded(Exception):
    pass


@dataclass(slots=True)
class QuotaState:
    plan: str  # "free" | "premium"
    daily_limit: int
    used_today: int
    referrals: int
    is_unlimited: bool


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def _as_aware_utc(dt: datetime | None) -> datetime | None:
    if dt is None:
        return None
    if dt.tzinfo is None:
        # если из БД пришёл naive — считаем UTC
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _today_utc() -> date:
    return _now_utc().date()


async def _count_referrals(session: AsyncSession, user: User) -> int:
    q = select(func.count(Referral.id)).where(Referral.inviter_user_id == user.id)
    n = await session.scalar(q)
    return int(n or 0)


async def _get_used_today(session: AsyncSession, user: User, today: date) -> int:
    # После добавления UNIQUE (user_id, day) scalar() безопасен.
    q = select(UsageDaily.used_count).where(
        UsageDaily.user_id == user.id,
        UsageDaily.day == today,
    )
    n = await session.scalar(q)
    return int(n or 0)


def _compute_daily_limit(plan: str, referrals: int) -> int:
    if plan == "premium":
        return PREMIUM_DAILY_LIMIT
    return FREE_DAILY_LIMIT + max(0, referrals) * REF_BONUS_PER_INVITE


async def get_quota_state(session: AsyncSession, user: User | None) -> QuotaState:
    if user is None:
        return QuotaState(
            plan="free",
            daily_limit=FREE_DAILY_LIMIT,
            used_today=0,
            referrals=0,
            is_unlimited=False,
        )

    now = _now_utc()
    premium_until = _as_aware_utc(user.premium_until)
    is_premium = bool(premium_until and premium_until > now)

    plan = "premium" if is_premium else "free"
    referrals = await _count_referrals(session, user)
    daily_limit = _compute_daily_limit(plan, referrals)

    today = _today_utc()
    used_today = await _get_used_today(session, user, today)

    return QuotaState(
        plan=plan,
        daily_limit=int(daily_limit),
        used_today=int(used_today),
        referrals=int(referrals),
        is_unlimited=(plan == "premium"),
    )


async def consume_quota(session: AsyncSession, *, user: User | None, cost: int = 1) -> QuotaState:
    """
    Atomically consume quota for today (UTC) for FREE users.

    Important:
    - Does NOT commit. Caller layer must commit/rollback.
    - Requires UNIQUE (user_id, day) on eagle.daily_usage (uq_daily_usage_user_day).
    """
    st = await get_quota_state(session, user)

    if user is None:
        return st
    if st.is_unlimited or cost <= 0:
        return st

    today = _today_utc()
    user_id = int(user.id)

    # Atomically insert-or-increment used_count.
    # Uses the UNIQUE(user_id, day) to avoid duplicates in concurrency.
    # We return the new used_count to enforce limit in-process.
    stmt = text(
        """
        INSERT INTO eagle.daily_usage (user_id, day, used_count, created_at)
        VALUES (:user_id, :day, :cost, now())
        ON CONFLICT (user_id, day)
        DO UPDATE SET used_count = eagle.daily_usage.used_count + EXCLUDED.used_count
        RETURNING used_count
        """
    )
    new_used = await session.scalar(stmt, {"user_id": user_id, "day": today, "cost": int(cost)})
    new_used = int(new_used or 0)

    if new_used > int(st.daily_limit):
        # Roll back the increment by raising and letting caller rollback transaction.
        # Caller MUST rollback on exception.
        raise QuotaExceeded()

    # used_today для state можем собрать без повторного SELECT по daily_usage,
    # но referral/premium может зависеть от БД, поэтому возвращаем свежий state.
    return await get_quota_state(session, user)