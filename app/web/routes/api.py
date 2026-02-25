# app/web/routes/api.py
from __future__ import annotations

import mimetypes
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse
from pydantic import BaseModel, HttpUrl
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.config import settings
from app.domain.services.jobs import create_job, get_job
from app.domain.services.media.saver import SaveError, SaveResult, cleanup_save_result, save_media_from_url
from app.domain.services.media.soundcloud import (
    SoundCloudError,
    cleanup_soundcloud_result,
    download_soundcloud_track_to_mp3,
)
from app.domain.services.quota import QuotaExceeded, consume_quota
from app.infra.db.schema import JobKind, User
from app.infra.db.session import get_session
from app.infra.queue.arq import enqueue_stt
from app.web.deps import get_current_user

router = APIRouter(tags=["api"])

DATA_DIR = Path(settings.data_dir)
RESULTS_DIR = DATA_DIR / "results"
TMP_DIR = DATA_DIR / "tmp"

RESULTS_DIR.mkdir(parents=True, exist_ok=True)
TMP_DIR.mkdir(parents=True, exist_ok=True)

# quota only for these tools (downloaders)
QUOTA_TOOLS: set[str] = {"save", "audio"}


class UrlIn(BaseModel):
    url: HttpUrl
    tool: str | None = None


class UrlOnly(BaseModel):
    url: HttpUrl


class FileOut(BaseModel):
    file_id: str
    filename: str


class SttIn(BaseModel):
    file_id: str


class SttOut(BaseModel):
    job_id: int


class SttStatusOut(BaseModel):
    status: str
    result_path: str | None = None
    error: str | None = None


def _http400(detail: str) -> HTTPException:
    return HTTPException(status_code=400, detail=detail)


def _safe_resolve_under(base: Path, name: str) -> Path:
    p = (base / name).resolve()
    b = base.resolve()
    if b not in p.parents and p != b:
        raise HTTPException(status_code=400, detail="unsafe_path")
    return p


def _ensure_under_results(out_path: Path) -> Path:
    if not out_path.exists() or not out_path.is_file():
        raise HTTPException(status_code=500, detail="save_inconsistent:no_file")

    if out_path.resolve().parent != RESULTS_DIR.resolve():
        fixed = RESULTS_DIR / out_path.name
        out_path.replace(fixed)
        out_path = fixed

    return out_path


async def _record_save_job(
    session: AsyncSession,
    *,
    user: User | None,
    file_id: str,
    save_result: SaveResult | None = None,
) -> None:
    """Сохраняем job в БД с metadata из SaveResult (если есть)."""
    user_id = int(user.id) if user else None

    title = None
    source_url = None
    extractor = None
    size_bytes = None

    if save_result:
        title = save_result.title
        source_url = save_result.source_url
        extractor = save_result.extractor
        size_bytes = save_result.size_bytes

    await create_job(
        session,
        kind=JobKind.save,
        file_id=file_id,
        user_id=user_id,
        title=title,
        source_url=source_url,
        extractor=extractor,
        size_bytes=size_bytes,
    )


@router.post("/save_job", response_model=FileOut)
async def api_save_job(
    payload: UrlOnly,
    tool: str = Query(default="save"),
    session: AsyncSession = Depends(get_session),
    user: User | None = Depends(get_current_user),
) -> FileOut:
    return await api_save(
        UrlIn(url=payload.url, tool=tool),
        session=session,
        user=user,
    )


@router.post("/save", response_model=FileOut)
async def api_save(
    payload: UrlIn,
    session: AsyncSession = Depends(get_session),
    user: User | None = Depends(get_current_user),
) -> FileOut:
    tool = (payload.tool or "save").lower().strip()

    # жестко: этот endpoint только для скачивалок
    if tool not in QUOTA_TOOLS:
        raise _http400("unknown_tool")

    if tool == "audio":
        sc_res = None
        out_path: Path | None = None
        try:
            sc_res = await download_soundcloud_track_to_mp3(
                str(payload.url),
                workdir=TMP_DIR,
                out_dir=RESULTS_DIR,
            )
            out_path = _ensure_under_results(Path(sc_res.filepath))

            # quota списываем ТОЛЬКО после успешного сохранения файла
            try:
                await consume_quota(session, user=user, cost=1)
            except QuotaExceeded:
                # ВАЖНО: откатываем инкремент (consume_quota больше не коммитит)
                await session.rollback()
                # файл уже есть => удаляем, чтобы не раздавать "бесплатно"
                try:
                    out_path.unlink(missing_ok=True)
                finally:
                    pass
                raise HTTPException(status_code=429, detail="daily_limit_reached")

            await _record_save_job(session, user=user, file_id=out_path.name, save_result=None)

            # ВАЖНО: коммитим и quota, и job одной транзакцией
            await session.commit()
            return FileOut(file_id=out_path.name, filename=out_path.name)

        except SoundCloudError as e:
            await session.rollback()
            # НЕ тратим quota на ошибки
            raise _http400(f"soundcloud_failed:{str(e)}")
        except HTTPException:
            await session.rollback()
            raise
        except Exception:
            await session.rollback()
            raise _http400("soundcloud_failed")
        finally:
            if sc_res is not None:
                cleanup_soundcloud_result(sc_res)

    res: SaveResult | None = None
    out_path: Path | None = None
    try:
        res = await save_media_from_url(
            str(payload.url),
            workdir=TMP_DIR,
            out_dir=RESULTS_DIR,
        )
        out_path = _ensure_under_results(Path(res.filepath))

        # quota списываем ТОЛЬКО после успеха
        try:
            await consume_quota(session, user=user, cost=1)
        except QuotaExceeded:
            await session.rollback()
            try:
                out_path.unlink(missing_ok=True)
            finally:
                pass
            raise HTTPException(status_code=429, detail="daily_limit_reached")

        await _record_save_job(session, user=user, file_id=out_path.name, save_result=res)

        await session.commit()
        return FileOut(file_id=out_path.name, filename=out_path.name)

    except SaveError as e:
        await session.rollback()
        raise _http400(f"save_failed:{str(e)}")
    except HTTPException:
        await session.rollback()
        raise
    except Exception:
        await session.rollback()
        raise _http400("save_failed")
    finally:
        if res is not None:
            cleanup_save_result(res)


@router.get("/file/{file_id}")
async def api_file(file_id: str):
    p = _safe_resolve_under(RESULTS_DIR, file_id)
    if not p.exists() or not p.is_file():
        raise HTTPException(status_code=404, detail="not_found")

    media_type, _ = mimetypes.guess_type(str(p))
    return FileResponse(
        path=str(p),
        media_type=media_type or "application/octet-stream",
        filename=p.name,
    )


# ✅ STT НЕ должен тратить quota (по твоей политике)
@router.post("/stt", response_model=SttOut)
async def api_stt(
    payload: SttIn,
    session: AsyncSession = Depends(get_session),
    user: User | None = Depends(get_current_user),
) -> SttOut:
    src = _safe_resolve_under(RESULTS_DIR, payload.file_id)
    if not src.exists() or not src.is_file():
        raise HTTPException(status_code=404, detail="input_file_not_found")

    try:
        user_id = int(user.id) if user else None
        job = await create_job(
            session,
            kind=JobKind.stt,
            file_id=payload.file_id,
            user_id=user_id,
        )
        await session.commit()
    except HTTPException:
        await session.rollback()
        raise
    except Exception:
        await session.rollback()
        raise

    await enqueue_stt(int(job.id))
    return SttOut(job_id=int(job.id))


@router.get("/stt/{job_id}", response_model=SttStatusOut)
async def api_stt_status(
    job_id: int,
    session: AsyncSession = Depends(get_session),
    user: User | None = Depends(get_current_user),
) -> SttStatusOut:
    job = await get_job(session, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="job_not_found")

    return SttStatusOut(
        status=str(job.status),
        result_path=getattr(job, "result_path", None),
        error=getattr(job, "error", None),
    )