from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


def tools_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🎧 Конвертировать в аудио",
                    callback_data="mode:audio",
                )
            ],
            [
                InlineKeyboardButton(
                    text="📝 Распознать речь в текст",
                    callback_data="mode:stt",
                )
            ],
            [
                InlineKeyboardButton(
                    text="⬅️ Назад",
                    callback_data="screen:menu",
                )
            ],
        ]
    )