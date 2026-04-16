from __future__ import annotations

import asyncio
import shutil
import tempfile
import uuid
from dataclasses import dataclass
from pathlib import Path

from aiogram import Bot
from aiogram.exceptions import TelegramBadRequest
from aiogram.types import Message


class ConvertError(RuntimeError):
    pass


@dataclass(frozen=True)
class ConvertResult:
    out_path: Path
    tmp_dir: Path


async def _run(cmd: list[str]) -> None:
    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    _, err = await proc.communicate()
    if proc.returncode != 0:
        raise ConvertError((err or b"").decode("utf-8", errors="ignore")[:800])


def _mk_tmp(workdir: Path) -> Path:
    workdir.mkdir(parents=True, exist_ok=True)
    return Path(tempfile.mkdtemp(prefix="audio_", dir=str(workdir)))


def _sanitize_filename(name: str) -> str:
    safe = "".join(c for c in (name or "") if c.isalnum() or c in "._-")
    return (safe or "input")[:120]


def _ffmpeg_args_for(fmt: str) -> list[str]:
    fmt = (fmt or "").lower().strip()

    if fmt == "mp3":
        return ["-vn", "-acodec", "libmp3lame", "-b:a", "192k"]
    if fmt == "m4a":
        # FIX #8: use -f ipod (not -f mp4) for .m4a — some mobile players
        # refuse to play .m4a files wrapped in the generic MP4 container.
        return ["-vn", "-acodec", "aac", "-b:a", "192k", "-f", "ipod"]
    if fmt == "wav":
        return ["-vn", "-acodec", "pcm_s16le"]
    if fmt == "opus":
        # opus (обычно в .opus контейнере ogg)
        return ["-vn", "-acodec", "libopus", "-b:a", "96k"]

    raise ConvertError("unsupported_format")


async def convert_audio_from_file(
    in_path: Path,
    *,
    fmt: str,
    workdir: Path,
) -> ConvertResult:
    if not in_path.exists():
        raise ConvertError("input_missing")

    fmt = (fmt or "mp3").lower().strip()
    tmp_dir = _mk_tmp(workdir)
    out_path = tmp_dir / (in_path.stem[:60] + f".{fmt}")

    cmd = ["ffmpeg", "-y", "-i", str(in_path), *_ffmpeg_args_for(fmt), str(out_path)]
    await _run(cmd)

    if not out_path.exists() or out_path.stat().st_size == 0:
        raise ConvertError("output_missing")

    return ConvertResult(out_path=out_path, tmp_dir=tmp_dir)


async def convert_to_mp3_from_file(in_path: Path, *, workdir: Path) -> ConvertResult:
    return await convert_audio_from_file(in_path, fmt="mp3", workdir=workdir)


async def tg_download_to_path(bot: Bot, message: Message, *, dst_dir: Path) -> Path:
    """
    Скачивает media из Telegram в локальный файл.
    Никаких текстов пользователю, только util.
    """
    dst_dir.mkdir(parents=True, exist_ok=True)

    file_id = None
    filename = "input.bin"

    if message.voice:
        file_id = message.voice.file_id
        filename = "voice.ogg"
    elif message.audio:
        file_id = message.audio.file_id
        filename = message.audio.file_name or "audio"
    elif message.video:
        file_id = message.video.file_id
        filename = "video.mp4"
    elif message.document:
        file_id = message.document.file_id
        filename = message.document.file_name or "file"

    if not file_id:
        raise ConvertError("unsupported_media")

    # FIX #15: prepend a unique prefix so concurrent downloads from different
    # users into the same dst_dir don't overwrite each other's files
    # (e.g. two simultaneous voice.ogg downloads).
    safe_name = f"{uuid.uuid4().hex[:8]}_{_sanitize_filename(filename)}"
    path = dst_dir / safe_name

    try:
        tg_file = await bot.get_file(file_id)
    except TelegramBadRequest as e:
        # Telegram server says - Bad Request: file is too big
        if "file is too big" in str(e).lower():
            raise ConvertError("tg_file_too_big") from e
        raise

    await bot.download_file(tg_file.file_path, destination=path)

    if not path.exists() or path.stat().st_size == 0:
        raise ConvertError("download_failed")

    return path


def cleanup_tmp_dir(path: Path) -> None:
    try:
        shutil.rmtree(path, ignore_errors=True)
    except Exception:
        pass