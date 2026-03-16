# app/web/routes/convert.py
from __future__ import annotations

import shutil
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from fastapi.responses import JSONResponse
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
}

def _readable_error(code: str) -> str:
    for key, msg in _ERROR_MAP.items():
        if code.startswith(key):
            return msg
    return "Ошибка конвертации"


@router.post("/convert")
async def api_convert(
    file:    UploadFile = File(...),
    action:  str        = Form(...),
    session: AsyncSession = Depends(get_session),
    user:    User         = Depends(get_current_user),
) -> JSONResponse:
    """
    Принимает файл + action, конвертирует через ffmpeg,
    сохраняет результат в RESULTS_DIR, возвращает download_url.
    """

    # ── Валидация action ───────────────────────────────────────
    action = (action or "").strip().lower()
    if action not in ALLOWED_ACTIONS:
        raise HTTPException(status_code=400, detail="unknown_action")

    # ── Проверяем план пользователя ───────────────────────────
    quota = await get_quota_state(session, user)
    is_premium = quota.is_unlimited
    max_bytes  = MAX_PREMIUM_BYTES if is_premium else MAX_FREE_BYTES

    # ── Проверяем квоту ───────────────────────────────────────
    if not is_premium and quota.used_today >= quota.daily_limit:
        raise HTTPException(status_code=429, detail="quota_exceeded")

    # ── Читаем файл ───────────────────────────────────────────
    # Сначала проверяем размер по Content-Length если есть
    content_length = file.size  # может быть None
    if content_length and content_length > max_bytes:
        raise HTTPException(status_code=413, detail="file_too_large")

    # Сохраняем во временный файл
    suffix = Path(file.filename or "input").suffix or ".bin"
    tmp_in  = TMP_DIR / f"{uuid.uuid4().hex}{suffix}"
    result: ConvertResult | None = None

    try:
        # Стримим файл на диск чтобы не держать в памяти
        TMP_DIR.mkdir(parents=True, exist_ok=True)
        written = 0
        with open(tmp_in, "wb") as fout:
            while True:
                chunk = await file.read(1024 * 256)  # 256 KB chunks
                if not chunk:
                    break
                written += len(chunk)
                if written > max_bytes:
                    fout.close()
                    tmp_in.unlink(missing_ok=True)
                    raise HTTPException(status_code=413, detail="file_too_large")
                fout.write(chunk)

        if written == 0:
            raise HTTPException(status_code=400, detail="empty_file")

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
        out_name = f"conv_{uuid.uuid4().hex[:12]}{result.out_path.suffix}"
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
        original_name = Path(file.filename or "file").name
        out_stem = Path(file.filename or "file").stem[:50]
        display_name = f"{out_stem}{result.out_path.suffix}"

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