from __future__ import annotations

from dataclasses import dataclass

from aiogram import Bot
from aiogram.exceptions import TelegramAPIError, TelegramBadRequest
from aiogram.types import InlineKeyboardMarkup, Message


@dataclass(frozen=True)
class PanelRef:
    chat_id: int
    message_id: int


async def delete_message_safe(bot: Bot, chat_id: int, message_id: int) -> None:
    try:
        await bot.delete_message(chat_id=chat_id, message_id=message_id)
    except Exception:
        pass


async def safe_edit_or_send(
    bot: Bot,
    chat_id: int,
    text: str,
    reply_markup: InlineKeyboardMarkup | None = None,
    current: PanelRef | None = None,
    parse_mode: str | None = "HTML",
    delete_after: Message | None = None,
) -> PanelRef:
    # Удаляем команду пользователя если передана
    if delete_after is not None:
        await delete_message_safe(bot, delete_after.chat.id, delete_after.message_id)

    if current is not None and current.chat_id != chat_id:
        current = None

    # Всегда удаляем старую панель и отправляем новую внизу
    if current is not None:
        await delete_message_safe(bot, current.chat_id, current.message_id)

    m = await bot.send_message(
        chat_id=chat_id,
        text=text,
        reply_markup=reply_markup,
        disable_web_page_preview=True,
        parse_mode=parse_mode,
    )
    return PanelRef(chat_id=m.chat.id, message_id=m.message_id)