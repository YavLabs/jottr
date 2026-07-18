"""Process-wide singletons wired up at startup.

Single-writer app: one NoteStore and one Indexer (one SQLite connection) serve
the whole process. FastAPI dependencies pull them from here.
"""

from __future__ import annotations

from fastapi import HTTPException

from .index.indexer import Indexer
from .storage.notes import NoteStore

_store: NoteStore | None = None
_indexer: Indexer | None = None


def set_runtime(store: NoteStore, indexer: Indexer) -> None:
    global _store, _indexer
    _store = store
    _indexer = indexer


def get_store() -> NoteStore:
    if _store is None:
        raise HTTPException(status_code=503, detail="Store not initialised")
    return _store


def get_indexer() -> Indexer:
    if _indexer is None:
        raise HTTPException(status_code=503, detail="Indexer not initialised")
    return _indexer
