"""REST API for notes, daily notes and search. All routes require a session."""

from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from pydantic import BaseModel

from ..auth.routes import current_user
from ..auth.session import SessionUser
from ..index.indexer import Indexer
from ..runtime import get_indexer, get_store
from ..storage import daily as daily_mod
from ..storage.notes import NoteError, NoteStore

router = APIRouter(prefix="/api", tags=["notes"], dependencies=[Depends(current_user)])


class NoteContent(BaseModel):
    content: str


def _meta_dict(m) -> dict:
    return {"path": m.path, "title": m.title, "kind": m.kind, "mtime": m.mtime, "size": m.size}


# --- Notes ----------------------------------------------------------------
@router.get("/notes")
def list_notes(store: NoteStore = Depends(get_store)) -> list[dict]:
    return [_meta_dict(m) for m in store.list()]


@router.get("/notes/{path:path}")
def get_note(path: str, store: NoteStore = Depends(get_store)) -> dict:
    try:
        note = store.read(path)
    except NoteError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    return {
        "path": note.path,
        "title": note.title,
        "kind": note.kind,
        "mtime": note.mtime,
        "size": note.size,
        "content": note.content,
        "frontmatter": note.frontmatter,
    }


@router.put("/notes/{path:path}")
def put_note(
    path: str,
    body: NoteContent,
    store: NoteStore = Depends(get_store),
    indexer: Indexer = Depends(get_indexer),
) -> dict:
    try:
        meta = store.write(path, body.content)
    except NoteError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    indexer.update(path)  # keep the index fresh immediately, don't wait for the watcher
    return _meta_dict(meta)


@router.delete("/notes/{path:path}")
def delete_note(
    path: str,
    store: NoteStore = Depends(get_store),
    indexer: Indexer = Depends(get_indexer),
) -> Response:
    try:
        store.delete(path)
    except NoteError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    indexer.remove(path)
    return Response(status_code=204)


# --- Daily notes ----------------------------------------------------------
@router.get("/daily")
def daily_today(
    store: NoteStore = Depends(get_store),
    indexer: Indexer = Depends(get_indexer),
) -> dict:
    return _daily_for(date.today(), store, indexer)


@router.get("/daily/{day}")
def daily_for_date(
    day: str,
    store: NoteStore = Depends(get_store),
    indexer: Indexer = Depends(get_indexer),
) -> dict:
    try:
        parsed = daily_mod.parse_date(day)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return _daily_for(parsed, store, indexer)


def _daily_for(day: date, store: NoteStore, indexer: Indexer) -> dict:
    existed = store.exists(daily_mod.daily_rel_path(day))
    note = daily_mod.get_or_create(store, day)
    if not existed:
        indexer.update(note.path)
    return {
        "path": note.path,
        "title": note.title,
        "kind": note.kind,
        "mtime": note.mtime,
        "content": note.content,
        "frontmatter": note.frontmatter,
    }


# --- Search ---------------------------------------------------------------
@router.get("/search")
def search(
    q: str = Query(default="", description="Full-text query"),
    limit: int = Query(default=30, ge=1, le=200),
    indexer: Indexer = Depends(get_indexer),
) -> dict:
    results = indexer.search(q, limit=limit)
    return {"query": q, "count": len(results), "results": results}
