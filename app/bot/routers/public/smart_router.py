# app/bot/routers/public/smart_router.py
"""
Smart router — the heart of the bot.

Handles:
  • Any URL sent to the bot → detect platform → offer actions
  • Any file (voice/audio/video/document) → detect type → offer actions
  • Callback queries for link actions  (lnk:*)
  • Callback queries for file actions  (fl:*)

Architecture (anti-ban):
  URL downloads go through our own web API (POST /api/internal/bot/save).
  The bot never calls yt-dlp directly — our server does, then bot reads the
  file from shared storage. Telegram only sees: text in → file out. Normal.
"""
from __future__ import annotations

import asyncio
import logging
import mimetypes
from pathlib import Path
from typing import Literal

from aiogram import F, Router
from aiogram.types import (
    CallbackQuery,
    FSInputFile,
    Message,
)

from app.bot.i18n import t
from app.bot.keyboards.premium import premium_limit_kb
from app.bot.keyboards.smart import (
    FileKind,
    PlatformCategory,
    after_file_kb,
    after_link_kb,
    file_actions_kb,
    format_pick_kb,
    link_actions_kb,
)
from app.bot.services.api_client import BotApiError, download_url
from app.common.config import settings
from app.domain.services.media import (
    ConvertError,
    SttError,
    cleanup_tmp_dir,
    convert_audio_from_file,
    tg_download_to_path,
    transcribe_to_text,
)
from app.domain.services.quota import QuotaExceeded, consume_quota, get_quota_state
from app.domain.services.user_repo import UserRepo
from app.infra.db.session import get_sessionmaker

log = logging.getLogger(__name__)
router = Router()
_repo = UserRepo()

TG_TEXT_LIMIT = 3800
TG_SAFE_MAX_BYTES = 19 * 1024 * 1024   # 19 MB — Telegram bot file limit
STT_SEM = asyncio.Semaphore(1)          # one STT job at a time


# ── Helpers ────────────────────────────────────────────────────────────────────

async def _get_lang(uid: int) -> str:
    sm = get_sessionmaker()
    async with sm() as session:
        user = await _repo.get_or_create(session, uid)
        return user.language_code or "ru"


def _is_url(text: str) -> bool:
    s = (text or "").strip().lower()
    return s.startswith("http://") or s.startswith("https://")


def _tmp_dir() -> Path:
    return Path(settings.data_dir) / "tmp"


def _results_dir() -> Path:
    return Path(settings.data_dir) / "results"


def _media_file_size(message: Message) -> int | None:
    for attr in ("voice", "audio", "video", "document"):
        obj = getattr(message, attr, None)
        if obj:
            return getattr(obj, "file_size", None)
    return None


# ── Quota helpers ──────────────────────────────────────────────────────────────

async def _check_and_consume_quota(message: Message, lang: str) -> bool:
    tg_id = message.from_user.id
    s = t(lang)
    sm = get_sessionmaker()
    async with sm() as session:
        user = await _repo.get_or_create(session, tg_id)
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


async def _check_and_consume_quota_cb(cb: CallbackQuery, lang: str) -> bool:
    """Same check but for callback queries — sends quota message to chat."""
    tg_id = cb.from_user.id
    s = t(lang)
    sm = get_sessionmaker()
    async with sm() as session:
        user = await _repo.get_or_create(session, tg_id)
        state = await get_quota_state(session, user)
        if not state.is_unlimited and state.used_today >= state.daily_limit:
            await cb.answer(
                s.quota_exceeded_short().replace("<b>", "").replace("</b>", ""),
                show_alert=True,
            )
            return False
        try:
            await consume_quota(session, user=user, cost=1)
            await session.commit()
        except QuotaExceeded:
            await session.rollback()
            await cb.answer(
                s.quota_exceeded_short().replace("<b>", "").replace("</b>", ""),
                show_alert=True,
            )
            return False
    return True


# ── Platform detection (URL → category + label) ────────────────────────────────

_MEDIA_DOMAINS = {
    "youtube.com", "youtu.be", "www.youtube.com", "m.youtube.com",
    "tiktok.com", "vm.tiktok.com", "www.tiktok.com",
    "instagram.com", "www.instagram.com",
    "twitter.com", "www.twitter.com", "x.com", "www.x.com", "t.co",
    "vk.com", "vkvideo.ru",
    "twitch.tv", "www.twitch.tv",
    "vimeo.com", "www.vimeo.com",
    "facebook.com", "www.facebook.com", "fb.watch",
    "dailymotion.com", "www.dailymotion.com",
    "rutube.ru", "www.rutube.ru",
    "ok.ru", "www.ok.ru",
    "coub.com", "www.coub.com",
    "bilibili.com", "www.bilibili.com",
    "reddit.com", "www.reddit.com", "v.redd.it",
    "streamable.com",
    "gfycat.com",
    "medal.tv",
    "clips.twitch.tv",
    "youtu.be",
}

_AUDIO_DOMAINS = {
    "soundcloud.com", "www.soundcloud.com",
    "open.spotify.com", "spotify.com",
    "music.yandex.ru", "music.yandex.com",
    "music.apple.com",
    "bandcamp.com",
    "mixcloud.com", "www.mixcloud.com",
    "audiomack.com",
}

_MEDIA_LABELS: dict[str, str] = {
    "youtube.com": "▶️ YouTube",
    "youtu.be": "▶️ YouTube",
    "tiktok.com": "🎵 TikTok",
    "vm.tiktok.com": "🎵 TikTok",
    "instagram.com": "📸 Instagram",
    "twitter.com": "🐦 Twitter / X",
    "x.com": "🐦 Twitter / X",
    "t.co": "🐦 Twitter / X",
    "vk.com": "💙 VK",
    "vkvideo.ru": "💙 VK Video",
    "twitch.tv": "🎮 Twitch",
    "vimeo.com": "🎬 Vimeo",
    "facebook.com": "📘 Facebook",
    "fb.watch": "📘 Facebook",
    "dailymotion.com": "🎬 Dailymotion",
    "rutube.ru": "🎬 Rutube",
    "ok.ru": "🔶 OK.ru",
    "coub.com": "🔁 Coub",
    "bilibili.com": "🎬 Bilibili",
    "reddit.com": "🟠 Reddit",
    "v.redd.it": "🟠 Reddit",
    "soundcloud.com": "☁️ SoundCloud",
    "open.spotify.com": "🟢 Spotify",
}

_AUDIO_FILE_EXTS = {".mp3", ".m4a", ".wav", ".opus", ".ogg", ".flac", ".aac", ".wma"}
_VIDEO_FILE_EXTS = {".mp4", ".mov", ".avi", ".mkv", ".webm", ".m4v", ".3gp"}


def _extract_domain(url: str) -> str:
    try:
        from urllib.parse import urlparse
        return urlparse(url).netloc.lower().lstrip("www.")
    except Exception:
        return ""


def detect_platform(url: str) -> tuple[PlatformCategory, str]:
    """
    Returns (category, human-readable label).
    category: "media" | "audio" | "direct" | "web"
    label:    e.g. "▶️ YouTube", "🔗 Direct link", etc.
    """
    domain = _extract_domain(url)

    # Check known media platforms
    for key in _MEDIA_DOMAINS:
        if domain == key or domain.endswith("." + key):
            label = _MEDIA_LABELS.get(key, f"🎬 {domain}")
            return "media", label

    # Check known audio platforms
    for key in _AUDIO_DOMAINS:
        if domain == key or domain.endswith("." + key):
            label = _MEDIA_LABELS.get(key, f"🎵 {domain}")
            return "audio", label

    # Direct file link by extension
    path = url.split("?")[0].lower()
    ext = Path(path).suffix
    if ext in _AUDIO_FILE_EXTS:
        return "direct", "🎵 Audio file"
    if ext in _VIDEO_FILE_EXTS:
        return "direct", "🎬 Video file"

    # Generic web page
    return "web", f"🌐 {domain}" if domain else "🌐 Link"


def _platform_intro(label: str, lang: str) -> str:
    s = t(lang)
    return s.link_detected(f"<b>{label}</b>")


# ── File kind detection ────────────────────────────────────────────────────────

_AUDIO_MIMES = {
    "audio/mpeg", "audio/mp4", "audio/m4a", "audio/wav", "audio/x-wav",
    "audio/ogg", "audio/opus", "audio/flac", "audio/aac",
    "audio/vnd.wave", "audio/x-m4a",
}
_VIDEO_MIMES = {
    "video/mp4", "video/quicktime", "video/x-msvideo", "video/x-matroska",
    "video/webm", "video/3gpp", "video/mpeg",
}


def _detect_file_kind(message: Message) -> tuple[FileKind, str]:
    """Returns (kind, human-readable label)."""
    if message.voice:
        size = _fmt_size(message.voice.file_size)
        return "voice", f"🎙 Voice message{size}"

    if message.audio:
        title = message.audio.title or message.audio.file_name or "audio"
        size = _fmt_size(message.audio.file_size)
        return "audio", f"🎵 {title[:40]}{size}"

    if message.video:
        dur = _fmt_duration(message.video.duration)
        size = _fmt_size(message.video.file_size)
        return "video", f"🎬 Video{dur}{size}"

    if message.document:
        mime = (message.document.mime_type or "").lower()
        fname = message.document.file_name or ""
        ext = Path(fname).suffix.lower()

        if mime in _AUDIO_MIMES or ext in _AUDIO_FILE_EXTS:
            size = _fmt_size(message.document.file_size)
            return "document_audio", f"🎵 {fname[:40] or 'Audio file'}{size}"

        if mime in _VIDEO_MIMES or ext in _VIDEO_FILE_EXTS:
            size = _fmt_size(message.document.file_size)
            return "document_video", f"🎬 {fname[:40] or 'Video file'}{size}"

        size = _fmt_size(message.document.file_size)
        return "document_other", f"📎 {fname[:40] or 'File'}{size}"

    return "document_other", "📎 File"


def _fmt_size(size: int | None) -> str:
    if not size:
        return ""
    if size < 1024:
        return f"  {size} B"
    if size < 1024 * 1024:
        return f"  {size / 1024:.0f} KB"
    return f"  {size / 1024 / 1024:.1f} MB"


def _fmt_duration(secs: int | None) -> str:
    if not secs:
        return ""
    m, s = divmod(secs, 60)
    h, m = divmod(m, 60)
    if h:
        return f"  {h}:{m:02d}:{s:02d}"
    return f"  {m}:{s:02d}"


# ── URL handler ────────────────────────────────────────────────────────────────

@router.message(F.text & ~F.text.startswith("/"))
async def on_text(message: Message) -> None:
    text = (message.text or "").strip()
    if not _is_url(text):
        return  # ignore non-URL text (let other handlers deal with it)

    lang = await _get_lang(message.from_user.id)
    category, label = detect_platform(text)

    if category == "web":
        # Nothing meaningful to do — just point to the app
        s = t(lang)
        await message.reply(
            f"🌐 <b>{label.lstrip('🌐 ')}</b>\n\n"
            + (
                "Open this in the mini app to work with its content."
                if lang == "en" else
                "Открой в мини-приложении, чтобы работать с контентом."
            ),
            reply_markup=link_actions_kb("web", lang),
            parse_mode="HTML",
        )
        return

    intro = _platform_intro(label, lang)
    await message.reply(
        intro,
        reply_markup=link_actions_kb(category, lang),
        parse_mode="HTML",
    )


# ── Link action callbacks  (lnk:*) ────────────────────────────────────────────

@router.callback_query(F.data.startswith("lnk:"))
async def on_link_action(cb: CallbackQuery) -> None:
    action = cb.data.removeprefix("lnk:")

    if action == "dismiss":
        try:
            await cb.message.delete()
        except Exception:
            pass
        await cb.answer()
        return

    # Recover the original URL from the user's message that was replied to
    orig = cb.message.reply_to_message
    if not orig or not orig.text:
        await cb.answer(
            "Link not found — please send it again." if cb.from_user.language_code
            and cb.from_user.language_code.startswith("en")
            else "Ссылка не найдена — отправь её ещё раз.",
            show_alert=True,
        )
        return

    url = orig.text.strip()
    lang = await _get_lang(cb.from_user.id)
    s = t(lang)

    if not await _check_and_consume_quota_cb(cb, lang):
        return

    # Show progress immediately
    progress_text = {
        "vid": s.link_processing,
        "aud": s.link_processing_audio,
        "stt": s.link_processing_stt,
    }.get(action, s.link_processing)

    try:
        await cb.message.edit_text(progress_text, reply_markup=None)
    except Exception:
        pass
    await cb.answer()

    if action in ("vid", "aud"):
        await _handle_link_download(cb, url, action, lang)
    elif action == "stt":
        await _handle_link_stt(cb, url, lang)


async def _handle_link_download(
    cb: CallbackQuery,
    url: str,
    action: Literal["vid", "aud"],
    lang: str,
) -> None:
    s = t(lang)
    api_action = "audio" if action == "aud" else "video"

    try:
        result = await download_url(url, action=api_action)
    except BotApiError as e:
        err = str(e)
        if "too_large" in err:
            await cb.message.edit_text(s.link_error_too_large, parse_mode="HTML")
        elif "timeout" in err:
            await cb.message.edit_text(s.link_error_timeout, parse_mode="HTML")
        else:
            await cb.message.edit_text(s.link_error, parse_mode="HTML")
        return

    filepath = _results_dir() / result.file_id
    if not filepath.exists():
        await cb.message.edit_text(s.link_error, parse_mode="HTML")
        return

    title = (result.title or "")[:100]
    file_input = FSInputFile(str(filepath))

    try:
        if action == "aud":
            await cb.message.answer_audio(
                audio=file_input,
                title=title or None,
                caption=f"🎵 {title}" if title else None,
            )
        else:
            # Try video first, fall back to document for large/unusual formats
            try:
                await cb.message.answer_video(
                    video=file_input,
                    caption=f"🎬 {title}" if title else None,
                    supports_streaming=True,
                )
            except Exception:
                file_input2 = FSInputFile(str(filepath))
                await cb.message.answer_document(
                    document=file_input2,
                    caption=f"🎬 {title}" if title else None,
                )
    except Exception as e:
        log.warning("Failed to send downloaded file: %s", e)
        await cb.message.edit_text(s.link_error, parse_mode="HTML")
        return

    # Show follow-up actions on the progress message
    try:
        await cb.message.edit_text(s.link_done, reply_markup=after_link_kb(action, lang))
    except Exception:
        pass


async def _handle_link_stt(cb: CallbackQuery, url: str, lang: str) -> None:
    s = t(lang)

    if STT_SEM.locked():
        await cb.message.edit_text(s.stt_busy, parse_mode="HTML")
        return

    # Download audio first
    try:
        result = await download_url(url, action="audio")
    except BotApiError as e:
        err = str(e)
        if "too_large" in err:
            await cb.message.edit_text(s.link_error_too_large, parse_mode="HTML")
        elif "timeout" in err:
            await cb.message.edit_text(s.link_error_timeout, parse_mode="HTML")
        else:
            await cb.message.edit_text(s.link_error, parse_mode="HTML")
        return

    filepath = _results_dir() / result.file_id
    if not filepath.exists():
        await cb.message.edit_text(s.link_error, parse_mode="HTML")
        return

    # Transcribe
    model_dir = Path(settings.data_dir) / "models" / "whisper"
    work_dir = _tmp_dir() / "stt"

    try:
        await cb.message.edit_text(s.stt_recognizing)
    except Exception:
        pass

    try:
        async with STT_SEM:
            res = await transcribe_to_text(
                filepath,
                workdir=work_dir,
                model_dir=model_dir,
                timeout_sec=180,
            )
    except SttError as e:
        msg = s.stt_timeout if "timeout" in str(e) else s.stt_empty
        await cb.message.edit_text(msg)
        return
    finally:
        # Clean up the downloaded audio
        try:
            filepath.unlink(missing_ok=True)
        except Exception:
            pass

    text = (res.text or "").strip()
    if not text:
        await cb.message.edit_text(s.stt_empty)
        return

    try:
        await cb.message.delete()
    except Exception:
        pass

    full = f"{s.stt_done}\n\n{text}"
    if len(full) <= TG_TEXT_LIMIT:
        await cb.message.answer(full)
    else:
        work_dir.mkdir(parents=True, exist_ok=True)
        out_txt = work_dir / "result.txt"
        out_txt.write_text(text, encoding="utf-8")
        await cb.message.answer_document(
            document=FSInputFile(str(out_txt)),
            caption=s.stt_done,
        )


# ── File handler ───────────────────────────────────────────────────────────────

@router.message(F.voice | F.audio | F.video | F.document)
async def on_file(message: Message) -> None:
    lang = await _get_lang(message.from_user.id)
    s = t(lang)

    size = _media_file_size(message)
    if size and size > TG_SAFE_MAX_BYTES:
        await message.reply(s.file_too_big, parse_mode="HTML")
        return

    kind, label = _detect_file_kind(message)

    if kind == "document_other":
        # We can't do anything useful with generic documents in the bot
        await message.reply(
            s.file_detected(f"<b>{label}</b>"),
            reply_markup=file_actions_kb(kind, lang),
            parse_mode="HTML",
        )
        return

    await message.reply(
        s.file_detected(f"<b>{label}</b>"),
        reply_markup=file_actions_kb(kind, lang),
        parse_mode="HTML",
    )


# ── File action callbacks  (fl:*) ─────────────────────────────────────────────

@router.callback_query(F.data.startswith("fl:"))
async def on_file_action(cb: CallbackQuery) -> None:
    action = cb.data.removeprefix("fl:")

    if action == "dismiss":
        try:
            await cb.message.delete()
        except Exception:
            pass
        await cb.answer()
        return

    if action == "fmt":
        # Show format picker
        lang = await _get_lang(cb.from_user.id)
        try:
            await cb.message.edit_reply_markup(reply_markup=format_pick_kb(lang))
        except Exception:
            pass
        await cb.answer()
        return

    # Recover the original file message
    orig = cb.message.reply_to_message
    if not orig:
        await cb.answer(
            "Original file not found — please send it again." if cb.from_user.language_code
            and cb.from_user.language_code.startswith("en")
            else "Исходный файл не найден — отправь его ещё раз.",
            show_alert=True,
        )
        return

    lang = await _get_lang(cb.from_user.id)
    s = t(lang)

    if not await _check_and_consume_quota_cb(cb, lang):
        return

    kind, _ = _detect_file_kind(orig)

    try:
        await cb.message.edit_text(s.file_processing, reply_markup=None)
    except Exception:
        pass
    await cb.answer()

    if action == "stt":
        await _handle_file_stt(cb, orig, kind, lang)
    elif action == "ext_aud":
        await _handle_file_extract_audio(cb, orig, kind, lang)
    elif action.startswith("conv:"):
        fmt = action.split(":", 1)[1]
        await _handle_file_convert(cb, orig, kind, fmt, lang)


async def _handle_file_stt(
    cb: CallbackQuery,
    orig: Message,
    kind: FileKind,
    lang: str,
) -> None:
    s = t(lang)

    if STT_SEM.locked():
        try:
            await cb.message.edit_text(s.stt_busy, reply_markup=file_actions_kb(kind, lang))
        except Exception:
            pass
        return

    base = _tmp_dir() / "stt"
    tmp_in = base / "in"
    model_dir = Path(settings.data_dir) / "models" / "whisper"
    in_path = None

    try:
        try:
            await cb.message.edit_text(s.stt_preparing)
        except Exception:
            pass

        in_path = await tg_download_to_path(cb.bot, orig, dst_dir=tmp_in)

        async with STT_SEM:
            try:
                await cb.message.edit_text(s.stt_recognizing)
            except Exception:
                pass
            res = await transcribe_to_text(
                in_path,
                workdir=base / "work",
                model_dir=model_dir,
                timeout_sec=180,
            )

        text = (res.text or "").strip()
        if not text:
            await cb.message.edit_text(s.stt_empty)
            return

        try:
            await cb.message.delete()
        except Exception:
            pass

        full = f"{s.stt_done}\n\n{text}"
        if len(full) <= TG_TEXT_LIMIT:
            await orig.reply(full)
        else:
            work = base / "work"
            work.mkdir(parents=True, exist_ok=True)
            out_txt = work / "result.txt"
            out_txt.write_text(text, encoding="utf-8")
            await orig.reply_document(
                document=FSInputFile(str(out_txt)),
                caption=s.stt_done,
            )

    except SttError as e:
        msg = s.stt_timeout if "timeout" in str(e) else s.stt_empty
        try:
            await cb.message.edit_text(msg, reply_markup=after_file_kb(kind, "stt", lang))
        except Exception:
            pass
    except Exception as e:
        log.exception("STT error: %s", e)
        try:
            await cb.message.edit_text(s.file_error)
        except Exception:
            pass
    finally:
        if in_path:
            try:
                in_path.unlink(missing_ok=True)
            except Exception:
                pass
        cleanup_tmp_dir(tmp_in)


async def _handle_file_extract_audio(
    cb: CallbackQuery,
    orig: Message,
    kind: FileKind,
    lang: str,
) -> None:
    s = t(lang)
    base = _tmp_dir() / "audio"
    tmp_in = base / "in"
    in_path = None
    res = None

    try:
        in_path = await tg_download_to_path(cb.bot, orig, dst_dir=tmp_in)
        res = await convert_audio_from_file(in_path, fmt="mp3", workdir=base / "work")

        await orig.reply_document(
            document=FSInputFile(str(res.out_path)),
            caption=s.convert_done,
        )
        try:
            await cb.message.edit_text(s.file_done, reply_markup=after_file_kb(kind, "ext_aud", lang))
        except Exception:
            pass

    except ConvertError as e:
        msg = s.file_too_big if "too_big" in str(e) else s.convert_error
        try:
            await cb.message.edit_text(msg, reply_markup=after_file_kb(kind, "ext_aud", lang))
        except Exception:
            pass
    except Exception as e:
        log.exception("Extract audio error: %s", e)
        try:
            await cb.message.edit_text(s.file_error)
        except Exception:
            pass
    finally:
        if in_path:
            try:
                in_path.unlink(missing_ok=True)
            except Exception:
                pass
        cleanup_tmp_dir(tmp_in)
        if res:
            cleanup_tmp_dir(res.tmp_dir)


async def _handle_file_convert(
    cb: CallbackQuery,
    orig: Message,
    kind: FileKind,
    fmt: str,
    lang: str,
) -> None:
    s = t(lang)
    allowed = {"mp3", "m4a", "wav", "opus"}
    if fmt not in allowed:
        fmt = "mp3"

    base = _tmp_dir() / "audio"
    tmp_in = base / "in"
    in_path = None
    res = None

    try:
        in_path = await tg_download_to_path(cb.bot, orig, dst_dir=tmp_in)
        res = await convert_audio_from_file(in_path, fmt=fmt, workdir=base / "work")

        await orig.reply_document(
            document=FSInputFile(str(res.out_path)),
            caption=s.convert_done,
        )
        try:
            await cb.message.edit_text(s.file_done, reply_markup=after_file_kb(kind, "conv", lang))
        except Exception:
            pass

    except ConvertError as e:
        msg = s.file_too_big if "too_big" in str(e) else s.convert_error
        try:
            await cb.message.edit_text(msg, reply_markup=after_file_kb(kind, "conv", lang))
        except Exception:
            pass
    except Exception as e:
        log.exception("Convert error: %s", e)
        try:
            await cb.message.edit_text(s.file_error)
        except Exception:
            pass
    finally:
        if in_path:
            try:
                in_path.unlink(missing_ok=True)
            except Exception:
                pass
        cleanup_tmp_dir(tmp_in)
        if res:
            cleanup_tmp_dir(res.tmp_dir)
