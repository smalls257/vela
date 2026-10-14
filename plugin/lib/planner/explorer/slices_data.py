"""The Slices view's data, from `slices.read_slices` and nothing else: one reader of a slice, so the dashboard can never
show a slice differently from check, check-slice, the handoff and planner next.

Each slice carries its status (one of the five, or "" for not planned yet), the flows it proves (with the key that opens
each flow), the joins it crosses (with the key that opens each contract), what it comes after, and the facts its page
writes. A vault with no slice pages still shows its slices, read from the releases page, and says so (`onPages`).
"""
from planner import releases, slices

from .record import inline_html, plain


def left_out(found):
    return [{"text": plain(left.text), "ids": list(left.ids), "reason": plain(left.reason)} for left in found]


def extract(vault, keys):
    found = slices.read_slices(vault)
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
            "joins": [{"id": c, "key": c if c in contracts else ""} for c in s.joins],
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
