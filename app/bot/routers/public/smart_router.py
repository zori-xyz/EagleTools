# app/bot/routers/public/smart_router.py
from __future__ import annotations

import asyncio
from pathlib import Path

from aiogram import Router, F
from aiogram.types import Message
from aiogram.types.input_file import FSInputFile

from app.bot.i18n import t
from app.common.config import settings
from app.domain.services.progress import run_countdown
from app.domain.services.user_repo import UserRepo
from app.domain.services.media import (
    tg_download_to_path,
    convert_audio_from_file,
    cleanup_tmp_dir,
    ConvertError,
    transcribe_to_text,
    SttError,
)
from app.infra.db.session import get_sessionmaker

router = Router()
repo = UserRepo()

TG_TEXT_LIMIT = 3800
STT_SEM = asyncio.Semaphore(1)
TG_SAFE_MAX_BYTES = 19 * 1024 * 1024


async def _get_lang(uid: int) -> str:
    sm = get_sessionmaker()
    async with sm() as session:
        user = await repo.get_or_create(session, uid)
        return user.language_code or "ru"


async def get_mode(uid: int) -> str | None:
    sm = get_sessionmaker()
    async with sm() as session:
        return await repo.get_active_tool(session, uid)


def is_url(s: str) -> bool:
    s = (s or "").strip().lower()
    return s.startswith("http://") or s.startswith("https://")


def _tmp_dir() -> Path:
    return Path(settings.data_dir) / "tmp"


def _media_file_size(message: Message) -> int | None:
    if message.voice:
        return message.voice.file_size
    if message.audio:
        return message.audio.file_size
    if message.video:
        return message.video.file_size
    if message.document:
        return message.document.file_size
    return None


async def _edit_or_send_status(message: Message, status: Message | None, text: str) -> Message:
    if status is None:
        return await message.reply(text)
    try:
        await status.edit_text(text)
        return status
    except Exception:
        return await message.reply(text)


async def _handle_audio_from_message(message: Message, lang: str) -> None:
    s = t(lang)
    size = _media_file_size(message)
    if size and size > TG_SAFE_MAX_BYTES:
        await message.reply(s.file_too_big)
        return

    base = _tmp_dir() / "audio"
    tmp_in = base / "in"
    in_path = None
    res = None

    uid = message.from_user.id
    sm = get_sessionmaker()
    async with sm() as session:
        fmt = await repo.get_audio_format(session, uid) or "mp3"

    try:
        in_path = await tg_download_to_path(message.bot, message, dst_dir=tmp_in)
        res = await convert_audio_from_file(in_path, fmt=fmt, workdir=base / "work")

        await message.answer_document(
            document=FSInputFile(str(res.out_path)),
            caption=s.convert_done,
        )

    except ConvertError as e:
        code = str(e)
        if code == "tg_file_too_big":
            await message.reply(s.file_too_big)
            return
        await message.reply(s.convert_error)
    finally:
        if in_path is not None:
            try:
                in_path.unlink(missing_ok=True)
            except Exception:
                pass
        cleanup_tmp_dir(tmp_in)
        if res is not None:
            cleanup_tmp_dir(res.tmp_dir)


async def _handle_stt_from_message(message: Message, lang: str) -> None:
    s = t(lang)
    size = _media_file_size(message)
    if size and size > TG_SAFE_MAX_BYTES:
        await message.reply(s.file_too_big)
        return

    if STT_SEM.locked():
        await message.reply(s.stt_busy)
        return

    base = _tmp_dir() / "stt"
    tmp_in = base / "in"
    model_dir = Path(settings.data_dir) / "models" / "whisper"

    in_path = None
    status: Message | None = None

    try:
        status = await _edit_or_send_status(message, status, s.stt_preparing)
        in_path = await tg_download_to_path(message.bot, message, dst_dir=tmp_in)

        async with STT_SEM:
            status = await _edit_or_send_status(message, status, s.stt_recognizing)
            res = await transcribe_to_text(
                in_path,
                workdir=base / "work",
                model_dir=model_dir,
                timeout_sec=90,
            )

        text = (res.text or "").strip()

        if len(text) <= TG_TEXT_LIMIT:
            await _edit_or_send_status(message, status, f"{s.stt_done}\n\n{text}")
        else:
            out_txt = (base / "work") / "result.txt"
            out_txt.parent.mkdir(parents=True, exist_ok=True)
            out_txt.write_text(text, encoding="utf-8")
            await _edit_or_send_status(message, status, s.stt_done_file)
            await message.answer_document(
                document=FSInputFile(str(out_txt)),
                caption=s.stt_done,
            )

    except SttError as e:
        code = str(e)
        if code == "timeout":
            msg = s.stt_timeout
        else:
            msg = s.stt_empty

        if status is None:
            await message.reply(msg)
        else:
            try:
                await status.edit_text(msg)
            except Exception:
                await message.reply(msg)

    finally:
        if in_path is not None:
            try:
                in_path.unlink(missing_ok=True)
            except Exception:
                pass
        cleanup_tmp_dir(tmp_in)


@router.message(F.text & ~F.text.startswith("/"))
async def on_text(message: Message):
    text = (message.text or "").strip()
    if not is_url(text):
        return
    lang = await _get_lang(message.from_user.id)
    await message.reply(t(lang).url_in_miniapp)


from app.domain.services.quota import QuotaExceeded, consume_quota, get_quota_state
from app.domain.services.user_repo import UserRepo as _UserRepoQuota
from app.bot.keyboards.premium import premium_limit_kb

_quota_repo = _UserRepoQuota()


async def _check_and_consume_quota(message: Message, lang: str) -> bool:
    """Returns True if quota ok, False if exceeded (sends message)."""
    tg_id = message.from_user.id
    s = t(lang)
    sm = get_sessionmaker()
    async with sm() as session:
        user = await _quota_repo.get_or_create(session, tg_id)
        state = await get_quota_state(session, user)

        if not state.is_unlimited and state.used_today >= state.daily_limit:
            await message.reply(
                s.quota_exceeded(state.used_today, state.daily_limit),
                reply_markup=premium_limit_kb(lang),
                parse_mode="HTML",
            )
            return False

        try:
            await consume_quota(session, user=user, cost=1)
            await session.commit()
        except QuotaExceeded:
            await session.rollback()
            await message.reply(
                s.quota_exceeded_short(),
                reply_markup=premium_limit_kb(lang),
                parse_mode="HTML",
            )
            return False

    return True


@router.message(F.voice | F.audio | F.video | F.document)
async def on_file(message: Message):
    lang = await _get_lang(message.from_user.id)
    s = t(lang)
    mode = await get_mode(message.from_user.id)
    if not mode:
        await message.reply(s.no_mode_selected)
        return

    if not await _check_and_consume_quota(message, lang):
        return

    if mode == "stt":
        await _handle_stt_from_message(message, lang)
        return

    await run_countdown(message.bot, message.chat.id, s.mode_title(mode), seconds=5, delete_on_done=True)

    if mode == "audio":
        await _handle_audio_from_message(message, lang)
        return

    await message.reply("✅")