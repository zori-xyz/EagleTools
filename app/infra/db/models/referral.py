from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.infra.db.base import Base


class Referral(Base):
    __tablename__ = "referrals"
    __table_args__ = {"schema": "eagle"}

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    inviter_user_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("eagle.users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    invited_user_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("eagle.users.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    inviter: Mapped["User"] = relationship("User", foreign_keys=[inviter_user_id], lazy="selectin")
    invited: Mapped["User"] = relationship("User", foreign_keys=[invited_user_id], lazy="selectin")