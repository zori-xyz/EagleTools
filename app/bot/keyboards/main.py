# app/bot/keyboards/main.py
from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from app.bot.i18n import t


def main_menu_kb(lang: str = "ru") -> InlineKeyboardMarkup:
    s = t(lang)
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=s.btn_tools, callback_data="screen:tools")],
            [
                InlineKeyboardButton(text=s.btn_settings, callback_data="screen:settings"),
                InlineKeyboardButton(text=s.btn_profile, callback_data="screen:profile"),
            ],
        ]
    )