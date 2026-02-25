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

# Alias for worker compatibility
SessionMaker = AsyncSessionLocal

# -------------------------
# Dependencies
# -------------------------

async def get_db() -> AsyncSession:
    async with AsyncSessionLocal() as session:
        yield session


# BACKWARD COMPATIBILITY
get_session = get_db