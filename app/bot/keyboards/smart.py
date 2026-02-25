from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from app.domain.services.capabilities import Action


def smart_actions_kb(actions: tuple[Action, ...]) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []

    for a in actions:
        if a == Action.DOWNLOAD:
            rows.append([InlineKeyboardButton(text="📥 Сохранить медиа", callback_data="act:download")])
        elif a == Action.CONVERT_AUDIO:
            rows.append([InlineKeyboardButton(text="🎧 Конвертировать в аудио", callback_data="act:convert")])
        elif a == Action.TRANSCRIBE:
            rows.append([InlineKeyboardButton(text="📝 Распознать речь в текст", callback_data="act:transcribe")])

    rows.append([InlineKeyboardButton(text="⬅️ Отмена", callback_data="act:cancel")])
    return InlineKeyboardMarkup(inline_keyboard=rows)