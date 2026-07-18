"""Note storage — markdown files in the volume are the source of truth.

A note's identity is its path relative to the data dir, e.g. ``daily/2026-07-18.md``
or ``notes/ideas/foo.md``. Only ``.md`` files under the ``notes/`` and ``daily/``
roots are addressable, and every path is validated so it cannot escape the volume.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

import yaml

from ..config import Settings

ALLOWED_ROOTS = ("notes", "daily")
_FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n?", re.DOTALL)
_HEADING_RE = re.compile(r"^#\s+(.+?)\s*$", re.MULTILINE)


class NoteError(Exception):
    """Raised for invalid note paths or IO problems."""


@dataclass
class NoteMeta:
    path: str
    title: str
    kind: str  # "daily" | "note"
    mtime: float
    size: int


@dataclass
class Note:
    path: str
    title: str
    kind: str
    mtime: float
    size: int
    content: str
    frontmatter: dict = field(default_factory=dict)

    def meta(self) -> NoteMeta:
        return NoteMeta(self.path, self.title, self.kind, self.mtime, self.size)


class NoteStore:
    def __init__(self, settings: Settings):
        self.settings = settings

    # --- path handling -----------------------------------------------------
    def _resolve(self, rel_path: str) -> Path:
        rel = (rel_path or "").strip().lstrip("/")
        if not rel.endswith(".md"):
            raise NoteError("Only .md paths are addressable")
        root = rel.split("/", 1)[0]
        if root not in ALLOWED_ROOTS:
            raise NoteError(f"Path must be under one of {ALLOWED_ROOTS}")

        base = self.settings.data_dir.resolve()
        target = (base / rel).resolve()
        # Containment check — no traversal outside the volume.
        if base not in target.parents and target != base:
            raise NoteError("Path escapes the data volume")
        return target

    @staticmethod
    def _kind(rel_path: str) -> str:
        return "daily" if rel_path.startswith("daily/") else "note"

    def _rel(self, abs_path: Path) -> str:
        return abs_path.resolve().relative_to(self.settings.data_dir.resolve()).as_posix()

    # --- parsing -----------------------------------------------------------
    @staticmethod
    def parse(rel_path: str, raw: str) -> tuple[dict, str, str]:
        """Return (frontmatter, body, title) for a raw markdown string."""
        frontmatter: dict = {}
        body = raw
        m = _FRONTMATTER_RE.match(raw)
        if m:
            try:
                loaded = yaml.safe_load(m.group(1)) or {}
                if isinstance(loaded, dict):
                    frontmatter = loaded
            except yaml.YAMLError:
                frontmatter = {}
            body = raw[m.end():]

        title = frontmatter.get("title")
        if not title:
            hm = _HEADING_RE.search(body)
            title = hm.group(1) if hm else Path(rel_path).stem
        return frontmatter, body, str(title)

    # --- operations --------------------------------------------------------
    def exists(self, rel_path: str) -> bool:
        return self._resolve(rel_path).is_file()

    def read(self, rel_path: str) -> Note:
        target = self._resolve(rel_path)
        if not target.is_file():
            raise NoteError("Note not found")
        raw = target.read_text(encoding="utf-8")
        stat = target.stat()
        frontmatter, _body, title = self.parse(rel_path, raw)
        return Note(
            path=rel_path,
            title=title,
            kind=self._kind(rel_path),
            mtime=stat.st_mtime,
            size=stat.st_size,
            content=raw,
            frontmatter=frontmatter,
        )

    def write(self, rel_path: str, content: str) -> NoteMeta:
        target = self._resolve(rel_path)
        target.parent.mkdir(parents=True, exist_ok=True)
        # Atomic-ish write: temp file then replace, so a crash can't truncate.
        tmp = target.with_suffix(target.suffix + ".tmp")
        tmp.write_text(content, encoding="utf-8")
        tmp.replace(target)
        stat = target.stat()
        _fm, _body, title = self.parse(rel_path, content)
        return NoteMeta(rel_path, title, self._kind(rel_path), stat.st_mtime, stat.st_size)

    def delete(self, rel_path: str) -> None:
        target = self._resolve(rel_path)
        if target.is_file():
            target.unlink()

    def list(self) -> list[NoteMeta]:
        base = self.settings.data_dir.resolve()
        out: list[NoteMeta] = []
        for root in ALLOWED_ROOTS:
            root_dir = base / root
            if not root_dir.is_dir():
                continue
            for p in root_dir.rglob("*.md"):
                if not p.is_file() or p.name.endswith(".tmp"):
                    continue
                rel = self._rel(p)
                try:
                    raw = p.read_text(encoding="utf-8")
                except OSError:
                    continue
                _fm, _body, title = self.parse(rel, raw)
                stat = p.stat()
                out.append(NoteMeta(rel, title, self._kind(rel), stat.st_mtime, stat.st_size))
        out.sort(key=lambda m: m.mtime, reverse=True)
        return out

    def iter_all(self):
        """Yield (rel_path, raw) for every note — used to rebuild the index."""
        base = self.settings.data_dir.resolve()
        for root in ALLOWED_ROOTS:
            root_dir = base / root
            if not root_dir.is_dir():
                continue
            for p in root_dir.rglob("*.md"):
                if not p.is_file() or p.name.endswith(".tmp"):
                    continue
                try:
                    yield self._rel(p), p.read_text(encoding="utf-8")
                except OSError:
                    continue

    def rel_for_abs(self, abs_path: Path) -> str | None:
        """Map a filesystem path (from the watcher) to a note rel-path, or None."""
        try:
            rel = self._rel(abs_path)
        except (ValueError, OSError):
            return None
        if not rel.endswith(".md") or rel.endswith(".tmp"):
            return None
        if rel.split("/", 1)[0] not in ALLOWED_ROOTS:
            return None
        return rel
