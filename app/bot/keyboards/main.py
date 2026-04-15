# app/bot/keyboards/main.py
from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from app.bot.i18n import t


def main_menu_kb(lang: str = "ru") -> InlineKeyboardMarkup:
    s = t(lang)
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="⚡️ Premium", callback_data="premium:open"),
                InlineKeyboardButton(text=s.btn_settings, callback_data="screen:settings"),
            ],
        ]
    )
