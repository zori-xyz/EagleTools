from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def back_home_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="⬅️ В меню", callback_data="nav:home")]
        ]
    )