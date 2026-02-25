from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.infra.db.schema import User


async def get_or_create_user(
    session: AsyncSession,
    *,
    telegram_id: int,
    is_admin: bool = False,
) -> User:
    res = await session.execute(
        select(User).where(User.telegram_id == telegram_id)
    )
    user = res.scalar_one_or_none()

    if user:
        return user

    user = User(
        telegram_id=telegram_id,
        is_admin=is_admin,
    )
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return user