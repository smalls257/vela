"""Where each app stands, and the mode to run next. Pure: the caller passes the date.

One computation feeds `vela status`, `vela next`, `vela query status` and
the `progress-map` block, so they never disagree. The rules are in CONVENTIONS.md
under "Progress and next step", in the order they are tried.
"""
import datetime
import re
from dataclasses import dataclass

from vela import ladder, model, override, schema, sizing, trace

OPENED_DATE = re.compile(r"^(\d{4}-\d{2}-\d{2})\b")
SETTLED = ("decided", "fact")


@dataclass(frozen=True)
class Unit:
    """Something of the app's that carries a state: its pages and the contracts on its page."""
    id: str
    state: str
    options: bool  # an **Options considered:** bullet is recorded
    overridden: bool = False  # a well-formed **Override:** sits on it


@dataclass(frozen=True)
class Row:
    app: object  # the app's building-blocks page
    stage: str  # "" outside the ladder
    mix: tuple  # counts at inkling, assumption, fact and decided, in that order
    oldest: object  # the open unknown that blocks the app and was opened first, or None
    opened: str  # its Opened date, "" when none is recorded
    rule: int  # the number of the rule that chose the mode, see RULES
    mode: str  # one of schema.NEXT_MODES
    subject: str  # the ID the suggestion is about
    reason: str  # one sentence
    by_override: int = 0  # how many of the decided count were decided by override


def text(value):
    return value.strip() if isinstance(value, str) else ""


def is_date(value):
    if not isinstance(value, str) or not schema.DATE_RE.match(value):
        return False
    try:
        datetime.date.fromisoformat(value)
    except ValueError:
        return False
    return True


def opened_date(unknown):
    """The YYYY-MM-DD an **Opened:** bullet starts with, or ""."""
    match = OPENED_DATE.match(unknown.fact("Opened"))
    return match.group(1) if match and is_date(match.group(1)) else ""


def last_session_date(vault):
    """The latest valid session date, or "" when the vault has no session yet."""
    dates = [s.meta.get("date") for s in vault.sessions]
    return max((d for d in dates if is_date(d)), default="")


def runtime_page(vault, app):
    if not app.name.endswith("-building-blocks"):
        return None
    page = vault.page(app.name[: -len("-building-blocks")] + "-runtime")
    return page if page is not None and page.type == "app-runtime" else None


def provided(vault, app):
    """Contracts that live on the app's page, including one kept there for an external provider."""
    return [c for c in vault.contracts if c.page is app]


def consumed(vault, app):
    return [c for c in vault.contracts if c.page is not app and app in vault.consumers(c)]


def units(vault, app):
    """The app page, its runtime page, then the contracts on its page by ID."""
    pages = [p for p in (app, runtime_page(vault, app)) if p is not None]
    out = [Unit(p.id, text(p.meta.get("state")), bool(p.page_bullets(schema.OPTIONS_LABEL)),
                bool(override.valid_overrides(p))) for p in pages]
    out += [Unit(c.id, c.fact("State"), schema.OPTIONS_LABEL in c.facts, bool(override.valid_overrides(c.page, c.id)))
            for c in provided(vault, app)]
    return out


def mix(vault, app):
    states = [u.state for u in units(vault, app)]
    return tuple(states.count(s) for s in schema.STATE_ITEM)


def decided_by_override(vault, app):
    """Decided units that carry an Override. They count as decided, and the grid says how many."""
    return sum(1 for u in units(vault, app) if u.state == "decided" and u.overridden)


def oldest_unknown(vault, app):
    """(unknown, opened date) for the open unknown that blocks the app and was opened first."""
    found = model.blocking_unknowns(vault, app)
    if not found:
        return None, ""
    first = min(found, key=lambda u: (opened_date(u) or "9999-99-99", u.id))
    return first, opened_date(first)


def overdue(unknown, as_of):
    ask_by = unknown.fact("Ask by")
    return bool(as_of) and is_date(ask_by) and ask_by < as_of


def in_grill_stage(vault, app):
    """GATE-1: an app's item can be grilled once its pages reach target or later."""
    reached = ladder.stage(vault, app)
    return bool(reached) and ladder.rank(reached) >= ladder.rank("target")


def is_boundary_stub(app):
    """A page a Boundary wrote as a stub and has not read back yet: its `stub: boundary` field, and no containers
    table. The field, not any sentence on the page, because a model rewrites sentences."""
    return (app.meta.get("stub") == "boundary"
            and not any(t.header[:2] == schema.CONTAINERS_HEADER for t in app.tables))


def suggest(vault, app, as_of, blocked):
    """(rule number, mode, subject ID, reason) by the first rule that matches."""
    mine = units(vault, app)
    sources = app.meta.get("sources")
    named, app_name = vault.named, vault.name_of(app.id)
    for unknown in model.blocking_unknowns(vault, app):
        if overdue(unknown, as_of):
            return 1, "probe", unknown.id, f"The open question {named(unknown.id)} was due an answer by {unknown.fact('Ask by')} and still holds up {app_name}."
    if is_boundary_stub(app):
        return 2, "boundary", app.id, f"{app_name} has only a placeholder page: its parts and edges haven't been read back to the lead yet."
    if not (isinstance(sources, list) and sources):
        return 2, "discover", app.id, f"{app_name} lists no sources yet."
    laddered = app.meta.get("change") in schema.LADDERED_CHANGES
    for unit in mine:
        # An integrated or unchanged app's page records what exists; there are no options to shape for it.
        if not laddered and unit.state in ("inkling", "assumption") and unit.id not in blocked:
            return 3, "discover", unit.id, (f"{named(unit.id)} {handoffwarn_phrase(unit.state)}, and {app_name} isn't being changed, so it "
                                            f"needs a source that shows it as fact.")
        if laddered and (unit.state == "inkling" or (unit.state == "assumption" and not unit.options)):
            if sizing.of(vault).needs(sizing.Need.OPTIONS_BEFORE_GRILL):
                return 3, "shape", unit.id, f"{named(unit.id)} {handoffwarn_phrase(unit.state)} and has no options written down."
            return 3, "grill", unit.id, (f"{named(unit.id)} {handoffwarn_phrase(unit.state)}, and nobody has said yet whether anything "
                                         "else was on the table; one question in a grill settles that.")
    ready = [u for u in mine if u.state == "assumption" and u.options and u.id not in blocked]
    if ready and not in_grill_stage(vault, app):
        stage = ladder.stage(vault, app) or "no stage"
        return 4, "discover", ready[0].id, f"{named(ready[0].id)} is ready to decide, but {app_name} is still at the {stage} stage; a grill needs the app at target or later."
    if ready:
        return 5, "grill", ready[0].id, f"{named(ready[0].id)} is not decided yet; its options are written down and no open question holds it up."
    for unit in mine:
        if unit.id in blocked:
            unknown = blocked[unit.id][0]
            return 6, "probe", unknown.id, (f"The open question {named(unknown.id)} holds up {named(unit.id)}; "
                                         + (f"ask {unknown.fact('Owner')}." if unknown.fact('Owner') else "nobody is named to answer it."))
    waiting = [c for c in provided(vault, app) + consumed(vault, app) if c.fact("State") not in SETTLED]
    if waiting:
        contract = sorted(waiting, key=lambda c: c.id)[0]
        return 7, "none", contract.id, f"{app_name} waits on {named(contract.id)}, which {handoffwarn_phrase(contract.fact('State')) if contract.fact('State') else 'has no state yet'}."
    if app.meta.get("change") not in schema.LADDERED_CHANGES:
        return 9, "none", "", f"{app_name} isn't being built or changed, and has nothing open."
    epics = [e for e in trace.epics(vault) if app.id in trace.listed(e, "apps")]
    unsettled = [e for e in epics if e.meta.get("state") != "decided"]
    if not epics:
        return 8, "epics", app.id, f"Every interface {app_name} offers or uses is settled, and no epic covers the app yet."
    if unsettled:
        return 8, "epics", unsettled[0].id, f"Every interface of {app_name} is settled, and the epic {named(unsettled[0].id)} {handoffwarn_phrase(text(unsettled[0].meta.get('state'))) if text(unsettled[0].meta.get('state')) else 'has no state yet'}."
    return 9, "none", "", f"Everything in {app_name} is settled and every epic for it is decided."


# How a state reads in a sentence; the same words handoffwarn uses (imported late: handoffwarn imports this module).
def handoffwarn_phrase(state):
    from vela import handoffwarn
    return handoffwarn.state_phrase(state)


def stage_rank(vault, app):
    return ladder.rank(ladder.stage(vault, app))


def grid(vault, as_of):
    """One Row per app page: apps on the ladder by stage, then the rest, each by ID."""
    blocked = model.blockers(vault)
    rows = []
    for app in vault.apps:
        oldest, opened = oldest_unknown(vault, app)
        rule, mode, subject, reason = suggest(vault, app, as_of, blocked)
        stage = ladder.stage(vault, app)
        rows.append(Row(app, stage, mix(vault, app), oldest, opened, rule, mode, subject, reason,
                        decided_by_override(vault, app)))
    return sorted(rows, key=lambda r: (not r.stage, stage_rank(vault, r.app), r.app.id))


def decided_text(row):
    """The decided count, with how many came by override: "3 (1 by override)"."""
    decided = row.mix[3]
    return f"{decided} ({row.by_override} by override)" if row.by_override else str(decided)


def best(rows):
    """The single frontier `vela next` names: the lowest rule number, then the earliest stage,
    then the app ID. None when every app's mode is none."""
    open_rows = [r for r in rows if r.mode != "none"]
    if not open_rows:
        return None
    return min(open_rows, key=lambda r: (r.rule, ladder.rank(r.stage), r.app.id))
