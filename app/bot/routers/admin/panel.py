# app/bot/routers/admin/panel.py
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message

from app.bot.keyboards.admin import (
    admin_back_kb,
    admin_grant_kb,
    admin_main_kb,
    admin_stats_kb,
    admin_users_kb,
)
from app.common.config import settings
from app.domain.services.panel import PanelRef, safe_edit_or_send
from app.domain.services.user_repo import UserRepo
from app.infra.db.session import SessionMaker

log = logging.getLogger(__name__)
router = Router()
_repo = UserRepo()

_admin_panels: dict[int, PanelRef] = {}


class AdminStates(StatesGroup):
    waiting_user_id = State()


# ── Admin guard ────────────────────────────────────────────────────────────────

def _is_admin(tg_id: int) -> bool:
    ids: set[int] = set()
    dev = getattr(settings, "dev_tg_user_id", None)
    if dev:
        ids.add(int(dev))
    raw = getattr(settings, "admin_ids", None) or ""
    for part in str(raw).split(","):
        part = part.strip()
        if part.isdigit():
            ids.add(int(part))
    return tg_id in ids


# ── Panel helper ───────────────────────────────────────────────────────────────

async def _show(source: Message | CallbackQuery, text: str, kb) -> None:
    if isinstance(source, Message):
        uid = source.from_user.id
        chat_id = source.chat.id
        bot = source.bot
        try:
            await source.delete()
        except Exception:
            pass
    else:
        uid = source.from_user.id
        chat_id = source.message.chat.id
        bot = source.bot

    current = _admin_panels.get(uid)
    if current and current.chat_id != chat_id:
        current = None

    ref = await safe_edit_or_send(
        bot=bot,
        chat_id=chat_id,
        text=text,
        reply_markup=kb,
        current=current,
        parse_mode="HTML",
    )
    _admin_panels[uid] = ref


# ── Stats ─────────────────────────────────────────────────────────────────────

async def _build_stats() -> str:
    from sqlalchemy import func, select, cast, Date
    from app.infra.db.models.user import User
    from app.infra.db.models.usage_daily import UsageDaily
    from app.infra.db.models.subscription_event import SubscriptionEvent
    from datetime import date, timedelta

    today = date.today()
    week_ago = today - timedelta(days=7)
    month_ago = today - timedelta(days=30)
    now = datetime.now(timezone.utc)

    async with SessionMaker() as session:
        total = await session.scalar(select(func.count()).select_from(User)) or 0
        new_today = await session.scalar(
            select(func.count()).select_from(User).where(cast(User.created_at, Date) == today)
        ) or 0
        new_week = await session.scalar(
            select(func.count()).select_from(User).where(cast(User.created_at, Date) >= week_ago)
        ) or 0
        premium_count = await session.scalar(
            select(func.count()).select_from(User).where(
                User.plan == "premium", User.premium_until > now,
            )
        ) or 0
        active_today = await session.scalar(
            select(func.count(UsageDaily.user_id.distinct())).where(
                UsageDaily.day == today, UsageDaily.used_count > 0,
            )
        ) or 0
        active_week = await session.scalar(
            select(func.count(UsageDaily.user_id.distinct())).where(
                UsageDaily.day >= week_ago, UsageDaily.used_count > 0,
            )
        ) or 0
        req_today = await session.scalar(
            select(func.sum(UsageDaily.used_count)).where(UsageDaily.day == today)
        ) or 0
        req_week = await session.scalar(
            select(func.sum(UsageDaily.used_count)).where(UsageDaily.day >= week_ago)
        ) or 0
        total_refs = await session.scalar(select(func.sum(User.referrals_count))) or 0
        rev_month = await session.scalar(
            select(func.count()).select_from(SubscriptionEvent).where(
                cast(SubscriptionEvent.created_at, Date) >= month_ago
            )
        ) or 0

    # Conversion rate today
    ctr = f"{active_today / total * 100:.1f}%" if total else "—"
    premium_pct = f"{premium_count / total * 100:.1f}%" if total else "—"

    return "\n".join([
        "📊 <b>EagleTools — Статистика</b>",
        f"<i>{datetime.now().strftime('%d.%m.%Y %H:%M')}</i>",
        "",
        "👥 <b>Пользователи</b>",
        f"  Всего: <b>{total:,}</b>  ·  ⚡️ Premium: <b>{premium_count}</b> ({premium_pct})",
        f"  Новых сегодня: <b>{new_today}</b>  ·  за неделю: <b>{new_week}</b>",
        "",
        "📈 <b>Активность</b>",
        f"  Активных сегодня: <b>{active_today}</b>  ({ctr} от базы)",
        f"  Активных за неделю: <b>{active_week}</b>",
        f"  Запросов сегодня: <b>{req_today:,}</b>  ·  за неделю: <b>{req_week:,}</b>",
        "",
        "🎁 <b>Рефералы</b>  ·  <b>{:,}</b> всего".format(int(total_refs)),
        "",
        "💳 <b>Подписки за 30 дней:</b>  <b>{}</b> событий".format(rev_month),
    ])


# ── /admin ────────────────────────────────────────────────────────────────────

@router.message(Command("admin"))
async def cmd_admin(message: Message) -> None:
    if not _is_admin(message.from_user.id):
        return
    await _show(message, "🛠 <b>EagleTools Admin</b>\n\nВыбери раздел:", admin_main_kb())


# ── Navigation callbacks ───────────────────────────────────────────────────────

@router.callback_query(F.data == "admin:main")
async def cb_admin_main(cb: CallbackQuery) -> None:
    if not _is_admin(cb.from_user.id):
        await cb.answer("⛔ Нет доступа", show_alert=True)
        return
    await cb.answer()
    await _show(cb, "🛠 <b>EagleTools Admin</b>\n\nВыбери раздел:", admin_main_kb())


@router.callback_query(F.data == "admin:close")
async def cb_admin_close(cb: CallbackQuery) -> None:
    if not _is_admin(cb.from_user.id):
        await cb.answer()
        return
    try:
        await cb.message.delete()
    except Exception:
        pass
    _admin_panels.pop(cb.from_user.id, None)
    await cb.answer("Закрыто")


@router.callback_query(F.data == "admin:stats")
async def cb_admin_stats(cb: CallbackQuery) -> None:
    if not _is_admin(cb.from_user.id):
        await cb.answer("⛔ Нет доступа", show_alert=True)
        return
    await cb.answer("Загружаю…")
    await _show(cb, await _build_stats(), admin_stats_kb())


@router.callback_query(F.data == "admin:stats:refresh")
async def cb_stats_refresh(cb: CallbackQuery) -> None:
    if not _is_admin(cb.from_user.id):
        await cb.answer("⛔ Нет доступа", show_alert=True)
        return
    await cb.answer("🔄 Обновляю…")
    await _show(cb, await _build_stats(), admin_stats_kb())


@router.callback_query(F.data == "admin:users")
async def cb_admin_users(cb: CallbackQuery) -> None:
    if not _is_admin(cb.from_user.id):
        await cb.answer("⛔ Нет доступа", show_alert=True)
        return
    await cb.answer("Загружаю…")

    from sqlalchemy import select
    from app.infra.db.models.user import User
    now = datetime.now(timezone.utc)

    async with SessionMaker() as session:
        res = await session.execute(
            select(User).order_by(User.created_at.desc()).limit(7)
        )
        recent = res.scalars().all()

        res2 = await session.execute(
            select(User).where(
                User.plan == "premium",
                User.premium_until > now,
            ).order_by(User.premium_until.desc()).limit(5)
        )
        premium_users = res2.scalars().all()

    lines = ["👥 <b>Последние регистрации</b>", ""]
    for u in recent:
        name = (u.first_name or "").strip() or "—"
        uname = f"@{u.username}" if u.username else "—"
        dt = u.created_at.strftime("%d.%m %H:%M") if u.created_at else "—"
        plan_icon = "⚡️" if u.plan == "premium" else "🆓"
        lines.append(f"{plan_icon} <b>{name}</b>  {uname}  <i>{dt}</i>")
        lines.append(f"   <code>/user {u.tg_id}</code>")

    lines += ["", "⚡️ <b>Активные Premium</b>", ""]
    if premium_users:
        for u in premium_users:
            name = (u.first_name or "").strip() or "—"
            uname = f"@{u.username}" if u.username else "—"
            until = u.premium_until.strftime("%d.%m.%Y") if u.premium_until else "∞"
            lines.append(f"• <b>{name}</b>  {uname}  до {until}")
            lines.append(f"   <code>/user {u.tg_id}</code>  ·  <code>/revoke {u.tg_id}</code>")
    else:
        lines.append("  Нет активных Premium")

    lines += [
        "",
        "<i>Используй /user &lt;id&gt; для деталей</i>",
    ]

    await _show(cb, "\n".join(lines), admin_users_kb())


@router.callback_query(F.data == "admin:user_search")
async def cb_user_search(cb: CallbackQuery, state: FSMContext) -> None:
    if not _is_admin(cb.from_user.id):
        await cb.answer("⛔ Нет доступа", show_alert=True)
        return
    await cb.answer()
    await state.set_state(AdminStates.waiting_user_id)
    await _show(
        cb,
        "🔍 <b>Поиск пользователя</b>\n\n"
        "Отправь Telegram ID или @username:",
        admin_back_kb(),
    )


@router.message(AdminStates.waiting_user_id)
async def on_user_search_input(message: Message, state: FSMContext) -> None:
    if not _is_admin(message.from_user.id):
        await state.clear()
        return
    await state.clear()
    query = (message.text or "").strip().lstrip("@")
    await _do_user_lookup(message, query)


@router.callback_query(F.data == "admin:grant")
async def cb_admin_grant(cb: CallbackQuery) -> None:
    if not _is_admin(cb.from_user.id):
        await cb.answer("⛔ Нет доступа", show_alert=True)
        return
    await cb.answer()
    text = (
        "⚡️ <b>Выдать Premium</b>\n\n"
        "<code>/grant &lt;tg_id&gt; &lt;tier&gt;</code>\n\n"
        "Тарифы:  <code>1m</code>  ·  <code>3m</code>  ·  <code>forever</code>\n\n"
        "Пример:\n<code>/grant 123456789 3m</code>\n\n"
        "Снять:\n<code>/revoke 123456789</code>"
    )
    await _show(cb, text, admin_grant_kb())


# ── /grant ────────────────────────────────────────────────────────────────────

@router.message(Command("grant"))
async def cmd_grant(message: Message) -> None:
    if not _is_admin(message.from_user.id):
        return
    parts = (message.text or "").split()
    if len(parts) != 3:
        await message.reply(
            "❌ <code>/grant &lt;tg_id&gt; &lt;tier&gt;</code>\n"
            "Тарифы: <code>1m</code> · <code>3m</code> · <code>forever</code>",
            parse_mode="HTML",
        )
        return
    _, tg_id_str, tier_key = parts
    if not tg_id_str.lstrip("-").isdigit():
        await message.reply("❌ tg_id должен быть числом", parse_mode="HTML")
        return

    tg_id = int(tg_id_str)
    from app.domain.services.premium import TIER_BY_KEY, activate_premium
    if tier_key not in TIER_BY_KEY:
        valid = " · ".join(f"<code>{k}</code>" for k in TIER_BY_KEY)
        await message.reply(f"❌ Неизвестный тариф. Доступны: {valid}", parse_mode="HTML")
        return

    try:
        async with SessionMaker() as session:
            user = await activate_premium(
                session, tg_id=tg_id, tier_key=tier_key,
                payment_method="admin_grant",
                payment_payload={"granted_by": message.from_user.id},
            )
            await session.commit()

        tier = TIER_BY_KEY[tier_key]
        until_str = "навсегда ♾️" if tier_key == "forever" else user.premium_until.strftime("%d.%m.%Y")

        try:
            await message.bot.send_message(
                chat_id=tg_id,
                text=(
                    f"🎉 <b>Premium активирован!</b>\n\n"
                    f"Тариф: {tier.label} · до {until_str} 🦅"
                ),
                parse_mode="HTML",
            )
        except Exception:
            log.warning("Could not notify %s about premium grant", tg_id)

        reply = await message.reply(
            f"✅ <b>Premium выдан</b>  <code>{tg_id}</code>  ·  {tier.label}  ·  до {until_str}",
            parse_mode="HTML",
        )
        await asyncio.sleep(5)
        try:
            await message.delete()
            await reply.delete()
        except Exception:
            pass

    except Exception:
        log.exception("Failed to grant premium to %s", tg_id)
        await message.reply("❌ Ошибка при выдаче Premium", parse_mode="HTML")


# ── /revoke ────────────────────────────────────────────────────────────────────

@router.message(Command("revoke"))
async def cmd_revoke(message: Message) -> None:
    if not _is_admin(message.from_user.id):
        return
    parts = (message.text or "").split()
    if len(parts) != 2:
        await message.reply("❌ <code>/revoke &lt;tg_id&gt;</code>", parse_mode="HTML")
        return
    tg_id = int(parts[1])
    async with SessionMaker() as session:
        user = await _repo.get_or_create(session, tg_id)
        user.plan = "free"
        user.premium_until = None
        await session.commit()

    reply = await message.reply(
        f"✅ Premium снят  ·  <code>{tg_id}</code>", parse_mode="HTML"
    )
    await asyncio.sleep(5)
    try:
        await message.delete()
        await reply.delete()
    except Exception:
        pass


# ── /user ──────────────────────────────────────────────────────────────────────

@router.message(Command("user"))
async def cmd_user_info(message: Message) -> None:
    if not _is_admin(message.from_user.id):
        return
    parts = (message.text or "").split()
    if len(parts) != 2:
        await message.reply("❌ <code>/user &lt;tg_id&gt;</code>", parse_mode="HTML")
        return
    await _do_user_lookup(message, parts[1])


async def _do_user_lookup(message: Message, query: str) -> None:
    from sqlalchemy import select, func
    from app.infra.db.models.user import User
    from app.infra.db.models.usage_daily import UsageDaily
    from app.infra.db.models.subscription_event import SubscriptionEvent
    from datetime import date

    now = datetime.now(timezone.utc)
    today = date.today()

    async with SessionMaker() as session:
        # Try by tg_id first, then by username
        user = None
        if query.lstrip("-").isdigit():
            tg_id = int(query)
            user = await _repo.get_or_create(session, tg_id)
        else:
            # Search by username
            res = await session.execute(
                select(User).where(User.username == query.lstrip("@"))
            )
            user = res.scalar_one_or_none()

        if user is None:
            await message.reply(
                f"❌ Пользователь <code>{query}</code> не найден.",
                parse_mode="HTML",
            )
            return

        today_usage = await session.scalar(
            select(UsageDaily.used_count).where(
                UsageDaily.user_id == user.id,
                UsageDaily.day == today,
            )
        ) or 0
        week_usage = await session.scalar(
            select(func.sum(UsageDaily.used_count)).where(
                UsageDaily.user_id == user.id,
            )
        ) or 0
        sub_events = await session.scalar(
            select(func.count()).select_from(SubscriptionEvent).where(
                SubscriptionEvent.user_id == user.id
            )
        ) or 0

    is_premium = user.plan == "premium" and user.premium_until and user.premium_until > now
    if is_premium:
        plan_str = f"⚡️ Premium  ·  до {user.premium_until.strftime('%d.%m.%Y')}"
    else:
        plan_str = "🆓 Free"

    name_parts = [user.first_name or "", user.last_name or ""]
    full_name = " ".join(p for p in name_parts if p).strip() or "—"
    uname = f"@{user.username}" if user.username else "—"

    lines = [
        f"👤 <b>{full_name}</b>  ·  {uname}",
        "",
        f"ID:        <code>{user.tg_id}</code>",
        f"Язык:      {user.language_code or '—'}",
        f"Тариф:     {plan_str}",
        f"Рефералов: {user.referrals_count}",
        "",
        f"Запросов сегодня:  <b>{today_usage}</b>",
        f"Запросов всего:    <b>{int(week_usage):,}</b>",
        f"Событий подписок:  <b>{sub_events}</b>",
        "",
        f"Зарегистрирован: {user.created_at.strftime('%d.%m.%Y %H:%M') if user.created_at else '—'}",
        "",
        f"<code>/grant {user.tg_id} 1m</code>  ·  "
        f"<code>/grant {user.tg_id} forever</code>  ·  "
        f"<code>/revoke {user.tg_id}</code>",
    ]

    await message.reply("\n".join(lines), parse_mode="HTML")


# ── Channel grant / reject (TON payments) ─────────────────────────────────────

@router.callback_query(F.data.startswith("admin:channel_grant:"))
async def cb_channel_grant(cb: CallbackQuery) -> None:
    if not _is_admin(cb.from_user.id):
        await cb.answer("⛔ Нет доступа", show_alert=True)
        return
    parts = cb.data.split(":")
    tg_id = int(parts[2])
    tier_key = parts[3]

    from app.domain.services.premium import TIER_BY_KEY, activate_premium
    try:
        async with SessionMaker() as session:
            user = await activate_premium(
                session, tg_id=tg_id, tier_key=tier_key,
                payment_method="ton_manual",
                payment_payload={"approved_by": cb.from_user.id},
            )
            await session.commit()

        tier = TIER_BY_KEY[tier_key]
        until_str = "навсегда ♾️" if tier_key == "forever" else user.premium_until.strftime("%d.%m.%Y")

        try:
            await cb.bot.send_message(
                chat_id=tg_id,
                text=f"🎉 <b>Premium активирован!</b>\n\nТариф: {tier.label}\nДо: {until_str} 🦅",
                parse_mode="HTML",
            )
        except Exception:
            log.warning("Could not notify %s about TON premium", tg_id)

        await cb.message.edit_text(
            cb.message.text + f"\n\n✅ <b>Выдано</b>  ·  {cb.from_user.first_name}  ·  {until_str}",
            reply_markup=None, parse_mode="HTML",
        )
        await cb.answer("✅ Premium выдан!")

    except Exception:
        log.exception("Failed to grant TON premium to %s", tg_id)
        await cb.answer("❌ Ошибка при выдаче", show_alert=True)


@router.callback_query(F.data.startswith("admin:channel_reject:"))
async def cb_channel_reject(cb: CallbackQuery) -> None:
    if not _is_admin(cb.from_user.id):
        await cb.answer("⛔ Нет доступа", show_alert=True)
        return
    tg_id = int(cb.data.split(":")[2])
    try:
        await cb.bot.send_message(
            chat_id=tg_id,
            text=(
                "❌ <b>Платёж не подтверждён</b>\n\n"
                "Транзакция не найдена или комментарий указан неверно.\n"
                "Обратись в поддержку."
            ),
            parse_mode="HTML",
        )
    except Exception:
        pass
    await cb.message.edit_text(
        cb.message.text + f"\n\n❌ <b>Отклонено</b>  ·  {cb.from_user.first_name}",
        reply_markup=None, parse_mode="HTML",
    )
    await cb.answer("Отклонено")
