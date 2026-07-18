"""REST API for tasks parsed out of markdown checkboxes.

The file is authoritative: toggles and roll-over edit the markdown and re-index.
"""

from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from ..auth.routes import current_user
from ..index.indexer import Indexer
from ..runtime import get_indexer, get_store
from ..storage import daily as daily_mod
from ..storage.notes import NoteError, NoteStore
from ..storage.tasks import (
    CHECKBOX_RE,
    is_valid_due,
    make_checkbox_line,
    parse_tasks,
    toggle_line,
)

router = APIRouter(prefix="/api/tasks", tags=["tasks"], dependencies=[Depends(current_user)])

VIEWS = {"today", "upcoming", "overdue", "completed", "open", "all"}


class ToggleBody(BaseModel):
    path: str
    line: int
    done: bool


class AddBody(BaseModel):
    text: str
    due: str | None = None
    priority: str | None = None  # high | medium | low


@router.get("")
def list_tasks(
    view: str = Query(default="open"),
    tag: str | None = Query(default=None),
    limit: int = Query(default=500, ge=1, le=2000),
    indexer: Indexer = Depends(get_indexer),
) -> dict:
    if view not in VIEWS:
        raise HTTPException(status_code=400, detail=f"view must be one of {sorted(VIEWS)}")
    tasks = indexer.list_tasks(view=view, tag=tag, limit=limit)
    return {"view": view, "tag": tag, "count": len(tasks), "tasks": tasks}


@router.get("/counts")
def counts(indexer: Indexer = Depends(get_indexer)) -> dict:
    return indexer.task_counts()


@router.post("/toggle")
def toggle(
    body: ToggleBody,
    store: NoteStore = Depends(get_store),
    indexer: Indexer = Depends(get_indexer),
) -> dict:
    try:
        note = store.read(body.path)
    except NoteError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    try:
        updated = toggle_line(note.content, body.line, body.done)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    store.write(body.path, updated)
    indexer.update(body.path)
    return {"path": body.path, "line": body.line, "done": body.done}


@router.post("/add")
def add_task(
    body: AddBody,
    store: NoteStore = Depends(get_store),
    indexer: Indexer = Depends(get_indexer),
) -> dict:
    text = body.text.strip()
    if not text:
        raise HTTPException(status_code=400, detail="Task text is required")
    if body.due:
        if not is_valid_due(body.due):
            raise HTTPException(status_code=400, detail="due must be YYYY-MM-DD")
        if "due:" not in text:
            text = f"{text} due:{body.due}"
    if body.priority in {"high", "medium", "low"} and "!" not in text:
        text = f"{text} !{body.priority}"

    day = date.today()
    daily_mod.get_or_create(store, day)
    rel = daily_mod.daily_rel_path(day)
    note = store.read(rel)
    sep = "" if note.content.endswith("\n") else "\n"
    new_content = f"{note.content}{sep}{make_checkbox_line(text)}\n"
    store.write(rel, new_content)
    indexer.update(rel)
    return {"path": rel, "added": text}


@router.post("/rollover")
def rollover(
    store: NoteStore = Depends(get_store),
    indexer: Indexer = Depends(get_indexer),
) -> dict:
    """Move unfinished tasks from past daily notes into today's daily note."""
    today = date.today()
    today_rel = daily_mod.daily_rel_path(today)
    daily_mod.get_or_create(store, today)

    # Candidates: incomplete tasks in daily notes dated before today.
    candidates = indexer.list_tasks(view="overdue", limit=2000)
    by_path: dict[str, list[int]] = {}
    for t in candidates:
        if t["kind"] == "daily" and t["path"] != today_rel:
            by_path.setdefault(t["path"], []).append(t["line"])

    moved_lines: list[str] = []
    touched: list[str] = []

    for path, lines in by_path.items():
        try:
            note = store.read(path)
        except NoteError:
            continue
        content_lines = note.content.splitlines(keepends=True)
        # Grab the original checkbox text, then drop those lines (descending).
        for ln in sorted(lines):
            if 1 <= ln <= len(content_lines):
                m = CHECKBOX_RE.match(content_lines[ln - 1].rstrip("\n"))
                if m:
                    moved_lines.append(make_checkbox_line(m.group("text")))
        for ln in sorted(lines, reverse=True):
            if 1 <= ln <= len(content_lines):
                del content_lines[ln - 1]
        store.write(path, "".join(content_lines))
        touched.append(path)

    if moved_lines:
        note = store.read(today_rel)
        sep = "" if note.content.endswith("\n") else "\n"
        block = "\n".join(moved_lines) + "\n"
        store.write(today_rel, f"{note.content}{sep}{block}")
        touched.append(today_rel)

    for path in touched:
        indexer.update(path)

    return {"moved": len(moved_lines), "from_notes": len(by_path)}
