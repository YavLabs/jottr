"""Index maintenance: turn notes into FTS rows and run search queries."""

from __future__ import annotations

import json
import re
import sqlite3
import threading
from datetime import date

from ..storage.notes import NoteStore
from ..storage.tasks import parse_tasks

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
            self.conn.execute("DELETE FROM tasks;")
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
            self._index_tasks(note.path, note.content)
            self.conn.commit()

    def remove(self, rel_path: str) -> None:
        with _write_lock:
            self.conn.execute("DELETE FROM notes_fts WHERE path = ?;", (rel_path,))
            self.conn.execute("DELETE FROM tasks WHERE path = ?;", (rel_path,))
            self.conn.commit()

    def _insert(self, rel_path: str, raw: str) -> None:
        _fm, _body, title = self.store.parse(rel_path, raw)
        kind = "daily" if rel_path.startswith("daily/") else "note"
        mtime = self.store._resolve(rel_path).stat().st_mtime
        self.conn.execute(
            "INSERT INTO notes_fts(path, title, body, kind, mtime) VALUES (?, ?, ?, ?, ?);",
            (rel_path, title, raw, kind, mtime),
        )
        self._index_tasks(rel_path, raw)

    def _index_tasks(self, rel_path: str, content: str) -> None:
        """Replace the task rows for one note. Caller holds the write lock."""
        kind = "daily" if rel_path.startswith("daily/") else "note"
        self.conn.execute("DELETE FROM tasks WHERE path = ?;", (rel_path,))
        rows = [
            (
                rel_path,
                t.line,
                t.text,
                1 if t.done else 0,
                t.due,
                t.effective_date,
                t.priority,
                json.dumps(t.tags),
                t.recurrence,
                kind,
            )
            for t in parse_tasks(rel_path, content)
        ]
        if rows:
            self.conn.executemany(
                "INSERT INTO tasks(path, line, text, done, due, effective_date, priority, tags, "
                "recurrence, kind) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?);",
                rows,
            )

    # --- task queries ------------------------------------------------------
    @staticmethod
    def _row_to_task(r: sqlite3.Row) -> dict:
        d = dict(r)
        d["done"] = bool(d["done"])
        d["tags"] = json.loads(d["tags"]) if d.get("tags") else []
        return d

    def list_tasks(self, view: str = "all", tag: str | None = None, limit: int = 500) -> list[dict]:
        today = date.today().isoformat()
        where = []
        params: list = []

        if view == "completed":
            where.append("done = 1")
        elif view == "today":
            where.append("done = 0 AND effective_date = ?")
            params.append(today)
        elif view == "overdue":
            where.append("done = 0 AND effective_date IS NOT NULL AND effective_date < ?")
            params.append(today)
        elif view == "upcoming":
            where.append("done = 0 AND effective_date IS NOT NULL AND effective_date > ?")
            params.append(today)
        elif view == "open":
            where.append("done = 0")
        # "all" -> no filter

        if tag:
            # tags stored as JSON array of strings; match the quoted tag token.
            where.append("tags LIKE ?")
            params.append(f'%"{tag}"%')

        sql = "SELECT * FROM tasks"
        if where:
            sql += " WHERE " + " AND ".join(where)
        # Undated last; then by date; high priority first.
        sql += (
            " ORDER BY (effective_date IS NULL), effective_date, "
            "CASE priority WHEN 'high' THEN 0 WHEN 'medium' THEN 1 WHEN 'low' THEN 2 ELSE 3 END, "
            "path, line LIMIT ?;"
        )
        params.append(limit)
        rows = self.conn.execute(sql, params).fetchall()
        return [self._row_to_task(r) for r in rows]

    def task_counts(self) -> dict:
        today = date.today().isoformat()
        row = self.conn.execute(
            """
            SELECT
              SUM(CASE WHEN done=0 AND effective_date=? THEN 1 ELSE 0 END) AS today,
              SUM(CASE WHEN done=0 AND effective_date IS NOT NULL AND effective_date<? THEN 1 ELSE 0 END) AS overdue,
              SUM(CASE WHEN done=0 AND effective_date IS NOT NULL AND effective_date>? THEN 1 ELSE 0 END) AS upcoming,
              SUM(CASE WHEN done=0 THEN 1 ELSE 0 END) AS open,
              SUM(CASE WHEN done=1 THEN 1 ELSE 0 END) AS completed
            FROM tasks;
            """,
            (today, today, today),
        ).fetchone()
        return {k: (row[k] or 0) for k in ("today", "overdue", "upcoming", "open", "completed")}

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
