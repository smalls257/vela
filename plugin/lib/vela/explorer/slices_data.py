"""The Slices view's data, from `slices.read_slices` and nothing else: one reader of a slice, so the dashboard can never
show a slice differently from check, check-slice, the handoff and planner next.

Each slice carries its status (one of the five, or "" for not planned yet), the flows it proves (with the key that opens
each flow), the joins its flows cross with both sides (with the key that opens each contract), what it comes after, the
apps that take part in it (`slices.taking_part`, the handoff's rule), its journey or the date it is due and whether that
date has passed with nothing recorded (`slices.journey_overdue`, the rule check's W400 and the Needs-you light use), its
flow check's state and overrides (`flowcheck.verdicts.state`, the same run check judges), and the facts its page writes.
A vault with no slice pages still shows its slices, read from the releases page, and says so (`onPages`).
"""
from vela import releases, slices
from vela.flowcheck import readers, verdicts

from .record import inline_html, plain

# The budget check itself gives each slice (cli.CHECK_SLICE_STATES): the dashboard shows the state check reports.
CHECK_STATES = 20_000


def left_out(found):
    return [{"text": plain(left.text), "ids": list(left.ids), "reason": plain(left.reason)} for left in found]


def flow_check(vault, found, today, specs):
    """{slice key: verdicts.state} for every slice, from one catalog read."""
    catalog = readers.read_catalog(vault, specs)
    by_key = {s.key: s for s in catalog.slices}
    out = {s.key: verdicts.state(catalog, by_key[s.key], today, CHECK_STATES) for s in found if s.key in by_key}
    for state in out.values():
        for o in state["overrides"]:
            o["text"] = plain(o["text"])
    return out


def recorded_words(found):
    """A `flowcheck.standing.Standing` as the page shows it; None when no standing was read for the slice."""
    if found is None:
        return None
    return {"state": found.state, "words": found.words, "checked": found.checked, "open": list(found.open), "why": found.why,
            "line": found.line(), "passed": found.passed}


def extract(vault, keys, today, specs=None, recorded=None):
    """The Slices view's data. `recorded` is {slice key: flowcheck.standing.Standing}, the last full flow check as
    recorded (the dashboard never reads the record itself); a slice with none reads "not checked"."""
    found = slices.read_slices(vault)
    part = slices.taking_part(vault, found)
    app_key = {a.id: keys.page(a) for a in vault.apps}
    checks = flow_check(vault, found, today, specs or {})
    tracer = slices.tracer(found)
    flow_key = {p.id: keys.page(p) for p in vault.of_type("flow")}
    page_of = {p.path: p for p in slices.pages(vault)}
    contracts = {c.id for c in vault.contracts}
    marked = slices.milestones(vault)
    circled = {k for circle in slices.cycles(found) for k in circle}
    rel = releases.page(vault)
    rows = []
    for s in found:
        page = page_of.get(s.path)
        journey = None
        if s.journey is not None:
            journey = {"date": s.journey.date, "by": s.journey.by, "problem": s.journey.problem,
                       "html": inline_html(s.journey.evidence, keys, page) if page is not None and not s.journey.problem else ""}
        rows.append({
            "key": keys.page(page) if page is not None else "", "id": s.id, "name": s.name, "label": s.label, "slice": s.key,
            "status": s.status, "statusRaw": s.status_raw, "order": s.order, "tracer": s is tracer,
            "flows": [{"id": f, "key": flow_key.get(f, "")} for f in s.flows],
            "joins": [{"id": c, "key": c if c in contracts else "", "from": sender, "to": receiver} for c, sender, receiver in s.sides],
            "apps": [app_key[a] for a in part.get(s.key, [])],
            "journeyDue": s.journey_due, "overdue": slices.journey_overdue_says(s) if slices.journey_overdue(s, today) else "",
            "check": checks.get(s.key),
            "recorded": recorded_words((recorded or {}).get(s.key)) if recorded is not None else None,
            "after": list(s.after), "circled": s.key in circled,
            "owner": s.owner, "doneWhen": plain(s.done_when), "shipsOff": plain(s.ships_off), "milestone": plain(s.milestone),
            "milestones": [r.name for r in marked.get(s.id, [])], "journey": journey, "notIn": left_out(s.not_in),
            "flowsNone": s.flows_none, "page": keys.page(rel) if rel is not None and page is None else ""})
    return {"statuses": list(slices.STATUSES), "list": rows, "onPages": slices.on_pages(vault)}


def tracer_data(vault, first):
    """The tracer for the flow views, the release card and the build plan: the tracer slice's flows (slices.tracer), with
    release one's own words while the vault still names its slices there. None when there is no tracer and no release."""
    t = slices.tracer(slices.read_slices(vault))
    if t is not None and not t.from_page and (first is None or t.name != first.name):
        t = None  # read from the releases page, only release one's Tracer is the tracer; a later release's Flows is not
    if t is None:
        if first is None:
            return None
        return {"given": first.tracer_given, "flows": [], "words": first.tracer_words, "none": first.tracer_none,
                "notIn": left_out(first.not_in_tracer), "slice": "", "name": ""}
    legacy = not t.from_page and first is not None
    return {"given": True, "flows": list(t.flows), "words": first.tracer_words if legacy else t.name,
            "none": t.flows_none, "notIn": left_out(t.not_in), "slice": t.id, "name": t.name}
