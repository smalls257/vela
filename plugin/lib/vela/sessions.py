"""Which session record is open, and on which branch: the pure half of `planner session open` (overhaul Task 6a).

The close skill used to carry this as a git recipe the model ran by hand: list `session/*` branches local and on
origin, `git show` each record, look for `status: open`, remember that a branch can hold more than one record. Each
step was a place to guess. The rules now live here, as functions over records the edge has already read:

- **A branch can hold more than one record.** An answer session opens its record on its challenge's branch
  (ANSWER-A-CHALLENGE.md), so the challenge's red check and its answer land in one pull request. That branch holds the
  challenge's closed record and the answer's open one; the branch to report is the one the record sits on, never a
  `session/<id>` built from the record's id. And every session branch carries the closed records merged from `main`,
  so "the record on this branch" is never assumed to be one file.
- **Remote branches count.** The lead may have opened the session on another machine; its branch then exists only on
  origin. A local and a remote copy of the same branch are one session, and the local copy wins, because it is the
  one this machine's work is on (it may already say `closed` while origin still says `open`).
- **One record id on several branches** (an open record that reached `main` by mistake, then every later branch
  carries it) is one session: the branch named `session/<id>` is its own, when it is among them. Otherwise every
  branch is listed and the lead picks.
- **Several open never guesses.** Picking one of two open sessions for the lead would file one session's captures
  into the other's record; the caller exits 3 and lists them.

Pure: records arrive as `(ref, path, text)`; no disk, git or clock. `edge/sessiongit.py` reads them.
"""
import datetime
import re
from dataclasses import dataclass

from vela import parse

LOCAL, REMOTE, FOLDER = "refs/heads/", "refs/remotes/origin/", ""
MONTHS = ("January", "February", "March", "April", "May", "June", "July", "August", "September", "October",
          "November", "December")
_DATED_HEADING = re.compile(r"^#\s+(?:\d{4}-\d{2}-\d{2}\s+)?(?P<title>.+?)\s*$", re.M)
_DATED_ID = re.compile(r"^\d{4}-\d{2}-\d{2}-")


@dataclass(frozen=True)
class Record:
    """One session record as found: `branch` is the short name (`session/x`), or None in a reader copy's folder."""
    id: str
    path: str
    branch: object
    remote_only: bool
    status: str
    modes: tuple
    date: str
    title: str

    def as_json(self):
        return {"id": self.id, "path": self.path, "branch": self.branch, "remote_only": self.remote_only,
                "status": self.status, "modes": list(self.modes), "date": self.date, "title": self.title}


def branch_of(ref):
    """(short branch name or None, is_remote) for a full ref; "" (a reader copy's folder) has no branch."""
    if ref.startswith(REMOTE):
        return ref[len(REMOTE):], True
    if ref.startswith(LOCAL):
        return ref[len(LOCAL):], False
    return None, False


def topic_of(meta, body, record_id):
    """What the lead calls the session: its `title:`, else the record's heading without the date, else the id's
    words."""
    if meta.get("title"):
        return str(meta["title"]).strip()
    heading = _DATED_HEADING.search(body)
    if heading:
        return heading.group("title")
    return _DATED_ID.sub("", record_id).replace("-", " ").capitalize()


def modes_of(meta):
    value = meta.get("modes") or ()
    return tuple(str(m) for m in (value if isinstance(value, (list, tuple)) else [value]))


def read(ref, path, text):
    """(Record, None) for one record's text, or (None, why) when its frontmatter cannot be read."""
    meta, body_start, error = parse.split_frontmatter(text)
    if error is not None:
        return None, f"{path}: {error.message}"
    stem = path.rsplit("/", 1)[-1][:-3] if path.endswith(".md") else path.rsplit("/", 1)[-1]
    record_id = str(meta.get("id") or stem)
    branch, remote = branch_of(ref)
    return Record(id=record_id, path=path, branch=branch, remote_only=remote, status=str(meta.get("status", "")),
                  modes=modes_of(meta), date=str(meta.get("date") or meta.get("started") or ""),
                  title=topic_of(meta, "\n".join(parse.lines_of(text)[body_start - 1:]), record_id)), None


def _one_per_branch(records):
    """A branch's local and origin copies of a record are one record; the local copy wins."""
    chosen = {}
    for record in records:
        key = (record.branch, record.path)
        if key not in chosen or (chosen[key].remote_only and not record.remote_only):
            chosen[key] = record
    return list(chosen.values())


def _one_per_id(records):
    """A record id on several branches is the session on `session/<id>` when that branch is among them."""
    by_id = {}
    for record in records:
        by_id.setdefault(record.id, []).append(record)
    out = []
    for group in by_id.values():
        own = [r for r in group if r.branch == f"session/{r.id}"]
        out.extend(own if own else group)
    return out


def find_open(found):
    """(open records, problems) from `(ref, path, text)` tuples. `problems` names each candidate whose frontmatter
    could not be read, so a broken record is reported, never silently skipped."""
    records, problems = [], []
    for ref, path, text in found:
        record, why = read(ref, path, text)
        if record is None:
            problems.append(why)
        else:
            records.append(record)
    still_open = [r for r in _one_per_branch(records) if r.status == "open"]
    ordered = sorted(_one_per_id(still_open), key=lambda r: (r.date, r.id, r.branch or ""))
    return ordered, problems


def pick(records, record_id):
    """The open records with this id (after `find_open`): how the lead's choice after exit 3 is carried out."""
    return [r for r in records if r.id == record_id]


def date_in_words(value, today=None):
    """'2026-10-14' -> '14 October', with the year when it is not `today`'s year; any other text unchanged."""
    try:
        day = datetime.date.fromisoformat(value)
    except (TypeError, ValueError):
        return value or "on a date the record doesn't give"
    words = f"{day.day} {MONTHS[day.month - 1]}"
    return words if today is not None and today.year == day.year else f"{words} {day.year}"
