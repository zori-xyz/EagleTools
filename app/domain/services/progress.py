from __future__ import annotations

import asyncio
from dataclasses import dataclass

from aiogram import Bot
from aiogram.exceptions import TelegramBadRequest, TelegramAPIError


@dataclass(frozen=True)
class ProgressRef:
    chat_id: int
    message_id: int


async def _safe_edit(bot: Bot, chat_id: int, message_id: int, text: str) -> None:
    try:
        await bot.edit_message_text(chat_id=chat_id, message_id=message_id, text=text)
    except TelegramBadRequest:
        pass
    except TelegramAPIError:
        pass
    except Exception:
        pass


async def _safe_delete(bot: Bot, chat_id: int, message_id: int) -> None:
    try:
        await bot.delete_message(chat_id=chat_id, message_id=message_id)
    except TelegramBadRequest:
        pass
    except TelegramAPIError:
        pass
    except Exception:
        pass


async def run_countdown(
    bot: Bot,
    chat_id: int,
    title: str,
    seconds: int = 5,
    delete_on_done: bool = True,
) -> ProgressRef:
    """
    Sends one progress message and edits it: 5s/4s/3s/2s/1s.
    Optionally deletes it after countdown.
    """
    msg = await bot.send_message(chat_id=chat_id, text=f"⏳ {title}… осталось {seconds}s")

    for s in range(seconds - 1, 0, -1):
        await asyncio.sleep(1)
        await _safe_edit(bot, msg.chat.id, msg.message_id, f"⏳ {title}… осталось {s}s")

    await asyncio.sleep(1)

    if delete_on_done:
        await _safe_delete(bot, msg.chat.id, msg.message_id)
    else:
        await _safe_edit(bot, msg.chat.id, msg.message_id, f"✅ {title}: готово")

    return ProgressRef(chat_id=msg.chat.id, message_id=msg.message_id)