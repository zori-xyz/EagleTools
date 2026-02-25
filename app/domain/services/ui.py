from __future__ import annotations

from dataclasses import dataclass

from aiogram import Bot
from aiogram.exceptions import TelegramAPIError
from aiogram.types import InlineKeyboardMarkup


@dataclass(frozen=True)
class ScreenRef:
    chat_id: int
    message_id: int


async def safe_delete(bot: Bot, chat_id: int, message_id: int) -> None:
    try:
        await bot.delete_message(chat_id=chat_id, message_id=message_id)
    except TelegramAPIError:
        pass
    except Exception:
        pass


async def send_screen(
    bot: Bot,
    chat_id: int,
    text: str,
    reply_markup: InlineKeyboardMarkup | None,
    prev: ScreenRef | None,
) -> ScreenRef:
    if prev is not None:
        await safe_delete(bot, prev.chat_id, prev.message_id)

    m = await bot.send_message(
        chat_id=chat_id,
        text=text,
        reply_markup=reply_markup,
        disable_web_page_preview=True,
    )
    return ScreenRef(chat_id=m.chat.id, message_id=m.message_id)