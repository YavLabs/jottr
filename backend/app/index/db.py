"""SQLite FTS5 index — a rebuildable derivative of the markdown files.

The index is never the source of truth: it is rebuilt from the volume on
startup and kept in sync by the file watcher. Delete it and it regenerates.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

_SCHEMA = """
CREATE VIRTUAL TABLE IF NOT EXISTS notes_fts USING fts5(
    path UNINDEXED,
    title,
    body,
    kind UNINDEXED,
    mtime UNINDEXED,
    tokenize = 'porter unicode61'
);

CREATE TABLE IF NOT EXISTS tasks (
    path            TEXT NOT NULL,
    line            INTEGER NOT NULL,
    text            TEXT NOT NULL,
    done            INTEGER NOT NULL,
    due             TEXT,
    effective_date  TEXT,
    priority        TEXT,
    tags            TEXT,   -- JSON array
    recurrence      TEXT,
    kind            TEXT,
    PRIMARY KEY (path, line)
);
CREATE INDEX IF NOT EXISTS idx_tasks_done ON tasks(done);
CREATE INDEX IF NOT EXISTS idx_tasks_effective ON tasks(effective_date);
"""


def connect(db_path: Path) -> sqlite3.Connection:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA busy_timeout=5000;")
    return conn


def init_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(_SCHEMA)
    conn.commit()
