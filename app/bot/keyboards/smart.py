# app/bot/keyboards/smart.py
"""
Context-aware inline keyboards for the smart router.

link_actions_kb  — shown when user sends a URL
file_actions_kb  — shown when user sends a file (audio/video/voice/document)
after_link_kb    — shown after a link download completes (follow-up options)
after_file_kb    — shown after a file operation completes (follow-up options)
format_pick_kb   — format picker for audio conversion
"""
from __future__ import annotations

from typing import Literal

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from app.bot.i18n import t

# Platform category → available actions
# "media"  : video-hosting sites (YouTube, TikTok, Instagram, …) → video + audio + stt
# "audio"  : audio-only sites (SoundCloud, Spotify, …) → audio + stt
# "direct" : direct file URL → download only
# "web"    : generic web page → (nothing useful in bot)

PlatformCategory = Literal["media", "audio", "direct", "web"]
FileKind = Literal["voice", "audio", "video", "document_audio", "document_video", "document_other"]


# ── Link keyboards ─────────────────────────────────────────────────────────────

def link_actions_kb(category: PlatformCategory, lang: str = "ru") -> InlineKeyboardMarkup:
    s = t(lang)
    rows: list[list[InlineKeyboardButton]] = []

    if category == "media":
        rows.append([
            InlineKeyboardButton(text=s.btn_download_video, callback_data="lnk:vid"),
            InlineKeyboardButton(text=s.btn_extract_audio, callback_data="lnk:aud"),
        ])
        rows.append([
            InlineKeyboardButton(text=s.btn_transcribe, callback_data="lnk:stt"),
        ])
    elif category == "audio":
        rows.append([
            InlineKeyboardButton(text=s.btn_extract_audio, callback_data="lnk:aud"),
            InlineKeyboardButton(text=s.btn_transcribe, callback_data="lnk:stt"),
        ])
    elif category == "direct":
        rows.append([
            InlineKeyboardButton(text=s.btn_download_file, callback_data="lnk:vid"),
        ])

    rows.append([
        InlineKeyboardButton(text=s.btn_cancel, callback_data="lnk:dismiss"),
    ])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def after_link_kb(last_action: str, lang: str = "ru") -> InlineKeyboardMarkup:
    """Shown after a link download is done — offer complementary actions."""
    s = t(lang)
    rows: list[list[InlineKeyboardButton]] = []

    if last_action == "vid":
        rows.append([
            InlineKeyboardButton(text=s.btn_extract_audio, callback_data="lnk:aud"),
            InlineKeyboardButton(text=s.btn_transcribe, callback_data="lnk:stt"),
        ])
    elif last_action == "aud":
        rows.append([
            InlineKeyboardButton(text=s.btn_transcribe, callback_data="lnk:stt"),
        ])

    rows.append([
        InlineKeyboardButton(text=s.btn_done, callback_data="lnk:dismiss"),
    ])
    return InlineKeyboardMarkup(inline_keyboard=rows)


# ── File keyboards ─────────────────────────────────────────────────────────────

def file_actions_kb(kind: FileKind, lang: str = "ru") -> InlineKeyboardMarkup:
    """Shown immediately when the user sends a file."""
    s = t(lang)
    rows: list[list[InlineKeyboardButton]] = []

    if kind == "voice":
        rows.append([
            InlineKeyboardButton(text=s.btn_transcribe, callback_data="fl:stt"),
            InlineKeyboardButton(text=s.btn_convert_format, callback_data="fl:fmt"),
        ])
    elif kind == "audio":
        rows.append([
            InlineKeyboardButton(text=s.btn_transcribe, callback_data="fl:stt"),
            InlineKeyboardButton(text=s.btn_convert_format, callback_data="fl:fmt"),
        ])
    elif kind == "video":
        rows.append([
            InlineKeyboardButton(text=s.btn_extract_audio_from_video, callback_data="fl:ext_aud"),
        ])
        rows.append([
            InlineKeyboardButton(text=s.btn_transcribe, callback_data="fl:stt"),
        ])
    elif kind in ("document_audio", "document_video"):
        rows.append([
            InlineKeyboardButton(text=s.btn_transcribe, callback_data="fl:stt"),
            InlineKeyboardButton(text=s.btn_convert_format, callback_data="fl:fmt"),
        ])
        if kind == "document_video":
            rows.append([
                InlineKeyboardButton(text=s.btn_extract_audio_from_video, callback_data="fl:ext_aud"),
            ])
    # Generic documents: nothing to do in bot, just show cancel

    rows.append([
        InlineKeyboardButton(text=s.btn_cancel, callback_data="fl:dismiss"),
    ])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def format_pick_kb(lang: str = "ru") -> InlineKeyboardMarkup:
    """Audio format selector."""
    s = t(lang)
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🎵 MP3", callback_data="fl:conv:mp3"),
            InlineKeyboardButton(text="🎶 M4A", callback_data="fl:conv:m4a"),
        ],
        [
            InlineKeyboardButton(text="📀 WAV", callback_data="fl:conv:wav"),
            InlineKeyboardButton(text="🗜 OPUS", callback_data="fl:conv:opus"),
        ],
        [
            InlineKeyboardButton(text=s.btn_cancel, callback_data="fl:dismiss"),
        ],
    ])


def stt_result_kb(dismiss_cb: str, lang: str = "ru") -> InlineKeyboardMarkup:
    """Shown after a successful STT transcription — just a close button."""
    s = t(lang)
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=s.btn_done, callback_data=dismiss_cb)],
    ])


def after_file_kb(kind: FileKind, last_action: str, lang: str = "ru") -> InlineKeyboardMarkup:
    """Shown after a file operation — offer remaining useful actions."""
    s = t(lang)
    rows: list[list[InlineKeyboardButton]] = []

    # Offer complementary actions depending on what was just done
    if last_action == "ext_aud":
        rows.append([
            InlineKeyboardButton(text=s.btn_transcribe, callback_data="fl:stt"),
        ])
    elif last_action in ("conv", "fmt"):
        if kind in ("audio", "voice", "document_audio"):
            rows.append([
                InlineKeyboardButton(text=s.btn_transcribe, callback_data="fl:stt"),
            ])
    elif last_action == "stt":
        if kind in ("video", "document_video"):
            rows.append([
                InlineKeyboardButton(text=s.btn_extract_audio_from_video, callback_data="fl:ext_aud"),
            ])

    rows.append([
        InlineKeyboardButton(text=s.btn_done, callback_data="fl:dismiss"),
    ])
    return InlineKeyboardMarkup(inline_keyboard=rows)
