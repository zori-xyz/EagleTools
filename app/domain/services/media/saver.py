from __future__ import annotations

import asyncio
import json
import mimetypes
import re
import shutil
import tempfile
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Final
from urllib.parse import urlparse

import httpx


class SaveError(RuntimeError):
    pass


@dataclass(frozen=True)
class SaveResult:
    file_id: str
    filename: str
    filepath: str
    tmp_dir: Path
    title: str | None = None
    source_url: str | None = None
    extractor: str | None = None
    size_bytes: int | None = None


_MAX_BYTES: Final[int] = 200 * 1024 * 1024  # 200MB
_CHUNK: Final[int] = 1024 * 256  # 256KB

_BLOCKED_CONTENT_TYPES: Final[set[str]] = {
    "text/html",
    "application/xhtml+xml",
}


def _ensure_dir(p: Path) -> None:
    p.mkdir(parents=True, exist_ok=True)


def _is_http_url(url: str) -> bool:
    try:
        u = urlparse(url)
        return u.scheme in ("http", "https") and bool(u.netloc)
    except Exception:
        return False


def _safe_ext_from_name(name: str) -> str:
    ext = (Path(name).suffix or "").lower()
    if not ext:
        return ""
    if len(ext) > 10:
        return ""
    if not re.fullmatch(r"\.[a-z0-9]+", ext):
        return ""
    return ext


def _ext_from_content_type(content_type: str | None) -> str:
    if not content_type:
        return ""
    ct = content_type.split(";")[0].strip().lower()
    ext = mimetypes.guess_extension(ct) or ""
    return _safe_ext_from_name("x" + ext)


def cleanup_save_result(res: SaveResult) -> None:
    try:
        shutil.rmtree(res.tmp_dir, ignore_errors=True)
    except Exception:
        pass


async def _run(cmd: list[str], timeout_sec: int = 900) -> tuple[bytes, bytes]:
    """Возвращает (stdout, stderr)"""
    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        try:
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout_sec)
        except asyncio.TimeoutError:
            proc.kill()
            raise SaveError("yt_dlp_timeout")

        if proc.returncode != 0:
            msg = (stderr or b"").decode("utf-8", errors="ignore")[:1200]
            raise SaveError(f"yt_dlp_failed:{msg}")

        return stdout, stderr
    except FileNotFoundError:
        raise SaveError("yt_dlp_not_installed")


def _mk_tmp(workdir: Path) -> Path:
    _ensure_dir(workdir)
    return Path(tempfile.mkdtemp(prefix="save_", dir=str(workdir)))


def _new_id() -> str:
    return uuid.uuid4().hex


async def _save_with_ytdlp(url: str, *, workdir: Path, out_dir: Path) -> tuple[Path, dict]:
    """
    Возвращает (путь к файлу, metadata dict)
    metadata содержит: title, extractor, size_bytes
    """
    tmp_dir = _mk_tmp(workdir)
    out_id = _new_id()

    _ensure_dir(out_dir)
    out_path = out_dir / f"{out_id}.mp4"

    cmd = [
        "yt-dlp",
        "--no-playlist",
        "--geo-bypass",
        "--no-warnings",
        "--no-check-certificate",
        "--print-json",
        "--user-agent",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0 Safari/537.36",
        "-f",
        "bv*+ba/b",
        "--merge-output-format",
        "mp4",
        "-o",
        str(out_path),
        url,
    ]

    try:
        stdout, _ = await _run(cmd)
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)

    if not out_path.exists() or not out_path.is_file() or out_path.stat().st_size == 0:
        raise SaveError("yt_dlp_no_output")

    metadata = {}
    try:
        lines = stdout.decode("utf-8", errors="ignore").strip().split("\n")
        for line in reversed(lines):
            if line.strip().startswith("{"):
                metadata = json.loads(line)
                break
    except Exception:
        pass

    title = metadata.get("title") or metadata.get("fulltitle") or None
    extractor = metadata.get("extractor") or metadata.get("extractor_key") or None
    size_bytes = out_path.stat().st_size

    return out_path, {
        "title": title,
        "extractor": extractor,
        "size_bytes": size_bytes,
    }


async def _save_direct_http(url: str, *, workdir: Path, out_dir: Path, timeout_sec: int) -> tuple[Path, dict]:
    tmp_dir = _mk_tmp(workdir)
    out_id = _new_id()
    tmp_path = tmp_dir / "download"

    limits = httpx.Limits(max_keepalive_connections=5, max_connections=10)
    timeout = httpx.Timeout(timeout_sec)

    final_path: Path | None = None

    try:
        async with httpx.AsyncClient(
            follow_redirects=True,
            timeout=timeout,
            limits=limits,
            headers={"User-Agent": "EagleTools/1.0"},
        ) as client:
            async with client.stream("GET", url) as r:
                r.raise_for_status()

                ct = (r.headers.get("content-type") or "").split(";")[0].strip().lower()
                if ct in _BLOCKED_CONTENT_TYPES:
                    raise SaveError("not_media_url")

                filename = ""
                cd = r.headers.get("content-disposition") or ""
                m = re.search(r'filename\*?=(?:UTF-8\'\')?"?([^";]+)"?', cd, re.IGNORECASE)
                if m:
                    filename = m.group(1).strip()

                if not filename:
                    filename = Path(httpx.URL(url).path).name

                ext = _safe_ext_from_name(filename)
                if not ext:
                    ext = _ext_from_content_type(r.headers.get("content-type"))

                if not ext:
                    ext = ".bin"

                out_name = f"{out_id}{ext}"
                final_path = out_dir / out_name

                cl = r.headers.get("content-length")
                if cl is not None:
                    try:
                        if int(cl) > _MAX_BYTES:
                            raise SaveError("too_large")
                    except ValueError:
                        pass

                written = 0
                with tmp_path.open("wb") as f:
                    async for chunk in r.aiter_bytes(chunk_size=_CHUNK):
                        if not chunk:
                            continue
                        written += len(chunk)
                        if written > _MAX_BYTES:
                            raise SaveError("too_large")
                        f.write(chunk)

        if not tmp_path.exists() or tmp_path.stat().st_size == 0:
            raise SaveError("empty_download")

        _ensure_dir(out_dir)
        tmp_path.replace(final_path)

        size_bytes = final_path.stat().st_size
        title = filename or None

        return final_path, {
            "title": title,
            "extractor": "direct_http",
            "size_bytes": size_bytes,
        }

    except SaveError:
        raise
    except httpx.HTTPStatusError as e:
        raise SaveError(f"http_status:{e.response.status_code}")
    except httpx.RequestError:
        raise SaveError("http_request_failed")
    except Exception:
        raise SaveError("save_failed")
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)


async def save_media_from_url(
    url: str,
    *,
    workdir: Path,
    out_dir: Path,
    timeout_sec: int = 60,
) -> SaveResult:
    if not _is_http_url(url):
        raise SaveError("bad_url")

    if url.strip().lower().startswith(("file://", "ftp://")):
        raise SaveError("bad_url")

    _ensure_dir(workdir)
    _ensure_dir(out_dir)

    # FIX #1: create a dedicated session-level tmp dir so cleanup_save_result
    # deletes only this session's temp files, not the entire workdir (data/tmp/).
    session_tmp = Path(tempfile.mkdtemp(prefix="save_", dir=str(workdir)))

    ytdlp_err: SaveError | None = None
    try:
        p, meta = await _save_with_ytdlp(url, workdir=session_tmp, out_dir=out_dir)
        return SaveResult(
            file_id=p.name,
            filename=p.name,
            filepath=str(p),
            tmp_dir=session_tmp,
            title=meta.get("title"),
            source_url=url,
            extractor=meta.get("extractor"),
            size_bytes=meta.get("size_bytes"),
        )
    except SaveError as e:
        ytdlp_err = e

    try:
        p2, meta2 = await _save_direct_http(url, workdir=session_tmp, out_dir=out_dir, timeout_sec=timeout_sec)
        return SaveResult(
            file_id=p2.name,
            filename=p2.name,
            filepath=str(p2),
            tmp_dir=session_tmp,
            title=meta2.get("title"),
            source_url=url,
            extractor=meta2.get("extractor"),
            size_bytes=meta2.get("size_bytes"),
        )
    except SaveError as http_err:
        # FIX #14: raise the HTTP error (more informative for direct links),
        # fall back to ytdlp_err only if http gave a generic failure.
        shutil.rmtree(session_tmp, ignore_errors=True)
        raise http_err if str(http_err) not in ("save_failed",) else ytdlp_err