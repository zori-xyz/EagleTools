# app/web/middleware.py
from __future__ import annotations

import time
from collections import defaultdict
from typing import Callable

from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

# ─────────────────────────────────────────────────────────────
# Пути которые возвращают 404 сразу — мусор от сканеров
# ─────────────────────────────────────────────────────────────
_JUNK_PREFIXES = (
    "/wp-", "/wordpress", "/phpmyadmin", "/pma", "/admin",
    "/backup", "/.git", "/.env", "/config", "/.aws",
    "/shell", "/cgi-bin", "/vendor", "/composer",
    "/xmlrpc", "/sql", "/dump", "/.svn", "/.DS_Store",
)

_JUNK_EXTENSIONS = (
    ".php", ".asp", ".aspx", ".jsp", ".cgi",
    ".bak", ".old", ".sql", ".tar", ".rar",
    ".zip", ".gz", ".tgz", ".7z",
)

# ─────────────────────────────────────────────────────────────
# Rate limiter — in-memory, per IP
# Для продакшна с несколькими воркерами лучше Redis,
# но для одного uvicorn воркера этого достаточно
# ─────────────────────────────────────────────────────────────
class _RateLimiter:
    def __init__(self, max_requests: int, window_sec: int):
        self.max_requests = max_requests
        self.window_sec   = window_sec
        self._buckets: dict[str, list[float]] = defaultdict(list)

    def is_allowed(self, key: str) -> bool:
        now = time.monotonic()
        window_start = now - self.window_sec
        bucket = self._buckets[key]

        # Чистим старые записи
        self._buckets[key] = [t for t in bucket if t > window_start]

        if len(self._buckets[key]) >= self.max_requests:
            return False

        self._buckets[key].append(now)
        return True

    def cleanup(self) -> None:
        """Периодическая очистка памяти — вызывай раз в минуту."""
        now = time.monotonic()
        cutoff = now - self.window_sec
        dead = [k for k, v in self._buckets.items() if all(t < cutoff for t in v)]
        for k in dead:
            del self._buckets[k]


# Разные лимиты для разных эндпоинтов
_api_limiter    = _RateLimiter(max_requests=60,  window_sec=60)   # 60 req/min на /api
_upload_limiter = _RateLimiter(max_requests=10,  window_sec=60)   # 10 upload/min
_global_limiter = _RateLimiter(max_requests=200, window_sec=60)   # 200 req/min глобально


def _get_client_ip(request: Request) -> str:
    # За nginx/proxy
    forwarded = request.headers.get("X-Forwarded-For", "")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


class SecurityMiddleware(BaseHTTPMiddleware):
    """
    Комбинированный middleware:
    1. Блокирует мусорные пути (сканеры WordPress, бэкапы и тп)
    2. Rate limiting по IP
    3. Добавляет базовые security headers
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        path = request.url.path.lower()
        ip   = _get_client_ip(request)

        # ── 1. Блокируем мусорные пути ────────────────────────
        if self._is_junk(path):
            return Response(status_code=404, content="Not found")

        # ── 2. Rate limiting ──────────────────────────────────
        # Глобальный лимит
        if not _global_limiter.is_allowed(ip):
            return JSONResponse(
                status_code=429,
                content={"detail": "too_many_requests"},
                headers={"Retry-After": "60"},
            )

        # Лимит на API
        if path.startswith("/api/"):
            limiter = _upload_limiter if path == "/api/convert" else _api_limiter
            if not limiter.is_allowed(ip):
                return JSONResponse(
                    status_code=429,
                    content={"detail": "rate_limit_exceeded"},
                    headers={"Retry-After": "60"},
                )

        # ── 3. Обрабатываем запрос ────────────────────────────
        response = await call_next(request)

        # ── 4. Security headers ───────────────────────────────
        response.headers["X-Content-Type-Options"]    = "nosniff"
        response.headers["X-Frame-Options"]           = "DENY"
        response.headers["X-XSS-Protection"]          = "1; mode=block"
        response.headers["Referrer-Policy"]           = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"]        = "geolocation=(), microphone=(), camera=()"

        return response

    @staticmethod
    def _is_junk(path: str) -> bool:
        for prefix in _JUNK_PREFIXES:
            if path.startswith(prefix):
                return True
        for ext in _JUNK_EXTENSIONS:
            if path.endswith(ext):
                return True
        return False