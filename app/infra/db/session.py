# app/infra/db/session.py
from __future__ import annotations

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.common.config import settings

# -------------------------
# Engine
# -------------------------

DATABASE_URL = settings.effective_database_url

engine: AsyncEngine = create_async_engine(
    DATABASE_URL,
    echo=settings.debug,
    future=True,
    pool_pre_ping=True,
)

# -------------------------
# Session factory
# -------------------------

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

# Aliases — все варианты которые встречаются в проекте
SessionMaker = AsyncSessionLocal


def get_sessionmaker() -> async_sessionmaker:
    """Returns the session factory. Used by bot routers."""
    return AsyncSessionLocal


# -------------------------
# FastAPI Dependencies
# -------------------------

async def get_db() -> AsyncSession:
    async with AsyncSessionLocal() as session:
        yield session


# Backward compatibility aliases
get_session = get_db