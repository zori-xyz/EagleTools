from __future__ import annotations

from datetime import datetime

from sqlalchemy import BigInteger, DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.infra.db.base import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)

    # language
    language: Mapped[str] = mapped_column(String(8), default="ru", nullable=False)

    # last "screen" message (main UI)
    panel_chat_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    panel_message_id: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # anti-spam "mode" message (separate info message)
    mode_chat_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    mode_message_id: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # active tool
    active_tool: Mapped[str | None] = mapped_column(String(32), nullable=True)

    # audio format for 🎧 tool
    audio_format: Mapped[str] = mapped_column(String(8), default="mp3", nullable=False)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)