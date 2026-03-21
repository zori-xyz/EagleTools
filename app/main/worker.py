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
    # Создаём директории при старте воркера
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    STT_DIR.mkdir(parents=True, exist_ok=True)
    print("[worker] directories ready", flush=True)
    await init_db()
    print("[worker] db ready", flush=True)
    ctx["gc_task"] = asyncio.create_task(_gc_loop())
    print("[worker] started", flush=True)


async def shutdown(ctx) -> None:
    task = ctx.get("gc_task")
    if task:
        task.cancel()


TG_TEXT_LIMIT = 3800


async def _notify_user(tg_id: int, text: str, job_id: int) -> None:
    """Отправляем результат STT пользователю."""
    from aiogram import Bot
    from aiogram.types import FSInputFile as AiogramFile
    bot = Bot(token=settings.effective_bot_token)
    try:
        if len(text) <= TG_TEXT_LIMIT:
            await bot.send_message(
                chat_id=tg_id,
                text=f"📝 <b>Распознанный текст:</b>\n\n{text}",
                parse_mode="HTML",
            )
        else:
            out_txt = STT_DIR / f"{job_id}_result.txt"
            out_txt.write_text(text, encoding="utf-8")
            await bot.send_document(
                chat_id=tg_id,
                document=AiogramFile(str(out_txt)),
                caption="📝 Распознанный текст",
            )
    finally:
        await bot.session.close()


async def process_stt(ctx, job_id: int) -> None:
    from sqlalchemy import select as sa_select
    from sqlalchemy.orm import selectinload
    from app.infra.db.models.job import Job as JobModel

    async with SessionMaker() as session:
        # Загружаем job вместе с user через selectinload
        res = await session.execute(
            sa_select(JobModel)
            .where(JobModel.id == job_id)
            .options(selectinload(JobModel.user))
        )
        job = res.scalar_one_or_none()

        if not job:
            print(f"[stt] job {job_id} not found", flush=True)
            return

        tg_id = job.user.tg_id if job.user else None
        print(f"[stt] job {job_id} started, tg_id={tg_id}", flush=True)

        await set_job_status(session, job_id, JobStatus.running)

        try:
            src = (RESULTS_DIR / job.file_id).resolve()
            try:
                src.relative_to(RESULTS_DIR)
            except Exception:
                raise PermissionError("invalid_file_path")

            if not src.exists() or not src.is_file():
                raise FileNotFoundError(f"file not found: {src}")

            print(f"[stt] transcribing {src.name} ({src.stat().st_size} bytes)", flush=True)
            model = _get_model()
            segments_gen, info = model.transcribe(str(src), beam_size=5)
            segments = list(segments_gen)

            full_text = " ".join(s.text.strip() for s in segments).strip()
            print(f"[stt] done, lang={info.language}, chars={len(full_text)}", flush=True)

            out = {
                "language": getattr(info, "language", None),
                "duration": getattr(info, "duration", None),
                "text": full_text,
                "segments": [{"start": s.start, "end": s.end, "text": s.text} for s in segments],
            }

            out_path = (STT_DIR / f"{job_id}.json").resolve()
            out_path.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")

            await set_job_status(session, job_id, JobStatus.done, result_path=str(out_path))

            # Отправляем результат пользователю
            if tg_id and full_text:
                try:
                    await _notify_user(tg_id, full_text, job_id)
                    print(f"[stt] notified user {tg_id}", flush=True)
                except Exception as e:
                    print(f"[stt] notify failed: {e}", flush=True)
            elif not full_text:
                print(f"[stt] empty result for job {job_id}", flush=True)
                if tg_id:
                    from aiogram import Bot
                    bot = Bot(token=settings.effective_bot_token)
                    try:
                        await bot.send_message(tg_id, "🤷 Не удалось распознать речь — возможно файл слишком тихий или повреждён.")
                    finally:
                        await bot.session.close()

        except Exception as e:
            print(f"[stt] job {job_id} error: {type(e).__name__}:{e}", flush=True)
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