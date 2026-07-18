"""Jottr FastAPI application entrypoint.

Serves the REST API under /api and the built single-page app for every other
route (SPA fallback). One process owns the data volume — single writer.
"""

from __future__ import annotations

import logging

from fastapi import FastAPI
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware

from .api.attachments import router as attachments_router
from .api.notes import router as notes_router
from .auth.routes import router as auth_router
from .config import get_settings
from .index.db import connect, init_schema
from .index.indexer import Indexer
from .index.watcher import IndexWatcher
from .runtime import set_runtime
from .storage.notes import NoteStore

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
log = logging.getLogger("jottr")

settings = get_settings()

app = FastAPI(title="Jottr", version="0.0.1")

# Authlib stores the OAuth state/nonce in this signed session between the
# /login redirect and the /callback. Separate from the app's own JWT cookie.
app.add_middleware(SessionMiddleware, secret_key=settings.jwt_secret, same_site="lax")

app.include_router(auth_router)
app.include_router(notes_router)
app.include_router(attachments_router)

_watcher: IndexWatcher | None = None


@app.on_event("startup")
def _startup() -> None:
    global _watcher
    settings.ensure_volume()
    log.info("Data volume ready at %s", settings.data_dir.resolve())
    if not settings.google_configured:
        log.warning(
            "Google OAuth not configured; dev auth %s",
            "ENABLED (login as %s)" % settings.dev_auth_email if settings.dev_auth else "DISABLED",
        )

    # Wire the store + rebuildable index, rebuild from files, then watch.
    store = NoteStore(settings)
    conn = connect(settings.index_db_path)
    init_schema(conn)
    indexer = Indexer(conn, store)
    set_runtime(store, indexer)
    count = indexer.reindex_all()
    log.info("Search index rebuilt from %d note(s)", count)

    _watcher = IndexWatcher(settings, indexer)
    _watcher.start()


@app.on_event("shutdown")
def _shutdown() -> None:
    if _watcher is not None:
        _watcher.stop()


@app.get("/api/health")
def health() -> JSONResponse:
    return JSONResponse(
        {
            "status": "ok",
            "app": "jottr",
            "version": app.version,
            "google_oauth": settings.google_configured,
            "dev_auth": settings.dev_auth and not settings.google_configured,
        }
    )


# --- Static SPA serving ---------------------------------------------------
# In production the Docker build drops the compiled SPA into static_dir. We
# mount its assets and fall back to index.html for client-side routes. When the
# dir is absent (pure-backend local dev) the API still works on its own.
def _mount_spa() -> None:
    static_dir = settings.static_dir
    index_file = static_dir / "index.html"
    if not index_file.exists():
        log.warning("SPA build not found at %s; API-only mode", static_dir.resolve())

        @app.get("/")
        def _no_spa() -> JSONResponse:
            return JSONResponse(
                {"detail": "Frontend not built. Run the Vite dev server or build the image."},
                status_code=200,
            )

        return

    assets = static_dir / "assets"
    if assets.exists():
        app.mount("/assets", StaticFiles(directory=assets), name="assets")

    @app.get("/{full_path:path}")
    def spa_fallback(full_path: str) -> FileResponse:
        # API routes are registered above and take precedence; anything else
        # returns the SPA shell so the client router can handle it.
        candidate = static_dir / full_path
        if full_path and candidate.is_file():
            return FileResponse(candidate)
        return FileResponse(index_file)


_mount_spa()
