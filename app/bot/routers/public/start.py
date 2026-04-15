# app/bot/routers/public/start.py
"""
/start, /menu, /settings, /premium commands + screen callbacks.

Profile screen removed — all profile data is in the mini app.
The bot's welcome screen now explains the core UX in one message.
"""
from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import Command, CommandStart
from aiogram.types import CallbackQuery, Message, User as TgUser

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from app.bot.i18n import t
from app.bot.keyboards.main import main_menu_kb
from app.bot.keyboards.settings import settings_kb
from app.common.config import settings
from app.domain.services.panel import PanelRef, delete_message_safe, safe_edit_or_send
from app.domain.services.quota import get_quota_state
from app.domain.services.referrals import apply_referral_start, make_ref_code, parse_ref_code
from app.domain.services.user_repo import UserRepo
from app.infra.db.session import SessionMaker

router = Router()
_repo = UserRepo()


# ── Helpers ────────────────────────────────────────────────────────────────────

async def _get_lang(uid: int) -> str:
    async with SessionMaker() as session:
        user = await _repo.get_or_create(session, uid)
        return user.language_code or "ru"


async def _get_panel(uid: int) -> PanelRef | None:
    async with SessionMaker() as session:
        ref = await _repo.get_screen(session, uid)
    return PanelRef(chat_id=ref[0], message_id=ref[1]) if ref else None


async def _save_panel(uid: int, ref: PanelRef) -> None:
    async with SessionMaker() as session:
        await _repo.set_screen(session, uid, ref.chat_id, ref.message_id)


async def _show(message: Message, text: str, kb) -> None:
    uid = message.from_user.id
    current = await _get_panel(uid)
    await delete_message_safe(message.bot, message.chat.id, message.message_id)
    ref = await safe_edit_or_send(
        bot=message.bot,
        chat_id=message.chat.id,
        text=text,
        reply_markup=kb,
        current=current,
        parse_mode="HTML",
    )
    await _save_panel(uid, ref)


async def _show_from_cb(cb: CallbackQuery, text: str, kb) -> None:
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


async def _sync_user(tg_user: TgUser) -> None:
    async with SessionMaker() as session:
        user = await _repo.get_or_create(session, tg_user.id)
        changed = False
        for attr, val in [
            ("first_name", (tg_user.first_name or "").strip()),
            ("last_name",  (tg_user.last_name  or "").strip()),
            ("username",   (tg_user.username   or "").strip()),
        ]:
            if val and getattr(user, attr) != val:
                setattr(user, attr, val)
                changed = True
        if not user.language_code:
            tg_lang = (tg_user.language_code or "").strip()
            user.language_code = "en" if tg_lang.startswith("en") else "ru"
            changed = True
        if changed:
            await session.commit()


def _parse_start_arg(text: str | None) -> str:
    if not text:
        return ""
    parts = text.split(maxsplit=1)
    return parts[1].strip() if len(parts) >= 2 else ""


# ── Commands ───────────────────────────────────────────────────────────────────

@router.message(CommandStart())
async def cmd_start(message: Message) -> None:
    await _sync_user(message.from_user)
    arg = _parse_start_arg(message.text)

    if arg.startswith("ref_"):
        code = arg.removeprefix("ref_")
        inviter_tg = parse_ref_code(code)
        if inviter_tg:
            async with SessionMaker() as session:
                await apply_referral_start(
                    session,
                    inviter_tg_id=inviter_tg,
                    invited_tg_id=message.from_user.id,
                )

    if arg == "premium":
        from app.bot.routers.public.premium import build_premium_menu_text
        from app.bot.keyboards.premium import premium_tiers_kb
        lang = await _get_lang(message.from_user.id)
        await _show(message, build_premium_menu_text(lang), premium_tiers_kb(lang))
        return

    await _show_welcome(message)


@router.message(Command("menu"))
async def cmd_menu(message: Message) -> None:
    await _sync_user(message.from_user)
    await _show_welcome(message)


@router.message(Command("settings"))
async def cmd_settings(message: Message) -> None:
    lang = await _get_lang(message.from_user.id)
    s = t(lang)
    await _show(message, s.settings_text, settings_kb(lang))


@router.message(Command("premium"))
async def cmd_premium(message: Message) -> None:
    from app.bot.routers.public.premium import build_premium_menu_text
    from app.bot.keyboards.premium import premium_tiers_kb
    lang = await _get_lang(message.from_user.id)
    await _show(message, build_premium_menu_text(lang), premium_tiers_kb(lang))


@router.message(Command("quota"))
async def cmd_quota(message: Message) -> None:
    uid = message.from_user.id
    lang = await _get_lang(uid)
    s = t(lang)
    async with SessionMaker() as session:
        user = await _repo.get_or_create(session, uid)
        state = await get_quota_state(session, user)
    text = s.quota_status(int(state.used_today), int(state.daily_limit), state.is_unlimited)
    await _show(message, text, main_menu_kb(lang))


# ── Screen builders ────────────────────────────────────────────────────────────

async def _show_welcome(message: Message) -> None:
    lang = await _get_lang(message.from_user.id)
    s = t(lang)
    await _show(message, s.welcome_text, main_menu_kb(lang))


# ── Callbacks ──────────────────────────────────────────────────────────────────

@router.callback_query(F.data == "screen:menu")
async def cb_menu(cb: CallbackQuery) -> None:
    await cb.answer()
    lang = await _get_lang(cb.from_user.id)
    s = t(lang)
    await _show_from_cb(cb, s.welcome_text, main_menu_kb(lang))


@router.callback_query(F.data == "screen:settings")
async def cb_settings(cb: CallbackQuery) -> None:
    await cb.answer()
    lang = await _get_lang(cb.from_user.id)
    s = t(lang)
    await _show_from_cb(cb, s.settings_text, settings_kb(lang))


@router.callback_query(F.data == "screen:referral")
async def cb_referral(cb: CallbackQuery) -> None:
    await cb.answer()
    uid = cb.from_user.id
    lang = await _get_lang(uid)
    s = t(lang)

    code = make_ref_code(uid)
    bot_username = (settings.bot_username or "").strip()
    if bot_username:
        link = f"https://t.me/{bot_username}?start=ref_{code}"
    else:
        link = f"https://t.me/?start=ref_{code}"

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=s.btn_back, callback_data="screen:menu")],
    ])
    await _show_from_cb(cb, s.referral_text(link), kb)


@router.callback_query(F.data == "settings:lang")
async def cb_toggle_lang(cb: CallbackQuery) -> None:
    await cb.answer()
    async with SessionMaker() as session:
        user = await _repo.get_or_create(session, cb.from_user.id)
        current = user.language_code or "ru"
        new_lang = "en" if current == "ru" else "ru"
        user.language_code = new_lang
        await session.commit()
    s = t(new_lang)
    await _show_from_cb(cb, s.settings_text, settings_kb(new_lang))
