"""The complexity waiver file, `.quality/complexity-waivers.tsv`: parse, write, and the checks that need no git.

It exists so a function over its cap is a recorded, owned, expiring exception rather than a quiet one. Two
Violations shape it:
  Paper Tiger  - a green gate whose exceptions grow. The file is delete-only: `added_entries` finds any line a
                 change adds or edits (a raised limit is an edited line), and only a reseed may add.
  Fossil Comments - a waiver for code that is gone, or a to-do comment whose date passed. Both expire by date.

Format, one tab-separated line per entry: key, limits, owner, expires, reason.
  key      `path::qualname` for a function, or `path` alone for a file.
  limits   space-separated `metric=int`, only the metrics that were over their cap; the recorded value is a ceiling.
  expires  YYYY-MM-DD, the last day the waiver holds.
Lines starting with `#` are comments; the one starting `# seeded ` records who seeded the file, when and from what.
Blank lines and a trailing carriage return are ignored.
"""
from __future__ import annotations

import datetime
import re
from dataclasses import dataclass
from typing import Iterable

from quality_report import Finding

WAIVER_FILE = ".quality/complexity-waivers.tsv"
METRICS = ("ccn", "nloc", "params", "nesting", "lines")
SEEDED_PREFIX = "# seeded "
DATED_TODO = re.compile(r"\b(TODO|FIXME|HACK)\(([^,()]+), (\d{4}-\d{2}-\d{2})\)")  # nosemgrep: todo-needs-owner-and-date -- the pattern names the marker words it looks for
ISO_DATE = re.compile(r"\d{4}-\d{2}-\d{2}")


class WaiverFileError(ValueError):
    pass


@dataclass(frozen=True)
class Waiver:
    key: str
    limits: dict
    owner: str
    expires: datetime.date
    reason: str
    line: int


def _data_lines(text: str) -> list[tuple[int, str]]:
    """(line number, line) for each entry line; comments, blanks and carriage returns are dropped."""
    lines = [(n, raw.rstrip("\r")) for n, raw in enumerate(text.split("\n"), start=1)]
    return [(n, line) for n, line in lines if line.strip() and not line.startswith("#")]


def _parse_limits(field: str, fail) -> dict:
    limits = {}
    for pair in field.split():
        metric, _, number = pair.partition("=")
        if metric not in METRICS:
            fail(f"unknown metric {metric!r}; use one of {', '.join(METRICS)}")
        if not number.isdigit():
            fail(f"{pair!r} is not metric=number")
        limits[metric] = int(number)
    if not limits:
        fail("no limits; write metric=number pairs such as ccn=59")
    return limits


def _parse_date(field: str, fail) -> datetime.date:
    if not ISO_DATE.fullmatch(field):
        fail(f"expiry {field!r} is not YYYY-MM-DD")
    try:
        return datetime.date.fromisoformat(field)
    except ValueError:
        fail(f"expiry {field!r} is not a real date")


def parse_waivers(text: str) -> dict[str, Waiver]:
    """The waivers by key. Any malformed line raises WaiverFileError naming it, so a broken file never reads as
    "no waivers"."""
    found: dict[str, Waiver] = {}
    for n, line in _data_lines(text):
        def fail(what: str, n: int = n) -> None:
            raise WaiverFileError(f"{WAIVER_FILE} line {n}: {what}")

        fields = line.split("\t")
        if len(fields) != 5:
            fail(f"expected 5 tab-separated fields (key, limits, owner, expires, reason), found {len(fields)}")
        key, limits, owner, expires, reason = (f.strip() for f in fields)
        if not key or not owner or not reason:
            fail("key, owner and reason must not be empty")
        if key in found:
            fail(f"{key} is already waived on line {found[key].line}")
        found[key] = Waiver(key, _parse_limits(limits, fail), owner, _parse_date(expires, fail), reason, n)
    return found


def format_waivers(waivers: Iterable[Waiver], seeded: str) -> str:
    """The file text: the seeded comment, then one line per waiver sorted by key so reseeds diff cleanly."""
    rows = []
    for w in sorted(waivers, key=lambda w: w.key):
        limits = " ".join(f"{m}={w.limits[m]}" for m in METRICS if m in w.limits)
        rows.append("\t".join((w.key, limits, w.owner, w.expires.isoformat(), w.reason)))
    return "\n".join([seeded, *rows]) + "\n"


def seeded_line(text: str) -> str:
    """The `# seeded ...` comment, or "" when the file has none."""
    return next((line.rstrip("\r") for line in text.split("\n") if line.startswith(SEEDED_PREFIX)), "")


def added_entries(base_text: str, head_text: str) -> list[str]:
    """Entry lines in head that base does not have. A changed line counts as added, so a raised limit is caught.
    A changed seeded line is a reseed, which the owner reviews as a whole, so it reports nothing."""
    head_seed = seeded_line(head_text)
    if head_seed and head_seed != seeded_line(base_text):
        return []
    known = {line for _, line in _data_lines(base_text)}
    return [line for _, line in _data_lines(head_text) if line not in known]


def expired(waivers: Iterable[Waiver], today: datetime.date) -> list[Waiver]:
    """The waivers whose last day is before today."""
    return [w for w in waivers if w.expires < today]


def _expired_todo(location: str, today: datetime.date) -> Finding | None:
    path, line_number, text = location.split(":", 2)
    hit = DATED_TODO.search(text)
    if not hit:
        return None
    kind, owner, date = hit.groups()
    try:
        due = datetime.date.fromisoformat(date)
    except ValueError:
        return Finding(path, int(line_number), "QG-WAIVER", f"{kind} by {owner} has an impossible date {date}: use a real YYYY-MM-DD")
    if due >= today:
        return None
    return Finding(path, int(line_number), "QG-WAIVER",
                   f"{kind} by {owner} expired on {date}: do it, or give it a new date and a reason in a reviewed commit")


def expired_todos(grep_lines: Iterable[str], today: datetime.date) -> list[Finding]:
    """Findings for dated to-do comments whose date is before today. Input is `git grep -n` output."""
    found = (_expired_todo(line, today) for line in grep_lines)
    return [f for f in found if f]
