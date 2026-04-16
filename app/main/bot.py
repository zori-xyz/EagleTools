# app/main/bot.py
from __future__ import annotations

import asyncio
import os
import sys

from aiogram import Bot, Dispatcher
from aiogram.types import BotCommand, Message, Update
from aiogram.dispatcher.middlewares.base import BaseMiddleware

from app.bot.routers import build_router
from app.bot.middleware import RateLimitMiddleware
from app.common.config import settings
from app.common.logging import setup_logging
from app.common.pidlock import PidLock
from app.infra.db.init_db import init_db


class DeleteCommandMiddleware(BaseMiddleware):
    """Auto-delete user command messages after they're handled."""

    async def __call__(self, handler, event: Update, data: dict):
        result = await handler(event, data)
        msg: Message | None = getattr(event, "message", None)
        if msg and msg.text and msg.text.startswith("/"):
            try:
                await msg.delete()
            except Exception:
                pass
        return result


async def main() -> None:
    setup_logging()

    os.makedirs(settings.data_dir, exist_ok=True)

    await init_db()

    lock_path = os.path.join(settings.data_dir, "bot.lock")
    try:
        lock = PidLock.acquire(lock_path)
    except RuntimeError as e:
        print(str(e), file=sys.stderr)
        return

    bot = Bot(token=settings.effective_bot_token)
    dp = Dispatcher()

    dp.message.outer_middleware(RateLimitMiddleware(max_calls=20, window_sec=60))
    dp.update.outer_middleware(DeleteCommandMiddleware())

    dp.include_router(build_router())

    try:
        await bot.delete_webhook(drop_pending_updates=True)

        await bot.set_my_commands([
            BotCommand(command="start",    description="Главное меню"),
            BotCommand(command="menu",     description="Главное меню"),
            BotCommand(command="premium",  description="⚡️ Получить Premium"),
            BotCommand(command="settings", description="Настройки"),
            BotCommand(command="quota",    description="📊 Мой лимит загрузок"),
        ])

        print("✅ Polling started")
        await dp.start_polling(bot)

    finally:
        await bot.session.close()
        lock.release()


if __name__ == "__main__":
    asyncio.run(main())
