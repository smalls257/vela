"""What `vela close finish` does, in order, decided before anything is written (overhaul Task 11). Pure.

The Violation this module's shape prevents is a Distributed Monolith of order: close section 7 (status closed, then
the close commit, then the handoff manifest, then the manifest's own commit) and section 9 (rebuild the dashboard, then
commit it alone) were sentences a model followed in three skills, and nothing stopped it writing the manifest before
the commit it is meant to name. Here the order is one tuple, `STEPS`, built by `plan`, and the command walks it (Shield).
Each rule keeps its reason:

- **The close commit comes first**, so the handoff manifest's `Commit` line names a commit that holds the session's
  work, and not "with uncommitted changes" (close section 7).
- **The manifest is committed alone**, `Handoff manifest for <APP-id>`, so the team's review of what they take on is
  one commit they can read by itself.
- **An existing manifest is the one the app's team accepted.** Replacing it needs `--replace` *and* a yes from that
  team in this session's record: a capture whose origin is a person the vault names as the app's team (its `owner`,
  or the name in its `handed_off`), not a bare "ok". Without both, nothing at all is written (exit 3), because a
  close that commits and then stops halfway would leave the lead a half-filed session. The check happens in `plan`,
  before the first write, for that reason.
- **The dashboard is rebuilt last and committed alone** (`Rebuild dashboard`), since it shows what the commits hold.
  A dashboard that fails to build never undoes the close: the close's work is filed, and the lead hears the failure
  in plain words ("The dashboard couldn't be updated: ..."), never "up to date".
- **A reader copy runs no git**: it writes the record (summary, `status: closed`) and rebuilds the dashboard on that
  machine, and says that nothing was committed. The owner gets the record through a proposal.

The shell (`commands/close_finish.py`) gathers the facts and runs each step through the public command that owns it
(`close stage --close`, `vela handoff`, `vela explore`); this module never touches git, the disk or the clock.
"""
import json
import re
from dataclasses import dataclass

from vela import closegate, parse, schema

CLOSE_MESSAGE = "Close session {id}"
MANIFEST_MESSAGE = "Handoff manifest for {app}"
DASHBOARD_MESSAGE = "Rebuild dashboard"
MESSAGES = (CLOSE_MESSAGE, MANIFEST_MESSAGE, DASHBOARD_MESSAGE)
DASHBOARD = "dashboard.html"

# Steps, in the only order they run.
RECORD, CLOSE_COMMIT, MANIFEST, DASHBOARD_BUILD, DASHBOARD_COMMIT = (
    "record", "close-commit", "manifest", "dashboard", "dashboard-commit")

# What the lead hears. The dashboard lines are the one copy of the sentence three skills used to carry.
DASHBOARD_DONE = ("The dashboard is up to date. Open dashboard.html in this folder, or run /vela:explore to open it "
                  "with a box where you can ask Claude about it.")
DASHBOARD_FAILED = "The dashboard couldn't be updated: {message}. Everything else is filed."
NO_SESSION_DASHBOARD = ("I've updated the dashboard on your machine only, since no session is open. It'll be shared "
                        "next time you finish a session, or I can put it on its own branch.")
NOT_SETTLED_HEAD = "Not settled at handoff for {app}, so its team should hear this before they accept it:"
READER_NOTHING_COMMITTED = ("This is a read copy, so I've closed your session record here and committed nothing. "
                            "It reaches the owner through a proposal.")


class SummaryRefused(ValueError):
    """The `--summary` given can't be stored as the record's one line."""


@dataclass(frozen=True)
class Handoff:
    """One app whose `handed_off` this session changed: the manifest close writes after the close commit."""
    app: str
    name: str
    exists: bool  # handoffs/<app>.md is already there: the one its team accepted
    team_yes: object = None  # the closegate.Capture holding the team's yes, or None


@dataclass(frozen=True)
class Plan:
    """The steps to run, in order, or what the lead must choose first (`needs_lead`; then `steps` is empty)."""
    steps: tuple  # (step, argument) pairs; argument is the app id for MANIFEST, else ""
    needs_lead: tuple = ()  # (app, plain sentence)
    replace: tuple = ()  # apps whose manifest is replaced (`vela handoff --replace`)


def checked_summary(summary):
    """The summary as it will be stored: one line, not empty, not the record's placeholder."""
    text = (summary or "").strip()
    if not text or "\n" in text or "\r" in text:
        raise SummaryRefused("--summary takes one line of plain words, saying what the session did.")
    if text == "In progress.":
        raise SummaryRefused("--summary still says 'In progress.', the line the record opened with; write what the "
                             "session did.")
    return text


def with_closed(record_text, summary):
    """The record with `status: closed` and `summary: <summary>` in its frontmatter (each added when missing). The
    summary is written as a double-quoted YAML scalar (JSON's string form is one), so a colon in it can't break YAML."""
    lines = record_text.split("\n")
    if not lines or lines[0].strip() != "---":
        raise SummaryRefused("the session record has no frontmatter block to close")
    end = next((i for i in range(1, len(lines)) if lines[i].strip() == "---"), None)
    if end is None:
        raise SummaryRefused("the session record's frontmatter block never ends")
    fields = {"status": "closed", "summary": json.dumps(checked_summary(summary), ensure_ascii=False)}
    head = lines[1:end]
    for key, value in fields.items():
        found = [i for i, line in enumerate(head) if re.match(rf"^{key}\s*:", line)]
        if found:
            head[found[0]] = f"{key}: {value}"
        else:
            head.append(f"{key}: {value}")
    text = "\n".join([lines[0], *head, *lines[end:]])
    meta, _, error = parse.split_frontmatter(text)
    if error is not None or meta.get("status") != "closed":
        raise SummaryRefused("the session record's frontmatter would not read after closing it")
    return text


def handed_off(vault):
    """{app id: the `handed_off` value as written} for every app page, "" when it has none."""
    return {app.id: str(app.meta.get("handed_off") or "").strip() for app in vault.apps}


def handoffs_due(before, after):
    """App ids whose `handed_off` this session set or changed (and did not clear), in id order."""
    return tuple(sorted(app for app, value in after.items() if value and before.get(app, "") != value))


def _who(origin):
    return origin.strip().lstrip("@").strip().lower()


def team_names(app_meta):
    """Who the vault names as the app's team: its `owner`, and the person in its `handed_off` (`<name>, <date>, PR`)."""
    names = {_who(str(app_meta.get("owner") or ""))}
    value = str(app_meta.get("handed_off") or "")
    if schema.HANDED_OFF_RE.match(value):
        names.add(_who(value.split(",", 1)[0]))
    return {n for n in names if n}


def team_yes(record_text, app_meta):
    """The capture in the record where the app's team said yes in their own words, or None. A person's origin, one
    of the team's names, and not a bare non-yes ("ok", "sure": START already says those are not a yes)."""
    names = team_names(app_meta)
    for capture in closegate.captures(record_text).values():
        if capture.is_person and _who(capture.origin) in names and not capture.is_bare_non_yes:
            return capture
    return None


def plan(reader, handoffs, replace):
    """The finish, in order. `handoffs` are the Handoffs this session made due; `replace` is whether `--replace` was
    given. Pure, and decided before anything is written, so an exit 3 changes nothing."""
    if reader:
        return Plan(((RECORD, ""), (DASHBOARD_BUILD, "")))
    asks, replaced = [], []
    for due in handoffs:
        if not due.exists:
            continue
        if not replace:
            asks.append((due.app, f"{due.name} already has a handoff record, the one its team accepted. I'll replace "
                                  "it only once they agree to the changes; then finish again with --replace."))
        elif due.team_yes is None:
            asks.append((due.app, f"Replacing {due.name}'s handoff record needs its team's own yes in this session's "
                                  "record, and there isn't one yet. Capture what they say, with them as the origin."))
        else:
            replaced.append(due.app)
    if asks:
        return Plan((), tuple(asks))
    steps = [(RECORD, ""), (CLOSE_COMMIT, "")] + [(MANIFEST, due.app) for due in handoffs]
    steps += [(DASHBOARD_BUILD, ""), (DASHBOARD_COMMIT, "")]
    return Plan(tuple(steps), (), tuple(replaced))
