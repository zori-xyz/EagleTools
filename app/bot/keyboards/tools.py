# app/bot/keyboards/tools.py
from __future__ import annotations

from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from app.bot.i18n import t


def tools_kb(lang: str = "ru") -> InlineKeyboardMarkup:
    s = t(lang)
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=s.btn_audio_convert, callback_data="mode:audio")],
            [InlineKeyboardButton(text=s.btn_stt, callback_data="mode:stt")],
            [InlineKeyboardButton(text=s.btn_back, callback_data="screen:menu")],
        ]
    )