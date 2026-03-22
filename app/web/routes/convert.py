# app/web/routes/convert.py
from __future__ import annotations

import shutil
import uuid
from pathlib import Path

import base64
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.config import settings
from app.domain.services.jobs import create_job
from app.domain.services.media.converter import ConvertError, ConvertResult, cleanup, convert_file
from app.domain.services.quota import QuotaExceeded, consume_quota, get_quota_state
from app.infra.db.schema import JobKind, JobStatus, User
from app.infra.db.session import get_session
from app.web.deps import get_current_user
from app.web.routes.api import file_download_url, make_file_token

router = APIRouter(tags=["convert"])


class ConvertIn(BaseModel):
    action:   str
    filename: str
    mimetype: str = "application/octet-stream"
    data:     str  # base64

DATA_DIR    = Path(settings.data_dir)
RESULTS_DIR = DATA_DIR / "results"
TMP_DIR     = DATA_DIR / "tmp" / "converter"

RESULTS_DIR.mkdir(parents=True, exist_ok=True)
TMP_DIR.mkdir(parents=True, exist_ok=True)

# Лимиты размера файла
MAX_FREE_BYTES    = 100 * 1024 * 1024   # 100 MB
MAX_PREMIUM_BYTES = 500 * 1024 * 1024   # 500 MB

# Допустимые action id — белый список
ALLOWED_ACTIONS: set[str] = {
    # video
    "video_to_mp3", "video_to_mp4", "video_to_gif",
    "video_compress", "video_to_m4a", "video_stt",
    # audio
    "audio_to_mp3", "audio_to_wav", "audio_to_ogg",
    "audio_to_m4a", "audio_compress", "audio_stt",
    # image
    "img_to_jpg", "img_to_png", "img_to_webp", "img_compress",
    # pdf
    "pdf_to_txt", "pdf_to_img", "pdf_compress",
    # documents
    "doc_to_pdf", "doc_to_txt",
}

# Читаемые ошибки для фронта
_ERROR_MAP: dict[str, str] = {
    "input_missing":      "Файл не найден",
    "ffmpeg_failed":      "Ошибка конвертации",
    "output_empty":       "Результат пустой — возможно файл повреждён",
    "unsupported_action": "Действие не поддерживается",
    "duration_exceeded":  "Файл слишком длинный",
    "timeout":            "Превышено время обработки",
    "stt_failed":         "Ошибка распознавания речи",
    "file_too_large":     "Файл слишком большой",
    "quota_exceeded":     "Достигнут дневной лимит",
    "unknown_action":     "Неизвестное действие",
    "pymupdf_missing":    "PyMuPDF не установлен",
    "libreoffice_missing":"LibreOffice не установлен",
    "ghostscript_missing":"Ghostscript не установлен",
    "gs_failed":          "Ошибка сжатия PDF",
}

def _readable_error(code: str) -> str:
    for key, msg in _ERROR_MAP.items():
        if code.startswith(key):
            return msg
    return "Ошибка конвертации"


@router.post("/convert")
async def api_convert(
    payload: ConvertIn,
    session: AsyncSession = Depends(get_session),
    user:    User         = Depends(get_current_user),
) -> JSONResponse:
    """
    Принимает base64 файл + action, конвертирует через ffmpeg,
    сохраняет результат в RESULTS_DIR, возвращает download_url.
    """

    # ── Валидация action ───────────────────────────────────────
    action = (payload.action or "").strip().lower()
    if action not in ALLOWED_ACTIONS:
        raise HTTPException(status_code=400, detail="unknown_action")

    # ── Проверяем план пользователя ───────────────────────────
    quota = await get_quota_state(session, user)
    is_premium = quota.is_unlimited
    max_bytes  = MAX_PREMIUM_BYTES if is_premium else MAX_FREE_BYTES

    # ── Проверяем квоту ───────────────────────────────────────
    if not is_premium and quota.used_today >= quota.daily_limit:
        raise HTTPException(status_code=429, detail="quota_exceeded")

    # ── Декодируем base64 ─────────────────────────────────────
    try:
        file_bytes = base64.b64decode(payload.data)
    except Exception:
        raise HTTPException(status_code=400, detail="invalid_base64")

    if len(file_bytes) == 0:
        raise HTTPException(status_code=400, detail="empty_file")

    if len(file_bytes) > max_bytes:
        raise HTTPException(status_code=413, detail="file_too_large")

    # ── Валидация magic bytes ──────────────────────────────────
    _MAGIC: list[tuple[bytes, str]] = [
        (b"\xff\xd8\xff", "image"),           # JPEG
        (b"\x89PNG\r\n\x1a\n", "image"),    # PNG
        (b"RIFF", "video"),                       # AVI/WAV
        (b"\x00\x00\x00", "video"),            # MP4/MOV (ftyp)
        (b"\x1aE\xdf\xa3", "video"),           # MKV/WebM
        (b"ID3", "audio"),                        # MP3
        (b"\xff\xfb", "audio"),                 # MP3
        (b"\xff\xf3", "audio"),                 # MP3
        (b"OggS", "audio"),                       # OGG
        (b"fLaC", "audio"),                       # FLAC
        (b"GIF87a", "image"),                     # GIF
        (b"GIF89a", "image"),                     # GIF
        (b"WEBP", "image"),                       # WebP (bytes 8-12)
        (b"%PDF", "pdf"),                         # PDF
        (b"PK\x03\x04", "document"),            # ZIP-based (docx, xlsx)
        (b"\xd0\xcf\x11\xe0", "document"),    # MS Office old format
        (b"\x1f\x8b", "any"),                   # gzip — пропускаем
    ]
    header = file_bytes[:12]
    detected = None
    for magic, ftype in _MAGIC:
        if header.startswith(magic) or (ftype == "image" and magic == b"WEBP" and magic in file_bytes[6:14]):
            detected = ftype
            break

    # Исполняемые файлы блокируем
    _BLOCKED_MAGIC = [b"MZ", b"\x7fELF", b"\xca\xfe\xba\xbe"]
    for bm in _BLOCKED_MAGIC:
        if header.startswith(bm):
            raise HTTPException(status_code=400, detail="executable_file_blocked")

    # Сохраняем во временный файл
    suffix = Path(payload.filename or "input").suffix or ".bin"
    tmp_in  = TMP_DIR / f"{uuid.uuid4().hex}{suffix}"
    result: ConvertResult | None = None

    try:
        TMP_DIR.mkdir(parents=True, exist_ok=True)
        tmp_in.write_bytes(file_bytes)
        written = len(file_bytes)



        # ── Конвертация ───────────────────────────────────────
        timeout = 600 if is_premium else 300
        result = await convert_file(
            tmp_in,
            action=action,
            workdir=TMP_DIR / "work",
            is_premium=is_premium,
            timeout_sec=timeout,
        )

        # ── Перемещаем результат в RESULTS_DIR ───────────────
        # Красивое имя файла: EagleTools_action_originalname.ext
        _action_labels = {
            "video_to_mp3": "audio", "video_to_mp4": "video", "video_to_gif": "gif",
            "video_compress": "compressed", "video_to_m4a": "audio", "video_stt": "text",
            "audio_to_mp3": "mp3", "audio_to_wav": "wav", "audio_to_ogg": "ogg",
            "audio_to_m4a": "m4a", "audio_compress": "compressed", "audio_stt": "text",
            "img_to_jpg": "jpg", "img_to_png": "png", "img_to_webp": "webp",
            "img_compress": "compressed",
        }
        _action_label = _action_labels.get(action, "converted")
        _orig_stem = Path(payload.filename or "file").stem[:40]
        _safe_stem = "".join(c for c in _orig_stem if c.isalnum() or c in "_- ")[:40].strip()
        _safe_stem = _safe_stem or "file"
        _uid = uuid.uuid4().hex[:6]
        out_name = f"EagleTools_{_action_label}_{_safe_stem}_{_uid}{result.out_path.suffix}"
        final_path = RESULTS_DIR / out_name
        shutil.copy2(result.out_path, final_path)

        # ── Потребляем квоту ──────────────────────────────────
        try:
            await consume_quota(session, user=user, cost=1)
        except QuotaExceeded:
            await session.rollback()
            final_path.unlink(missing_ok=True)
            raise HTTPException(status_code=429, detail="quota_exceeded")

        # ── Пишем job в историю ───────────────────────────────
        display_name = out_name

        await create_job(
            session,
            kind=JobKind.save,
            file_id=out_name,
            user_id=int(user.id),
            title=display_name,
            size_bytes=final_path.stat().st_size,
        )
        await session.commit()

        return JSONResponse({
            "ok":           True,
            "file_id":      out_name,
            "filename":     display_name,
            "download_url": file_download_url(out_name),
            "size_bytes":   final_path.stat().st_size,
        })

    except HTTPException:
        await session.rollback()
        raise
    except ConvertError as e:
        await session.rollback()
        code = str(e)
        raise HTTPException(status_code=422, detail=_readable_error(code))
    except Exception as e:
        await session.rollback()
        raise HTTPException(status_code=500, detail=f"internal:{e}")
    finally:
        # Чистим временные файлы
        tmp_in.unlink(missing_ok=True)
        if result is not None:
            cleanup(result)