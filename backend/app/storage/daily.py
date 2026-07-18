"""Daily-note helpers: one note per day at ``daily/YYYY-MM-DD.md``, auto-created."""

from __future__ import annotations

import re
from datetime import date

from .notes import Note, NoteStore

_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def daily_rel_path(day: date) -> str:
    return f"daily/{day.isoformat()}.md"


def parse_date(value: str) -> date:
    if not _DATE_RE.match(value):
        raise ValueError("Date must be YYYY-MM-DD")
    return date.fromisoformat(value)


def _template(day: date) -> str:
    heading = day.strftime("%A, %B %-d, %Y")
    return f"---\ndate: {day.isoformat()}\ntype: daily\n---\n\n# {heading}\n\n"


def get_or_create(store: NoteStore, day: date) -> Note:
    rel = daily_rel_path(day)
    if not store.exists(rel):
        store.write(rel, _template(day))
    return store.read(rel)
