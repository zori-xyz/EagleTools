from __future__ import annotations

import asyncio
import json
import os
from pathlib import Path

from arq.connections import RedisSettings
from arq.cron import cron
from faster_whisper import WhisperModel

from app.common.config import settings
from app.domain.services.gc.results_gc import prune_results_dir
from app.domain.services.jobs import get_job, set_job_status
from app.infra.db.init_db import init_db
from app.infra.db.schema import JobStatus
from app.infra.db.session import SessionMaker


DATA_DIR = Path(settings.data_dir)
RESULTS_DIR = (DATA_DIR / "results").resolve()
STT_DIR = (DATA_DIR / "stt").resolve()
STT_DIR.mkdir(parents=True, exist_ok=True)

_model: WhisperModel | None = None


def _get_model() -> WhisperModel:
    global _model
    if _model is None:
        _model = WhisperModel("small", device="cpu", compute_type="int8")
    return _model


async def _gc_loop() -> None:
    ttl_hours = int(os.getenv("RESULTS_TTL_HOURS", "72"))
    interval_min = int(os.getenv("GC_INTERVAL_MIN", "30"))
    grace_sec = int(os.getenv("GC_GRACE_SECONDS", "600"))
    jitter_sec = int(os.getenv("GC_JITTER_SECONDS", "5"))

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    while True:
        try:
            stats = prune_results_dir(
                RESULTS_DIR,
                ttl_seconds=ttl_hours * 3600,
                grace_seconds=grace_sec,
            )
            if stats.deleted:
                print(
                    f"[gc] results: deleted={stats.deleted} freed={stats.freed_bytes}B scanned={stats.scanned}",
                    flush=True,
                )
        except Exception as e:
            print(f"[gc] error: {type(e).__name__}:{e}", flush=True)

        await asyncio.sleep(interval_min * 60 + jitter_sec)


async def startup(ctx) -> None:
    await init_db()
    ctx["gc_task"] = asyncio.create_task(_gc_loop())


async def shutdown(ctx) -> None:
    task = ctx.get("gc_task")
    if task:
        task.cancel()


async def process_stt(ctx, job_id: int) -> None:
    async with SessionMaker() as session:
        job = await get_job(session, job_id)
        if not job:
            return

        await set_job_status(session, job_id, JobStatus.running)

        try:
            src = (RESULTS_DIR / job.file_id).resolve()

            try:
                src.relative_to(RESULTS_DIR)
            except Exception:
                raise PermissionError("invalid_file_path")

            if not src.exists() or not src.is_file():
                raise FileNotFoundError("input_file_not_found")

            model = _get_model()
            segments, info = model.transcribe(str(src), beam_size=5)

            out = {
                "language": getattr(info, "language", None),
                "duration": getattr(info, "duration", None),
                "segments": [{"start": s.start, "end": s.end, "text": s.text} for s in segments],
            }

            out_path = (STT_DIR / f"{job_id}.json").resolve()
            out_path.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")

            await set_job_status(session, job_id, JobStatus.done, result_path=str(out_path))

        except Exception as e:
            await set_job_status(session, job_id, JobStatus.failed, error=f"{type(e).__name__}:{e}")


async def notify_expiring_premium(ctx) -> None:
    """
    Cron: runs daily at 10:00 UTC.
    Sends notification to users whose Premium expires in 3 days.
    """
    from datetime import datetime, timezone, timedelta
    from sqlalchemy import select
    from aiogram import Bot
    from app.infra.db.models.user import User

    now = datetime.now(timezone.utc)
    window_start = now + timedelta(days=3)
    window_end = now + timedelta(days=3, hours=24)

    print(f"[cron] notify_expiring_premium: checking window {window_start:%Y-%m-%d} …", flush=True)

    bot = Bot(token=settings.effective_bot_token)

    try:
        async with SessionMaker() as session:
            result = await session.execute(
                select(User).where(
                    User.plan == "premium",
                    User.premium_until >= window_start,
                    User.premium_until < window_end,
                )
            )
            users = result.scalars().all()

        print(f"[cron] notify_expiring_premium: found {len(users)} users", flush=True)

        for user in users:
            lang = user.language_code or "ru"
            until_str = user.premium_until.strftime("%d.%m.%Y") if user.premium_until else "—"

            if lang == "en":
                text = (
                    "⏳ <b>Your Premium expires in 3 days</b>\n\n"
                    f"Valid until: <b>{until_str}</b>\n\n"
                    "Renew now to keep unlimited access 🦅"
                )
            else:
                text = (
                    "⏳ <b>Твой Premium истекает через 3 дня</b>\n\n"
                    f"Действует до: <b>{until_str}</b>\n\n"
                    "Продли сейчас чтобы сохранить безлимитный доступ 🦅"
                )

            from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
            kb = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(
                    text="⚡️ Продлить Premium" if lang != "en" else "⚡️ Renew Premium",
                    callback_data="premium:open",
                )],
            ])

            try:
                await bot.send_message(
                    chat_id=user.tg_id,
                    text=text,
                    reply_markup=kb,
                    parse_mode="HTML",
                )
                print(f"[cron] notified user {user.tg_id}", flush=True)
            except Exception as e:
                print(f"[cron] failed to notify {user.tg_id}: {e}", flush=True)

            # небольшая пауза чтобы не флудить Telegram API
            await asyncio.sleep(0.05)

    finally:
        await bot.session.close()


class WorkerSettings:
    on_startup = startup
    on_shutdown = shutdown
    functions = [process_stt]
    cron_jobs = [
        cron(notify_expiring_premium, hour=10, minute=0),  # каждый день в 10:00 UTC
    ]
    redis_settings = RedisSettings.from_dsn(settings.redis_url)