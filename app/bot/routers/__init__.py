# app/bot/routers/__init__.py
from aiogram import Router

from app.bot.routers.admin.panel import router as admin_panel_router
from app.bot.routers.admin.broadcast import router as admin_broadcast_router
from app.bot.routers.public.premium import router as premium_router
from app.bot.routers.public.start import router as start_router
from app.bot.routers.public.smart_router import router as smart_router


def build_router() -> Router:
    r = Router()

    # Admin first — /grant, /admin, /user must not be swallowed by other routers
    r.include_router(admin_panel_router)
    r.include_router(admin_broadcast_router)

    # Premium: pre_checkout queries must be registered before smart_router
    r.include_router(premium_router)

    # Menu / welcome / settings
    r.include_router(start_router)

    # Smart router always last — catch-all for files and URLs
    r.include_router(smart_router)

    return r
