from __future__ import annotations

from aiogram import Router, F
from aiogram.filters import Command, CommandStart
from aiogram.types import CallbackQuery, Message
from aiogram.exceptions import TelegramBadRequest, TelegramAPIError

from app.bot.keyboards.main import main_menu_kb
from app.bot.keyboards.tools import tools_kb
from app.bot.keyboards.back import back_kb
from app.bot.keyboards.audio_format import audio_format_kb
from app.domain.services.ui import ScreenRef, send_screen, safe_delete
from app.domain.services.user_repo import UserRepo
from app.infra.db.session import SessionMaker

from app.domain.services.referrals import apply_referral_start, parse_ref_code
from app.bot.routers.public.profile import build_profile_text

router = Router()
repo = UserRepo()


def txt_menu() -> str:
    return "🦅 EagleTools\n\nВыбери раздел:"


def txt_tools() -> str:
    return "🧰 Инструменты\n\nВыбери режим:\n\n🌐 Ссылки открывай в Mini App."


def txt_settings() -> str:
    return "⚙️ Настройки\n\nПока базово. (Язык позже)"


def mode_name(mode: str) -> str:
    return {
        "audio": "🎧 Конвертировать в аудио",
        "stt": "📝 Распознать речь в текст",
    }.get(mode, mode)


def _fmt_name(fmt: str | None) -> str:
    f = (fmt or "mp3").lower()
    return {"mp3": "MP3", "m4a": "M4A", "wav": "WAV", "opus": "OPUS"}.get(f, f.upper())


def _parse_start_arg(text: str | None) -> str:
    if not text:
        return ""
    parts = text.split(maxsplit=1)
    if len(parts) < 2:
        return ""
    return parts[1].strip()


async def _get_prev_screen(uid: int) -> ScreenRef | None:
    async with SessionMaker() as session:
        ref = await repo.get_screen(session, uid)
        if not ref:
            return None
        return ScreenRef(chat_id=ref[0], message_id=ref[1])


async def _set_screen(uid: int, chat_id: int, message_id: int) -> None:
    async with SessionMaker() as session:
        await repo.set_screen(session, uid, chat_id, message_id)


async def _cleanup_clicked_message(cb: CallbackQuery) -> None:
    await safe_delete(cb.bot, cb.message.chat.id, cb.message.message_id)


async def _delete_mode_message(uid: int, bot) -> None:
    async with SessionMaker() as session:
        ref = await repo.get_mode_msg(session, uid)

    if ref:
        chat_id, msg_id = ref
        await safe_delete(bot, chat_id, msg_id)

        async with SessionMaker() as session:
            await repo.clear_mode_msg(session, uid)


async def _upsert_mode_message(message: Message, text: str, kb=None) -> None:
    uid = message.from_user.id

    async with SessionMaker() as session:
        ref = await repo.get_mode_msg(session, uid)

    if ref:
        chat_id, msg_id = ref
        try:
            await message.bot.edit_message_text(
                chat_id=chat_id,
                message_id=msg_id,
                text=text,
                reply_markup=kb,
            )
            return
        except TelegramBadRequest:
            pass
        except TelegramAPIError:
            pass

        await safe_delete(message.bot, chat_id, msg_id)
        async with SessionMaker() as session:
            await repo.clear_mode_msg(session, uid)

    m = await message.answer(text, reply_markup=kb)
    async with SessionMaker() as session:
        await repo.set_mode_msg(session, uid, m.chat.id, m.message_id)


async def show_screen(message: Message, text: str, kb) -> None:
    uid = message.from_user.id
    prev = await _get_prev_screen(uid)
    ref = await send_screen(message.bot, message.chat.id, text, kb, prev)
    await _set_screen(uid, ref.chat_id, ref.message_id)


async def show_menu(message: Message) -> None:
    await _delete_mode_message(message.from_user.id, message.bot)
    await show_screen(message, txt_menu(), main_menu_kb())


async def show_tools(message: Message) -> None:
    await show_screen(message, txt_tools(), tools_kb())


async def show_settings(message: Message) -> None:
    await _delete_mode_message(message.from_user.id, message.bot)
    await show_screen(message, txt_settings(), back_kb())


async def show_profile(message: Message) -> None:
    await _delete_mode_message(message.from_user.id, message.bot)
    text = await build_profile_text(message.from_user.id)
    await show_screen(message, text, back_kb())


# ---------- commands ----------
@router.message(CommandStart())
async def cmd_start(message: Message):
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

    await show_menu(message)


@router.message(Command("menu"))
async def cmd_menu(message: Message):
    await show_menu(message)


@router.message(Command("tools"))
async def cmd_tools(message: Message):
    await show_tools(message)


@router.message(Command("settings"))
async def cmd_settings(message: Message):
    await show_settings(message)


@router.message(Command("profile"))
async def cmd_profile(message: Message):
    await show_profile(message)


# ---------- callbacks ----------
@router.callback_query(F.data == "screen:menu")
async def cb_menu(cb: CallbackQuery):
    await cb.answer()
    await _cleanup_clicked_message(cb)
    await show_menu(cb.message)


@router.callback_query(F.data == "screen:tools")
async def cb_tools(cb: CallbackQuery):
    await cb.answer()
    await _cleanup_clicked_message(cb)
    await show_tools(cb.message)


@router.callback_query(F.data == "screen:settings")
async def cb_settings(cb: CallbackQuery):
    await cb.answer()
    await _cleanup_clicked_message(cb)
    await show_settings(cb.message)


@router.callback_query(F.data == "screen:profile")
async def cb_profile(cb: CallbackQuery):
    await cb.answer()
    await _cleanup_clicked_message(cb)
    await show_profile(cb.message)


@router.callback_query(F.data.startswith("mode:"))
async def cb_mode(cb: CallbackQuery):
    uid = cb.from_user.id
    mode = cb.data.split(":", 1)[1]

    async with SessionMaker() as session:
        await repo.set_active_tool(session, uid, mode)

    await cb.answer("Ок")

    if mode == "audio":
        async with SessionMaker() as session:
            fmt = await repo.get_audio_format(session, uid)

        await _upsert_mode_message(
            cb.message,
            "✅ Режим выбран: 🎧 Конвертировать в аудио\n"
            f"Формат: {_fmt_name(fmt)}\n\n"
            "Отправь файл.",
            kb=audio_format_kb(),
        )
        return

    await _upsert_mode_message(
        cb.message,
        f"✅ Режим выбран: {mode_name(mode)}\nОтправь файл или ссылку.",
    )