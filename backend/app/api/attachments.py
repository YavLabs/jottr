"""Attachment storage — images, ink SVGs, and other files referenced by notes.

Attachments live in ``attachments/`` in the volume. Notes reference them by URL
(``/api/attachments/<name>``); the editor renders and (for ink) reopens them.
"""

from __future__ import annotations

import re
import secrets
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel

from ..auth.routes import current_user
from ..config import Settings, get_settings

router = APIRouter(prefix="/api/attachments", tags=["attachments"], dependencies=[Depends(current_user)])

_SAFE_NAME_RE = re.compile(r"[^A-Za-z0-9._-]+")
_MAX_BYTES = 25 * 1024 * 1024  # 25 MB per attachment


def _safe_name(name: str) -> str:
    cleaned = _SAFE_NAME_RE.sub("-", (name or "").strip()).strip("-.")
    return cleaned or "file"


def _resolve(settings: Settings, name: str) -> Path:
    safe = _safe_name(name)
    base = settings.attachments_dir.resolve()
    target = (base / safe).resolve()
    if base not in target.parents:
        raise HTTPException(status_code=400, detail="Invalid attachment name")
    return target


class InkPayload(BaseModel):
    # Raw SVG markup for an inline ink block. Name optional (server mints one).
    name: str | None = None
    svg: str


@router.post("")
async def upload(file: UploadFile, settings: Settings = Depends(get_settings)) -> dict:
    settings.attachments_dir.mkdir(parents=True, exist_ok=True)
    raw = await file.read()
    if len(raw) > _MAX_BYTES:
        raise HTTPException(status_code=413, detail="Attachment too large")

    stem = _safe_name(Path(file.filename or "file").stem)
    suffix = _safe_name(Path(file.filename or "").suffix.lstrip("."))
    token = secrets.token_hex(4)
    name = f"{stem}-{token}.{suffix}" if suffix else f"{stem}-{token}"
    target = _resolve(settings, name)
    target.write_bytes(raw)
    return {"name": name, "url": f"/api/attachments/{name}", "size": len(raw)}


@router.put("/ink/{name}")
def save_ink(name: str, payload: InkPayload, settings: Settings = Depends(get_settings)) -> dict:
    """Create or overwrite an ink SVG attachment (idempotent by name)."""
    settings.attachments_dir.mkdir(parents=True, exist_ok=True)
    if not name.endswith(".svg"):
        raise HTTPException(status_code=400, detail="Ink attachments must be .svg")
    target = _resolve(settings, name)
    target.write_text(payload.svg, encoding="utf-8")
    return {"name": name, "url": f"/api/attachments/{name}", "size": target.stat().st_size}


@router.get("/{name}")
def get_attachment(name: str, settings: Settings = Depends(get_settings)) -> FileResponse:
    target = _resolve(settings, name)
    if not target.is_file():
        raise HTTPException(status_code=404, detail="Attachment not found")
    return FileResponse(target)
