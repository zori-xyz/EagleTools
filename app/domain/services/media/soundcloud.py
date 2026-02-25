from __future__ import annotations

import asyncio
import shutil
import tempfile
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse


class SoundCloudError(RuntimeError):
    pass


@dataclass(frozen=True)
class SoundCloudResult:
    filepath: Path
    tmp_dir: Path


def _is_http_url(url: str) -> bool:
    try:
        u = urlparse(url)
        return u.scheme in ("http", "https") and bool(u.netloc)
    except Exception:
        return False


async def _run(cmd: list[str]) -> None:
    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    _, err = await proc.communicate()
    if proc.returncode != 0:
        raise SoundCloudError((err or b"").decode("utf-8", errors="ignore")[:1200])


def _mk_tmp(workdir: Path) -> Path:
    workdir.mkdir(parents=True, exist_ok=True)
    return Path(tempfile.mkdtemp(prefix="soundcloud_", dir=str(workdir)))


def cleanup_soundcloud_result(res: SoundCloudResult) -> None:
    try:
        shutil.rmtree(res.tmp_dir, ignore_errors=True)
    except Exception:
        pass


async def download_soundcloud_track_to_mp3(
    url: str,
    *,
    workdir: Path | None = None,
    out_dir: Path | None = None,
) -> SoundCloudResult:
    if not _is_http_url(url):
        raise SoundCloudError("invalid_url")

    base = out_dir if out_dir is not None else (workdir or Path("tmp") / "work")
    tmp_dir = _mk_tmp(base)

    out_tmpl = str(tmp_dir / "%(title).80s_%(id)s.%(ext)s")

    cmd = [
        "yt-dlp",
        "-x",
        "--audio-format",
        "mp3",
        "--no-playlist",
        "-o",
        out_tmpl,
        url,
    ]
    await _run(cmd)

    mp3s = [p for p in tmp_dir.glob("*.mp3") if p.is_file()]
    if not mp3s:
        raise SoundCloudError("no_output")

    mp3s.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    src = mp3s[0]

    if out_dir is not None and tmp_dir.resolve() != out_dir.resolve():
        out_dir.mkdir(parents=True, exist_ok=True)
        dst = out_dir / src.name
        try:
            src.replace(dst)
        except Exception:
            shutil.copy2(src, dst)
        return SoundCloudResult(filepath=dst, tmp_dir=tmp_dir)

    return SoundCloudResult(filepath=src, tmp_dir=tmp_dir)