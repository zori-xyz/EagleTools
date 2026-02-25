# app/main/smoke.py
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.infra.db.schema import User
from app.infra.db.session import get_session

router = APIRouter(prefix="/__smoke", tags=["smoke"])


@router.get("/health")
async def health():
    return {"ok": True}


@router.get("/db")
async def db(session: AsyncSession = Depends(get_session)):
    # 1) базовая проверка коннекта
    await session.execute(text("SELECT 1"))

    # 2) проверка что модели маппятся и registry не конфликтует
    u = User(tg_id=999999999, plan="free")
    session.add(u)
    await session.flush()

    # откатываем, чтобы не засорять базу
    await session.rollback()
    return {"ok": True}