# app/bot/keyboards/admin.py
from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def admin_main_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="📊 Статистика", callback_data="admin:stats"),
            InlineKeyboardButton(text="👥 Пользователи", callback_data="admin:users"),
        ],
        [
            InlineKeyboardButton(text="⚡️ Выдать Premium", callback_data="admin:grant"),
            InlineKeyboardButton(text="📣 Рассылка", callback_data="admin:broadcast"),
        ],
        [
            InlineKeyboardButton(text="✖️ Закрыть", callback_data="admin:close"),
        ],
    ])


def admin_stats_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔄 Обновить", callback_data="admin:stats:refresh")],
        [
            InlineKeyboardButton(text="◀️ Назад", callback_data="admin:main"),
            InlineKeyboardButton(text="✖️ Закрыть", callback_data="admin:close"),
        ],
    ])


def admin_users_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⚡️ Выдать Premium", callback_data="admin:grant")],
        [
            InlineKeyboardButton(text="◀️ Назад", callback_data="admin:main"),
            InlineKeyboardButton(text="✖️ Закрыть", callback_data="admin:close"),
        ],
    ])


def admin_grant_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="◀️ Назад", callback_data="admin:main"),
            InlineKeyboardButton(text="✖️ Закрыть", callback_data="admin:close"),
        ],
    ])


def admin_back_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="◀️ Назад", callback_data="admin:main"),
            InlineKeyboardButton(text="✖️ Закрыть", callback_data="admin:close"),
        ],
    ])