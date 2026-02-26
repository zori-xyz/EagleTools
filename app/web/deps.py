# app/domain/services/user_repo.py
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.infra.db.models.user import User


class UserRepo:
    """
    Храним минимальное состояние юзера для бота:
    - last screen message (чтобы редактировать одно сообщение, anti-spam)
    - active tool
    - audio format

    ВАЖНО:
    В текущей схеме БД НЕТ panel_chat_id/panel_message_id.
    Поэтому "screen" маппим на mode_chat_id/mode_message_id.
    """

    async def get_or_create(self, session: AsyncSession, tg_id: int) -> User:
        q = select(User).where(User.tg_id == int(tg_id)).limit(1)
        res = await session.execute(q)
        user = res.scalar_one_or_none()
        if user is not None:
            return user

        user = User(tg_id=int(tg_id))
        session.add(user)
        await session.commit()
        await session.refresh(user)
        return user

    # ---------- last screen (single-message UI) ----------
    async def get_screen(self, session: AsyncSession, tg_id: int) -> tuple[int, int] | None:
        user = await self.get_or_create(session, tg_id)
        if user.mode_chat_id and user.mode_message_id:
            return int(user.mode_chat_id), int(user.mode_message_id)
        return None

    async def set_screen(self, session: AsyncSession, tg_id: int, chat_id: int, message_id: int) -> None:
        user = await self.get_or_create(session, tg_id)
        user.mode_chat_id = int(chat_id)
        user.mode_message_id = int(message_id)
        await session.commit()

    async def clear_screen(self, session: AsyncSession, tg_id: int) -> None:
        user = await self.get_or_create(session, tg_id)
        user.mode_chat_id = None
        user.mode_message_id = None
        await session.commit()

    # ---------- compatibility aliases (if some code still calls mode_*) ----------
    async def get_mode_msg(self, session: AsyncSession, tg_id: int) -> tuple[int, int] | None:
        return await self.get_screen(session, tg_id)

    async def set_mode_msg(self, session: AsyncSession, tg_id: int, chat_id: int, message_id: int) -> None:
        await self.set_screen(session, tg_id, chat_id, message_id)

    async def clear_mode_msg(self, session: AsyncSession, tg_id: int) -> None:
        await self.clear_screen(session, tg_id)

    # ---------- active tool ----------
    async def set_active_tool(self, session: AsyncSession, tg_id: int, tool: str | None) -> None:
        user = await self.get_or_create(session, tg_id)
        user.active_tool = (tool or None)
        await session.commit()

    async def get_active_tool(self, session: AsyncSession, tg_id: int) -> str | None:
        user = await self.get_or_create(session, tg_id)
        return user.active_tool

    # ---------- audio format ----------
    async def set_audio_format(self, session: AsyncSession, tg_id: int, fmt: str) -> None:
        user = await self.get_or_create(session, tg_id)
        user.audio_format = (fmt or "mp3").lower().strip() or "mp3"
        await session.commit()

    async def get_audio_format(self, session: AsyncSession, tg_id: int) -> str:
        user = await self.get_or_create(session, tg_id)
        return (user.audio_format or "mp3").lower().strip() or "mp3"