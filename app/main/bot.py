from __future__ import annotations

import asyncio
import os
import sys

from aiogram import Bot, Dispatcher
from aiogram.types import BotCommand

from app.bot.routers import build_router
from app.common.config import settings
from app.common.logging import setup_logging
from app.common.pidlock import PidLock
from app.infra.db.init_db import init_db


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

    bot = Bot(token=settings.bot_token)
    dp = Dispatcher()
    dp.include_router(build_router())

    try:
        await bot.delete_webhook(drop_pending_updates=True)

        await bot.set_my_commands(
            [
                BotCommand(command="start", description="Запуск"),
                BotCommand(command="menu", description="Открыть меню"),
                BotCommand(command="tools", description="Инструменты"),
                BotCommand(command="settings", description="Настройки"),
                BotCommand(command="profile", description="Профиль"),
                BotCommand(command="lang", description="Сменить язык"),
            ]
        )

        print("✅ Polling started")
        await dp.start_polling(bot)

    finally:
        await bot.session.close()
        lock.release()


if __name__ == "__main__":
    asyncio.run(main())