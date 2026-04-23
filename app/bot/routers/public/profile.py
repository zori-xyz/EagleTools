# app/bot/routers/public/profile.py
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select

from app.bot.i18n import t
from app.common.config import settings
from app.domain.services.quota import get_quota_state
from app.domain.services.referrals import make_ref_code
from app.infra.db.schema import User
from app.infra.db.session import SessionMaker


def _bot_username() -> str:
    for name in ("bot_username", "BOT_USERNAME"):
        v = getattr(settings, name, None)
        if v:
            return str(v).lstrip("@")
    return "EagleToolsBot"


def _fmt_dt(dt: datetime | None) -> str:
    if not dt:
        return "—"
    try:
        return dt.astimezone(timezone.utc).strftime("%d.%m.%Y")
    except Exception:
        return str(dt)


async def build_profile_text(tg_id: int, lang: str = "ru") -> str:
    # Единая сессия — читаем свежие данные без кеша
    async with SessionMaker() as session:
        res = await session.execute(select(User).where(User.tg_id == tg_id))
        user = res.scalar_one_or_none()

        if user is None:
            user = User(tg_id=tg_id)
            session.add(user)
            await session.commit()
            await session.refresh(user)

        st = await get_quota_state(session, user)

    s = t(lang)
    used = int(st.used_today or 0)
    limit = int(st.daily_limit or 0)
    left = max(0, limit - used)
    referrals = int(getattr(user, "referrals_count", 0) or 0)
    is_premium = st.is_unlimited

    name = (user.first_name or "").strip() or "—"

    code = make_ref_code(tg_id)
    link = f"https://t.me/{_bot_username()}?start=ref_{code}"

    lines = [f"👤 <b>{name}</b>", ""]

    if is_premium:
        until = _fmt_dt(user.premium_until)
        lines.append(s.profile_premium_until(until))
        lines.append(s.profile_downloads_today(used, "∞"))
        lines.append(s.profile_referrals(referrals))
        lines.append("")
        # Реф бонус для премиума — +3 дня за каждые 3 реферала
        need = 3 - (referrals % 3)
        if need == 3:
            lines.append(s.profile_premium_bonus_ready)
        else:
            lines.append(s.profile_premium_bonus_need(need))
        lines.append("")
        lines.append(s.profile_ref_link_label)
        lines.append(f"<code>{link}</code>")
    else:
        lines.append(s.profile_plan_free)
        lines.append(s.profile_downloads_left(used, limit, left))
        lines.append(s.profile_referrals(referrals))
        lines.append("")
        # Реф бонус для фри — +5 загрузок за каждого друга
        lines.append(s.profile_ref_hint)
        lines.append(s.profile_ref_link_label)
        lines.append(f"<code>{link}</code>")

    return "\n".join(lines)