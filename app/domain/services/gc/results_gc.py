from __future__ import annotations

import time
from dataclasses import dataclass
from pathlib import Path


@dataclass(slots=True)
class GCStats:
    scanned: int = 0
    deleted: int = 0
    freed_bytes: int = 0


def prune_results_dir(results_dir: Path, *, ttl_seconds: int, grace_seconds: int = 600) -> GCStats:
    """
    Best-effort cleanup:
    - deletes files older than ttl_seconds
    - never touches files newer than grace_seconds (downloads in progress)
    """
    stats = GCStats()
    now = time.time()

    results_dir = results_dir.resolve()
    if not results_dir.exists() or not results_dir.is_dir():
        return stats

    for p in results_dir.iterdir():
        if not p.is_file():
            continue

        stats.scanned += 1

        try:
            st = p.stat()
        except FileNotFoundError:
            continue

        age = now - st.st_mtime
        if age < grace_seconds:
            continue
        if age < ttl_seconds:
            continue

        try:
            size = int(st.st_size)
            p.unlink(missing_ok=True)
            stats.deleted += 1
            stats.freed_bytes += size
        except Exception:
            # never crash worker because of permissions/locks
            continue

    return stats