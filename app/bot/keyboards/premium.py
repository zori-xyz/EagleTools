# app/bot/keyboards/premium.py
from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from app.bot.i18n import t
from app.domain.services.premium import TIERS


def premium_tiers_kb(lang: str = "ru") -> InlineKeyboardMarkup:
    s = t(lang)
    rows = []
    for tier in TIERS:
        rows.append([
            InlineKeyboardButton(
                text=f"{tier.localized_label(lang)} — ⭐ {tier.stars_price} / 💎 {tier.ton_price} TON",
                callback_data=f"premium:select:{tier.key}",
            )
        ])
    rows.append([InlineKeyboardButton(text=s.btn_back, callback_data="screen:menu")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def premium_pay_kb(tier_key: str, lang: str = "ru") -> InlineKeyboardMarkup:
    s = t(lang)
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=s.btn_pay_stars, callback_data=f"premium:pay:stars:{tier_key}")],
            [InlineKeyboardButton(text=s.btn_pay_ton, callback_data=f"premium:pay:ton:{tier_key}")],
            [InlineKeyboardButton(text=s.btn_back_premium, callback_data="premium:back_tiers")],
        ]
    )


def premium_limit_kb(lang: str = "ru") -> InlineKeyboardMarkup:
    s = t(lang)
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=s.btn_get_premium, callback_data="premium:open")],
            [InlineKeyboardButton(text=s.btn_invite_friend, callback_data="premium:referral")],
        ]
    )