# app/web/app.py
from __future__ import annotations

from pathlib import Path

from fastapi import Depends, FastAPI
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

from app.web.deps import get_tg_user
from app.web.routes.api import router as api_router, file_router
from app.web.routes.convert import router as convert_router
from app.web.routes.profile import router as profile_router
from app.web.routes.recent import router as recent_router
from app.web.routes.internal import router as internal_router


def _find_index_html() -> Path:
    here = Path(__file__).resolve()
    templates_dir = here.parent / "templates"
    index_path = (templates_dir / "index.html").resolve()
    if not index_path.exists():
        raise FileNotFoundError(f"index.html not found: {index_path}")
    return index_path


def create_app() -> FastAPI:
    app = FastAPI(title="EagleTools WebApp")

    # Static
    static_dir = (Path(__file__).resolve().parent / "static").resolve()
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

    # Public file download (no auth)
    app.include_router(file_router, prefix="/api")

    # Protected API (WebApp auth)
    protected = [Depends(get_tg_user)]
    app.include_router(api_router, prefix="/api", dependencies=protected)
    app.include_router(profile_router, prefix="/api", dependencies=protected)

    # recent_router already has prefix="/api" inside router
    app.include_router(recent_router, dependencies=protected)
    app.include_router(convert_router, prefix="/api", dependencies=protected)

    # Internal API
    app.include_router(internal_router)

    # Index
    index_path = _find_index_html()

    @app.get("/", response_class=HTMLResponse)
    async def index() -> HTMLResponse:
        return HTMLResponse(index_path.read_text(encoding="utf-8"))

    return app


app = create_app()