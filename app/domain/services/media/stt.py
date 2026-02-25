from __future__ import annotations

import asyncio
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

try:
    from faster_whisper import WhisperModel
except Exception:  # pragma: no cover
    WhisperModel = None  # type: ignore


class SttError(RuntimeError):
    pass

@dataclass(frozen=True)
class SttResult:
    text: str
    tmp_dir: Path


_MODEL: WhisperModel | None = None
_MODEL_LOCK = asyncio.Lock()


def _ensure_dir(p: Path) -> None:
    p.mkdir(parents=True, exist_ok=True)


async def _get_model(model_dir: Path) -> WhisperModel:
    """
    Кешируем модель в памяти.
    model_dir — папка, где хранится HF-кеш/файлы модели.
    """
    global _MODEL

    if WhisperModel is None:
        raise SttError("missing_dependency")

    async with _MODEL_LOCK:
        if _MODEL is not None:
            return _MODEL

        _ensure_dir(model_dir)

        # СТАБИЛЬНО/БЫСТРО:
        # device=cpu + compute_type=int8 работает почти везде.
        # model_size=small — адекватный баланс.
        _MODEL = WhisperModel(
            "Systran/faster-whisper-small",
            device="cpu",
            compute_type="int8",
            download_root=str(model_dir),
        )
        return _MODEL


def _transcribe_sync(
    audio_path: Path,
    model: WhisperModel,
) -> str:
    """
    Синхронный транскрайб: вынесено отдельно, запускаем через to_thread.
    ВАЖНО: Не включаем агрессивный vad_filter — он часто режет короткие фразы в ноль.
    """
    segments, _info = model.transcribe(
        str(audio_path),
        beam_size=1,
        best_of=1,
        temperature=0.0,
        vad_filter=False,
        condition_on_previous_text=False,
    )
    parts: list[str] = []
    for s in segments:
        t = (s.text or "").strip()
        if t:
            parts.append(t)
    return " ".join(parts).strip()


async def transcribe_to_text(
    in_path: Path,
    *,
    workdir: Path,
    model_dir: Path,
    timeout_sec: int = 90,
) -> SttResult:
    """
    Асинхронное распознавание.
    workdir нужен только чтобы соответствовать твоей архитектуре и для будущих расширений.
    tmp_dir возвращаем для совместимости с текущим контрактом.
    """
    if not in_path.exists():
        raise SttError("input_missing")

    _ensure_dir(workdir)
    tmp_dir = workdir  # оставляем совместимость: ты чистишь tmp_dir снаружи

    model = await _get_model(model_dir)

    try:
        text = await asyncio.wait_for(
            asyncio.to_thread(_transcribe_sync, in_path, model),
            timeout=timeout_sec,
        )
    except asyncio.TimeoutError:
        raise SttError("timeout")
    except SttError:
        raise
    except Exception:
        raise SttError("failed")

    if not text:
        raise SttError("empty")

    return SttResult(text=text, tmp_dir=tmp_dir)