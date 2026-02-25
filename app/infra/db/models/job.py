from __future__ import annotations

from datetime import datetime

from sqlalchemy import BigInteger, Column, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import relationship

from app.infra.db.base import Base


class Job(Base):
    __tablename__ = "jobs"
    __table_args__ = {"schema": "eagle"}

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("eagle.users.id", ondelete="SET NULL"), nullable=True, index=True)

    kind = Column(String(16), nullable=False, index=True)
    status = Column(String(16), nullable=False, index=True)

    file_id = Column(String(255), nullable=True)
    result_path = Column(String(1024), nullable=True)
    error = Column(Text, nullable=True)

    # ✅ Новые поля (metadata)
    title = Column(String(512), nullable=True)
    source_url = Column(String(2048), nullable=True)
    extractor = Column(String(64), nullable=True)
    size_bytes = Column(BigInteger, nullable=True)

    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    user = relationship("User", lazy="selectin")