from __future__ import annotations

from datetime import datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.infra.db.base import Base


class User(Base):
    __tablename__ = "users"
    __table_args__ = {"schema": "eagle"}

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    tg_id: Mapped[int] = mapped_column(BigInteger, unique=True, index=True, nullable=False)

    # enums-free (в БД CHECK constraint)
    plan: Mapped[str] = mapped_column(String(16), nullable=False, default="free")
    premium_until: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)

    referred_by_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("eagle.users.id", ondelete="SET NULL"),
        nullable=True,
    )
    referrals_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    active_tool: Mapped[str] = mapped_column(String(32), nullable=True)
    audio_format: Mapped[str] = mapped_column(String(8), nullable=False, default="mp3")

    mode_chat_id: Mapped[int] = mapped_column(BigInteger, nullable=True)
    mode_message_id: Mapped[int] = mapped_column(Integer, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    # self-referential relationship
    referred_by: Mapped["User"] = relationship(
        "User",
        remote_side="User.id",
        foreign_keys=[referred_by_id],
        lazy="selectin",
    )