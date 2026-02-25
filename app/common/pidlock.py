from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class PidLock:
    path: str
    fd: int

    @classmethod
    def acquire(cls, path: str) -> "PidLock":
        os.makedirs(os.path.dirname(path), exist_ok=True)
        flags = os.O_CREAT | os.O_EXCL | os.O_WRONLY
        try:
            fd = os.open(path, flags, 0o644)
        except FileExistsError:
            raise RuntimeError(f"Bot already running (lock exists): {path}")

        os.write(fd, str(os.getpid()).encode("utf-8"))
        os.fsync(fd)
        return cls(path=path, fd=fd)

    def release(self) -> None:
        try:
            os.close(self.fd)
        except OSError:
            pass
        try:
            os.remove(self.path)
        except FileNotFoundError:
            pass