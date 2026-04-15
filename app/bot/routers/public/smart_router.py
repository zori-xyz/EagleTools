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
import uuid
from pathlib import Path
from typing import Literal

from aiogram import F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.types import (
    Bot,
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
    stt_result_kb,
)
from app.bot.services import ctx_store
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
from app.domain.services.panel import delete_message_safe
from app.domain.services.quota import QuotaExceeded, consume_quota, get_quota_state
from app.domain.services.user_repo import UserRepo
from app.infra.db.session import get_sessionmaker

log = logging.getLogger(__name__)
router = Router()
_repo = UserRepo()

# ── Per-user state (in-memory; Redis is the persistence fallback) ─────────────

# Stores URL string or file info dict for active callbacks.
_user_ctx: dict[int, dict] = {}

# Tracks current panel message so it can be cleaned up on next input.
_panel_ref: dict[int, tuple[int, int]] = {}  # uid → (chat_id, message_id)

# Prevents double-tap: user IDs currently being processed.
_processing: set[int] = set()

TG_TEXT_LIMIT = 3800
TG_SAFE_MAX_BYTES = 19 * 1024 * 1024   # 19 MB — Telegram bot file limit
STT_SEM = asyncio.Semaphore(1)          # one STT job at a time


# ── Generic helpers ────────────────────────────────────────────────────────────

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


def _extract_file_info(message: Message) -> tuple[str | None, str]:
    """Return (file_id, filename) for any media message."""
    if message.voice:
        return message.voice.file_id, "voice.ogg"
    if message.audio:
        return message.audio.file_id, message.audio.file_name or "audio"
    if message.video:
        return message.video.file_id, "video.mp4"
    if message.document:
        return message.document.file_id, message.document.file_name or "file"
    return None, "file"


# ── Progress animation ─────────────────────────────────────────────────────────

async def _progress_anim(message: Message, base_text: str, stop: asyncio.Event) -> None:
    """
    Edits the progress message every 4 s, appending elapsed seconds.
    Stops when `stop` is set or on any edit error.
    """
    # Strip leading emoji so we can control it
    stripped = base_text
    for prefix in ("⏳ ", "⌛ ", "🧠 "):
        if stripped.startswith(prefix):
            stripped = stripped[len(prefix):]
            break

    frames = ["⏳", "⌛"]
    elapsed = 0
    while not stop.is_set():
        await asyncio.sleep(4)
        if stop.is_set():
            break
        elapsed += 4
        icon = frames[(elapsed // 4) % 2]
        try:
            await message.edit_text(
                f"{icon} {stripped} <i>{elapsed}с</i>",
                reply_markup=None,
                parse_mode="HTML",
            )
        except Exception:
            return  # message was edited or deleted, stop silently


# ── Auto-delete helper ─────────────────────────────────────────────────────────

async def _delete_after(bot: Bot, chat_id: int, message_id: int, delay: int) -> None:
    await asyncio.sleep(delay)
    try:
        await bot.delete_message(chat_id=chat_id, message_id=message_id)
    except Exception:
        pass


async def _send_autodelete(
    bot: Bot,
    chat_id: int,
    text: str,
    parse_mode: str = "HTML",
    delay: int = 10,
) -> None:
    """Send a message and schedule its deletion after `delay` seconds."""
    try:
        msg = await bot.send_message(chat_id=chat_id, text=text, parse_mode=parse_mode)
    except Exception:
        return
    asyncio.create_task(_delete_after(bot, chat_id, msg.message_id, delay))


# ── File download helper (supports both Message and file_id fallback) ──────────

async def _download_from_ctx(bot: Bot, ctx: dict, dst_dir: Path) -> Path:
    """
    Download a Telegram file using whatever is available in ctx:
      - 'orig_msg'  → use tg_download_to_path (fast, same session)
      - 'file_id'   → download directly by file_id (Redis fallback after restart)
    """
    orig = ctx.get("orig_msg")
    if orig is not None:
        return await tg_download_to_path(bot, orig, dst_dir=dst_dir)

    file_id = ctx.get("file_id")
    filename = ctx.get("filename", "file")
    if not file_id:
        raise ConvertError("no_file_reference")

    dst_dir.mkdir(parents=True, exist_ok=True)
    safe = f"{uuid.uuid4().hex[:8]}_{filename[:60]}"
    path = dst_dir / safe

    try:
        tg_file = await bot.get_file(file_id)
    except TelegramBadRequest as e:
        if "file is too big" in str(e).lower():
            raise ConvertError("tg_file_too_big") from e
        raise

    await bot.download_file(tg_file.file_path, destination=path)
    if not path.exists() or path.stat().st_size == 0:
        raise ConvertError("download_failed")
    return path


# ── Quota helpers ──────────────────────────────────────────────────────────────

async def _check_and_consume_quota(message: Message, lang: str) -> bool:
    tg_id = message.from_user.id
    s = t(lang)
    sm = get_sessionmaker()
    async with sm() as session:
        user = await _repo.get_or_create(session, tg_id)
        state = await get_quota_state(session, user)
        if not state.is_unlimited and state.used_today >= state.daily_limit:
            await _send_autodelete(
                message.bot,
                message.chat.id,
                s.quota_exceeded(state.used_today, state.daily_limit),
                delay=12,
            )
            return False
        try:
            await consume_quota(session, user=user, cost=1)
            await session.commit()
        except QuotaExceeded:
            await session.rollback()
            await _send_autodelete(
                message.bot,
                message.chat.id,
                s.quota_exceeded_short(),
                delay=12,
            )
            return False
    return True


async def _check_and_consume_quota_cb(cb: CallbackQuery, lang: str) -> bool:
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
    domain = _extract_domain(url)
    for key in _MEDIA_DOMAINS:
        if domain == key or domain.endswith("." + key):
            return "media", _MEDIA_LABELS.get(key, f"🎬 {domain}")
    for key in _AUDIO_DOMAINS:
        if domain == key or domain.endswith("." + key):
            return "audio", _MEDIA_LABELS.get(key, f"🎵 {domain}")
    path = url.split("?")[0].lower()
    ext = Path(path).suffix
    if ext in _AUDIO_FILE_EXTS:
        return "direct", "🎵 Audio file"
    if ext in _VIDEO_FILE_EXTS:
        return "direct", "🎬 Video file"
    return "web", f"🌐 {domain}" if domain else "🌐 Link"


def _platform_intro(label: str, lang: str) -> str:
    return t(lang).link_detected(f"<b>{label}</b>")


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
    if message.voice:
        return "voice", f"🎙 Voice message{_fmt_size(message.voice.file_size)}"
    if message.audio:
        title = message.audio.title or message.audio.file_name or "audio"
        return "audio", f"🎵 {title[:40]}{_fmt_size(message.audio.file_size)}"
    if message.video:
        return "video", f"🎬 Video{_fmt_duration(message.video.duration)}{_fmt_size(message.video.file_size)}"
    if message.document:
        mime = (message.document.mime_type or "").lower()
        fname = message.document.file_name or ""
        ext = Path(fname).suffix.lower()
        if mime in _AUDIO_MIMES or ext in _AUDIO_FILE_EXTS:
            return "document_audio", f"🎵 {fname[:40] or 'Audio file'}{_fmt_size(message.document.file_size)}"
        if mime in _VIDEO_MIMES or ext in _VIDEO_FILE_EXTS:
            return "document_video", f"🎬 {fname[:40] or 'Video file'}{_fmt_size(message.document.file_size)}"
        return "document_other", f"📎 {fname[:40] or 'File'}{_fmt_size(message.document.file_size)}"
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
        return

    uid = message.from_user.id
    url = text
    category, label = detect_platform(url)

    if category == "web":
        return  # nothing useful for generic web pages in the bot

    lang = await _get_lang(uid)

    # Store URL — in memory + Redis (for post-restart callbacks)
    _user_ctx[uid] = {"url": url, "type": "url"}
    asyncio.create_task(ctx_store.ctx_set(uid, {"url": url, "type": "url"}))

    # Delete previous smart-router panel to keep chat clean
    if uid in _panel_ref:
        old_chat, old_msg = _panel_ref.pop(uid)
        await delete_message_safe(message.bot, old_chat, old_msg)

    panel = await message.bot.send_message(
        chat_id=message.chat.id,
        text=_platform_intro(label, lang),
        reply_markup=link_actions_kb(category, lang),
        parse_mode="HTML",
        disable_web_page_preview=True,
    )
    _panel_ref[uid] = (panel.chat.id, panel.message_id)


# ── Link action callbacks  (lnk:*) ────────────────────────────────────────────

@router.callback_query(F.data.startswith("lnk:"))
async def on_link_action(cb: CallbackQuery) -> None:
    action = cb.data.removeprefix("lnk:")
    uid = cb.from_user.id

    if action == "dismiss":
        _panel_ref.pop(uid, None)
        _user_ctx.pop(uid, None)
        asyncio.create_task(ctx_store.ctx_del(uid))
        try:
            await cb.message.delete()
        except Exception:
            pass
        await cb.answer()
        return

    # Double-tap protection
    if uid in _processing:
        is_en = (cb.from_user.language_code or "").startswith("en")
        await cb.answer(
            "Already processing, please wait…" if is_en else "Уже обрабатываю, подожди…",
            show_alert=True,
        )
        return

    # Retrieve URL — in-memory first, then Redis fallback
    url = _user_ctx.get(uid, {}).get("url")
    if not url:
        redis_ctx = await ctx_store.ctx_get(uid)
        url = redis_ctx.get("url")
        if url:
            _user_ctx[uid] = redis_ctx  # warm the memory cache

    if not url:
        await cb.answer(
            "Link not found — please send it again."
            if (cb.from_user.language_code or "").startswith("en")
            else "Ссылка не найдена — отправь её ещё раз.",
            show_alert=True,
        )
        return

    lang = await _get_lang(uid)
    s = t(lang)

    if not await _check_and_consume_quota_cb(cb, lang):
        return

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

    _processing.add(uid)
    try:
        if action in ("vid", "aud"):
            await _handle_link_download(cb, url, action, lang)
        elif action == "stt":
            await _handle_link_stt(cb, url, lang)
    finally:
        _processing.discard(uid)


async def _handle_link_download(
    cb: CallbackQuery,
    url: str,
    action: Literal["vid", "aud"],
    lang: str,
) -> None:
    s = t(lang)
    api_action = "audio" if action == "aud" else "video"

    # Start progress animation
    stop = asyncio.Event()
    anim = asyncio.create_task(_progress_anim(cb.message, {
        "vid": s.link_processing,
        "aud": s.link_processing_audio,
    }.get(action, s.link_processing), stop))

    try:
        result = await download_url(url, action=api_action)
    except BotApiError as e:
        stop.set(); anim.cancel()
        err = str(e)
        if "too_large" in err:
            await cb.message.edit_text(s.link_error_too_large, parse_mode="HTML")
        elif "timeout" in err:
            await cb.message.edit_text(s.link_error_timeout, parse_mode="HTML")
        else:
            await cb.message.edit_text(s.link_error, parse_mode="HTML")
        return
    finally:
        stop.set(); anim.cancel()

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

    try:
        await cb.message.edit_text(s.link_done, reply_markup=after_link_kb(action, lang))
    except Exception:
        pass


async def _handle_link_stt(cb: CallbackQuery, url: str, lang: str) -> None:
    s = t(lang)

    if STT_SEM.locked():
        await cb.message.edit_text(s.stt_busy, parse_mode="HTML")
        return

    # Download audio
    stop_dl = asyncio.Event()
    anim_dl = asyncio.create_task(_progress_anim(cb.message, s.link_processing_audio, stop_dl))
    try:
        result = await download_url(url, action="audio")
    except BotApiError as e:
        stop_dl.set(); anim_dl.cancel()
        err = str(e)
        if "too_large" in err:
            await cb.message.edit_text(s.link_error_too_large, parse_mode="HTML")
        elif "timeout" in err:
            await cb.message.edit_text(s.link_error_timeout, parse_mode="HTML")
        else:
            await cb.message.edit_text(s.link_error, parse_mode="HTML")
        return
    finally:
        stop_dl.set(); anim_dl.cancel()

    filepath = _results_dir() / result.file_id
    if not filepath.exists():
        await cb.message.edit_text(s.link_error, parse_mode="HTML")
        return

    model_dir = Path(settings.data_dir) / "models" / "whisper"
    work_dir = _tmp_dir() / "stt"

    # Transcribe with animated progress
    stop_stt = asyncio.Event()
    try:
        await cb.message.edit_text(s.stt_recognizing)
    except Exception:
        pass
    anim_stt = asyncio.create_task(_progress_anim(cb.message, s.stt_recognizing, stop_stt))

    try:
        async with STT_SEM:
            res = await transcribe_to_text(
                filepath,
                workdir=work_dir,
                model_dir=model_dir,
                timeout_sec=180,
            )
    except SttError as e:
        stop_stt.set(); anim_stt.cancel()
        msg = s.stt_timeout if "timeout" in str(e) else s.stt_empty
        await cb.message.edit_text(msg, reply_markup=stt_result_kb("lnk:dismiss", lang))
        return
    finally:
        stop_stt.set(); anim_stt.cancel()
        try:
            filepath.unlink(missing_ok=True)
        except Exception:
            pass

    text = (res.text or "").strip()
    if not text:
        await cb.message.edit_text(s.stt_empty, reply_markup=stt_result_kb("lnk:dismiss", lang))
        return

    full = f"📝 {s.stt_done}\n\n{text}"
    if len(full) <= TG_TEXT_LIMIT:
        try:
            await cb.message.edit_text(full, reply_markup=stt_result_kb("lnk:dismiss", lang), parse_mode=None)
        except Exception:
            await cb.message.answer(full)
    else:
        work_dir.mkdir(parents=True, exist_ok=True)
        out_txt = work_dir / "result.txt"
        out_txt.write_text(text, encoding="utf-8")
        await cb.message.answer_document(
            document=FSInputFile(str(out_txt)),
            caption=s.stt_done,
        )
        try:
            await cb.message.edit_text(s.link_done, reply_markup=stt_result_kb("lnk:dismiss", lang))
        except Exception:
            pass


# ── File handler ───────────────────────────────────────────────────────────────

@router.message(F.voice | F.audio | F.video | F.document)
async def on_file(message: Message) -> None:
    uid = message.from_user.id
    lang = await _get_lang(uid)
    s = t(lang)

    size = _media_file_size(message)
    if size and size > TG_SAFE_MAX_BYTES:
        await _send_autodelete(message.bot, message.chat.id, s.file_too_big, delay=10)
        return

    kind, label = _detect_file_kind(message)
    file_id, filename = _extract_file_info(message)

    # Store context — in memory + Redis
    ctx_data = {"type": "file", "kind": kind, "orig_msg": message, "file_id": file_id, "filename": filename}
    _user_ctx[uid] = ctx_data
    asyncio.create_task(ctx_store.ctx_set(uid, ctx_data))

    # Delete previous panel
    if uid in _panel_ref:
        old_chat, old_msg = _panel_ref.pop(uid)
        await delete_message_safe(message.bot, old_chat, old_msg)

    panel = await message.bot.send_message(
        chat_id=message.chat.id,
        text=s.file_detected(f"<b>{label}</b>"),
        reply_markup=file_actions_kb(kind, lang),
        parse_mode="HTML",
    )
    _panel_ref[uid] = (panel.chat.id, panel.message_id)


# ── File action callbacks  (fl:*) ─────────────────────────────────────────────

@router.callback_query(F.data.startswith("fl:"))
async def on_file_action(cb: CallbackQuery) -> None:
    action = cb.data.removeprefix("fl:")
    uid = cb.from_user.id

    if action == "dismiss":
        _panel_ref.pop(uid, None)
        _user_ctx.pop(uid, None)
        asyncio.create_task(ctx_store.ctx_del(uid))
        try:
            await cb.message.delete()
        except Exception:
            pass
        await cb.answer()
        return

    if action == "fmt":
        lang = await _get_lang(uid)
        try:
            await cb.message.edit_reply_markup(reply_markup=format_pick_kb(lang))
        except Exception:
            pass
        await cb.answer()
        return

    # Double-tap protection
    if uid in _processing:
        is_en = (cb.from_user.language_code or "").startswith("en")
        await cb.answer(
            "Already processing, please wait…" if is_en else "Уже обрабатываю, подожди…",
            show_alert=True,
        )
        return

    # Retrieve file context — memory first, then Redis fallback
    ctx = _user_ctx.get(uid)
    if not ctx or ctx.get("type") != "file":
        redis_ctx = await ctx_store.ctx_get(uid)
        if redis_ctx and redis_ctx.get("type") == "file":
            ctx = redis_ctx
            _user_ctx[uid] = ctx

    if not ctx or (not ctx.get("orig_msg") and not ctx.get("file_id")):
        await cb.answer(
            "Original file not found — please send it again."
            if (cb.from_user.language_code or "").startswith("en")
            else "Исходный файл не найден — отправь его ещё раз.",
            show_alert=True,
        )
        return

    lang = await _get_lang(uid)
    s = t(lang)

    if not await _check_and_consume_quota_cb(cb, lang):
        return

    orig = ctx.get("orig_msg")
    kind = ctx.get("kind") or (orig and _detect_file_kind(orig)[0]) or "document_other"

    try:
        await cb.message.edit_text(s.file_processing, reply_markup=None)
    except Exception:
        pass
    await cb.answer()

    _processing.add(uid)
    try:
        if action == "stt":
            await _handle_file_stt(cb, ctx, kind, lang)
        elif action == "ext_aud":
            await _handle_file_extract_audio(cb, ctx, kind, lang)
        elif action.startswith("conv:"):
            fmt = action.split(":", 1)[1]
            await _handle_file_convert(cb, ctx, kind, fmt, lang)
    finally:
        _processing.discard(uid)


async def _handle_file_stt(
    cb: CallbackQuery,
    ctx: dict,
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
        stop_dl = asyncio.Event()
        anim_dl = asyncio.create_task(_progress_anim(cb.message, s.stt_preparing, stop_dl))
        try:
            in_path = await _download_from_ctx(cb.bot, ctx, dst_dir=tmp_in)
        finally:
            stop_dl.set(); anim_dl.cancel()

        stop_stt = asyncio.Event()
        try:
            await cb.message.edit_text(s.stt_recognizing)
        except Exception:
            pass
        anim_stt = asyncio.create_task(_progress_anim(cb.message, s.stt_recognizing, stop_stt))

        try:
            async with STT_SEM:
                res = await transcribe_to_text(
                    in_path,
                    workdir=base / "work",
                    model_dir=model_dir,
                    timeout_sec=180,
                )
        finally:
            stop_stt.set(); anim_stt.cancel()

        text = (res.text or "").strip()
        if not text:
            await cb.message.edit_text(s.stt_empty, reply_markup=stt_result_kb("fl:dismiss", lang))
            return

        full = f"📝 {s.stt_done}\n\n{text}"
        if len(full) <= TG_TEXT_LIMIT:
            try:
                await cb.message.edit_text(full, reply_markup=stt_result_kb("fl:dismiss", lang), parse_mode=None)
            except Exception:
                await cb.message.answer(full)
        else:
            work = base / "work"
            work.mkdir(parents=True, exist_ok=True)
            out_txt = work / "result.txt"
            out_txt.write_text(text, encoding="utf-8")
            await cb.message.answer_document(
                document=FSInputFile(str(out_txt)),
                caption=s.stt_done,
            )
            try:
                await cb.message.edit_text(s.file_done, reply_markup=stt_result_kb("fl:dismiss", lang))
            except Exception:
                pass

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
    ctx: dict,
    kind: FileKind,
    lang: str,
) -> None:
    s = t(lang)
    base = _tmp_dir() / "audio"
    tmp_in = base / "in"
    in_path = None
    res = None

    try:
        stop = asyncio.Event()
        anim = asyncio.create_task(_progress_anim(cb.message, s.file_processing, stop))
        try:
            in_path = await _download_from_ctx(cb.bot, ctx, dst_dir=tmp_in)
            res = await convert_audio_from_file(in_path, fmt="mp3", workdir=base / "work")
        finally:
            stop.set(); anim.cancel()

        await cb.message.answer_document(
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
    ctx: dict,
    kind: FileKind,
    fmt: str,
    lang: str,
) -> None:
    s = t(lang)
    if fmt not in {"mp3", "m4a", "wav", "opus"}:
        fmt = "mp3"

    base = _tmp_dir() / "audio"
    tmp_in = base / "in"
    in_path = None
    res = None

    try:
        stop = asyncio.Event()
        anim = asyncio.create_task(_progress_anim(cb.message, s.file_processing, stop))
        try:
            in_path = await _download_from_ctx(cb.bot, ctx, dst_dir=tmp_in)
            res = await convert_audio_from_file(in_path, fmt=fmt, workdir=base / "work")
        finally:
            stop.set(); anim.cancel()

        await cb.message.answer_document(
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
