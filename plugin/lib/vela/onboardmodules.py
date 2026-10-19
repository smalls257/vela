"""What each onboarding module says, built from the explorer's data and nothing else.

The Violation this module exists to prevent is the Infected Core's cousin, the invented fact: every sentence below is
a template filled with a name, a count, a date or a page's own opening words that the vault holds. There is no free
text and no model call, so two builds of one vault say the same thing. When the vault has no word on a part, the
module says "Not recorded yet" and who to ask (as /vela:ask does); it is never hidden and never filled in.

Pure: `facts` is the dict `explorer.build.extract` returns (the page's D). Links are the dashboard's real routes, and a
key the data doesn't hold gets no link, so a dead link can't be written (the page's selftest follows each one).
"""
import math
from urllib.parse import quote

from vela import onboarding, plainwords, say

DEPTHS = {"gist": {"body": 0, "items": 3}, "normal": {"body": 2, "items": 6}, "everything": {"body": None, "items": None}}
SECTION_OF_KIND = {"app": "apps", "capability": "capabilities", "epic": "epics", "flow": "flows", "decision": "decisions",
                   "slice": "slices", "concern": "concerns"}
NOUN = {"lead": "a solution lead", "exec": "an exec", "product": "a product owner", "qa": "a QA lead", "eng": "an engineer", "mgr": "a manager"}
OPEN_LISTED = 4  # open questions listed under Where things stand: about four things at a time
LEVEL_WORD = {"warning": "overdue", "caution": "waiting"}
TONE_OF_STATE = {"decided": "ok", "fact": "ok", "confirmed": "ok", "resolved": "ok", "mitigated": "ok", "open": "open",
                 "proposed": "open", "assumption": "open", "inkling": "open", "draft": "open"}
TITLES = {
    "goal": ("What this is for", "The goal, and why now."),
    "approach": ("How we plan to get there", "The approach, the slices and the tracer."),
    "standing": ("Where things stand", "What is decided and why, what was ruled out, and what is still open."),
    "fit": ("Where you fit", "What your role touches here, and what matters most for it."),
    "people": ("Who to talk to", "The people who own what you will touch, and who holds each open answer."),
    "needs-you": ("What's waiting", "The things the plan is waiting on its lead for, most urgent first."),
    "open-questions": ("Open questions", "What nobody has answered yet, who can, and by when."),
    "risks": ("Risks", "What could go wrong, and what is being done about it."),
    "dates": ("Dates", "The dates the plan commits to."),
    "decisions-waiting": ("Decisions waiting", "Choices proposed but not settled yet."),
    "capabilities": ("Capabilities", "What the product has to be able to do."),
    "journeys": ("Journeys", "The paths a person takes through the system, step by step."),
    "slices": ("Slices", "Each slice is one journey built end to end; here is where each stands."),
    "apps": ("Apps", "The applications this plan builds or changes."),
    "contracts": ("Contracts", "What the apps promise each other."),
    "criteria": ("Acceptance criteria", "How we will know each piece of work is done."),
    "failure": ("Failure behavior", "What each app does when something it depends on fails."),
    "handoff": ("Handoff", "What each app's team was handed, and what has changed since."),
    "progress": ("Progress", "How far each app has got."),
    "blocked": ("Who is blocking what", "Open questions grouped by the person who can answer them."),
}
TRY = {
    "approach": ("slices", "Open Slices and switch to Path to see what can be built side by side."),
    "standing": ("garden", "Open the decision log and pick a decision to see what it ruled out."),
    "open-questions": ("asks", "Open Who to ask and find the person with the most open questions."),
    "needs-you": ("ranked", "Open What's waiting; the most urgent thing is first."),
    "journeys": ("flows", "Open a journey and press Present to watch it step by step."),
    "contracts": ("contracts", "Open the map and pick a line to see the contract behind it."),
    "slices": ("slices", "Open Slices and open a row to see what it is done when."),
    "apps": ("apps", "Open the map and pick an app to see what it provides and uses."),
    "progress": ("apps", "Open Progress to see each app's stage side by side."),
}


# --------------------------------------------------------------------------- small, shared pieces

def say_text(text):
    """A vault sentence as a person reads it: handles as names, ISO dates as dates. Empty when it still holds a code
    (an ID, a check code), because the page shows names and never those."""
    text = say.LEAD_PATTERNS["handle"].sub(lambda m: say.person_words(m.group(0)), text or "")
    text = say.LEAD_PATTERNS["ISO date"].sub(lambda m: say.date_words(m.group(0)), text)
    text = " ".join(text.split())
    return "" if any(say.LEAD_PATTERNS[kind].search(text) for kind in say.ID_KINDS) else text


def cut(text, limit):
    if len(text) <= limit:
        return text
    return text[:limit - 1].rsplit(" ", 1)[0].rstrip(" ,;:.") + "…"


def first_sentence(text, limit=220):
    text = say_text(text)
    end = text.find(". ")
    return cut(text[:end + 1] if 0 < end < limit else text, limit)


def entity(f, key):
    return f["entities"].get(key)


def title(f, key):
    e = entity(f, key)
    return say_text(e["title"]) if e else ""


def route(f, key):
    """The dashboard hash that opens `key`, or "" when the data holds no such thing or the page has no place for it."""
    e = entity(f, key)
    if not e:
        return ""
    kind, q = e["kind"], quote(key, safe="")
    if kind == "unknown":
        return f"#asks&open={q}"
    if kind in ("contract", "party"):
        return f"#map&open={q}"
    if kind == "risk":
        return "#s=unknowns"
    if kind in ("section", "page"):
        section = next((s["id"] for s in f["sections"] if s["page"] == key), "")
        return f"#s={section}" if section else ""
    section = SECTION_OF_KIND.get(kind)
    return f"#s={section}&open={q}" if section else ""


def item(label, pill="", note="", href="", key="", tone=""):
    return {"label": label, "pill": pill, "note": note, "href": href, "key": key, "tone": tone}


def link(label, href):
    return {"label": label, "href": href}


def state_item(f, key, note="", pill=None):
    """An item for a page or an entity: its name, its state in words, and where it opens."""
    e = entity(f, key)
    state = e["state"] if e else ""
    return item(title(f, key), plainwords.state_word(state) if pill is None else pill, note, route(f, key), key,
                TONE_OF_STATE.get(state, ""))


def person(handle):
    words = say.person_words(handle)
    return words[:1].upper() + words[1:]


def date_phrase(iso):
    return say.date_words(iso) if iso else ""


def most_owning_person(f):
    """The owner with the most pages and items, as a name: who to ask when a part has no owner of its own."""
    ranked = sorted(f["owners"].values(), key=lambda o: (-len(o["owns"]), o["handle"]))
    return person(ranked[0]["handle"]) if ranked else ""


def who_to_ask(f, page_key=""):
    e = entity(f, page_key) if page_key else None
    owner = e["ownerKey"] if e and e.get("ownerKey") else ""
    return person(owner) if owner else most_owning_person(f) or "whoever shared this plan with you"


def section_page(f, section_id):
    return next((s["page"] for s in f["sections"] if s["id"] == section_id and s["page"]), "")


def opening(f, page_key):
    """A page's opening words, the plan's own sentences (empty when the page isn't written or holds a code)."""
    e = entity(f, page_key)
    return say_text(e["text"]) if e else ""


def make(mid, gist, body=(), items=(), links=(), terms=(), missing=None):
    title_, lede = TITLES[mid]
    gist = gist if gist.rstrip().endswith((".", "!", "?", "\u2026")) else gist.rstrip() + "."
    body = [b for b in body if b]
    items = [i for i in items if i["label"]]
    words = len(gist.split()) + sum(len(b.split()) for b in body) + sum(len((i["label"] + " " + i["note"]).split()) for i in items)
    tried = TRY.get(mid)
    return {"id": mid, "name": onboarding.NAMES[mid], "title": title_, "lede": lede, "gist": gist, "body": body, "items": items,
            "links": [l for l in links if l["href"]], "terms": list(terms), "tryIt": tried[1] if tried and items else "",
            "notRecorded": missing, "minutes": max(2, min(8, 1 + math.ceil(words / 140)))}


def not_recorded(f, mid, what, page_key=""):
    """The module for a part the plan is silent on: it says so, and who to ask. Never hidden, never filled in."""
    who = who_to_ask(f, page_key)
    return make(mid, f"Not recorded yet: {what}.", [f"Ask {who}."], missing={"what": what, "ask": who})


def verb(n, one, many):
    return one if n == 1 else many


def of_them(n, total, word):
    return f"all {word}" if n == total else f"{n} of them {word}"


def count_phrase(n, one, many=None):
    return f"{n} {one if n == 1 else (many or one + 's')}"


# --------------------------------------------------------------------------- the five core parts

def goal(f):
    rows = [g for g in f["goals"] if say_text(g["goalText"])]
    if not rows:
        return not_recorded(f, "goal", "what this initiative is for", section_page(f, "goals"))
    first = cut(say_text(rows[0]["goalText"]), 180)
    releases = f["releases"]["states"]
    why_now = release_sentence(releases[1:])
    items = [item(cut(say_text(g["goalText"]), 140), plainwords.state_word(g["state"]),
                  say_text(g["measure"]) if g["measure"] and g["measure"] != "not set" else "No measure yet",
                  "#s=goals", "", TONE_OF_STATE.get(g["state"], "")) for g in rows]
    return make("goal", f"The first goal: {first}", [opening(f, section_page(f, "goals")), why_now], items,
                [link("The goals, as written", "#s=goals"), link("The timeline", "#s=releases" if f["releases"]["count"] else "")])


def release_sentence(later):
    """The first release's date when it has one; else the next dated release, named, so a date is never given to the wrong release."""
    if later and later[0]["target"]:
        return f"The first release is aimed at {date_phrase(later[0]['target'])}."
    dated = next((s for s in later if s["target"]), None)
    if not dated:
        return ""
    return f"The next dated release, {say_text(dated.get('heading') or dated['name'])}, is due {date_phrase(dated['target'])}."


def approach(f):
    slices = f["slicePlan"]["list"]
    strategy = opening(f, section_page(f, "strategy"))
    if not strategy and not slices:
        return not_recorded(f, "approach", "how the work is planned", section_page(f, "strategy"))
    tracer = next((s for s in slices if s["tracer"]), None)
    body = [strategy]
    if slices and strategy:
        body.append(f"The work is cut into {count_phrase(len(slices), 'slice')}, each one journey built end to end.")
    if tracer:
        body.append(f"The tracer is {say_text(tracer['name'])}.")
    items = [item(say_text(s["name"]), s["status"] or "not planned yet", "The tracer" if s["tracer"] else "",
                  route(f, s["key"]) or "#s=slices", s["key"]) for s in slices]
    gist = first_sentence(strategy) or f"The work is cut into {count_phrase(len(slices), 'slice')}."
    return make("approach", gist, body, items, [link("The strategy, as written", "#s=strategy"), link("The slices", "#s=slices" if slices else "")],
                terms=[t for t, on in (("slice", slices), ("tracer", tracer)) if on])


def decision_key(tree):
    """The page a decision lives on: its record, else the first page carrying it."""
    return (tree.get("adr") or {}).get("key") or tree["carriedBy"][0]["key"]


def standing(f):
    trees = [t for t in f["garden"]["trees"] if t.get("state")]
    open_asks = [a for a in f["asks"] if a["state"] == "open"]
    if not trees and not open_asks:
        return not_recorded(f, "standing", "what is decided and what is open", section_page(f, "decisions"))
    decided = [t for t in trees if t["state"] == "decided"]
    others = [t for t in trees if t["state"] != "decided"]
    late = [a for a in open_asks if a["light"]["level"] == "warning"]
    parts = [p for p in (f"{count_phrase(len(decided), 'decision')} settled" if decided else "",
                         f"{len(others)} proposed" if others else "",
                         f"{count_phrase(len(open_asks), 'question')} still open" if open_asks else "") if p]
    gist = ", ".join(parts) if decided else "Nothing is settled yet" + (": " + ", ".join(parts) if parts else "")
    if late:
        gist += ", " + of_them(len(late), len(open_asks), "overdue")
    body = []
    for t in (decided + others)[:3]:
        gone = [r for r in t["rejected"] if say_text(r["label"])]
        why = ""
        if gone:
            reason = cut(say_text(gone[0]["reason"]), 160)
            why = f" We ruled out {say_text(gone[0]['label'])}" + (f": {reason}" if reason else "")
            why += "" if why[-1] in ".!?…" else "."  # a reason that ends in its own punctuation is not followed by another period
        body.append(f"{say_text(t['picked']['label'])} is {plainwords.state_word(t['state'])}.{why}")
    items = []
    for t in decided + others:
        key = decision_key(t)
        gone = ", ".join(say_text(r["label"]) for r in t["rejected"] if say_text(r["label"]))
        items.append(item(cut(say_text(t["picked"]["label"]), 100), plainwords.state_word(t["state"]), f"Ruled out: {gone}" if gone else "",
                          route(f, key), key if entity(f, key) else "", TONE_OF_STATE.get(t["state"], "")))
    for a in sorted(open_asks, key=lambda a: -a["light"]["urgency"])[:OPEN_LISTED]:  # the most urgent few; the rest are one link away
        by = f" by {date_phrase(a['askBy'])}" if a["askBy"] else ""
        late = a["light"]["level"] == "warning"
        items.append(item(cut(say_text(a["question"]), 110), "overdue" if late else "open", f"Ask {a['ask']['name']}{by}", route(f, a["id"]), a["id"], "late" if late else "open"))
    return make("standing", gist[:1].upper() + gist[1:] + ".", body, items, [link("The decision log", "#s=decisions"), link("Who to ask", "#asks" if open_asks else "")])


def fit(f, audience):
    label = onboarding.AUDIENCE_LABELS[audience]
    touched = touches(f, audience)
    if not touched["keys"]:
        return not_recorded(f, "fit", f"what {NOUN[audience]} touches here", section_page(f, "apps"))
    n = len(touched["keys"])
    lit = [k for k in f["ranked"] if k in touched["keys"]]
    first = lit[:3] or touched["keys"][:3]
    gist = f"As {NOUN[audience]}, you will mostly deal with {touched['phrase']}: {n} here."
    body = [f"What needs attention first: {', '.join(title(f, k) for k in first)}." if lit else "Nothing in them is overdue or waiting on someone right now."]
    items = [state_item(f, k, note=LEVEL_WORD.get(f["lights"].get(k, {}).get("level", ""), "")) for k in touched["keys"]]
    return make("fit", gist, body, items, [link(f"The {label} view", f"#role={audience}" if audience != "lead" else "#home")])


def touches(f, audience):
    """What an audience works with here: {"phrase", "keys"}. The lead sees the apps; the others see their own kind."""
    kinds = {"lead": ("app", "the apps"), "exec": ("decision", "the decisions"), "product": ("capability", "the capabilities"),
             "qa": ("epic", "the epics, with their acceptance criteria"), "eng": ("app", "the apps being built or changed"),
             "mgr": ("app", "the apps and how far they have got")}
    kind, phrase = kinds[audience]
    keys = {k for k, e in f["entities"].items() if e["kind"] == kind and (audience != "eng" or e["change"] not in ("unchanged", "integrated"))}
    if audience == "exec":  # decisions come from the decision trees, the way "Decisions waiting" finds them; not every one is its own entity kind
        keys |= {decision_key(t) for t in f["garden"]["trees"] if t.get("state") and decision_key(t) in f["entities"]}
        keys |= {r["id"] for r in f["riskList"] if r["id"] in f["entities"]}
        phrase = "the decisions and risks"
    return {"phrase": phrase, "keys": sorted(keys)}


def people(f, audience):
    keys = set(touches(f, audience)["keys"])
    owners = sorted(f["owners"].values(), key=lambda o: (-len(keys & set(o["owns"])), -len(o["owns"]), o["handle"]))
    items = []
    for o in owners[:6]:
        mine = [title(f, k) for k in o["owns"] if k in keys and title(f, k)][:2]
        role = o["names"][0] if o["names"] else ""
        note = ("Owns " + " and ".join(mine)) if mine else f"Owns {count_phrase(len(o['owns']), 'page or item', 'pages and items')}"
        items.append(item(person(o["handle"]), role, note, "#asks"))
    asks = who_holds(f)
    for name, mine in asks[:3]:
        items.append(item(name, "holds answers", count_phrase(len(mine), "open question"), "#asks"))
    if not items:
        return not_recorded(f, "people", "who owns what", section_page(f, "unknowns"))
    names = [i["label"] for i in items[:3]]
    return make("people", f"Start with {', '.join(names)}.", [f"{count_phrase(len(owners), 'owner')} named in this plan."], items, [link("Who to ask", "#asks")])


def who_holds(f):
    """[(name, [open asks])], most first: who the open questions wait on."""
    held = {}
    for a in f["asks"]:
        if a["state"] == "open":
            held.setdefault(a["ask"]["name"], []).append(a)
    return sorted(held.items(), key=lambda kv: (-len(kv[1]), kv[0]))


# --------------------------------------------------------------------------- the role specifics

def needs_you(f):
    lit = [k for k in f["ranked"] if entity(f, k) and f["lights"][k]["level"] in LEVEL_WORD]
    if not lit:
        return make("needs-you", "Nothing is waiting on the lead right now.", [], [], [link("What's waiting", "#home")])
    late = [k for k in lit if f["lights"][k]["level"] == "warning"]
    items = [item(title(f, k), LEVEL_WORD[f["lights"][k]["level"]], "", route(f, k), k, "late" if f["lights"][k]["level"] == "warning" else "open") for k in lit]
    return make("needs-you", f"{count_phrase(len(lit), 'thing')} {verb(len(lit), 'needs', 'need')} the lead" + (f", {of_them(len(late), len(lit), 'overdue')}" if late else "") + ".", [], items, [link("What's waiting", "#home")])


def open_questions(f):
    asks = sorted((a for a in f["asks"] if a["state"] == "open"), key=lambda a: -a["light"]["urgency"])
    if not asks:
        return make("open-questions", "No question is open.", [], [], [link("Who to ask", "#asks")])
    items = []
    for a in asks:
        by = f" by {date_phrase(a['askBy'])}" if a["askBy"] else ""
        late = a["light"]["level"] == "warning"
        items.append(item(cut(say_text(a["question"]), 110), "overdue" if late else "open", f"Ask {a['ask']['name']}{by}", f"#asks&open={quote(a['id'], safe='')}", a["id"], "late" if late else "open"))
    late = sum(1 for i in items if i["tone"] == "late")
    gist = f"{count_phrase(len(asks), 'question')} open" + (f", {of_them(late, len(asks), 'past their date')}" if late else "")
    return make("open-questions", gist + ".", [], items, [link("Who to ask", "#asks")])


def risks(f):
    rows = f["riskList"]
    if not rows:
        return not_recorded(f, "risks", "the risks", section_page(f, "unknowns"))
    items = []
    for r in rows:
        state = r["facts"].get("State", "")
        items.append(item(cut(say_text(r["title"]), 100), plainwords.state_word(state), cut(say_text(r["facts"].get("Mitigation", "")), 140), route(f, r["id"]), r["id"] if entity(f, r["id"]) else "",
                          TONE_OF_STATE.get(state, "open")))
    return make("risks", f"{count_phrase(len(rows), 'risk')} written down.", [], items, [link("Unknowns and risks", "#s=unknowns")])


def dates(f):
    items = []
    for s in f["releases"]["states"][1:]:
        if s["target"]:
            items.append(item(say_text(s["heading"] if "heading" in s else s["name"]), date_phrase(s["target"]), plainwords.state_word(s["state"]), "#s=releases", ""))
    for s in f["slicePlan"]["list"]:
        if s["journeyDue"]:
            items.append(item(say_text(s["name"]), date_phrase(s["journeyDue"]), say_text(s["overdue"]) if s["overdue"] else "journey due", route(f, s["key"]) or "#s=slices", s["key"],
                              "late" if s["overdue"] else ""))
    if not items:
        return not_recorded(f, "dates", "any dates", section_page(f, "releases"))
    return make("dates", f"{count_phrase(len(items), 'date')} on the plan.", [], items, [link("The timeline", "#s=releases"), link("The slices", "#s=slices" if f["slicePlan"]["list"] else "")])


def decisions_waiting(f):
    waiting = [t for t in f["garden"]["trees"] if t.get("state") in ("proposed", "pending", "overridden")]
    if not waiting:
        return make("decisions-waiting", "No decision is waiting.", [], [], [link("The decision log", "#s=decisions")])
    words = {"proposed": "proposed", "pending": "waiting for review", "overridden": "decided by exception"}
    items = []
    for t in waiting:
        key = decision_key(t)
        items.append(item(cut(say_text(t["picked"]["label"]), 100), words[t["state"]], "", route(f, key), key if entity(f, key) else "", "open"))
    return make("decisions-waiting", f"{count_phrase(len(waiting), 'decision')} waiting to be settled.", [], items, [link("The decision log", "#s=decisions")])


def capabilities(f):
    keys = sorted(k for k, e in f["entities"].items() if e["kind"] == "capability")
    if not keys:
        return not_recorded(f, "capabilities", "what the product must be able to do", section_page(f, "capabilities"))
    items = [state_item(f, k, note=plainwords.state_word(f["entities"][k]["change"]) if f["entities"][k]["change"] else "") for k in keys]
    return make("capabilities", f"{count_phrase(len(keys), 'capability', 'capabilities')} the plan touches.", [], items, [link("The capability map", "#s=capabilities")])


def journeys(f):
    keys = [fl["key"] for fl in f["flows"] if entity(f, fl["key"])]
    if not keys:
        return not_recorded(f, "journeys", "any journeys", section_page(f, "flows"))
    items = [state_item(f, k, note=count_phrase(len(next(fl for fl in f["flows"] if fl["key"] == k)["steps"]), "step")) for k in keys]
    return make("journeys", f"{count_phrase(len(keys), 'journey')} written step by step.", [], items, [link("The journeys", "#s=flows")])


def slices(f):
    rows = f["slicePlan"]["list"]
    if not rows:
        return not_recorded(f, "slices", "any slices", section_page(f, "strategy"))
    done = sum(1 for s in rows if s["status"] in ("journey passes", "live but off", "on"))
    items = [item(say_text(s["name"]), s["status"] or "not planned yet", say_text(s["overdue"]) if s["overdue"] else ("The tracer" if s["tracer"] else ""),
                  route(f, s["key"]) or "#s=slices", s["key"], "late" if s["overdue"] else "ok" if s["status"] in ("journey passes", "on") else "") for s in rows]
    return make("slices", f"{done} of {count_phrase(len(rows), 'slice')} {verb(done, 'has', 'have')} passed {verb(done, 'its', 'their')} journey.", [], items, [link("The slices", "#s=slices")], terms=["slice"])


def apps(f):
    rows = [a for a in f["map"]["apps"] if a["change"] not in ("unchanged", "integrated")] or f["map"]["apps"]
    if not rows:
        return not_recorded(f, "apps", "any apps", section_page(f, "apps"))
    items = [item(say_text(a["title"]), plainwords.stage_word(a["stage"]) if a["stage"] else plainwords.state_word(a["state"]),
                  plainwords.state_word(a["change"]) if a["change"] else "", route(f, a["key"]), a["key"]) for a in rows]
    return make("apps", f"{count_phrase(len(rows), 'app')} to build or change.", [], items, [link("The apps", "#s=apps")])


def contracts(f):
    rows = f["map"]["contracts"]
    if not rows:
        return not_recorded(f, "contracts", "any contracts", section_page(f, "apps"))
    items = []
    for c in rows:
        to = ", ".join(title(f, k) or k for k in c["consumers"] if title(f, k))
        items.append(item(say_text(c["title"]), plainwords.state_word(c["state"]), f"{title(f, c['provider'])} to {to}" if title(f, c["provider"]) and to else "",
                          route(f, c["id"]), c["id"] if entity(f, c["id"]) else "", TONE_OF_STATE.get(c["state"], "")))
    return make("contracts", f"{count_phrase(len(rows), 'contract')} between the apps.", [], items, [link("The map", "#map")])


def criteria(f):
    rows = [(k, v) for k, v in f["epicCriteria"].items() if v and entity(f, k)]
    if not rows:
        return not_recorded(f, "criteria", "any acceptance criteria", section_page(f, "epics"))
    items = [item(title(f, k), count_phrase(len(v), "criterion", "criteria"), cut(say_text(v[0].get("heading") or ""), 90), route(f, k), k) for k, v in sorted(rows)]
    total = sum(len(v) for _, v in rows)
    return make("criteria", f"{count_phrase(total, 'criterion', 'criteria')} across {count_phrase(len(rows), 'epic')}.", [], items, [link("The epics", "#s=epics")])


def failure(f):
    rows = [(k, v) for k, v in f["failure"].items() if entity(f, k)]
    if not rows:
        return not_recorded(f, "failure", "how any app behaves when something fails", section_page(f, "apps"))
    items = [item(title(f, k), "written down" if v["sections"] else "not written yet", cut(say_text(v["sections"][0]["heading"]), 90) if v["sections"] else "",
                  route(f, k), k, "ok" if v["sections"] else "open") for k, v in sorted(rows)]
    return make("failure", f"{sum(1 for _, v in rows if v['sections'])} of {count_phrase(len(rows), 'app')} {verb(sum(1 for _, v in rows if v['sections']), 'says', 'say')} what happens on failure.", [], items, [link("The apps", "#s=apps")])


def handoff(f):
    rows = [r for r in f["progress"]["rows"] if entity(f, r["app"])]
    if not rows:
        return not_recorded(f, "handoff", "any app handoff", section_page(f, "apps"))
    items = []
    for r in rows:
        h = r["handoff"]
        done = say_text(h["handedOff"])
        drift = h["changed"] + h["removed"]
        note = f"{count_phrase(len(f['handoffList'].get(r['app'], [])), 'item')} handed over" + (f"; {drift} changed since" if done and drift else "")
        items.append(item(title(f, r["app"]), "handed off" if done else "not handed off yet", note, route(f, r["app"]), r["app"], "late" if drift else "ok" if done else "open"))
    return make("handoff", f"{sum(1 for i in items if i['pill'] == 'handed off')} of {count_phrase(len(items), 'app')} handed to a team.", [], items, [link("Progress", "#s=apps&v=progress")])


def progress(f):
    rows = [r for r in f["progress"]["rows"] if r["stage"] and entity(f, r["app"])]
    if not rows:
        return not_recorded(f, "progress", "any app's stage", section_page(f, "apps"))
    items = [item(title(f, r["app"]), plainwords.stage_word(r["stage"]), cut(say_text(r["reason"]), 140), route(f, r["app"]), r["app"]) for r in rows]
    return make("progress", f"The plan is about {f['progress']['percent']}% written down, across {count_phrase(len(rows), 'app')}.", [], items, [link("Progress", "#s=apps&v=progress")])


def blocked(f):
    held = who_holds(f)
    if not held:
        return make("blocked", "Nobody is holding anything up.", [], [], [link("Who to ask", "#asks")])
    items = []
    for name, mine in held:
        late = sum(1 for a in mine if a["light"]["level"] == "warning")
        items.append(item(name, count_phrase(len(mine), "open question"), f"{late} overdue" if late else "", "#asks", "", "late" if late else "open"))
    return make("blocked", f"{count_phrase(len(held), 'person', 'people')} {verb(len(held), 'holds', 'hold')} answers the plan is waiting on.", [], items, [link("Who to ask", "#asks")])


BUILDERS = {"goal": goal, "approach": approach, "standing": standing, "needs-you": needs_you, "open-questions": open_questions,
            "risks": risks, "dates": dates, "decisions-waiting": decisions_waiting, "capabilities": capabilities, "journeys": journeys,
            "slices": slices, "apps": apps, "contracts": contracts, "criteria": criteria, "failure": failure, "handoff": handoff,
            "progress": progress, "blocked": blocked}
BOUND_BUILDERS = {"fit": fit, "people": people}


def build_all(facts):
    """{module key: module} for every module: one entry per shared module, and `fit@<audience>` / `people@<audience>`."""
    out = {mid: build(facts) for mid, build in BUILDERS.items()}
    for audience in onboarding.AUDIENCES:
        for mid, build in BOUND_BUILDERS.items():
            out[onboarding.key_of(mid, audience)] = build(facts, audience)
    return out
