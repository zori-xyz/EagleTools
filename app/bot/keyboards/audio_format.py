# app/bot/keyboards/audio_format.py
from __future__ import annotations

from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from app.bot.i18n import t


def audio_format_kb(lang: str = "ru") -> InlineKeyboardMarkup:
    s = t(lang)
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
                InlineKeyboardButton(text=s.btn_back, callback_data="screen:tools"),
            ],
        ]
    )