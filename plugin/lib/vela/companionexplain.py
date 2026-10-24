"""One plan question, answered from the digest: a closed list of views, vela's own numbers, and what the plan doesn't
know. Pure.

Why a closed list: Claude used to answer "what's stuck?" by counting what it read, which sounds right and is not the
dashboard's count (a Paper Tiger). Here each view is a function of the digest, so the headline Claude repeats word for
word and the panel beside it can never disagree. Why "not recorded": silence is not good news. Every view names what
the plan does not know, so a director never reads "nothing stuck" as "the teams are fine".
"""
import datetime
import difflib
import re
from dataclasses import dataclass

from vela import companionsvg, say

VERSION = 1
VIEWS = ("track", "stuck", "needs", "left", "who", "flow", "page", "none")  # closed: a view not here is refused
NOT_RECORDED = {
    "track": "The plan doesn't track build progress; the team leads do.",
    "stuck": "Not in the plan: how far the teams have built. Ask the team leads for that.",
    "needs": "The plan only knows what was asked of you in it; anything asked in a meeting isn't here.",
    "left": "Story and task progress isn't in the plan; tickets go out to Jira and nothing comes back.",
    "who": "Only questions written into the plan are here.",
    "flow": "", "page": "", "none": ""}
NO_VIEW = "No view for this one. Ask it in the dashboard?"
NEEDS_WHO = "Who are you in the plan? Your GitHub name will do."
STATE_WORDS = {"decided": "decided", "assumption": "not decided yet", "inkling": "an early idea", "fact": "confirmed"}
ROUTES = {"track": "#slices", "stuck": "#asks", "needs": "#needs", "left": "#progress", "who": "#asks",
          "flow": "#flows", "page": "", "none": ""}
LIST_LIMIT = 4


@dataclass(frozen=True)
class Viewer:
    handle: str  # "@hl-director", "" when unknown
    role: str    # the onboarding audience, "" when none


class Unknown(Exception):
    """`about` names nothing; `matches` are the closest names, so Claude can ask which one was meant."""

    def __init__(self, about, matches):
        super().__init__(f"The plan has nothing called that: {about}")
        self.about, self.matches = about, list(matches)


class NeedsViewer(Exception):
    """The needs view is about one person and nobody has said who."""


def count_words(n, one, many):
    return f"{n} {one if n == 1 else many}"


def date_words(value, today):
    return say.date_words(value, datetime.date.fromisoformat(today))


def days_out(target, today):
    return (datetime.date.fromisoformat(target) - datetime.date.fromisoformat(today)).days


def ask_item(ask):
    return {"id": ask["id"], "name": ask["name"], "who": ask["who"], "open_days": ask["open_days"],
            "ask_by": ask["ask_by"], "holds": ask["holds"], "light": ask["light"]}


def verdict(digest, release, today):
    """Never "on track": the plan can only say a date passed with nothing recorded, or what could make it late."""
    if any(s["overdue"] for s in digest["slices"]):
        return "Late: a due date passed with nothing recorded."
    could = len(digest["stuck"])
    if could:
        return f"{count_words(could, 'thing', 'things')} could make it late."
    return "Nothing in the plan says it's late."


def view_track(digest, about, viewer, today):
    dated = [r for r in digest["releases"] if r["target"]]
    if not dated:
        return ["No release has a date yet."], [], []
    release = dated[0]
    out = days_out(release["target"], today)
    when = f"{out} days out" if out >= 0 else f"{-out} days ago"
    headline = [f"{release['name']} is due {date_words(release['target'], today)}, {when}."]
    slices = digest["slices"]
    if slices:
        building = [s for s in slices if s["status"] != "planned"]
        planned = len(slices) - len(building)
        headline.append(f"{len(building)} of {len(slices)} slices {'is' if len(building) == 1 else 'are'} building and "
                        f"{planned} {'is' if planned == 1 else 'are'} only planned.")
    headline.append(verdict(digest, release, today))
    items = [{"id": release["name"], "name": release["name"], "target": release["target"], "days_out": out}]
    items += [{"id": s["key"], "name": s["name"], "status": s["status"], "overdue": s["overdue"]} for s in slices]
    return headline, items, []


def view_stuck(digest, about, viewer, today):
    stuck = digest["stuck"]
    if not stuck:
        return ["Nothing is stuck."], [], []
    headline = [f"{count_words(len(stuck), 'thing is', 'things are')} stuck."]
    waited = [a["open_days"] for a in stuck if a["open_days"] is not None]
    if waited:
        headline.append(f"The oldest has waited {max(waited)} days.")
    mine = [a for a in stuck if viewer.handle and a["who_key"] == viewer.handle]
    if mine:
        headline.append(f"{len(mine)} is waiting on you." if len(mine) == 1 else f"{len(mine)} are waiting on you.")
    return headline, [ask_item(a) for a in stuck], by_holder(stuck)


def by_holder(asks):
    groups = {}
    for ask in asks:
        groups.setdefault(ask["who"], []).append(ask_item(ask))
    return [{"who": who, "items": items} for who, items in groups.items()]


def need_words(line, today):
    base = f"A yes on {line['name']}"
    return f"{base} by {date_words(line['date'], today)}." if line["date"] else f"{base}."


def view_needs(digest, about, viewer, today):
    if not viewer.handle:
        raise NeedsViewer(NEEDS_WHO)
    mine = [line for line in digest["needs"]["lines"] if viewer.handle in line["for"]]
    if not mine:
        return ["Nothing right now."], [], []
    headline = [f"{count_words(len(mine), 'thing needs', 'things need')} you."]
    headline += [need_words(line, today) for line in mine[:LIST_LIMIT]]
    if len(mine) > LIST_LIMIT:
        headline.append(f"and {len(mine) - LIST_LIMIT} more.")
    return headline, [{"id": l["key"], "name": l["name"], "date": l["date"], "days": l["days"], "standing": l["standing"]}
                      for l in mine], []


def view_left(digest, about, viewer, today):
    rows = digest["progress"]
    decided, total = sum(r["decided"] for r in rows), sum(r["total"] for r in rows)
    open_apps = [r for r in rows if r["open"]]
    headline = [f"{decided} of {total} planned items are decided."]
    headline.append(f"{len(open_apps)} apps still have open items." if len(open_apps) != 1 else "1 app still has open items.")
    items = [{"id": "total", "name": "All apps", "decided": decided, "total": total, "apps_open": len(open_apps)}]
    items += [{"id": r["app"], "name": r["name"], "decided": r["decided"], "total": r["total"], "stage": r["stage"],
               "next": r["next"]} for r in rows]
    return headline, items, []


def view_who(digest, about, viewer, today):
    asks = [a for a in digest["asks"] if a["state"] == "open"]
    groups = by_holder(asks)
    headline = [f"{count_words(len(asks), 'open question sits', 'open questions sit')} with "
                f"{count_words(len(groups), 'person', 'people')}."]
    items = [{"id": "total", "name": "Open questions", "open": len(asks), "people": len(groups)}]
    return headline, items + [ask_item(a) for a in asks], groups


def close_names(about, names):
    words = set(re.findall(r"[a-z0-9]+", about.lower()))
    shared = [n for n in names if words & set(re.findall(r"[a-z0-9]+", n.lower()))]
    near = difflib.get_close_matches(about, names, n=3, cutoff=0.3)
    return list(dict.fromkeys(near + shared))[:5]


def find(rows, about, key="name"):
    """The one row `about` names, by name (any letter case), key or an unambiguous part of a name; else Unknown."""
    lowered = about.strip().lower()
    exact = [r for r in rows if lowered in (r[key].lower(), str(r.get("key", "")).lower())]
    part = [r for r in rows if lowered and lowered in r[key].lower()]
    found = exact or (part if len(part) == 1 else [])
    if not found:
        raise Unknown(about, close_names(about, [r[key] for r in rows]))
    return found[0]


def view_flow(digest, about, viewer, today):
    flow = find(digest["flows"], about)
    steps = flow["steps"]
    headline = [f"{flow['name']} has {count_words(len(steps), 'step', 'steps')}."]
    items = [{"id": str(s["n"]), "name": companionsvg.label(s["text"], 90)} for s in steps]
    return headline, items, []


def view_page(digest, about, viewer, today):
    page = find(digest["pages"], about)
    state = STATE_WORDS.get(page["state"], page["state"] or "not given a state")
    return [f"{page['name']} is {state}."], [{"id": page["key"], "name": page["name"], "state": state,
                                               "opening": page["opening"]}], []


def view_none(digest, about, viewer, today):
    return [NO_VIEW], [], []


READERS = {"track": view_track, "stuck": view_stuck, "needs": view_needs, "left": view_left, "who": view_who,
           "flow": view_flow, "page": view_page, "none": view_none}


def diagram_of(digest, view, about, items):
    if view == "flow":
        flow = find(digest["flows"], about)
        return {"kind": "sequence", "of": flow["key"], "name": flow["name"], "steps": flow["steps"],
                "svg": companionsvg.sequence(flow["steps"], flow["name"]), "text": companionsvg.text_of(flow["steps"])}
    if view == "stuck" and any(level in ("warning", "caution", "unexamined") for level in digest["app_lights"].values()):  # a map with nothing lit says nothing
        return {"kind": "map", "of": "", "name": "Where they sit", "steps": [],
                "svg": companionsvg.lit_map(digest["apps"], digest["app_lights"]), "text": ""}
    return None


def explain(digest, view, about, viewer, since, today):
    """The explain JSON (version 1). Raises Unknown for flow/page naming nothing, NeedsViewer for needs with no handle."""
    headline, items, groups = READERS[view](digest, about, viewer, today)
    dashboard = "dashboard.html" + (ROUTES[view] if view != "flow" else "#flows&open=" + find(digest["flows"], about)["key"])
    return {"version": VERSION, "kind": "explain", "view": view, "as_of": today,
            "copy": {"title": digest["title"], "made": digest["made"]},
            "viewer": {"handle": viewer.handle, "role": viewer.role}, "headline": headline, "since": since,
            "items": items, "groups": groups, "diagram": diagram_of(digest, view, about, items),
            "dashboard": dashboard if view != "none" else "dashboard.html",
            "not_recorded": [NOT_RECORDED[view]] if NOT_RECORDED[view] else [], "files": {}, "vault": "", "warnings": []}
