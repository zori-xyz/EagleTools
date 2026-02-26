# app/domain/services/user_repo.py
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.infra.db.schema import User


class UserRepo:
    """
    Repo для User, где user_id = Telegram user id (tg_id).

    Важно:
    - В БД PK = users.id, но в коде бота/веба почти везде оперируем tg_id.
    - В твоей текущей схеме есть поля mode_chat_id/mode_message_id.
      Мы используем их и для "last screen", чтобы не требовать миграции прямо сейчас.
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

    # ---------- language ----------
    async def set_language(self, session: AsyncSession, tg_id: int, language: str) -> None:
        user = await self.get_or_create(session, tg_id)
        # в модели сейчас поле language_code (если нет — просто игнор)
        if hasattr(user, "language_code"):
            setattr(user, "language_code", language)
        await session.commit()

    # ---------- last screen ----------
    async def get_screen(self, session: AsyncSession, tg_id: int) -> tuple[int, int] | None:
        user = await self.get_or_create(session, tg_id)
        chat_id = getattr(user, "mode_chat_id", None)
        message_id = getattr(user, "mode_message_id", None)
        if chat_id and message_id:
            return int(chat_id), int(message_id)
        return None

    async def set_screen(self, session: AsyncSession, tg_id: int, chat_id: int, message_id: int) -> None:
        user = await self.get_or_create(session, tg_id)
        setattr(user, "mode_chat_id", int(chat_id))
        setattr(user, "mode_message_id", int(message_id))
        await session.commit()

    async def clear_screen(self, session: AsyncSession, tg_id: int) -> None:
        user = await self.get_or_create(session, tg_id)
        setattr(user, "mode_chat_id", None)
        setattr(user, "mode_message_id", None)
        await session.commit()

    # ---------- active tool ----------
    async def set_active_tool(self, session: AsyncSession, tg_id: int, tool: str | None) -> None:
        user = await self.get_or_create(session, tg_id)
        setattr(user, "active_tool", tool)
        await session.commit()

    async def get_active_tool(self, session: AsyncSession, tg_id: int) -> str | None:
        user = await self.get_or_create(session, tg_id)
        return getattr(user, "active_tool", None)

    # ---------- mode message (anti-spam) ----------
    async def get_mode_msg(self, session: AsyncSession, tg_id: int) -> tuple[int, int] | None:
        # сейчас это те же поля, что и screen
        return await self.get_screen(session, tg_id)

    async def set_mode_msg(self, session: AsyncSession, tg_id: int, chat_id: int, message_id: int) -> None:
        await self.set_screen(session, tg_id, chat_id, message_id)

    async def clear_mode_msg(self, session: AsyncSession, tg_id: int) -> None:
        await self.clear_screen(session, tg_id)

    # ---------- audio format ----------
    async def set_audio_format(self, session: AsyncSession, tg_id: int, fmt: str) -> None:
        user = await self.get_or_create(session, tg_id)
        setattr(user, "audio_format", fmt)
        await session.commit()

    async def get_audio_format(self, session: AsyncSession, tg_id: int) -> str:
        user = await self.get_or_create(session, tg_id)
        return str(getattr(user, "audio_format", None) or "mp3")