from __future__ import annotations

from dataclasses import dataclass

from aiogram import Bot
from aiogram.exceptions import TelegramAPIError, TelegramBadRequest
from aiogram.types import InlineKeyboardMarkup


@dataclass(frozen=True)
class PanelRef:
    chat_id: int
    message_id: int


async def safe_edit_or_send(
    bot: Bot,
    chat_id: int,
    text: str,
    reply_markup: InlineKeyboardMarkup | None = None,
    current: PanelRef | None = None,
) -> PanelRef:
    # если панель из другого чата — не редактируем
    if current is not None and current.chat_id != chat_id:
        current = None

    if current is not None:
        try:
            await bot.edit_message_text(
                chat_id=current.chat_id,
                message_id=current.message_id,
                text=text,
                reply_markup=reply_markup,
                disable_web_page_preview=True,
            )
            return current
        except TelegramBadRequest as e:
            msg = str(e).lower()
            if "message is not modified" in msg:
                return current
            # дальше fallback на send
        except TelegramAPIError:
            # любые другие телеграм-ошибки тоже лечим send'ом
            pass
        except Exception:
            # вообще всё остальное (редко, но лучше не молчать)
            pass

    m = await bot.send_message(
        chat_id=chat_id,
        text=text,
        reply_markup=reply_markup,
        disable_web_page_preview=True,
    )
    return PanelRef(chat_id=m.chat.id, message_id=m.message_id)