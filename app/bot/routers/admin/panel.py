# app/bot/routers/admin/panel.py
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone

from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message

from app.bot.keyboards.admin import (
    admin_main_kb,
    admin_stats_kb,
    admin_users_kb,
    admin_grant_kb,
)
from app.common.config import settings
from app.domain.services.panel import PanelRef, safe_edit_or_send
from app.domain.services.user_repo import UserRepo
from app.infra.db.session import SessionMaker

log = logging.getLogger(__name__)
router = Router()
repo = UserRepo()

# In-memory single-message panel per admin uid
_admin_panels: dict[int, PanelRef] = {}


# ── Admin check ───────────────────────────────────────────────────────────────

def _is_admin(tg_id: int) -> bool:
    admin_ids: set[int] = set()
    dev_id = getattr(settings, "dev_tg_user_id", None)
    if dev_id:
        admin_ids.add(int(dev_id))
    raw = getattr(settings, "admin_ids", None) or ""
    for part in str(raw).split(","):
        part = part.strip()
        if part.isdigit():
            admin_ids.add(int(part))
    return tg_id in admin_ids


# ── Single-message panel ──────────────────────────────────────────────────────

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


# ── Stats builder ─────────────────────────────────────────────────────────────

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
        total = await session.scalar(select(func.count()).select_from(User))
        new_today = await session.scalar(
            select(func.count()).select_from(User).where(cast(User.created_at, Date) == today)
        )
        new_week = await session.scalar(
            select(func.count()).select_from(User).where(cast(User.created_at, Date) >= week_ago)
        )
        premium_count = await session.scalar(
            select(func.count()).select_from(User).where(
                User.plan == "premium", User.premium_until > now,
            )
        )
        active_today = await session.scalar(
            select(func.count(UsageDaily.user_id.distinct())).where(
                UsageDaily.day == today, UsageDaily.used_count > 0,
            )
        )
        active_week = await session.scalar(
            select(func.count(UsageDaily.user_id.distinct())).where(
                UsageDaily.day >= week_ago, UsageDaily.used_count > 0,
            )
        )
        requests_today = await session.scalar(
            select(func.sum(UsageDaily.used_count)).where(UsageDaily.day == today)
        ) or 0
        requests_week = await session.scalar(
            select(func.sum(UsageDaily.used_count)).where(UsageDaily.day >= week_ago)
        ) or 0
        total_refs = await session.scalar(select(func.sum(User.referrals_count))) or 0
        revenue_events = await session.scalar(
            select(func.count()).select_from(SubscriptionEvent).where(
                cast(SubscriptionEvent.created_at, Date) >= month_ago
            )
        ) or 0

    return "\n".join([
        "📊 <b>Статистика EagleTools</b>",
        "",
        "👥 <b>Пользователи</b>",
        f"  Всего: <b>{total:,}</b>",
        f"  Новых сегодня: <b>{new_today}</b>",
        f"  Новых за неделю: <b>{new_week}</b>",
        f"  ⚡️ Premium активных: <b>{premium_count}</b>",
        "",
        "📈 <b>Активность</b>",
        f"  Активных сегодня: <b>{active_today}</b>",
        f"  Активных за неделю: <b>{active_week}</b>",
        f"  Запросов сегодня: <b>{requests_today:,}</b>",
        f"  Запросов за неделю: <b>{requests_week:,}</b>",
        "",
        "🎁 <b>Рефералы</b>",
        f"  Всего приглашений: <b>{total_refs:,}</b>",
        "",
        "💳 <b>Подписки</b>",
        f"  Событий за 30 дней: <b>{revenue_events}</b>",
        "",
        f"🕐 <i>{datetime.now().strftime('%d.%m.%Y %H:%M')}</i>",
    ])


# ── /admin ────────────────────────────────────────────────────────────────────

@router.message(Command("admin"))
async def cmd_admin(message: Message) -> None:
    if not _is_admin(message.from_user.id):
        return
    await _show(message, "🛠 <b>EagleTools Admin Panel</b>\n\nВыбери раздел:", admin_main_kb())


# ── Main menu callbacks ───────────────────────────────────────────────────────

@router.callback_query(F.data == "admin:main")
async def cb_admin_main(cb: CallbackQuery) -> None:
    if not _is_admin(cb.from_user.id):
        await cb.answer("⛔ Нет доступа", show_alert=True)
        return
    await cb.answer()
    await _show(cb, "🛠 <b>EagleTools Admin Panel</b>\n\nВыбери раздел:", admin_main_kb())


@router.callback_query(F.data == "admin:close")
async def cb_admin_close(cb: CallbackQuery) -> None:
    if not _is_admin(cb.from_user.id):
        await cb.answer()
        return
    uid = cb.from_user.id
    try:
        await cb.message.delete()
    except Exception:
        pass
    _admin_panels.pop(uid, None)
    await cb.answer("Закрыто")


@router.callback_query(F.data == "admin:stats")
async def cb_admin_stats(cb: CallbackQuery) -> None:
    if not _is_admin(cb.from_user.id):
        await cb.answer("⛔ Нет доступа", show_alert=True)
        return
    await cb.answer("Загружаю...")
    await _show(cb, await _build_stats(), admin_stats_kb())


@router.callback_query(F.data == "admin:stats:refresh")
async def cb_stats_refresh(cb: CallbackQuery) -> None:
    if not _is_admin(cb.from_user.id):
        await cb.answer("⛔ Нет доступа", show_alert=True)
        return
    await cb.answer("🔄 Обновляю...")
    await _show(cb, await _build_stats(), admin_stats_kb())


@router.callback_query(F.data == "admin:users")
async def cb_admin_users(cb: CallbackQuery) -> None:
    if not _is_admin(cb.from_user.id):
        await cb.answer("⛔ Нет доступа", show_alert=True)
        return
    await cb.answer("Загружаю...")

    from sqlalchemy import select
    from app.infra.db.models.user import User
    now = datetime.now(timezone.utc)

    async with SessionMaker() as session:
        result = await session.execute(
            select(User).order_by(User.created_at.desc()).limit(5)
        )
        recent_users = result.scalars().all()

        result2 = await session.execute(
            select(User).where(
                User.plan == "premium",
                User.premium_until > now,
            ).order_by(User.premium_until.desc()).limit(5)
        )
        premium_users = result2.scalars().all()

    lines = ["👥 <b>Последние пользователи</b>\n"]
    for u in recent_users:
        name = u.first_name or "—"
        uname = f"@{u.username}" if u.username else "нет username"
        dt = u.created_at.strftime("%d.%m %H:%M") if u.created_at else "—"
        lines.append(f"• <b>{name}</b> · {uname} · {dt}\n  ID: <code>{u.tg_id}</code>")

    lines += ["", "⚡️ <b>Активные Premium</b>\n"]
    if premium_users:
        for u in premium_users:
            name = u.first_name or "—"
            uname = f"@{u.username}" if u.username else "нет username"
            until = u.premium_until.strftime("%d.%m.%Y") if u.premium_until else "∞"
            lines.append(f"• <b>{name}</b> · {uname} · до {until}\n  ID: <code>{u.tg_id}</code>")
    else:
        lines.append("  Нет активных Premium")

    lines += [
        "",
        "Нажми на ID чтобы скопировать, затем:",
        "<code>/grant ID 1m</code>  |  <code>/grant ID forever</code>",
    ]

    await _show(cb, "\n".join(lines), admin_users_kb())


@router.callback_query(F.data == "admin:grant")
async def cb_admin_grant(cb: CallbackQuery) -> None:
    if not _is_admin(cb.from_user.id):
        await cb.answer("⛔ Нет доступа", show_alert=True)
        return
    await cb.answer()
    text = (
        "⚡️ <b>Выдать Premium</b>\n\n"
        "Отправь команду:\n\n"
        "<code>/grant &lt;tg_id&gt; &lt;tier&gt;</code>\n\n"
        "Тарифы:\n"
        "  <code>1m</code> — 1 месяц\n"
        "  <code>3m</code> — 3 месяца\n"
        "  <code>forever</code> — навсегда\n\n"
        "Пример:\n"
        "<code>/grant 123456789 3m</code>\n\n"
        "Снять:\n"
        "<code>/revoke 123456789</code>"
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
            "❌ Формат: <code>/grant &lt;tg_id&gt; &lt;tier&gt;</code>\n"
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
                session,
                tg_id=tg_id,
                tier_key=tier_key,
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
                    f"Тариф: {tier.label}\n"
                    f"Действует до: {until_str} 🦅"
                ),
                parse_mode="HTML",
            )
        except Exception:
            log.warning("Could not notify user %s about premium grant", tg_id)

        reply = await message.reply(
            f"✅ <b>Premium выдан</b>\n"
            f"Пользователь: <code>{tg_id}</code>\n"
            f"Тариф: {tier.label} · до {until_str}",
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


# ── /revoke ───────────────────────────────────────────────────────────────────

@router.message(Command("revoke"))
async def cmd_revoke(message: Message) -> None:
    if not _is_admin(message.from_user.id):
        return

    parts = (message.text or "").split()
    if len(parts) != 2:
        await message.reply("❌ Формат: <code>/revoke &lt;tg_id&gt;</code>", parse_mode="HTML")
        return

    tg_id = int(parts[1])
    async with SessionMaker() as session:
        user = await repo.get_or_create(session, tg_id)
        user.plan = "free"
        user.premium_until = None
        await session.commit()

    reply = await message.reply(
        f"✅ Premium снят с <code>{tg_id}</code>", parse_mode="HTML"
    )
    await asyncio.sleep(5)
    try:
        await message.delete()
        await reply.delete()
    except Exception:
        pass


# ── Channel grant/reject (TON payment notifications) ─────────────────────────

@router.callback_query(F.data.startswith("admin:channel_grant:"))
async def cb_channel_grant(cb: CallbackQuery) -> None:
    if not _is_admin(cb.from_user.id):
        await cb.answer("⛔ Нет доступа", show_alert=True)
        return

    # callback_data: admin:channel_grant:{tg_id}:{tier_key}
    parts = cb.data.split(":")
    tg_id = int(parts[2])
    tier_key = parts[3]

    from app.domain.services.premium import TIER_BY_KEY, activate_premium
    try:
        async with SessionMaker() as session:
            user = await activate_premium(
                session,
                tg_id=tg_id,
                tier_key=tier_key,
                payment_method="ton_manual",
                payment_payload={"approved_by": cb.from_user.id},
            )
            await session.commit()

        tier = TIER_BY_KEY[tier_key]
        until_str = "навсегда ♾️" if tier_key == "forever" else user.premium_until.strftime("%d.%m.%Y")

        try:
            await cb.bot.send_message(
                chat_id=tg_id,
                text=(
                    f"🎉 <b>Premium активирован!</b>\n\n"
                    f"Тариф: {tier.label}\n"
                    f"Действует до: {until_str} 🦅"
                ),
                parse_mode="HTML",
            )
        except Exception:
            log.warning("Could not notify user %s about TON premium", tg_id)

        await cb.message.edit_text(
            cb.message.text + f"\n\n✅ <b>Выдано</b> · {cb.from_user.first_name} · {until_str}",
            reply_markup=None,
            parse_mode="HTML",
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
                "Обратись в поддержку если считаешь это ошибкой."
            ),
            parse_mode="HTML",
        )
    except Exception:
        pass

    await cb.message.edit_text(
        cb.message.text + f"\n\n❌ <b>Отклонено</b> · {cb.from_user.first_name}",
        reply_markup=None,
        parse_mode="HTML",
    )
    await cb.answer("Отклонено")


# ── /user ─────────────────────────────────────────────────────────────────────

@router.message(Command("user"))
async def cmd_user_info(message: Message) -> None:
    if not _is_admin(message.from_user.id):
        return

    parts = (message.text or "").split()
    if len(parts) != 2:
        await message.reply("❌ Формат: <code>/user &lt;tg_id&gt;</code>", parse_mode="HTML")
        return

    tg_id = int(parts[1])
    now = datetime.now(timezone.utc)

    from sqlalchemy import select, func
    from app.infra.db.models.usage_daily import UsageDaily
    from app.infra.db.models.subscription_event import SubscriptionEvent
    from datetime import date

    async with SessionMaker() as session:
        user = await repo.get_or_create(session, tg_id)
        today_usage = await session.scalar(
            select(UsageDaily.used_count).where(
                UsageDaily.user_id == user.id,
                UsageDaily.day == date.today(),
            )
        ) or 0
        sub_events = await session.scalar(
            select(func.count()).select_from(SubscriptionEvent).where(
                SubscriptionEvent.user_id == user.id
            )
        ) or 0

    is_premium = user.plan == "premium" and user.premium_until and user.premium_until > now
    plan_str = f"⚡️ Premium до {user.premium_until.strftime('%d.%m.%Y')}" if is_premium else "🆓 Free"

    await message.reply(
        "\n".join([
            "👤 <b>Пользователь</b>",
            f"ID: <code>{tg_id}</code>",
            "",
            f"Имя: {user.first_name or '—'}{' ' + user.last_name if user.last_name else ''}",
            f"Username: @{user.username}" if user.username else "Username: —",
            f"Язык: {user.language_code or '—'}",
            f"Тариф: {plan_str}",
            f"Рефералов: {user.referrals_count}",
            f"Запросов сегодня: {today_usage}",
            f"Событий подписки: {sub_events}",
            f"Зарегистрирован: {user.created_at.strftime('%d.%m.%Y %H:%M') if user.created_at else '—'}",
        ]),
        parse_mode="HTML",
    )