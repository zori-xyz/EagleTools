from __future__ import annotations

import asyncio
import json
import os
from pathlib import Path

from arq.connections import RedisSettings
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
    """
    Periodic best-effort cleanup for DATA_DIR/results.
    Policy: keep files for some time after user deletes from Recent.
    """
    ttl_hours = int(os.getenv("RESULTS_TTL_HOURS", "72"))       # keep results for 72h by default
    interval_min = int(os.getenv("GC_INTERVAL_MIN", "30"))      # run every 30 min
    grace_sec = int(os.getenv("GC_GRACE_SECONDS", "600"))       # don't touch fresh files (10 min)
    jitter_sec = int(os.getenv("GC_JITTER_SECONDS", "5"))       # small jitter to avoid stampedes

    # Ensure dir exists (safe)
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
    # ensure tables exist in dev
    await init_db()

    # start GC loop
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

            # safety: prevent path traversal outside RESULTS_DIR
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


class WorkerSettings:
    on_startup = startup
    on_shutdown = shutdown
    functions = [process_stt]
    redis_settings = RedisSettings.from_dsn(settings.redis_url)