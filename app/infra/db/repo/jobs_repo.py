from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from sqlalchemy import delete, desc, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.infra.db.models import Job


@dataclass(frozen=True)
class JobsRepo:
    session: AsyncSession

    async def create_job(
        self,
        *,
        user_id: int | None,
        kind: str,
        status: str = "queued",
        file_id: str | None = None,
        result_path: str | None = None,
        error: str | None = None,
    ) -> Job:
        job = Job(
            user_id=user_id,
            kind=kind,
            status=status,
            file_id=file_id,
            result_path=result_path,
            error=error,
        )
        self.session.add(job)
        await self.session.flush()  # gives id
        return job

    async def get_job(self, job_id: int) -> Job | None:
        res = await self.session.execute(select(Job).where(Job.id == job_id))
        return res.scalar_one_or_none()

    async def list_recent_jobs(
        self,
        *,
        user_id: int | None,
        limit: int = 30,
        kinds: Iterable[str] | None = None,
    ) -> list[Job]:
        q = select(Job)

        if user_id is None:
            q = q.where(Job.user_id.is_(None))
        else:
            q = q.where(Job.user_id == user_id)

        if kinds:
            q = q.where(Job.kind.in_(list(kinds)))

        q = q.order_by(desc(Job.created_at)).limit(limit)

        res = await self.session.execute(q)
        return list(res.scalars().all())

    async def delete_job(self, job_id: int, *, user_id: int | None) -> bool:
        q = delete(Job).where(Job.id == job_id)

        if user_id is None:
            q = q.where(Job.user_id.is_(None))
        else:
            q = q.where(Job.user_id == user_id)

        res = await self.session.execute(q)
        return (res.rowcount or 0) > 0

    async def set_status(
        self,
        job_id: int,
        *,
        status: str,
        result_path: str | None = None,
        error: str | None = None,
        file_id: str | None = None,
    ) -> None:
        values: dict = {"status": status}
        if result_path is not None:
            values["result_path"] = result_path
        if error is not None:
            values["error"] = error
        if file_id is not None:
            values["file_id"] = file_id

        await self.session.execute(
            update(Job).where(Job.id == job_id).values(**values)
        )