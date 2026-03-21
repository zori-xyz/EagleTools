# app/bot/routers/public/premium.py
from __future__ import annotations

import logging
from datetime import datetime, timezone

from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    LabeledPrice,
    Message,
    PreCheckoutQuery,
)

from app.bot.i18n import t
from app.bot.keyboards.premium import premium_pay_kb, premium_tiers_kb
from app.domain.services.panel import PanelRef, safe_edit_or_send
from app.domain.services.premium import TIER_BY_KEY, TIERS, activate_premium
from app.domain.services.user_repo import UserRepo
from app.infra.db.session import SessionMaker

log = logging.getLogger(__name__)
router = Router()
repo = UserRepo()


async def _get_lang(uid: int) -> str:
    async with SessionMaker() as session:
        user = await repo.get_or_create(session, uid)
        return user.language_code or "ru"


async def _get_panel(uid: int) -> PanelRef | None:
    async with SessionMaker() as session:
        ref = await repo.get_screen(session, uid)
    return PanelRef(chat_id=ref[0], message_id=ref[1]) if ref else None


async def _save_panel(uid: int, ref: PanelRef) -> None:
    async with SessionMaker() as session:
        await repo.set_screen(session, uid, ref.chat_id, ref.message_id)


async def _show_panel(cb: CallbackQuery, text: str, kb) -> None:
    uid = cb.from_user.id
    current = PanelRef(chat_id=cb.message.chat.id, message_id=cb.message.message_id)
    ref = await safe_edit_or_send(
        bot=cb.bot,
        chat_id=cb.message.chat.id,
        text=text,
        reply_markup=kb,
        current=current,
        parse_mode="HTML",
    )
    await _save_panel(uid, ref)


def build_premium_menu_text(lang: str) -> str:
    s = t(lang)
    lines = [s.premium_menu_header]
    for tier in TIERS:
        lines.append(f"• <b>{tier.label}</b> — ⭐ {tier.stars_price} Stars  |  💎 {tier.ton_price} TON")
    lines.append(s.premium_menu_features)
    return "\n".join(lines)


def _build_tier_text(tier_key: str, lang: str) -> str:
    tier = TIER_BY_KEY[tier_key]
    return t(lang).premium_tier_text(tier.label, tier.stars_price, tier.ton_price)


def _invoice_cancel_kb(tier_key: str, invoice_msg_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❌ Отменить", callback_data=f"premium:invoice_cancel:{tier_key}:{invoice_msg_id}")],
    ])


@router.message(Command("premium"))
async def cmd_premium(message: Message) -> None:
    uid = message.from_user.id
    lang = await _get_lang(uid)
    current = await _get_panel(uid)
    ref = await safe_edit_or_send(
        bot=message.bot,
        chat_id=message.chat.id,
        text=build_premium_menu_text(lang),
        reply_markup=premium_tiers_kb(lang),
        current=current,
        parse_mode="HTML",
    )
    await _save_panel(uid, ref)


@router.callback_query(F.data == "premium:open")
async def cb_premium_open(cb: CallbackQuery) -> None:
    await cb.answer()
    lang = await _get_lang(cb.from_user.id)
    await _show_panel(cb, build_premium_menu_text(lang), premium_tiers_kb(lang))


@router.callback_query(F.data == "premium:back_tiers")
async def cb_back_tiers(cb: CallbackQuery) -> None:
    await cb.answer()
    lang = await _get_lang(cb.from_user.id)
    await _show_panel(cb, build_premium_menu_text(lang), premium_tiers_kb(lang))


@router.callback_query(F.data.startswith("premium:select:"))
async def cb_select_tier(cb: CallbackQuery) -> None:
    tier_key = cb.data.split(":", 2)[2]
    lang = await _get_lang(cb.from_user.id)
    s = t(lang)
    if tier_key not in TIER_BY_KEY:
        await cb.answer(s.premium_unknown_tier, show_alert=True)
        return
    await cb.answer()
    await _show_panel(cb, _build_tier_text(tier_key, lang), premium_pay_kb(tier_key, lang))


@router.callback_query(F.data.startswith("premium:pay:stars:"))
async def cb_pay_stars(cb: CallbackQuery) -> None:
    tier_key = cb.data.split(":", 3)[3]
    lang = await _get_lang(cb.from_user.id)
    s = t(lang)
    tier = TIER_BY_KEY.get(tier_key)
    if not tier:
        await cb.answer(s.premium_unknown_tier, show_alert=True)
        return
    await cb.answer()

    # Send invoice WITHOUT reply_markup (Telegram only allows Pay button there)
    invoice_msg = await cb.message.answer_invoice(
        title=s.premium_invoice_title(tier.label),
        description=s.premium_invoice_desc(tier.label),
        payload=f"premium_stars_{tier_key}",
        currency="XTR",
        prices=[LabeledPrice(label=f"Premium {tier.label}", amount=tier.stars_price)],
    )

    # Send cancel button as a separate message right after
    cancel_msg = await cb.message.answer(
        "Передумал? Отмени платёж:",
        reply_markup=_invoice_cancel_kb(tier_key, invoice_msg.message_id),
    )

    # Store both message ids: invoice:{invoice_id}:{cancel_id}
    async with SessionMaker() as session:
        user = await repo.get_or_create(session, cb.from_user.id)
        user.active_tool = f"invoice:{invoice_msg.message_id}:{cancel_msg.message_id}"
        await session.commit()


@router.callback_query(F.data.startswith("premium:invoice_cancel:"))
async def cb_invoice_cancel(cb: CallbackQuery) -> None:
    await cb.answer("Отменено")
    # callback_data: premium:invoice_cancel:{tier_key}:{invoice_msg_id}
    parts = cb.data.split(":")
    invoice_msg_id = int(parts[-1]) if parts[-1].isdigit() else None

    # Delete invoice message
    if invoice_msg_id:
        try:
            await cb.bot.delete_message(chat_id=cb.message.chat.id, message_id=invoice_msg_id)
        except Exception:
            pass

    # Delete cancel button message
    try:
        await cb.message.delete()
    except Exception:
        pass

    # Clear stored invoice id
    async with SessionMaker() as session:
        user = await repo.get_or_create(session, cb.from_user.id)
        if user.active_tool and user.active_tool.startswith("invoice:"):
            user.active_tool = None
            await session.commit()


@router.pre_checkout_query()
async def pre_checkout(pcq: PreCheckoutQuery) -> None:
    await pcq.answer(ok=True)


@router.message(F.successful_payment)
async def on_successful_payment(message: Message) -> None:
    payload = message.successful_payment.invoice_payload
    parts = payload.split("_")
    if len(parts) != 3 or parts[0] != "premium" or parts[1] != "stars":
        log.warning("Unknown payment payload: %s", payload)
        return

    tier_key = parts[2]
    tg_id = message.from_user.id
    charge_id = message.successful_payment.telegram_payment_charge_id
    lang = await _get_lang(tg_id)
    s = t(lang)

    # Delete the invoice message + cancel button message
    try:
        async with SessionMaker() as session:
            user = await repo.get_or_create(session, tg_id)
            if user.active_tool and user.active_tool.startswith("invoice:"):
                msg_parts = user.active_tool.split(":")
                for msg_id_str in msg_parts[1:]:
                    if msg_id_str.isdigit():
                        try:
                            await message.bot.delete_message(
                                chat_id=message.chat.id,
                                message_id=int(msg_id_str),
                            )
                        except Exception:
                            pass
                user.active_tool = None
                await session.commit()
    except Exception:
        log.warning("Could not delete invoice messages for user %s", tg_id)

    # Delete Telegram's system "payment successful" message
    try:
        await message.delete()
    except Exception:
        pass

    try:
        async with SessionMaker() as session:
            user = await activate_premium(
                session,
                tg_id=tg_id,
                tier_key=tier_key,
                payment_method="stars",
                payment_payload={"charge_id": charge_id},
            )
            await session.commit()

        tier = TIER_BY_KEY[tier_key]
        until = s.premium_activated_forever if tier_key == "forever" else user.premium_until.strftime("%d.%m.%Y")

        # Show success on the existing panel message
        current = await _get_panel(tg_id)
        ref = await safe_edit_or_send(
            bot=message.bot,
            chat_id=message.chat.id,
            text=s.premium_activated(tier.label, until),
            reply_markup=None,
            current=current,
            parse_mode="HTML",
        )
        await _save_panel(tg_id, ref)

    except Exception:
        log.exception("Failed to activate premium after Stars payment")
        await message.answer(s.premium_payment_error)


@router.callback_query(F.data.startswith("premium:pay:ton:"))
def _make_ton_deeplink(wallet: str, amount_ton: float, comment: str) -> str:
    """
    Tonkeeper universal link — работает и как веб и открывает приложение.
    https://app.tonkeeper.com/transfer/<wallet>?amount=<nanotons>&text=<comment>
    """
    nanotons = int(amount_ton * 1_000_000_000)
    from urllib.parse import quote
    return f"https://app.tonkeeper.com/transfer/{wallet}?amount={nanotons}&text={quote(comment)}"


async def cb_pay_ton(cb: CallbackQuery) -> None:
    tier_key = cb.data.split(":", 3)[3]
    lang = await _get_lang(cb.from_user.id)
    s = t(lang)
    tier = TIER_BY_KEY.get(tier_key)
    if not tier:
        await cb.answer(s.premium_unknown_tier, show_alert=True)
        return

    from app.common.config import settings as app_settings
    ton_wallet = getattr(app_settings, "ton_wallet", None) or "UQAExampleWalletAddressHere"
    comment    = f"eagle_premium_{tier_key}_{cb.from_user.id}"
    deeplink   = _make_ton_deeplink(ton_wallet, tier.ton_price, comment)

    await cb.answer()
    await _show_panel(
        cb,
        s.premium_ton_text(tier.label, tier.ton_price, ton_wallet, comment),
        _ton_sent_kb(tier_key, lang, deeplink),
    )


def _ton_sent_kb(tier_key: str, lang: str, deeplink: str = "") -> InlineKeyboardMarkup:
    s = t(lang)
    rows = []

    # Кнопка открывает @wallet / Tonkeeper с уже заполненными данными
    if deeplink:
        pay_label = "💎 Оплатить в кошельке" if lang == "ru" else "💎 Pay in wallet"
        rows.append([InlineKeyboardButton(text=pay_label, url=deeplink)])

    rows.append([InlineKeyboardButton(text=s.btn_ton_sent, callback_data=f"premium:ton_sent:{tier_key}")])
    rows.append([InlineKeyboardButton(text=s.btn_back_premium, callback_data=f"premium:select:{tier_key}")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


@router.callback_query(F.data.startswith("premium:ton_sent:"))
async def cb_ton_sent(cb: CallbackQuery) -> None:
    tier_key = cb.data.split(":", 2)[2]
    lang = await _get_lang(cb.from_user.id)
    s = t(lang)
    tier = TIER_BY_KEY.get(tier_key)
    tg_id = cb.from_user.id
    comment = f"eagle_premium_{tier_key}_{tg_id}"
    await cb.answer()
    await _show_panel(cb, s.premium_ton_sent_text(tier.ton_price, comment), None)

    # Notify admin channel
    from app.common.config import settings as app_settings
    channel_id = getattr(app_settings, "admin_channel_id", None)
    log.info("TON notification: channel_id=%s tier=%s tg_id=%s", channel_id, tier_key, tg_id)

    if not channel_id:
        log.warning("ADMIN_CHANNEL_ID not set, skipping notification")
        return

    async with SessionMaker() as session:
        user = await repo.get_or_create(session, tg_id)

    name = user.first_name or "—"
    username = f"@{user.username}" if user.username else f"tg_id: {tg_id}"

    text = (
        "💎 <b>Новая заявка на TON Premium</b>\n\n"
        f"👤 {name} · {username}\n"
        f"🆔 <code>{tg_id}</code>\n"
        f"📦 Тариф: <b>{tier.label}</b> · {tier.ton_price} TON\n"
        f"💬 Комментарий: <code>{comment}</code>\n\n"
        "Проверь транзакцию и выдай Premium:"
    )

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text=f"✅ Выдать {tier.label}",
            callback_data=f"admin:channel_grant:{tg_id}:{tier_key}",
        )],
        [InlineKeyboardButton(
            text="❌ Отклонить",
            callback_data=f"admin:channel_reject:{tg_id}",
        )],
    ])

    try:
        await cb.bot.send_message(
            chat_id=channel_id,
            text=text,
            reply_markup=kb,
            parse_mode="HTML",
        )
        log.info("TON notification sent to channel %s OK", channel_id)
    except Exception as e:
        log.exception("Could not send TON notification to channel %s: %s", channel_id, e)


@router.callback_query(F.data == "premium:referral")
async def cb_referral(cb: CallbackQuery) -> None:
    from app.domain.services.referrals import make_ref_code
    from app.common.config import settings as app_settings
    lang = await _get_lang(cb.from_user.id)
    s = t(lang)
    tg_id = cb.from_user.id
    bot_username = app_settings.bot_username or "EagleToolsBot"
    link = f"https://t.me/{bot_username}?start=ref_{make_ref_code(tg_id)}"
    await cb.answer()
    await _show_panel(cb, s.referral_text(link), _back_to_premium_kb(lang))


def _back_to_premium_kb(lang: str) -> InlineKeyboardMarkup:
    s = t(lang)
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=s.btn_back_premium, callback_data="premium:open")],
    ])