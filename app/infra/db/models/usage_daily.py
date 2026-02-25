from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import Date, DateTime, ForeignKey, Integer, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.infra.db.base import Base


class UsageDaily(Base):
    __tablename__ = "daily_usage"
    __table_args__ = {"schema": "eagle"}

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    user_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("eagle.users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    day: Mapped[date] = mapped_column(Date, nullable=False, index=True)

    used_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    user: Mapped["User"] = relationship("User", lazy="selectin")