from __future__ import annotations

from app.infra.db.base import Base
from app.infra.db.session import engine


async def init_db() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)