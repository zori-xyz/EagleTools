# app/web/routes/recent.py
from __future__ import annotations

from datetime import date, datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.infra.db.models import Job
from app.infra.db.schema import User
from app.infra.db.session import get_db
from app.web.deps import get_current_user

router = APIRouter(prefix="/api", tags=["recent"])


def _jsonify(v: Any) -> Any:
    if isinstance(v, (datetime, date)):
        return v.isoformat()
    return v


def _to_item(row: dict[str, Any]) -> dict[str, Any]:
    file_id = row.get("file_id") or ""
    filename = file_id
    ext = ""
    if isinstance(filename, str) and "." in filename:
        ext = filename.rsplit(".", 1)[-1]

    return {
        "id": row.get("id"),
        "kind": row.get("kind"),
        "status": row.get("status"),
        "file_id": file_id,
        "filename": filename,
        "title": filename or file_id or "file",
        "ext": ext,
        "size_bytes": row.get("size_bytes") if "size_bytes" in row else None,
        "created_at": row.get("created_at"),
        "updated_at": row.get("updated_at"),
        "download_url": f"/api/file/{file_id}" if file_id else None,
    }


async def _delete_job(db: AsyncSession, *, job_id: int, user_id: int) -> int:
    t = Job.__table__
    res = await db.execute(delete(t).where(t.c.id == job_id, t.c.user_id == user_id))
    await db.commit()
    return int(res.rowcount or 0)


@router.get("/recent")
async def recent_list(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    # UI-контракт: { items: [...] }
    t = Job.__table__
    cols = list(t.c)

    q = (
        select(*cols)
        .select_from(t)
        .where(t.c.user_id == int(user.id))
        .order_by(t.c.id.desc())
        .limit(50)
    )
    res = await db.execute(q)

    items: list[dict[str, Any]] = []
    for row in res.mappings().all():
        d = {k: _jsonify(v) for k, v in row.items()}
        items.append(_to_item(d))

    return {"items": items}


@router.post("/recent/clear")
async def recent_clear(
    payload: dict[str, Any] | None = None,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    # payload может содержать delete_files, пока игнорируем
    t = Job.__table__
    res = await db.execute(delete(t).where(t.c.user_id == int(user.id)))
    await db.commit()
    return {"ok": True, "deleted": int(res.rowcount or 0)}


@router.post("/recent/delete")
async def recent_delete(
    payload: dict[str, Any],
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    job_id = payload.get("id")
    if job_id is None:
        raise HTTPException(status_code=400, detail="missing_id")

    try:
        jid = int(job_id)
    except Exception:
        raise HTTPException(status_code=400, detail="bad_id")

    deleted = await _delete_job(db, job_id=jid, user_id=int(user.id))
    if deleted <= 0:
        raise HTTPException(status_code=404, detail="job_not_found")

    return {"ok": True, "id": jid}


@router.delete("/recent/{job_id}")
async def recent_delete_rest(
    job_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    deleted = await _delete_job(db, job_id=int(job_id), user_id=int(user.id))
    if deleted <= 0:
        raise HTTPException(status_code=404, detail="job_not_found")

    return {"ok": True, "id": int(job_id)}