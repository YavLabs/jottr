"""File-watcher: keep the index in sync when files change on disk.

Files can be edited outside the app (a backup restore, git, another editor).
The watcher notices and the index catches up — the files stay authoritative.
"""

from __future__ import annotations

import logging
import threading
from pathlib import Path

try:
    from watchfiles import Change, watch

    _WATCHFILES_AVAILABLE = True
except ImportError:  # optional: not every Python build has a watchfiles wheel
    Change = None  # type: ignore[assignment]
    watch = None  # type: ignore[assignment]
    _WATCHFILES_AVAILABLE = False

from ..config import Settings
from .indexer import Indexer

log = logging.getLogger("jottr.watcher")


class IndexWatcher:
    def __init__(self, settings: Settings, indexer: Indexer):
        self.settings = settings
        self.indexer = indexer
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        if not _WATCHFILES_AVAILABLE:
            log.warning(
                "watchfiles not installed — out-of-band file edits won't auto-index "
                "(index still rebuilds on startup and updates on API writes)"
            )
            return
        watch_dirs = [self.settings.notes_dir, self.settings.daily_dir]
        for d in watch_dirs:
            d.mkdir(parents=True, exist_ok=True)
        self._thread = threading.Thread(
            target=self._run, args=(watch_dirs,), name="jottr-watcher", daemon=True
        )
        self._thread.start()
        log.info("File watcher started on %s", [str(d) for d in watch_dirs])

    def stop(self) -> None:
        self._stop.set()

    def _run(self, watch_dirs: list[Path]) -> None:
        try:
            for changes in watch(*watch_dirs, stop_event=self._stop, watch_filter=None):
                for change, path in changes:
                    self._handle(change, Path(path))
        except Exception as exc:  # never let the watcher thread kill the app
            log.exception("Watcher stopped unexpectedly: %s", exc)

    def _handle(self, change: Change, abs_path: Path) -> None:
        rel = self.indexer.store.rel_for_abs(abs_path)
        if rel is None:
            return
        try:
            if change == Change.deleted:
                self.indexer.remove(rel)
                log.debug("Index: removed %s", rel)
            else:
                self.indexer.update(rel)
                log.debug("Index: updated %s", rel)
        except Exception as exc:
            log.warning("Failed to index change for %s: %s", rel, exc)
