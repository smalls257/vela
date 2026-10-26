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
    "stuck": "How far the teams have built. Ask the team leads for that.",
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


STATUS_WORDS = {"on": "on", "live but off": "live but switched off", "journey passes": "past their journey check",
                "building": "building", "planned": "only planned"}  # best first; each status in its own word


def is_shipped(release, slices):
    """Shipped means it has slices and every one of them is on. A date with no slice recorded is not shipped."""
    mine = [s for s in slices if s["key"] in release["slices"]]
    return bool(mine) and all(s["status"] == "on" for s in mine)


def release_named(digest, about):
    """The release `--about` names, else the earliest dated release that has not shipped, else None."""
    dated = [r for r in digest["releases"] if r["target"]]
    if about.strip():
        return find(dated, about)
    waiting = [r for r in dated if not is_shipped(r, digest["slices"])]
    return min(waiting, key=lambda r: r["target"]) if waiting else None


def could_hold_up(digest, slices):
    """The stuck questions whose holds reach one of these slices."""
    reached = {key for s in slices for key in s["reach"]}
    pages = {page for s in slices for page in s.get("reach_pages", [])}
    return [a for a in digest["stuck"] if reached & set(a["hold_keys"]) or pages & set(a.get("hold_pages", []))]


def verdict(digest, release, mine, out):
    """Never says the plan is fine: it can only say a date passed with nothing recorded, or what could make it late.
    A passed date with the release not on is Late whatever else is true, so the words never contradict the date."""
    if out < 0 or any(s["overdue"] for s in mine):
        return "Late: the date passed." if out < 0 else "Late: a due date passed with nothing recorded."
    could = len(could_hold_up(digest, mine))
    if could:
        return f"{count_words(could, 'thing', 'things')} could make it late."
    return "Nothing in the plan says it's late."


def status_sentence(mine):
    counts = {status: sum(1 for s in mine if s["status"] == status) for status in STATUS_WORDS}
    parts = [f"{n} {'is' if n == 1 else 'are'} {STATUS_WORDS[status]}" for status, n in counts.items() if n]
    return f"Of {count_words(len(mine), 'slice', 'slices')}, " + (", ".join(parts[:-1]) + " and " + parts[-1] if len(parts) > 1 else parts[0]) + "."


def view_track(digest, about, viewer, today):
    if not any(r["target"] for r in digest["releases"]):
        return ["No release has a date yet."], [], []
    release = release_named(digest, about)
    if release is None:
        return ["Every dated release has shipped."], [], []
    out = days_out(release["target"], today)
    mine = [s for s in digest["slices"] if s["key"] in release["slices"]]
    if is_shipped(release, digest["slices"]):
        headline = [f"{release['name']} shipped: every slice tied to it is on.", status_sentence(mine)]
        return headline, [{"id": release["name"], "name": release["name"], "target": release["target"], "days_out": out}], []
    when = f"{out} days out" if out >= 0 else f"{-out} days ago"
    headline = [f"{release['name']} is due {date_words(release['target'], today)}, {when}."]
    headline.append(status_sentence(mine) if mine else "No slice is tied to it yet.")
    headline.append(verdict(digest, release, mine, out))
    items = [{"id": release["name"], "name": release["name"], "target": release["target"], "days_out": out}]
    items += [{"id": s["key"], "name": s["name"], "status": s["status"], "overdue": s["overdue"]} for s in mine]
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


NEED_OPENERS = {"question": "An answer on", "proposal": "Your review of", "handed": "Your take on", "grill": "A grill on"}


def need_words(line, today):
    base = f"{NEED_OPENERS.get(line['kind'], 'Your attention on')} {line['name']}"
    return f"{base} by {date_words(line['date'], today)}." if line["date"] else f"{base}."


def view_needs(digest, about, viewer, today):
    if not viewer.handle:
        raise NeedsViewer(NEEDS_WHO)
    mine = [line for line in digest["needs"]["lines"] if viewer.handle in line["for"]]
    if not mine:
        next_release = release_named(digest, "")
        when = f" The plan's next date is {next_release['name']}, {date_words(next_release['target'], today)}." if next_release else ""
        return ["Nothing right now." + when], [], []
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
                "svg": companionsvg.sequence(flow["steps"], flow["name"])}
    if view == "stuck" and any(level in ("warning", "caution", "unexamined") for level in digest["app_lights"].values()):  # a map with nothing lit says nothing
        return {"kind": "map", "of": "", "name": "Where they sit", "steps": [],
                "svg": companionsvg.lit_map(digest["apps"], digest["app_lights"])}
    return None


def views_that_answer(digest, viewer):
    """The views worth offering as "also ask": the ones that have something to say for this plan and this reader. The
    plan's own dates make "when is it due?" answerable, a known reader makes "what do you need from me?" answerable."""
    answers = {"stuck": True, "left": bool(digest["progress"]), "who": any(a["state"] == "open" for a in digest["asks"]),
               "needs": bool(viewer.handle), "track": any(r["target"] for r in digest["releases"])}
    return [view for view, yes in answers.items() if yes]


def explain(digest, view, about, viewer, since, today):
    """The explain JSON (version 1). Raises Unknown for flow/page naming nothing, NeedsViewer for needs with no handle."""
    headline, items, groups = READERS[view](digest, about, viewer, today)
    dashboard = "dashboard.html" + (ROUTES[view] if view != "flow" else "#flows&open=" + find(digest["flows"], about)["key"])
    return {"version": VERSION, "kind": "explain", "view": view, "as_of": today,
            "copy": {"title": digest["title"], "made": digest["made"]},
            "viewer": {"handle": viewer.handle, "role": viewer.role}, "headline": headline, "since": since,
            "items": items, "groups": groups, "diagram": diagram_of(digest, view, about, items),
            "also": [v for v in views_that_answer(digest, viewer) if v != view],
            "dashboard": dashboard if view != "none" else "dashboard.html",
            "not_recorded": [NOT_RECORDED[view]] if NOT_RECORDED[view] else [], "files": {}, "vault": "", "warnings": []}
