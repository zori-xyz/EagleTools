from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select

from app.common.config import settings
from app.domain.services.quota import get_quota_state
from app.domain.services.referrals import make_ref_code
from app.infra.db.schema import User
from app.infra.db.session import SessionMaker


def _bot_username() -> str:
    # подхватит если у тебя есть settings.bot_username или env BOT_USERNAME
    for name in ("bot_username", "BOT_USERNAME"):
        v = getattr(settings, name, None)
        if v:
            return str(v).lstrip("@")
    return "<BOT_USERNAME>"


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def _is_premium(user: User) -> bool:
    if str(user.plan) != "premium":
        return False
    if user.premium_until is None:
        return True
    return user.premium_until > _now_utc()


async def _get_or_create_eagle_user(tg_id: int) -> User:
    async with SessionMaker() as session:
        res = await session.execute(select(User).where(User.tg_id == tg_id))
        u = res.scalar_one_or_none()
        if u:
            return u
        u = User(tg_id=tg_id)
        session.add(u)
        await session.commit()
        await session.refresh(u)
        return u


def _fmt_dt(dt: datetime | None) -> str:
    if not dt:
        return "—"
    # timezone-aware expected; show short
    try:
        return dt.astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    except Exception:
        return str(dt)


async def build_profile_text(tg_id: int) -> str:
    """
    Returns formatted profile text for bot UI:
    - plan
    - daily limit / used / left
    - referrals count
    - ref link for free users
    - premium reward progress for premium users (each 3 refs -> +3 days)
    """
    user = await _get_or_create_eagle_user(tg_id)

    async with SessionMaker() as session:
        # quota service expects infra User (can be None), we pass user
        st = await get_quota_state(session, user)

    daily_limit = int(st.daily_limit or 0)
    used_today = int(st.used_today or 0)
    left_today = max(0, daily_limit - used_today)

    referrals = int(getattr(user, "referrals_count", 0) or 0)
    plan = str(getattr(user, "plan", "free") or "free")

    lines: list[str] = []
    lines.append("👤 Профиль\n")
    lines.append(f"Тариф: {plan}")

    # premium info
    if _is_premium(user):
        lines.append(f"Premium до: {_fmt_dt(user.premium_until)}")

    # limits (for premium you said unlimited; keep output but can show "∞")
    if plan == "premium":
        lines.append("Лимит сегодня: ∞")
    else:
        lines.append(f"Лимит сегодня: {used_today}/{daily_limit} (осталось {left_today})")

    lines.append(f"Рефералов: {referrals}")

    # ref link logic:
    # - free: show link
    # - premium: show reward progress (3 refs -> +3 days)
    if plan == "free":
        code = make_ref_code(tg_id)
        link = f"https://t.me/{_bot_username()}?start=ref_{code}"
        lines.append("")
        lines.append("🔗 Твоя ссылка:")
        lines.append(link)
    else:
        # premium reward: each 3 invited -> +3 days premium
        need = 3 - (referrals % 3)
        if need == 3:
            need = 0
        lines.append("")
        lines.append(f"До +3 дней Premium: осталось пригласить {need} чел." if need else "До +3 дней Premium: порог выполнен ✅")

    return "\n".join(lines)