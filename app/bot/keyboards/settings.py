# app/bot/keyboards/settings.py
from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from app.bot.i18n import t


def settings_kb(lang: str = "ru") -> InlineKeyboardMarkup:
    s = t(lang)
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=s.btn_lang_toggle, callback_data="settings:lang")],
            [InlineKeyboardButton(text=s.btn_privacy, url="https://telegra.ph/Politika-konfidencialnosti---EagleTools-03-11-2")],
            [InlineKeyboardButton(text=s.btn_back, callback_data="screen:menu")],
        ]
    )