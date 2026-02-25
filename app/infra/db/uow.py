from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncIterator

from sqlalchemy.ext.asyncio import AsyncSession

from app.infra.db.session import async_session_maker


@asynccontextmanager
async def uow() -> AsyncIterator[AsyncSession]:
    """
    Unit of Work for a single request.
    - commits on success
    - rollbacks on error
    """
    async with async_session_maker() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise