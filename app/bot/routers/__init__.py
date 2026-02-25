from aiogram import Router

from app.bot.routers.public.audio_format import router as audio_format_router
from app.bot.routers.public.start import router as start_router
from app.bot.routers.public.smart_router import router as smart_router


def build_router() -> Router:
    r = Router()

    # ВАЖНО: перехваты до меню
    r.include_router(audio_format_router)

    # ВАЖНО: сначала команды и меню
    r.include_router(start_router)

    # ВАЖНО: smart_router всегда ПОСЛЕДНИЙ
    r.include_router(smart_router)

    return r