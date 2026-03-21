from __future__ import annotations

from arq import create_pool
from arq.connections import RedisSettings

from app.common.config import settings


def _redis_settings() -> RedisSettings:
    return RedisSettings.from_dsn(settings.redis_url)


async def enqueue_stt(job_id: int) -> None:
    redis = await create_pool(_redis_settings())
    try:
        await redis.enqueue_job("process_stt", job_id)
    finally:
        try:
            await redis.aclose()
        except Exception:
            try:
                redis.close()
                await redis.wait_closed()
            except Exception:
                pass