from __future__ import annotations

import asyncio
import os
import sys

from arq.worker import run_worker

from app.main.worker import WorkerSettings


def main() -> None:
    os.environ.setdefault("PYTHONUNBUFFERED", "1")
    print("[worker] starting…", flush=True)

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    try:
        run_worker(WorkerSettings)
    finally:
        try:
            loop.stop()
        except Exception:
            pass
        loop.close()
        print("[worker] stopped", flush=True)


if __name__ == "__main__":
    main()