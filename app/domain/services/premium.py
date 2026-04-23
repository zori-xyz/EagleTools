# app/domain/services/premium.py
from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Literal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.infra.db.models.user import User
from app.infra.db.models.subscription_event import SubscriptionEvent


# ── Тарифы ───────────────────────────────────────────────────────────────────

FOREVER_DAYS = 36500  # 100 лет = "навсегда"


@dataclass(frozen=True)
class PlanTier:
    key: str          # "1m" | "3m" | "forever"
    label: str        # "1 месяц" (RU)
    label_en: str     # "1 month" (EN)
    days: int
    stars_price: int  # Telegram Stars
    ton_price: float  # TON

    def localized_label(self, lang: str) -> str:
        return self.label_en if (lang or "").startswith("en") else self.label


TIERS: list[PlanTier] = [
    PlanTier("1m",      "1 месяц",   "1 month",  30,           149, 1.5),
    PlanTier("3m",      "3 месяца",  "3 months", 90,           349, 3.5),
    PlanTier("forever", "Навсегда",  "Forever",  FOREVER_DAYS, 999, 9.9),
]

TIER_BY_KEY: dict[str, PlanTier] = {t.key: t for t in TIERS}


# ── Helpers ───────────────────────────────────────────────────────────────────

def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def _as_aware(dt: datetime | None) -> datetime | None:
    if dt is None:
        return None
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


# ── Core: activate premium ────────────────────────────────────────────────────

async def activate_premium(
    session: AsyncSession,
    *,
    tg_id: int,
    tier_key: str,
    payment_method: Literal["stars", "ton", "admin_grant", "ton_manual"],
    payment_payload: dict | None = None,
) -> User:
    """
    Grants premium to user. Extends existing premium if still active.
    Records SubscriptionEvent. Does NOT commit — caller must commit.
    """
    tier = TIER_BY_KEY.get(tier_key)
    if not tier:
        raise ValueError(f"Unknown tier: {tier_key!r}")

    user = await session.scalar(select(User).where(User.tg_id == int(tg_id)))
    if user is None:
        raise LookupError(f"User tg_id={tg_id} not found")

    now = _now_utc()
    current_until = _as_aware(user.premium_until)

    # Extend from max(now, current_until)
    base = max(now, current_until) if (current_until and current_until > now) else now
    new_until = base + timedelta(days=tier.days)

    user.plan = "premium"          # ← фикс: ставим план
    user.premium_until = new_until

    # Record event
    event = SubscriptionEvent(
        user_id=user.id,
        kind=f"purchase_{payment_method}",
        days_delta=tier.days,
        meta=json.dumps({
            "tier": tier_key,
            "method": payment_method,
            **(payment_payload or {}),
        }, ensure_ascii=False),
    )
    session.add(event)

    return user


async def get_user_by_tg_id(session: AsyncSession, tg_id: int) -> User | None:
    return await session.scalar(select(User).where(User.tg_id == int(tg_id)))