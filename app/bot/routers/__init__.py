# app/bot/routers/__init__.py
from aiogram import Router

from app.bot.routers.admin.panel import router as admin_panel_router
from app.bot.routers.admin.broadcast import router as admin_broadcast_router
from app.bot.routers.public.audio_format import router as audio_format_router
from app.bot.routers.public.premium import router as premium_router
from app.bot.routers.public.start import router as start_router
from app.bot.routers.public.smart_router import router as smart_router


def build_router() -> Router:
    r = Router()

    # Admin роутеры первыми — чтобы команды /grant, /admin, /user не перехватывались
    r.include_router(admin_panel_router)
    r.include_router(admin_broadcast_router)

    # Перехваты до меню
    r.include_router(audio_format_router)

    # Premium: payments и pre_checkout должны быть до smart_router
    r.include_router(premium_router)

    # Команды и меню
    r.include_router(start_router)

    # smart_router всегда ПОСЛЕДНИМ
    r.include_router(smart_router)

    return r