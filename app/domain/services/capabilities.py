from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Iterable


class Action(str, Enum):
    DOWNLOAD = "download"
    CONVERT_AUDIO = "convert_audio"
    TRANSCRIBE = "transcribe"


@dataclass(frozen=True)
class Capabilities:
    actions: tuple[Action, ...]

    def has(self, action: Action) -> bool:
        return action in self.actions


# Простые хелперы определения типа
AUDIO_EXT = {".mp3", ".wav", ".flac", ".ogg", ".opus", ".m4a"}
VIDEO_EXT = {".mp4", ".mkv", ".webm", ".mov", ".avi"}


def _ext(name: str | None) -> str:
    if not name or "." not in name:
        return ""
    return name.lower().rsplit(".", 1)[-1].join(["."])


def from_link(url: str) -> Capabilities:
    # Пока считаем, что yt-dlp способен понять большинство ссылок
    # Значит можем: скачать, извлечь аудио, распознать
    return Capabilities(actions=(Action.DOWNLOAD, Action.CONVERT_AUDIO, Action.TRANSCRIBE))


def from_file(filename: str | None, mime: str | None, is_voice: bool) -> Capabilities:
    if is_voice:
        return Capabilities(actions=(Action.CONVERT_AUDIO, Action.TRANSCRIBE))

    ext = _ext(filename)

    if ext in AUDIO_EXT:
        return Capabilities(actions=(Action.CONVERT_AUDIO, Action.TRANSCRIBE))

    if ext in VIDEO_EXT:
        return Capabilities(actions=(Action.CONVERT_AUDIO, Action.TRANSCRIBE))

    # неизвестно что — ничего не предлагаем
    return Capabilities(actions=())