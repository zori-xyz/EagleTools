# app/bot/keyboards/profile.py
from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from app.bot.i18n import t


def profile_kb(is_premium: bool = False, lang: str = "ru") -> InlineKeyboardMarkup:
    s = t(lang)
    rows = []
    if not is_premium:
        rows.append([InlineKeyboardButton(text=s.btn_get_premium, callback_data="premium:open")])
    rows.append([InlineKeyboardButton(text=s.btn_back, callback_data="screen:menu")])
    return InlineKeyboardMarkup(inline_keyboard=rows)