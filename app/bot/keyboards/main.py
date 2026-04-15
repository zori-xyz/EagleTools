# app/bot/keyboards/main.py
from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from app.bot.i18n import t
from app.common.config import settings


def _app_url() -> str:
    return (settings.webapp_url or "").rstrip("/") or "https://t.me"


def main_menu_kb(lang: str = "ru") -> InlineKeyboardMarkup:
    s = t(lang)
    app_label = "🚀 Open app" if lang == "en" else "🚀 Открыть приложение"
    premium_label = "⚡️ Premium" if lang == "en" else "⚡️ Premium"
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text=app_label, url=_app_url()),
            ],
            [
                InlineKeyboardButton(text=premium_label, callback_data="premium:open"),
                InlineKeyboardButton(text=s.btn_settings, callback_data="screen:settings"),
            ],
        ]
    )
