# app/bot/routers/admin/broadcast.py
from __future__ import annotations

import asyncio
import logging

from aiogram import Router, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message

from app.bot.keyboards.admin import admin_back_kb
from app.bot.routers.admin.panel import _is_admin
from app.infra.db.session import SessionMaker

log = logging.getLogger(__name__)
router = Router()


class BroadcastStates(StatesGroup):
    waiting_text = State()


@router.callback_query(F.data == "admin:broadcast")
async def cb_broadcast(cb: CallbackQuery, state: FSMContext) -> None:
    if not _is_admin(cb.from_user.id):
        await cb.answer("⛔ Нет доступа", show_alert=True)
        return
    await cb.answer()
    await state.set_state(BroadcastStates.waiting_text)
    await cb.message.answer(
        "📣 <b>Рассылка</b>\n\n"
        "Отправь текст сообщения (поддерживается HTML).\n\n"
        "Для отмены — /cancel",
        parse_mode="HTML",
        reply_markup=admin_back_kb(),
    )


@router.message(Command("cancel"), BroadcastStates.waiting_text)
async def cmd_cancel_broadcast(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.reply("❌ Рассылка отменена")


@router.message(BroadcastStates.waiting_text)
async def handle_broadcast_text(message: Message, state: FSMContext) -> None:
    if not _is_admin(message.from_user.id):
        return

    text = message.html_text or message.text or ""
    await state.clear()

    from sqlalchemy import select
    from app.infra.db.models.user import User

    async with SessionMaker() as session:
        result = await session.execute(select(User.tg_id))
        tg_ids = [row[0] for row in result.fetchall()]

    total = len(tg_ids)
    sent = 0
    failed = 0

    status_msg = await message.reply(
        f"📣 Начинаю рассылку...\n0 / {total}",
        parse_mode="HTML",
    )

    for i, tg_id in enumerate(tg_ids):
        try:
            await message.bot.send_message(
                chat_id=tg_id,
                text=text,
                parse_mode="HTML",
            )
            sent += 1
        except Exception:
            failed += 1

        # Update status every 20 users
        if (i + 1) % 20 == 0:
            try:
                await status_msg.edit_text(
                    f"📣 Рассылка...\n{i+1} / {total} (✅ {sent} ❌ {failed})",
                    parse_mode="HTML",
                )
            except Exception:
                pass

        await asyncio.sleep(0.05)  # ~20 msg/sec, within Telegram limits

    await status_msg.edit_text(
        f"✅ <b>Рассылка завершена</b>\n\n"
        f"Всего: {total}\n"
        f"Доставлено: {sent}\n"
        f"Ошибок: {failed}",
        parse_mode="HTML",
    )