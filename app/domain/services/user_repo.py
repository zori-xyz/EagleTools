from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.models.user import User


class UserRepo:
    async def get_or_create(self, session: AsyncSession, user_id: int) -> User:
        user = await session.get(User, user_id)
        if user is not None:
            return user

        user = User(id=user_id)
        session.add(user)
        await session.commit()
        return user

    # ---------- language ----------
    async def set_language(self, session: AsyncSession, user_id: int, language: str) -> None:
        user = await self.get_or_create(session, user_id)
        user.language = language
        await session.commit()

    # ---------- last screen ----------
    async def get_screen(self, session: AsyncSession, user_id: int) -> tuple[int, int] | None:
        user = await self.get_or_create(session, user_id)
        if user.panel_chat_id and user.panel_message_id:
            return int(user.panel_chat_id), int(user.panel_message_id)
        return None

    async def set_screen(self, session: AsyncSession, user_id: int, chat_id: int, message_id: int) -> None:
        user = await self.get_or_create(session, user_id)
        user.panel_chat_id = chat_id
        user.panel_message_id = message_id
        await session.commit()

    async def clear_screen(self, session: AsyncSession, user_id: int) -> None:
        user = await self.get_or_create(session, user_id)
        user.panel_chat_id = None
        user.panel_message_id = None
        await session.commit()

    # ---------- active tool ----------
    async def set_active_tool(self, session: AsyncSession, user_id: int, tool: str | None) -> None:
        user = await self.get_or_create(session, user_id)
        user.active_tool = tool
        await session.commit()

    async def get_active_tool(self, session: AsyncSession, user_id: int) -> str | None:
        user = await self.get_or_create(session, user_id)
        return user.active_tool

    # ---------- mode message (anti-spam) ----------
    async def get_mode_msg(self, session: AsyncSession, user_id: int) -> tuple[int, int] | None:
        user = await self.get_or_create(session, user_id)
        if user.mode_chat_id and user.mode_message_id:
            return int(user.mode_chat_id), int(user.mode_message_id)
        return None

    async def set_mode_msg(self, session: AsyncSession, user_id: int, chat_id: int, message_id: int) -> None:
        user = await self.get_or_create(session, user_id)
        user.mode_chat_id = chat_id
        user.mode_message_id = message_id
        await session.commit()

    async def clear_mode_msg(self, session: AsyncSession, user_id: int) -> None:
        user = await self.get_or_create(session, user_id)
        user.mode_chat_id = None
        user.mode_message_id = None
        await session.commit()

    # ---------- audio format ----------
    async def set_audio_format(self, session: AsyncSession, user_id: int, fmt: str) -> None:
        user = await self.get_or_create(session, user_id)
        user.audio_format = fmt
        await session.commit()

    async def get_audio_format(self, session: AsyncSession, user_id: int) -> str:
        user = await self.get_or_create(session, user_id)
        return user.audio_format or "mp3"