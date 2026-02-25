from __future__ import annotations

from sqlalchemy.ext.asyncio import create_async_engine

from app.common.config import settings

engine = create_async_engine(
    settings.database_url,
    echo=False,
    future=True,
)