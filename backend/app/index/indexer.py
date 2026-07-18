"""Index maintenance: turn notes into FTS rows and run search queries."""

from __future__ import annotations

import re
import sqlite3
import threading

from ..storage.notes import NoteStore

# One lock serialises writes from the API and the file-watcher thread.
_write_lock = threading.Lock()

_TOKEN_RE = re.compile(r"[^\w]+", re.UNICODE)


class Indexer:
    def __init__(self, conn: sqlite3.Connection, store: NoteStore):
        self.conn = conn
        self.store = store

    # --- maintenance -------------------------------------------------------
    def reindex_all(self) -> int:
        count = 0
        with _write_lock:
            self.conn.execute("DELETE FROM notes_fts;")
            for rel, raw in self.store.iter_all():
                self._insert(rel, raw)
                count += 1
            self.conn.commit()
        return count

    def update(self, rel_path: str) -> None:
        """Re-index a single note that was created or modified."""
        try:
            note = self.store.read(rel_path)
        except Exception:
            # File vanished between the event and now — treat as delete.
            self.remove(rel_path)
            return
        with _write_lock:
            self.conn.execute("DELETE FROM notes_fts WHERE path = ?;", (rel_path,))
            self.conn.execute(
                "INSERT INTO notes_fts(path, title, body, kind, mtime) VALUES (?, ?, ?, ?, ?);",
                (note.path, note.title, note.content, note.kind, note.mtime),
            )
            self.conn.commit()

    def remove(self, rel_path: str) -> None:
        with _write_lock:
            self.conn.execute("DELETE FROM notes_fts WHERE path = ?;", (rel_path,))
            self.conn.commit()

    def _insert(self, rel_path: str, raw: str) -> None:
        _fm, _body, title = self.store.parse(rel_path, raw)
        kind = "daily" if rel_path.startswith("daily/") else "note"
        mtime = self.store._resolve(rel_path).stat().st_mtime
        self.conn.execute(
            "INSERT INTO notes_fts(path, title, body, kind, mtime) VALUES (?, ?, ?, ?, ?);",
            (rel_path, title, raw, kind, mtime),
        )

    # --- search ------------------------------------------------------------
    def search(self, query: str, limit: int = 30) -> list[dict]:
        match = self._to_match_query(query)
        if not match:
            return []
        rows = self.conn.execute(
            """
            SELECT path, title, kind, mtime,
                   snippet(notes_fts, 2, '<mark>', '</mark>', '…', 12) AS snippet
            FROM notes_fts
            WHERE notes_fts MATCH ?
            ORDER BY rank
            LIMIT ?;
            """,
            (match, limit),
        ).fetchall()
        return [dict(r) for r in rows]

    @staticmethod
    def _to_match_query(query: str) -> str:
        """Build a safe FTS5 MATCH string: prefix-match each alnum token."""
        tokens = [t for t in _TOKEN_RE.split(query or "") if t]
        if not tokens:
            return ""
        return " ".join(f'"{t}"*' for t in tokens)
