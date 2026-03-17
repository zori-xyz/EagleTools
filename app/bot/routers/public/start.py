# app/bot/routers/public/start.py
from __future__ import annotations

from aiogram import Router, F
from aiogram.filters import Command, CommandStart
from aiogram.types import CallbackQuery, Message, User as TgUser

from app.bot.i18n import t
from app.bot.keyboards.audio_format import audio_format_kb
from app.bot.keyboards.back import back_kb
from app.bot.keyboards.profile import profile_kb
from app.bot.keyboards.main import main_menu_kb
from app.bot.keyboards.tools import tools_kb
from app.domain.services.panel import PanelRef, safe_edit_or_send, delete_message_safe
from app.domain.services.referrals import apply_referral_start, parse_ref_code
from app.domain.services.user_repo import UserRepo
from app.infra.db.session import SessionMaker
from app.bot.routers.public.profile import build_profile_text

router = Router()
repo = UserRepo()


# ── Panel helpers ─────────────────────────────────────────────────────────────

async def _get_panel(uid: int) -> PanelRef | None:
    async with SessionMaker() as session:
        ref = await repo.get_screen(session, uid)
    if ref:
        return PanelRef(chat_id=ref[0], message_id=ref[1])
    return None


async def _save_panel(uid: int, ref: PanelRef) -> None:
    async with SessionMaker() as session:
        await repo.set_screen(session, uid, ref.chat_id, ref.message_id)


async def _show(message: Message, text: str, kb) -> None:
    """Show panel and delete the command message."""
    uid = message.from_user.id
    current = await _get_panel(uid)
    # Delete command message first
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


async def _get_lang(uid: int) -> str:
    async with SessionMaker() as session:
        user = await repo.get_or_create(session, uid)
        return user.language_code or "ru"


# ── Profile sync ──────────────────────────────────────────────────────────────

async def _sync_user_profile(tg_user: TgUser) -> None:
    async with SessionMaker() as session:
        user = await repo.get_or_create(session, tg_user.id)
        changed = False

        for attr, val in [
            ("first_name", (tg_user.first_name or "").strip()),
            ("last_name",  (tg_user.last_name or "").strip()),
            ("username",   (tg_user.username or "").strip()),
        ]:
            if val and getattr(user, attr) != val:
                setattr(user, attr, val)
                changed = True

        # Устанавливаем язык только при первом входе — потом не трогаем
        if not user.language_code:
            tg_lang = (tg_user.language_code or "").strip()
            user.language_code = "en" if tg_lang.startswith("en") else "ru"
            changed = True
        # Если язык уже установлен — не перезаписываем (пользователь мог сменить вручную)

        if changed:
            await session.commit()


def _parse_start_arg(text: str | None) -> str:
    if not text:
        return ""
    parts = text.split(maxsplit=1)
    return parts[1].strip() if len(parts) >= 2 else ""


# ── Commands ──────────────────────────────────────────────────────────────────

@router.message(CommandStart())
async def cmd_start(message: Message) -> None:
    await _sync_user_profile(message.from_user)
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

    await show_menu(message)


@router.message(Command("menu"))
async def cmd_menu(message: Message) -> None:
    await _sync_user_profile(message.from_user)
    await show_menu(message)


@router.message(Command("tools"))
async def cmd_tools(message: Message) -> None:
    await show_tools(message)


@router.message(Command("settings"))
async def cmd_settings(message: Message) -> None:
    await show_settings(message)


@router.message(Command("profile"))
async def cmd_profile(message: Message) -> None:
    await show_profile(message)


# ── Screens ───────────────────────────────────────────────────────────────────

async def show_menu(message: Message) -> None:
    lang = await _get_lang(message.from_user.id)
    s = t(lang)
    await _show(message, s.menu_text, main_menu_kb(lang))


async def show_tools(message: Message) -> None:
    lang = await _get_lang(message.from_user.id)
    s = t(lang)
    await _show(message, s.tools_text, tools_kb(lang))


async def show_settings(message: Message) -> None:
    from app.bot.keyboards.settings import settings_kb
    lang = await _get_lang(message.from_user.id)
    s = t(lang)
    await _show(message, s.settings_text, settings_kb(lang))


async def show_profile(message: Message) -> None:
    from datetime import datetime, timezone
    uid = message.from_user.id
    lang = await _get_lang(uid)
    text = await build_profile_text(uid, lang)
    async with SessionMaker() as session:
        user = await repo.get_or_create(session, uid)
        is_premium = bool(user.premium_until and user.premium_until > datetime.now(timezone.utc))
    await _show(message, text, profile_kb(is_premium, lang))


# ── Callbacks ─────────────────────────────────────────────────────────────────

@router.callback_query(F.data == "screen:menu")
async def cb_menu(cb: CallbackQuery) -> None:
    await cb.answer()
    lang = await _get_lang(cb.from_user.id)
    s = t(lang)
    await _show_from_cb(cb, s.menu_text, main_menu_kb(lang))


@router.callback_query(F.data == "screen:tools")
async def cb_tools(cb: CallbackQuery) -> None:
    await cb.answer()
    lang = await _get_lang(cb.from_user.id)
    s = t(lang)
    await _show_from_cb(cb, s.tools_text, tools_kb(lang))


@router.callback_query(F.data == "screen:settings")
async def cb_settings(cb: CallbackQuery) -> None:
    await cb.answer()
    from app.bot.keyboards.settings import settings_kb
    lang = await _get_lang(cb.from_user.id)
    s = t(lang)
    await _show_from_cb(cb, s.settings_text, settings_kb(lang))


@router.callback_query(F.data == "screen:profile")
async def cb_profile(cb: CallbackQuery) -> None:
    await cb.answer()
    from datetime import datetime, timezone
    uid = cb.from_user.id
    lang = await _get_lang(uid)
    text = await build_profile_text(uid, lang)
    async with SessionMaker() as session:
        user = await repo.get_or_create(session, uid)
        is_premium = bool(user.premium_until and user.premium_until > datetime.now(timezone.utc))
    await _show_from_cb(cb, text, profile_kb(is_premium, lang))


@router.callback_query(F.data == "settings:lang")
async def cb_toggle_lang(cb: CallbackQuery) -> None:
    from app.bot.keyboards.settings import settings_kb
    await cb.answer()
    async with SessionMaker() as session:
        user = await repo.get_or_create(session, cb.from_user.id)
        current_lang = user.language_code or "ru"
        new_lang = "en" if current_lang == "ru" else "ru"
        user.language_code = new_lang
        await session.commit()
    s = t(new_lang)
    await _show_from_cb(cb, s.settings_text, settings_kb(new_lang))


@router.callback_query(F.data.startswith("mode:"))
async def cb_mode(cb: CallbackQuery) -> None:
    uid = cb.from_user.id
    mode = cb.data.split(":", 1)[1]

    async with SessionMaker() as session:
        await repo.set_active_tool(session, uid, mode)

    await cb.answer()

    lang = await _get_lang(uid)
    s = t(lang)

    if mode == "audio":
        async with SessionMaker() as session:
            fmt = await repo.get_audio_format(session, uid)
        await _show_from_cb(cb, s.mode_audio_text(fmt or "mp3"), audio_format_kb(lang))
    elif mode == "stt":
        await _show_from_cb(cb, s.mode_stt_text, back_kb(lang))
    else:
        await _show_from_cb(cb, s.mode_unknown_text(mode), back_kb(lang))