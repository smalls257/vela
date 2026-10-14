"""The close state record: what `planner close sync-main` found, kept so `planner close gate` can say it. Pure: no disk.

The Violation this exists to prevent is a Black Box between two close steps. Sync-main and the gate are separate
commands (one capability each), so without a record the gate cannot tell "main was brought in" from "nobody tried"
from "the shared copy could not be reached". Each outcome is written as one JSON file, `.planner/close/<key>.json`
(`.planner/` is never committed), and the gate reads it through `verdict`, the one place that says which statuses
let a close go on. A missing or unreadable record is never read as a pass (Silent Fallback): `verdict(None)` blocks.

Shape (version 1):

    {"version": 1, "branch": "session/x", "status": "merged", "reason": "",
     "main": "<origin/main sha compared against, or ''>", "head": "<HEAD after, or ''>", "date": "YYYY-MM-DD",
     "files": [{"path": "...", "lines": ["12-18"]}]}

`files` lists the hunks that stopped the merge (status `conflict`) or the generated-only files settled with `-X ours`.
"""
import json
import re
from dataclasses import dataclass

VERSION = 1
UP_TO_DATE, MERGED, MERGED_GENERATED = "up-to-date", "merged", "merged-generated-only"
CONFLICT, NOT_COMPARED, ACCEPTED, READER = "conflict", "not-compared", "not-compared-accepted", "reader"
STATUSES = (UP_TO_DATE, MERGED, MERGED_GENERATED, CONFLICT, NOT_COMPARED, ACCEPTED, READER)

# Why a branch was not compared, so the gate and a reviewer can tell an outage from a dirty tree.
FETCH_FAILED, UNCOMMITTED, GIT_FAILED = "fetch-failed", "uncommitted-edits", "git-failed"

# A reader copy has no git, so no branch to key by; a git that failed before naming the branch has none either.
READER_KEY, UNKNOWN_KEY = "reader-copy", "unknown-branch"
FOLDER = ".planner/close"


class StateUnreadable(ValueError):
    """The record exists but is not a record this version wrote. The gate says so; it never treats it as a pass."""


def key_for(branch):
    """The file name stem for a branch: `session/x` -> `session__x`. A branch name may hold slashes and characters a
    file system refuses, and sync-main and the gate must agree on the name, so both call this."""
    if not branch:
        return UNKNOWN_KEY
    return re.sub(r"[^\w.-]", "_", branch.replace("/", "__"))


def record(status, branch, main="", head="", date="", reason="", files=()):
    """A close state record. Raises ValueError for a status this version does not know, so a typo is a bug, not a
    record the gate cannot read."""
    if status not in STATUSES:
        raise ValueError(f"planner bug: unknown close state status {status!r}")
    return {"version": VERSION, "branch": branch or "", "status": status, "reason": reason, "main": main or "",
            "head": head or "", "date": date, "files": [dict(f) for f in files]}


def dumps(rec):
    return json.dumps(rec, indent=2, ensure_ascii=False) + "\n"


def parse(text):
    """The record in `text`; StateUnreadable when it is not JSON or not a record this version knows."""
    try:
        rec = json.loads(text)
    except ValueError as exc:
        raise StateUnreadable(f"the close state is not JSON ({exc})") from exc
    if not isinstance(rec, dict) or rec.get("version") != VERSION or rec.get("status") not in STATUSES:
        raise StateUnreadable("the close state is not a record this planner wrote")
    return rec


@dataclass(frozen=True)
class Verdict:
    """What the gate makes of a record. `blocks` stops the close; `plain` is the lead-facing reason (no codes);
    `listed` means the close may go on but the gate must still say it (the lead chose to go on without main)."""
    blocks: bool
    plain: str
    status: str = ""
    listed: bool = False


_PASS = {UP_TO_DATE: "This branch has everything on main.",
         MERGED: "What changed on main was brought in.",
         MERGED_GENERATED: "What changed on main was brought in; the overlaps were only in generated summaries."}


def verdict(rec):
    """The gate's reading of a record (or None when sync-main has not run on this branch). The gate calls this and
    lists `plain` for every verdict that blocks or is `listed`."""
    if rec is None:
        return Verdict(True, "Main hasn't been brought in yet: sync-main hasn't run on this branch.", "")
    status = rec.get("status")
    if status in _PASS:
        return Verdict(False, _PASS[status], status)
    if status == READER:
        return Verdict(False, "This is a read copy, so there is no main to bring in.", status)
    if status == ACCEPTED:
        return Verdict(False, "This branch wasn't compared with main; the lead chose to go on without it.", status, True)
    if status == CONFLICT:
        return Verdict(True, "Main changed pages this branch changed too, so the merge was stopped and is still open.",
                       status)
    return Verdict(True, "This branch isn't compared with main yet.", status or NOT_COMPARED)
