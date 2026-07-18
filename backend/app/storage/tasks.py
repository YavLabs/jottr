"""Parse markdown checkboxes into structured tasks.

A task is a checkbox line inside a note; the file is authoritative and the
index follows. Inline metadata (documented convention):

    - [ ] Ship the parser due:2026-07-20 !high #jottr #backend every:weekly

    due:YYYY-MM-DD   explicit due date
    !high|!medium|!low   priority (also !med)
    #tag             one or more tags
    every:daily|weekly|monthly|weekday   recurrence (parsed, not yet expanded)

Effective date = explicit due date, else the daily-note's date (for tasks that
live in daily/YYYY-MM-DD.md), else none.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date

CHECKBOX_RE = re.compile(r"^(?P<indent>\s*)[-*+]\s+\[(?P<mark>[ xX])\]\s+(?P<text>.*\S.*)$")
DUE_RE = re.compile(r"\bdue:(\d{4}-\d{2}-\d{2})\b")
PRIORITY_RE = re.compile(r"(?:^|\s)!(high|medium|med|low)\b", re.IGNORECASE)
RECUR_RE = re.compile(r"\bevery:(daily|weekly|monthly|weekday)\b", re.IGNORECASE)
TAG_RE = re.compile(r"(?:^|\s)#([A-Za-z0-9_][A-Za-z0-9_/-]*)")
DAILY_PATH_RE = re.compile(r"^daily/(\d{4}-\d{2}-\d{2})\.md$")

_PRIORITY_NORM = {"high": "high", "medium": "medium", "med": "medium", "low": "low"}


@dataclass
class ParsedTask:
    line: int  # 1-based line number in the file
    text: str  # display text with metadata tokens stripped (tags kept)
    done: bool
    due: str | None
    priority: str | None
    tags: list[str] = field(default_factory=list)
    recurrence: str | None = None
    effective_date: str | None = None


def daily_date_of(rel_path: str) -> str | None:
    m = DAILY_PATH_RE.match(rel_path)
    return m.group(1) if m else None


def _clean_text(text: str) -> str:
    text = DUE_RE.sub("", text)
    text = PRIORITY_RE.sub(" ", text)
    text = RECUR_RE.sub("", text)
    return re.sub(r"\s{2,}", " ", text).strip()


def parse_tasks(rel_path: str, content: str) -> list[ParsedTask]:
    daily_date = daily_date_of(rel_path)
    out: list[ParsedTask] = []
    for i, raw_line in enumerate(content.splitlines(), start=1):
        m = CHECKBOX_RE.match(raw_line)
        if not m:
            continue
        text = m.group("text")
        done = m.group("mark").lower() == "x"

        due_m = DUE_RE.search(text)
        due = due_m.group(1) if due_m else None
        prio_m = PRIORITY_RE.search(text)
        priority = _PRIORITY_NORM[prio_m.group(1).lower()] if prio_m else None
        recur_m = RECUR_RE.search(text)
        recurrence = recur_m.group(1).lower() if recur_m else None
        tags = TAG_RE.findall(text)

        out.append(
            ParsedTask(
                line=i,
                text=_clean_text(text),
                done=done,
                due=due,
                priority=priority,
                tags=tags,
                recurrence=recurrence,
                effective_date=due or daily_date,
            )
        )
    return out


def toggle_line(content: str, line: int, done: bool) -> str:
    """Return content with the checkbox on `line` (1-based) set to done/undone."""
    lines = content.splitlines(keepends=True)
    if line < 1 or line > len(lines):
        raise ValueError("Line out of range")
    original = lines[line - 1]
    m = CHECKBOX_RE.match(original.rstrip("\n"))
    if not m:
        raise ValueError("Target line is not a checkbox")
    newline = "\n" if original.endswith("\n") else ""
    mark = "x" if done else " "
    body = original.rstrip("\n")
    # Replace only the first "[ ]" / "[x]" marker on the line.
    replaced = re.sub(r"\[[ xX]\]", f"[{mark}]", body, count=1)
    lines[line - 1] = replaced + newline
    return "".join(lines)


def make_checkbox_line(text: str, done: bool = False) -> str:
    return f"- [{'x' if done else ' '}] {text.strip()}"


def is_valid_due(value: str) -> bool:
    try:
        date.fromisoformat(value)
        return True
    except ValueError:
        return False
