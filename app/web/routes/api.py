# app/web/routes/api.py
from __future__ import annotations

import hashlib
import hmac
import mimetypes
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse
from pydantic import BaseModel, HttpUrl
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.config import settings
from app.domain.services.jobs import create_job, get_job
from app.domain.services.media.saver import SaveError, SaveResult, cleanup_save_result, save_media_from_url
from app.domain.services.media.soundcloud import SoundCloudError, cleanup_soundcloud_result, download_soundcloud_track_to_mp3
from app.domain.services.quota import QuotaExceeded, consume_quota
from app.infra.db.schema import JobKind, User
from app.infra.db.session import get_session
from app.infra.queue.arq import enqueue_stt
from app.web.deps import get_current_user

router = APIRouter(tags=["api"])
file_router = APIRouter(tags=["files"])

DATA_DIR = Path(settings.data_dir)
RESULTS_DIR = DATA_DIR / "results"
TMP_DIR = DATA_DIR / "tmp"

RESULTS_DIR.mkdir(parents=True, exist_ok=True)
TMP_DIR.mkdir(parents=True, exist_ok=True)

QUOTA_TOOLS: set[str] = {"save", "audio"}


# ─────────────────────────────────────────────
# File download token (HMAC, no DB needed)
# ─────────────────────────────────────────────

def _file_token_secret() -> bytes:
    key = (settings.effective_webapp_secret or "").encode()
    return hashlib.sha256(b"file_dl:" + key).digest()


def make_file_token(file_id: str) -> str:
    return hmac.new(_file_token_secret(), file_id.encode(), hashlib.sha256).hexdigest()[:32]


def verify_file_token(file_id: str, token: str) -> bool:
    expected = make_file_token(file_id)
    return hmac.compare_digest(expected, token)


def file_download_url(file_id: str) -> str:
    token = make_file_token(file_id)
    return f"/api/file/{file_id}?token={token}"


# ─────────────────────────────────────────────
# Pydantic models
# ─────────────────────────────────────────────

class UrlIn(BaseModel):
    url: HttpUrl
    tool: str | None = None


class UrlOnly(BaseModel):
    url: HttpUrl


class FileOut(BaseModel):
    file_id: str
    filename: str
    download_url: str


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


def _pretty_filename(out_path: Path, title: str | None = None, tool: str = "download") -> str:
    """Генерирует красивое имя: EagleTools_tool_title.ext"""
    ext = out_path.suffix
    if title:
        stem = "".join(c for c in title[:50] if c.isalnum() or c in "_- ").strip()
    else:
        stem = out_path.stem[:20]
    stem = stem or "file"
    import uuid as _uuid
    uid = _uuid.uuid4().hex[:6]
    return f"EagleTools_{tool}_{stem}_{uid}{ext}"


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
    user: User,
    file_id: str,
    save_result: SaveResult | None = None,
) -> None:
    user_id = int(user.id)
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
    user: User = Depends(get_current_user),
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
    user: User = Depends(get_current_user),
) -> FileOut:
    tool = (payload.tool or "save").lower().strip()

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
            try:
                await consume_quota(session, user=user, cost=1)
            except QuotaExceeded:
                await session.rollback()
                try:
                    out_path.unlink(missing_ok=True)
                finally:
                    pass
                raise HTTPException(status_code=429, detail="daily_limit_reached")
            pretty = _pretty_filename(out_path, tool="soundcloud")
            pretty_path = RESULTS_DIR / pretty
            out_path.rename(pretty_path)
            out_path = pretty_path
            await _record_save_job(session, user=user, file_id=out_path.name, save_result=None)
            await session.commit()
            return FileOut(
                file_id=out_path.name,
                filename=out_path.name,
                download_url=file_download_url(out_path.name),
            )
        except SoundCloudError as e:
            await session.rollback()
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
        try:
            await consume_quota(session, user=user, cost=1)
        except QuotaExceeded:
            await session.rollback()
            try:
                out_path.unlink(missing_ok=True)
            finally:
                pass
            raise HTTPException(status_code=429, detail="daily_limit_reached")
        pretty = _pretty_filename(out_path, title=res.title if res else None, tool="video")
        pretty_path = RESULTS_DIR / pretty
        out_path.rename(pretty_path)
        out_path = pretty_path
        await _record_save_job(session, user=user, file_id=out_path.name, save_result=res)
        await session.commit()
        return FileOut(
            file_id=out_path.name,
            filename=out_path.name,
            download_url=file_download_url(out_path.name),
        )
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


@router.post("/stt", response_model=SttOut)
async def api_stt(
    payload: SttIn,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
) -> SttOut:
    src = _safe_resolve_under(RESULTS_DIR, payload.file_id)
    if not src.exists() or not src.is_file():
        raise HTTPException(status_code=404, detail="input_file_not_found")
    try:
        job = await create_job(
            session,
            kind=JobKind.stt,
            file_id=payload.file_id,
            user_id=int(user.id),
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
    user: User = Depends(get_current_user),
) -> SttStatusOut:
    job = await get_job(session, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="job_not_found")
    job_user_id = getattr(job, "user_id", None)
    if job_user_id is not None and int(job_user_id) != int(user.id):
        raise HTTPException(status_code=404, detail="job_not_found")
    return SttStatusOut(
        status=str(job.status),
        result_path=getattr(job, "result_path", None),
        error=getattr(job, "error", None),
    )


# ─────────────────────────────────────────────
# Public file endpoint (no auth, HMAC token)
# ─────────────────────────────────────────────

@file_router.get("/file/{file_id}")
async def api_file(file_id: str, token: str = Query(default="")):
    """Public endpoint — verifies HMAC token, no auth required."""
    if not token or not verify_file_token(file_id, token):
        raise HTTPException(status_code=403, detail="invalid_token")
    p = _safe_resolve_under(RESULTS_DIR, file_id)
    if not p.exists() or not p.is_file():
        raise HTTPException(status_code=404, detail="not_found")
    media_type, _ = mimetypes.guess_type(str(p))
    # Форсируем скачивание а не открытие в браузере
    # Только ASCII для latin-1 совместимости в заголовке
    safe_name = "".join(ch for ch in p.name if ord(ch) < 128 and (ch.isalnum() or ch in "._- ")).strip() or "file"
    return FileResponse(
        path=str(p),
        media_type="application/octet-stream",
        filename=safe_name,
        headers={
            "Content-Disposition": "attachment; filename="" + safe_name + """,
            "Cache-Control": "private, max-age=3600",
        },
    )