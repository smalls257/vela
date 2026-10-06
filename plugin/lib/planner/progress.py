"""Where each app stands, and the mode to run next. Pure: the caller passes the date.

One computation feeds `planner status`, `planner next`, `planner query status` and
the `progress-map` block, so they never disagree. The rules are in CONVENTIONS.md
under "Progress and next step", in the order they are tried.
"""
import datetime
import re
from dataclasses import dataclass

from planner import model, override, schema, trace

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


def in_grill_stage(app):
    """GATE-1: an app's item can be grilled once the app is at target or later."""
    stage = text(app.meta.get("stage"))
    order = schema.ENUMS["stage"]
    return stage in order and order.index(stage) >= order.index("target")


def suggest(vault, app, as_of, blocked):
    """(rule number, mode, subject ID, reason) by the first rule that matches."""
    mine = units(vault, app)
    sources = app.meta.get("sources")
    for unknown in model.blocking_unknowns(vault, app):
        if overdue(unknown, as_of):
            return 1, "probe", unknown.id, f"{unknown.id} was due an answer by {unknown.fact('Ask by')} and still blocks {app.id}."
    if not (isinstance(sources, list) and sources):
        return 2, "discover", app.id, f"{app.id} lists no sources."
    for unit in mine:
        if unit.state == "inkling" or (unit.state == "assumption" and not unit.options):
            return 3, "shape", unit.id, f"{unit.id} is at {unit.state} with no options recorded."
    ready = [u for u in mine if u.state == "assumption" and u.options and u.id not in blocked]
    if ready and not in_grill_stage(app):
        stage = text(app.meta.get("stage")) or "no stage"
        return 4, "discover", ready[0].id, f"{ready[0].id} is ready to grill, but {app.id} is at {stage} and a Grill needs target or later."
    if ready:
        return 5, "grill", ready[0].id, f"{ready[0].id} is at assumption with options recorded, and no open unknown blocks it."
    for unit in mine:
        if unit.id in blocked:
            unknown = blocked[unit.id][0]
            return 6, "probe", unknown.id, f"{unknown.id} blocks {unit.id}; its owner is {unknown.fact('Owner') or 'not recorded'}."
    waiting = [c for c in provided(vault, app) + consumed(vault, app) if c.fact("State") not in SETTLED]
    if waiting:
        contract = sorted(waiting, key=lambda c: c.id)[0]
        return 7, "none", contract.id, f"{app.id} waits on {contract.id}, which is at {contract.fact('State') or 'no state'}."
    if app.meta.get("change") not in schema.LADDERED_CHANGES:
        return 9, "none", "", f"{app.id} sits outside the ladder and has nothing open."
    epics = [e for e in trace.epics(vault) if app.id in trace.listed(e, "apps")]
    unsettled = [e for e in epics if e.meta.get("state") != "decided"]
    if not epics:
        return 8, "epics", app.id, f"Every contract {app.id} provides or consumes is decided or fact, and no epic lists it."
    if unsettled:
        return 8, "epics", unsettled[0].id, f"Every contract of {app.id} is settled, and {unsettled[0].id} is {text(unsettled[0].meta.get('state')) or 'without a state'}."
    return 9, "none", "", f"Every item of {app.id} is settled and every epic for it is decided."


def stage_rank(app):
    stage = text(app.meta.get("stage"))
    order = schema.ENUMS["stage"]
    return order.index(stage) if stage in order else len(order)


def grid(vault, as_of):
    """One Row per app page: apps on the ladder by stage, then the rest, each by ID."""
    blocked = model.blockers(vault)
    rows = []
    for app in vault.apps:
        oldest, opened = oldest_unknown(vault, app)
        rule, mode, subject, reason = suggest(vault, app, as_of, blocked)
        stage = text(app.meta.get("stage")) if app.meta.get("change") in schema.LADDERED_CHANGES else ""
        rows.append(Row(app, stage, mix(vault, app), oldest, opened, rule, mode, subject, reason,
                        decided_by_override(vault, app)))
    return sorted(rows, key=lambda r: (not r.stage, stage_rank(r.app), r.app.id))


def decided_text(row):
    """The decided count, with how many came by override: "3 (1 by override)"."""
    decided = row.mix[3]
    return f"{decided} ({row.by_override} by override)" if row.by_override else str(decided)


def best(rows):
    """The single frontier `planner next` names: the lowest rule number, then the earliest stage,
    then the app ID. None when every app's mode is none."""
    open_rows = [r for r in rows if r.mode != "none"]
    if not open_rows:
        return None
    return min(open_rows, key=lambda r: (r.rule, stage_rank(r.app), r.app.id))
