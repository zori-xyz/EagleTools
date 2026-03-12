# app/bot/keyboards/back.py
from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from app.bot.i18n import t


def back_kb(lang: str = "ru") -> InlineKeyboardMarkup:
    s = t(lang)
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text=s.btn_back, callback_data="screen:menu")]]
    )