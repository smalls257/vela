"""What `vela close finish` does, in order, decided before anything is written (overhaul Task 11). Pure.

The Violation this module's shape prevents is a Distributed Monolith of order: close's "Check, then finish and send" (status closed, then
the close commit, then the handoff manifest, then the manifest's own commit) and section 9 (rebuild the dashboard, then
commit it alone) were sentences a model followed in three skills, and nothing stopped it writing the manifest before
the commit it is meant to name. Here the order is one tuple, `STEPS`, built by `plan`, and the command walks it (Shield).
Each rule keeps its reason:

- **The close commit comes first**, so the handoff manifest's `Commit` line names a commit that holds the session's
  work, and not "with uncommitted changes" (close's "Check, then finish and send").
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
from dataclasses import dataclass

from vela import closegate, privaterecord, schema

CLOSE_MESSAGE = "Close session {id}"
MANIFEST_MESSAGE = "Handoff manifest for {app}"
DASHBOARD_MESSAGE = "Rebuild dashboard"
MESSAGES = (CLOSE_MESSAGE, MANIFEST_MESSAGE, DASHBOARD_MESSAGE)
DASHBOARD = "dashboard.html"

# Steps, in the only order they run.
RECORD, CLOSE_COMMIT, MANIFEST, DASHBOARD_BUILD, DASHBOARD_COMMIT = (
    "record", "close-commit", "manifest", "dashboard", "dashboard-commit")

# What the lead hears. The dashboard lines are the one copy of the sentence three skills used to carry.
DASHBOARD_DONE = "The dashboard is up to date; /vela:explore opens it."  # voice audit row 162: no file name
DASHBOARD_FAILED = "The dashboard couldn't be updated: {message}. Everything else is filed."
DASHBOARD_PUT_BACK = "I've left the dashboard as it was. It'll be brought up to date when you next finish a session."
NOT_SETTLED_HEAD ="Not settled at handoff for {app}, so its team should hear this before they accept it:"
READER_NOTHING_COMMITTED = ("This is your copy, so I've closed your session record here and committed nothing. "
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


def closed_stub(stub_text):
    """The committed stub with `status: closed`. The summary goes in the private file (`privaterecord.with_summary`),
    so the committed header never carries the lead's words."""
    try:
        return privaterecord.with_status(stub_text, "closed")
    except ValueError as exc:
        raise SummaryRefused("the session record's frontmatter would not read after closing it") from exc


def handed_off(vault):
    """{app id: the `handed_off` value as written} for every app page, "" when it has none."""
    return {app.id: str(app.meta.get("handed_off") or "").strip() for app in vault.apps}


def handoffs_due(before, after):
    """App ids whose `handed_off` this session set or changed (and did not clear), in id order."""
    return tuple(sorted(app for app, value in after.items() if value and before.get(app, "") != value))


def _who(origin):
    return origin.strip().lstrip("@").strip().lower()


def team_names(app_meta):
    """Who the vault names as the app's team: its `owner`, and the person in its `handed_off` (`<name>, <date>`)."""
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
