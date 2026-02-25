from __future__ import annotations

import asyncio
from pathlib import Path

from aiogram import Router, F
from aiogram.types import Message
from aiogram.types.input_file import FSInputFile

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


async def get_mode(uid: int) -> str | None:
    sm = get_sessionmaker()
    async with sm() as session:
        return await repo.get_active_tool(session, uid)


def is_url(s: str) -> bool:
    s = (s or "").strip().lower()
    return s.startswith("http://") or s.startswith("https://")


def mode_title(mode: str) -> str:
    return {
        "audio": "Преобразую",
        "stt": "Распознаю",
    }.get(mode, "Обрабатываю")


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
        # если не смогли отредактировать (удалено/устарело) — шлем новое
        return await message.reply(text)


async def _handle_audio_from_message(message: Message) -> None:
    size = _media_file_size(message)
    if size and size > TG_SAFE_MAX_BYTES:
        await message.reply(
            "⚠️ Файл слишком большой для обработки через Telegram.\n\n"
            "Попробуй отправить меньший файл или укоротить/сжать."
        )
        return

    base = _tmp_dir() / "audio"
    tmp_in = base / "in"
    in_path = None
    res = None

    # выбранный формат
    uid = message.from_user.id
    sm = get_sessionmaker()
    async with sm() as session:
        fmt = await repo.get_audio_format(session, uid) or "mp3"

    try:
        in_path = await tg_download_to_path(message.bot, message, dst_dir=tmp_in)
        res = await convert_audio_from_file(in_path, format=fmt, workdir=base / "work")

        await message.answer_document(
            document=FSInputFile(str(res.out_path)),
            caption="✅ Готово",
        )

    except ConvertError as e:
        code = str(e)
        if code == "tg_file_too_big":
            await message.reply(
                "⚠️ Файл слишком большой для обработки через Telegram.\n\n"
                "Попробуй отправить меньший файл или укоротить/сжать."
            )
            return
        await message.reply("Не получилось преобразовать файл.")
    finally:
        if in_path is not None:
            try:
                in_path.unlink(missing_ok=True)
            except Exception:
                pass
        cleanup_tmp_dir(tmp_in)
        if res is not None:
            cleanup_tmp_dir(res.tmp_dir)


async def _handle_stt_from_message(message: Message) -> None:
    size = _media_file_size(message)
    if size and size > TG_SAFE_MAX_BYTES:
        await message.reply(
            "⚠️ Файл слишком большой для распознавания через Telegram.\n\n"
            "Попробуй отправить меньший файл или укоротить/сжать."
        )
        return

    # очередь/конкурентность: только один STT одновременно
    if STT_SEM.locked():
        await message.reply("Сейчас распознавание занято. Попробуй ещё раз через минуту.")
        return

    base = _tmp_dir() / "stt"
    tmp_in = base / "in"
    model_dir = Path(settings.data_dir) / "models" / "whisper"

    in_path = None
    status: Message | None = None

    try:
        status = await _edit_or_send_status(
            message,
            status,
            "🧠 Подготавливаю распознавание…",
        )

        in_path = await tg_download_to_path(message.bot, message, dst_dir=tmp_in)

        async with STT_SEM:
            status = await _edit_or_send_status(
                message,
                status,
                "🧠 Распознаю…",
            )
            res = await transcribe_to_text(
                in_path,
                workdir=base / "work",
                model_dir=model_dir,
                timeout_sec=90,
            )

        text = (res.text or "").strip()

        if len(text) <= TG_TEXT_LIMIT:
            await _edit_or_send_status(
                message,
                status,
                f"✅ Готово\n\n{text}",
            )
        else:
            # если текста много — файл
            out_txt = (base / "work") / "result.txt"
            out_txt.parent.mkdir(parents=True, exist_ok=True)
            out_txt.write_text(text, encoding="utf-8")

            # статус оставим коротким, а результат как файл
            await _edit_or_send_status(message, status, "✅ Готово (файл)")
            await message.answer_document(
                document=FSInputFile(str(out_txt)),
                caption="✅ Готово",
            )

    except SttError as e:
        code = str(e)
        if code == "timeout":
            msg = "⏳ Распознавание заняло слишком много времени."
        elif code in ("empty",):
            msg = "Не получилось распознать речь."
        else:
            msg = "Не получилось распознать речь."

        # ВАЖНО: не шлем новое сообщение, а редактируем статус
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

    await message.reply(
        "🌐 Ссылки обрабатываются в Mini App.\n"
        "Открой её через 🧰 Инструменты → 🌐 Mini App (ссылки)."
    )


@router.message(F.voice | F.audio | F.video | F.document)
async def on_file(message: Message):
    mode = await get_mode(message.from_user.id)
    if not mode:
        await message.reply("Выбери режим в 🧰 Инструментах и отправь файл ещё раз.")
        return

    # ВАЖНО: для stt не запускаем countdown, чтобы не плодить статусы
    if mode == "stt":
        await _handle_stt_from_message(message)
        return

    # для остальных можно оставить countdown
    await run_countdown(message.bot, message.chat.id, mode_title(mode), seconds=5, delete_on_done=True)

    if mode == "audio":
        await _handle_audio_from_message(message)
        return

    await message.reply("✅ Готово.")