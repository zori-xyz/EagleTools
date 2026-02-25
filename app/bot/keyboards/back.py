from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def back_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="⬅️ Назад", callback_data="screen:menu")]]
    )