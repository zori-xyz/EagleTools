from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


def audio_format_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="🎵 MP3", callback_data="audiofmt:mp3"),
                InlineKeyboardButton(text="🎶 M4A", callback_data="audiofmt:m4a"),
            ],
            [
                InlineKeyboardButton(text="📀 WAV", callback_data="audiofmt:wav"),
                InlineKeyboardButton(text="🗜 OPUS", callback_data="audiofmt:opus"),
            ],
            [
                InlineKeyboardButton(text="⬅️ Назад", callback_data="screen:tools"),
            ],
        ]
    )