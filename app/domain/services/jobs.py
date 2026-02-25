from __future__ import annotations

from datetime import datetime
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.infra.db.schema import Job, JobKind, JobStatus


async def create_job(
    session: AsyncSession,
    *,
    kind: JobKind,
    file_id: str,
    user_id: int | None = None,
    title: str | None = None,
    source_url: str | None = None,
    extractor: str | None = None,
    size_bytes: int | None = None,
) -> Job:
    """
    Создаёт job с metadata.
    Новые поля: title, source_url, extractor, size_bytes
    """
    job = Job(
        kind=kind,
        status=JobStatus.queued,
        file_id=file_id,
        user_id=user_id,
        title=title,
        source_url=source_url,
        extractor=extractor,
        size_bytes=size_bytes,
    )
    session.add(job)
    await session.commit()
    await session.refresh(job)
    return job


async def get_job(session: AsyncSession, job_id: int) -> Job | None:
    res = await session.execute(select(Job).where(Job.id == job_id))
    return res.scalar_one_or_none()


async def set_job_status(
    session: AsyncSession,
    job_id: int,
    status: JobStatus,
    *,
    result_path: str | None = None,
    error: str | None = None,
) -> None:
    stmt = (
        update(Job)
        .where(Job.id == job_id)
        .values(
            status=status,
            result_path=result_path,
            error=error,
            updated_at=datetime.utcnow(),
        )
    )
    await session.execute(stmt)
    await session.commit()