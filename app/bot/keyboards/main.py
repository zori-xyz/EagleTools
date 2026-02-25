from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def main_menu_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🧰 Инструменты", callback_data="screen:tools")],
            [
                InlineKeyboardButton(text="⚙️ Настройки", callback_data="screen:settings"),
                InlineKeyboardButton(text="👤 Профиль", callback_data="screen:profile"),
            ],
        ]
    )