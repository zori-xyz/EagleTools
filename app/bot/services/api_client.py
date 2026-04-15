# app/bot/services/api_client.py
"""
HTTP client: Telegram bot → internal web API.

The bot sends URLs here instead of running yt-dlp directly —
this keeps the heavy processing off the bot process and reduces
the chance of Telegram banning the bot for outbound scraping.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Literal

import httpx

from app.common.config import settings

log = logging.getLogger(__name__)

_TIMEOUT = httpx.Timeout(360.0, connect=10.0)


@dataclass
class DownloadResult:
    file_id: str          # filename in data/results/
    title: str | None
    extractor: str | None
    size_bytes: int | None
    ext: str | None       # "mp4", "mp3", etc.


class BotApiError(RuntimeError):
    """Raised when the internal API returns an error."""


def _is_configured() -> bool:
    return bool(
        (settings.bot_api_url or "").strip()
        and (settings.bot_api_key or "").strip()
    )


async def download_url(
    url: str,
    action: Literal["video", "audio"] = "video",
) -> DownloadResult:
    """
    Ask the internal web API to download *url*.

    Falls back to local processing if BOT_API_URL / BOT_API_KEY are not set.
    Raises BotApiError on failure.
    """
    if not _is_configured():
        return await _download_locally(url, action)

    base = (settings.bot_api_url or "").rstrip("/")
    endpoint = f"{base}/api/internal/bot/save"
    headers = {"X-API-KEY": settings.bot_api_key or ""}

    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT, follow_redirects=True) as client:
            resp = await client.post(
                endpoint,
                json={"url": url, "action": action},
                headers=headers,
            )
    except httpx.RequestError as e:
        log.warning("BotApiClient request error: %s — falling back to local", e)
        return await _download_locally(url, action)

    if resp.status_code == 401:
        raise BotApiError("api_unauthorized")
    if resp.status_code == 504:
        raise BotApiError("download_timeout")
    if resp.status_code == 422:
        detail = resp.json().get("detail", "download_failed")
        raise BotApiError(detail)
    if not resp.is_success:
        raise BotApiError(f"api_error:{resp.status_code}")

    data = resp.json()
    return DownloadResult(
        file_id=data["file_id"],
        title=data.get("title"),
        extractor=data.get("extractor"),
        size_bytes=data.get("size_bytes"),
        ext=data.get("ext"),
    )


# ── Local fallback (when internal API is not configured) ──────────────────────

async def _download_locally(
    url: str,
    action: Literal["video", "audio"],
) -> DownloadResult:
    """Process URL directly in the bot process (no web API)."""
    from pathlib import Path
    from app.domain.services.media.saver import save_media_from_url, SaveError

    results_dir = Path(settings.data_dir) / "results"
    tmp_dir = Path(settings.data_dir) / "tmp" / "bot_local"
    results_dir.mkdir(parents=True, exist_ok=True)
    tmp_dir.mkdir(parents=True, exist_ok=True)

    if action == "audio":
        return await _download_audio_locally(url, results_dir, tmp_dir)

    try:
        res = await save_media_from_url(str(url), workdir=tmp_dir, out_dir=results_dir)
        return DownloadResult(
            file_id=res.file_id,
            title=res.title,
            extractor=res.extractor,
            size_bytes=res.size_bytes,
            ext=None,
        )
    except SaveError as e:
        raise BotApiError(str(e))


async def _download_audio_locally(
    url: str,
    results_dir: "Path",
    tmp_dir: "Path",
) -> DownloadResult:
    import asyncio
    import shutil
    import uuid
    from pathlib import Path

    out_id = uuid.uuid4().hex
    work = tmp_dir / out_id
    work.mkdir(parents=True, exist_ok=True)
    try:
        out_tpl = str(work / "audio.%(ext)s")
        cmd = [
            "yt-dlp",
            "--no-playlist", "--geo-bypass", "--no-warnings",
            "--no-check-certificate", "--print-json",
            "--user-agent",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
            " (KHTML, like Gecko) Chrome/122.0 Safari/537.36",
            "-x", "--audio-format", "mp3", "--audio-quality", "192k",
            "-o", out_tpl,
            url,
        ]
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        try:
            stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=300)
        except asyncio.TimeoutError:
            proc.kill()
            raise BotApiError("download_timeout")
        if proc.returncode != 0:
            raise BotApiError("download_failed")

        candidates = list(work.glob("audio.*"))
        if not candidates or candidates[0].stat().st_size == 0:
            raise BotApiError("download_empty")
        src = candidates[0]
        dest_name = f"{out_id}{src.suffix}"
        dest = results_dir / dest_name
        src.rename(dest)

        meta: dict = {}
        try:
            import json
            for line in reversed(stdout.decode("utf-8", errors="ignore").strip().split("\n")):
                if line.strip().startswith("{"):
                    meta = json.loads(line)
                    break
        except Exception:
            pass

        return DownloadResult(
            file_id=dest.name,
            title=meta.get("title") or meta.get("fulltitle"),
            extractor=meta.get("extractor") or meta.get("extractor_key"),
            size_bytes=dest.stat().st_size,
            ext=dest.suffix.lstrip(".") or "mp3",
        )
    finally:
        shutil.rmtree(work, ignore_errors=True)
