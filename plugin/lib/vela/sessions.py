"""Which session record is open, and on which branch: the pure half of `vela session open` (overhaul Task 6a).

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

Task 6b adds what `vela session start` decides, each rule with the reason START.md gave for it:

- **The id is the date and the topic, and never one already taken.** A second `sessions/<id>.md`, or a branch
  `session/<id>` here or on origin, would put two sessions' captures in one record or one pull request; `-2`, `-3`
  and on are tried until all are free (`new_id`).
- **An answer is found by its PR's exact title suffix.** gh's search for `Challenge: CON-001` also returns
  `Challenge: CON-0010`; an answer opened on the wrong challenge's branch lands its decision in the wrong PR. So only
  a title ending in exactly `Challenge: <ID>` counts, and none or several stops (`challenge_matches`). A PR named by
  number must be open and titled as a challenge is (`challenged_id`). Never a guessed branch.
- **A dirty tree stops only when the pull would overwrite it.** A lead's unsaved edit to a page comes into the
  session unstaged and is said in one clause; only a path the pull changes is a choice that would lose work
  (`clobbered`, `carried`). vela's own `.vela/` output is never a reason and never mentioned.
- **The initiative is named once.** The template's `title: New initiative` heads the dashboard and every reader's
  copy, so it is asked before the first question and written only in the lead's words (`is_unnamed`, `with_title`).
- **A reader copy can't run an owner's mode.** A challenge opens its own pull request and an answer pushes to one;
  a published copy has no git (`OWNER_ONLY`).

Pure: records arrive as `(ref, path, text)`; no disk, git or clock. `edge/sessiongit.py` reads them.
"""
import datetime
import re
from dataclasses import dataclass

from vela import parse, planscope, say, schema

LOCAL, REMOTE, FOLDER = "refs/heads/", "refs/remotes/origin/", ""
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


def _one_per_id(records, scope=""):
    """A record id on several branches is the session on `session/<id>` (`session/<plan>/<id>` in a plan that shares
    its repo, see planscope) when that branch is among them."""
    by_id = {}
    for record in records:
        by_id.setdefault(record.id, []).append(record)
    out = []
    for group in by_id.values():
        own = [r for r in group if r.branch == planscope.session_branch(scope, r.id)]
        out.extend(own if own else group)
    return out


def find_open(found, scope=""):
    """(open records, problems) from `(ref, path, text)` tuples. `scope` is the plan's name when it shares its repo
    with other plans (planscope), "" otherwise. `problems` names each candidate whose frontmatter could not be read,
    so a broken record is reported, never silently skipped."""
    records, problems = [], []
    for ref, path, text in found:
        record, why = read(ref, path, text)
        if record is None:
            problems.append(why)
        else:
            records.append(record)
    still_open = [r for r in _one_per_branch(records) if r.status == "open"]
    ordered = sorted(_one_per_id(still_open, scope), key=lambda r: (r.date, r.id, r.branch or ""))
    return ordered, problems


def pick(records, record_id):
    """The open records with this id (after `find_open`): how the lead's choice after exit 3 is carried out."""
    return [r for r in records if r.id == record_id]


def date_in_words(value, today=None):
    """'2026-10-14' -> 'October 14', with the year when it is not `today`'s year; any other text unchanged."""
    if not (isinstance(value, str) and re.fullmatch(r"\d{4}-\d{2}-\d{2}", value)):
        return value or "on a date the record doesn't give"
    return say.date_words(value, today)


# The display names MODES.md gives each mode, used in a record's title ("Grill: consent").
MODE_NAMES = {"dump": "Dump & Diverge", "discover": "Discover", "shape": "Shape", "boundary": "Boundary",
              "allocate": "Allocate", "releases": "Releases", "grill": "Grill", "requirements": "Requirements",
              "epics": "Epics", "challenge": "Challenge", "answer": "Answer"}
OWNER_ONLY = ("challenge", "answer")  # each opens or pushes to a pull request, which a published copy can't
STALE_DAYS = 14  # START step 2: an open record older than this is said to be old
NAMING_QUESTION = "What short name should this initiative go by? A few words, as you would say it to a colleague."
_CHALLENGE_TITLE = re.compile(r"^\d{4}-\d{2}-\d{2}\b.*\bChallenge: (?P<id>\S+)$")
_NOT_SLUG = re.compile(r"[^a-z0-9]+")


def slug(words):
    return _NOT_SLUG.sub("-", words.lower()).strip("-")


def _free(base, taken):
    candidate, n = base, 1
    while taken(candidate):
        n += 1
        candidate = f"{base}-{n}"
    return candidate


def new_id(today, topic, taken):
    """`<today>-<topic slug>`, with `-2`, `-3` and on until `taken(id)` is false. Raises ValueError for a topic with
    no letters or digits, since an id of only the date would collide with every other topicless session."""
    words = slug(topic)
    if not words:
        raise ValueError(f"the topic '{topic}' has no letters or digits to name the session by")
    return _free(f"{today}-{words}", taken)


def answer_id(today, challenged, taken):
    """`<today>-answer-<id lower-cased>`, as ANSWER-A-CHALLENGE.md names an answer session."""
    return _free(f"{today}-answer-{slug(challenged)}", taken)


def challenged_id(pr):
    """The id a PR named by number challenges, or None when it isn't an open challenge PR: its title starts with a
    date and ends `Challenge: <id>`, and gh says it is OPEN."""
    match = _CHALLENGE_TITLE.match(str(pr.get("title", "")))
    if not match or str(pr.get("state", "")).upper() != "OPEN":
        return None
    return match.group("id")


def challenge_matches(prs, challenged):
    """The PRs whose title ends with exactly `Challenge: <id>` (gh's search matches longer ids too)."""
    out = []
    for pr in prs:
        match = _CHALLENGE_TITLE.match(str(pr.get("title", "")))
        if match and match.group("id") == challenged:
            out.append(pr)
    return out


def is_tool_state(path):
    """True for a vault-relative path under `.vela/`, the tool's working state on this machine."""
    return path == ".vela" or path.startswith(".vela/")


_own = is_tool_state


def clobbered(dirty, incoming):
    """The uncommitted paths the switch to main and the pull would overwrite: the ones that need the lead."""
    coming = set(incoming)
    return [path for path in dirty if path in coming and not _own(path)]


def carried(dirty, incoming):
    """The uncommitted paths that come into the session unstaged, to say in one clause."""
    coming = set(incoming)
    return [path for path in dirty if path not in coming and not _own(path)]


def is_unnamed(config):
    """True while `.vela.yaml` keeps the title the template ships (W718)."""
    return str(config.get("title", "")).strip() == schema.PLACEHOLDER_TITLE


def with_title(yaml_text, title):
    """`.vela.yaml` with its `title:` line set to `title`, every other line kept as written, comments too."""
    line = "title: " + '"' + title.replace("\\", "\\\\").replace('"', '\\"') + '"'
    lines = yaml_text.split("\n")
    for i, row in enumerate(lines):
        if row.startswith("title:"):
            lines[i] = line
            return "\n".join(lines)
    body = yaml_text if (yaml_text.endswith("\n") or not yaml_text) else yaml_text + "\n"
    return body + line + "\n"


def title_for(modes, topic, challenged=""):
    """`<Mode name>: <topic>`, or `Answer: <ID>` for an answer session."""
    if challenged:
        return f"Answer: {challenged}"
    return f"{MODE_NAMES.get(modes[0], modes[0].capitalize())}: {topic.strip()}"


def record_text(record_id, title, today, modes):
    """A new session record, in the form START step 5 gives."""
    quoted = title.replace("\\", "\\\\").replace('"', '\\"')
    return (f"---\nid: {record_id}\ntype: session\ntitle: \"{quoted}\"\ndate: {today}\nmodes: [{', '.join(modes)}]\n"
            f"status: open\nsummary: In progress.\n---\n\n# {today} {title}\n\n## Captures\n\n## Changes\n\n"
            "| ID | From | To | Source |\n|---|---|---|---|\n")


def last_closed(metas):
    """The highest `date:` among closed session records (frontmatter dicts), or "" when none is closed: the day
    from which merged session PRs may carry review comments nobody brought in yet (START step 3)."""
    dates = [str(m.get("date", "")) for m in metas if m.get("status") == "closed"]
    return max((d for d in dates if re.match(r"^\d{4}-\d{2}-\d{2}$", d)), default="")


def _login(entry, key):
    who = entry.get(key) if isinstance(entry, dict) else None
    return str(who.get("login", "")) if isinstance(who, dict) else ""


def review_candidates(pr, view, line_comments):
    """Every non-empty comment on one merged PR, as a candidate capture with its author as the origin: the PR's
    conversation comments, the review bodies, then the line comments. A review with no body (a bare approval) is
    nothing to capture."""
    base = {"pr": pr.get("number"), "pr_title": pr.get("title", ""), "url": pr.get("url", "")}
    out = []
    view = view if isinstance(view, dict) else {}
    for kind, entries, key in (("comment", view.get("comments"), "author"), ("review", view.get("reviews"), "author"),
                               ("line", line_comments, "user")):
        for entry in entries if isinstance(entries, list) else []:
            body = str(entry.get("body") or "").strip() if isinstance(entry, dict) else ""
            if body:
                out.append({**base, "kind": kind, "author": _login(entry, key), "body": body,
                            "path": entry.get("path", "")})
    return out


def is_stale(record, today):
    """True for an open record started more than STALE_DAYS before `today` (a date)."""
    try:
        started = datetime.date.fromisoformat(record.date)
    except (TypeError, ValueError):
        return False
    return (today - started).days > STALE_DAYS
