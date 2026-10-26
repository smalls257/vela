"""The Requirements section's data: every functional requirement and whether it is met so far.

    extract(vault, keys, entities, designs, plans, blocked, asks, today) -> {rows, counts, lede, notKnown}

The Violation this exists to prevent is a Distributed Monolith of rules: "is it carried, released, in an epic,
designed, built, free of open questions" decided once here, in Python, from the readers the rest of the dashboard
already uses (allocation, releases, trace and criteria, the designs and plans the build has read, model.blockers). The
page draws `rows` and never works a check out for itself, so a second view of the same requirements cannot disagree.

Two more failures are ruled out by how it speaks. A Paper Tiger: vela cannot see code or test results, so a row never
says "met"; it says how many of six checks are met so far, and `notKnown` says what the plan cannot see. A Silent
Fallback: a check that cannot be worked out (no tech design from an app, no breakdown at all) says so in words
("no tech design yet from Consent and identity or Summarizer") and counts as not met, never as a quiet green.

Each check is {k, v, short, long}: `v` is "yes", "part" or "no"; `short` is the table cell; `long` is the sentence the
panel and the focus view quote. Sentences carry names and American dates, never codes: IDs travel only as keys.
"""
import datetime
import re

from vela import allocation, breakdown, criteria, model, progress, releases, say, slices, trace

from .record import plain

CHECKS = ("carried", "release", "epic", "designed", "stories", "open")
# What to do about a check that is not met: the words a lead acts on. The open check names who to ask (ask_words).
NEXT = {"carried": "Run /vela:allocate to divide it among the apps.",
        "release": "Add it to the release that will deliver it, once nothing holds it back.",
        "epic": "Name it on the Trace line of the epic criterion that builds it.",
        "designed": "Each of those apps' teams runs /vela:design from the plan's folder.",
        "stories": "Those teams write the work breakdown once their design is done."}
YES, PART, NO = "yes", "part", "no"
NOT_KNOWN = "Built and tested: not something the plan knows; see the tracker."
FLOW_ID = re.compile(r"^FLO-\d+$")
CONTRACT_ID = re.compile(r"^CON-\d+$")


def base(item_id):
    return item_id.split("@")[0]


def check(k, v, short, long):
    return {"k": k, "v": v, "short": short, "long": long}


def share_of(count, total):
    """yes when every one, part when some, no when none: the shape of the designed and stories checks."""
    return YES if count == total and total else PART if count else NO


def plural(n, one, many=None):
    return f"{n} {one if n == 1 else (many or one + 's')}"


def either_said(names):
    """['a', 'b', 'c'] -> 'a, b or c': a name may hold "and" ("Consent and identity"), so the join is never a replace."""
    names = [n for n in names if n]
    return names[0] if len(names) == 1 else ", ".join(names[:-1]) + f" or {names[-1]}" if names else ""


def first_lower(text):
    return text[:1].lower() + text[1:] if text else text


# --------------------------------------------------------------------------- what each reader says about one requirement

def carriers(vault, keys, entities, req):
    """[{key, name, share}] for each app with a row at assumption or later; allocation.carried is the one rule for what
    carries. An app with two rows says both shares."""
    shares = {}
    for row in allocation.carried(vault).get(req.id, []):
        key = keys.page(row.app)
        shares.setdefault(key, [row.app, []])[1].append(row.share)
    return [{"key": key, "name": entities[key]["title"], "share": "; ".join(s for s in said if s), "id": app.id}
            for key, (app, said) in shares.items()]


def guessers(vault, keys, entities, req):
    """Names of the apps whose only row for it is an inkling: a guess at a share, which carries nothing."""
    have = {a["key"] for a in carriers(vault, keys, entities, req)}
    found = [keys.page(r.app) for r in allocation.rows(vault) if r.requirement == req.id and r.state == "inkling"]
    return [entities[k]["title"] for k in dict.fromkeys(found) if k not in have]


def through(vault, req):
    """Contract IDs that carry it across: those on its allocation rows, in the order the rows run."""
    return list(dict.fromkeys(c for row in allocation.carried(vault).get(req.id, []) for c in row.through))


def epic_hits(vault, keys, req):
    """([{key, criteria}], the Trace IDs of the criteria that name it): trace.epics and criteria.read are the readers of
    which epic criterion traces to a requirement."""
    epics, named = [], []
    for epic in trace.epics(vault):
        hits = [c for c in criteria.read(epic) if not c.struck and any(base(t) == req.id for t in c.trace)]
        if hits:
            epics.append({"key": keys.page(epic), "criteria": len(hits)})
            named += [t for c in hits for t in c.trace]
    return epics, list(dict.fromkeys(named))


def release_of(vault, req):
    """The first release whose Delivers table names the requirement, or None."""
    for index, release in enumerate(releases.releases(vault), 1):
        for row in release.rows:
            if row.requirement == req.id:
                return index, release, row
    return None


def release_short(name):
    """"Release one: February pilot, Client Delivery London" as a table cell says it: "February pilot"."""
    return re.sub(r"^[^:]*:\s*", "", name).split(",")[0].strip() or name


def release_check(vault, req, said):
    found = release_of(vault, req)
    if found is None:
        why, where = slices.left_out(vault).get(req.id, (None, ""))
        reason = (f"on no release, and {where} says why: {why.reason.rstrip('.')}" if why and why.reason
                  else "on no release, so nothing says when it ships")
        if not releases.releases(vault):
            reason = "no release is planned yet"
        return None, "", check("release", NO, "none", reason)
    index, release, row = found
    when = say.date_words(release.target) if release.target else "no date yet"
    note = said(row.note).rstrip(".") if row.note else ""
    partial = f"; only criteria {', '.join(str(n) for n in row.criteria)} of it" if row.criteria else ""
    long = f"delivered in the {release_short(release.name)}, {when}{partial}" + (f"; {first_lower(note)}" if note else "")
    return {"name": release.name, "short": release_short(release.name), "date": when, "note": note, "index": index}, note, check("release", YES, release_short(release.name), long)


def design_entry(designs, carrier, req):
    """{app, designed, components, doc}: a design traces it when one of its components' trace entries names it (the
    requirement bare, or as CAP-nnn.FRn@APP-x)."""
    design = designs.get(carrier["key"])
    owners = [name for name, entries in (design["trace"] if design else {}).items() if any(base(e["id"]) == req.id for e in entries)]
    said = ("" if owners else f"{carrier['name']}: no tech design yet" if design is None else f"{carrier['name']}: its tech design does not trace it")
    return {"app": carrier["key"], "designed": bool(owners), "components": owners, "doc": design["path"] if design else "", "say": said}


def stories_entry(plans, carrier, req):
    """{app, breakdown, stories, putOff, reason}: the stories the app's breakdown credits with building it. A story that is
    deferred or merged, or a requirement the plan lists as not planned, is put off and counts as no story."""
    plan = plans.get(carrier["key"])
    if plan is None:
        return {"app": carrier["key"], "breakdown": False, "stories": [], "names": {}, "putOff": False, "reason": "",
                "say": f"{carrier['name']}: no breakdown yet"}
    named = [i for t in plan["coverage"]["targets"] if base(t["target"]) == req.id for i in t["stories"]]
    state = {s["id"]: s for s in plan["stories"]}
    built = [i for i in dict.fromkeys(named) if state[i]["state"] not in breakdown.NOT_BUILT]
    parked = [i for i in dict.fromkeys(named) if i not in built]
    said = next((line for line in plan["notPlanned"] if re.search(rf"(?<![\w.-]){re.escape(req.id)}\b", line)), "")
    put_off = not built and bool(parked or said)
    shown = built or parked
    words = f"{carrier['name']}: put off" if put_off else "" if built else f"{carrier['name']}: no story builds it"
    return {"app": carrier["key"], "breakdown": True, "stories": shown, "names": {i: state[i]["name"] for i in shown},
            "putOff": put_off, "reason": said, "say": words}


def open_questions(req, blocked, named, open_ids):
    """Open unknowns whose Blocks lists it, then open unknowns an epic criterion for it names, each once."""
    held = [u.id for u in blocked.get(req.id, [])]
    return list(dict.fromkeys(held + [i for i in named if i in open_ids]))


# --------------------------------------------------------------------------- the six checks, in the order work flows

def carried_check(carrying, guessed):
    names = [c["name"] for c in carrying]
    if names:
        return check("carried", YES, plural(len(names), "app"), f"carried by {say.names_said(names)}")
    long = "no app carries it yet: no app has taken it on at assumption or later"
    return check("carried", NO, "no app", long + (f"; {say.names_said(guessed)} only guessed at a share" if guessed else ""))


def epic_check(epics, entities):
    n = sum(e["criteria"] for e in epics)
    if not n:
        return check("epic", NO, "none", "no epic criterion traces to it")
    where = say.names_said([entities[e["key"]]["title"] for e in epics])
    return check("epic", YES, plural(n, "criterion", "criteria"), f"{plural(n, 'epic criterion', 'epic criteria')} trace{'s' if n == 1 else ''} to it, in {where}")


def designed_check(designs, carrying):
    if not carrying:
        return check("designed", NO, "no app", "no app carries it, so no tech design can trace it")
    done = [d for d in designs if d["designed"]]
    v = share_of(len(done), len(carrying))
    missing = [c["name"] for c, d in zip(carrying, designs) if not d["designed"]]
    long = ("every app that carries it has a tech design that traces it" if v == YES
            else f"no tech design yet from {either_said(missing)}" + ("" if v == NO else " (the others trace it)"))
    return check("designed", v, f"{len(done)} of {plural(len(carrying), 'app')}", long)


def stories_check(entries, carrying):
    if not carrying:
        return check("stories", NO, "no app", "no app carries it, so no story can build it")
    built = [e for e in entries if e["stories"] and not e["putOff"]]
    parked = [e for e in entries if e["putOff"]]
    v = share_of(len(built), len(carrying))
    if v == YES:
        return check("stories", v, f"{len(built)} of {plural(len(carrying), 'app')}", "every app that carries it has a story that builds it")
    lacking = [c["name"] for c, e in zip(carrying, entries) if not (e["stories"] and not e["putOff"])]
    nobreak = [c["name"] for c, e in zip(carrying, entries) if not e["breakdown"]]
    long = f"no {'breakdown' if set(lacking) == set(nobreak) else 'story'} yet from {either_said(lacking)}"
    if parked and not built:
        names = say.names_said([c["name"] for c, e in zip(carrying, entries) if e["putOff"]])
        undated = " and no review date is recorded" if any("no review date" in e["reason"] for e in parked) else ""
        return check("stories", NO, "put off", f"every story for it is put off in {names}'s breakdown{undated}")
    return check("stories", v, f"{len(built)} of {plural(len(carrying), 'app')}", long)


def ask_words(questions, asks, today):
    """"Ask Legal counsel, by October 29." from the dashboard's own asks (who holds each answer, and by when)."""
    held = [a for a in asks if a["id"] in questions]
    who = list(dict.fromkeys(a["ask"]["name"] for a in held if a["ask"]["name"]))
    dates = sorted(a["askBy"] for a in held if a["askBy"])
    by = f", by {say.date_words(dates[0], today)}" if dates else ""
    return f"Ask {say.names_said(who)}{by}." if who else "Ask whoever owns each question."


def open_check(questions, vault):
    if not questions:
        return check("open", YES, "clear", "no open question holds it")
    names = [f"“{vault.name_of(q)}”" for q in questions]
    return check("open", NO, plural(len(questions), "question"), f"waits on {say.names_said(names)}")


def decided_check(state):
    words = {"decided": (YES, "decided: a Grill settled it"),
             "fact": (PART, "a fact the plan records, not yet decided: a Grill decides it"),
             "assumption": (PART, "still an assumption: a Grill decides it"),
             "inkling": (NO, "still an inkling: it is not yet an assumption")}
    v, long = words.get(state, (NO, "no state recorded"))
    return {"k": "decided", "v": v, "short": state or "none", "long": long}


# --------------------------------------------------------------------------- one requirement, and the page's words

def criteria_rows(req):
    return [{"text": plain(text), "trace": list(ids)} for text, ids in releases.requirement_criteria(req)]


def row_of(vault, keys, entities, designs, plans, blocked, open_ids, said, asks, today, req):
    carrying = carriers(vault, keys, entities, req)
    epics, named = epic_hits(vault, keys, req)
    release, note, release_row = release_check(vault, req, said)
    design_rows = [design_entry(designs, c, req) for c in carrying]
    story_rows = [stories_entry(plans, c, req) for c in carrying]
    questions = open_questions(req, blocked, named, open_ids)
    checks = [carried_check(carrying, guessers(vault, keys, entities, req)), release_row, epic_check(epics, entities),
              designed_check(design_rows, carrying), stories_check(story_rows, carrying), open_check(questions, vault)]
    contracts = [c for c in dict.fromkeys(through(vault, req) + [t for t in named if CONTRACT_ID.match(t)]) if vault.item(c)]
    flows = [keys.page(vault.by_id[f][0]) for f in dict.fromkeys(t for t in named if FLOW_ID.match(t)) if f in vault.by_id]
    for c in checks:
        c["next"] = "" if c["v"] == YES else NEXT.get(c["k"]) or ask_words(questions, asks, today)
    state = req.fact("State")
    return {"id": req.id, "key": req.id, "name": entities[req.id]["title"], "capability": req.id.split(".")[0], "state": state,
            "text": entities[req.id]["text"], "criteria": criteria_rows(req),
            "apps": [{k: c[k] for k in ("key", "name", "share")} for c in carrying], "through": contracts, "flows": flows,
            "release": release, "releaseNote": note, "epics": epics, "designs": design_rows, "stories": story_rows,
            "questions": questions, "checks": checks, "decided": decided_check(state),
            "met": sum(1 for c in checks if c["v"] == YES), "in": filters_of(checks, questions)}


def filters_of(checks, questions):
    """The list's filters a requirement falls in, so the page filters by this and never by a rule of its own."""
    found = ["all"]
    if any(c["v"] != YES for c in checks):
        found.append("gap")
    if questions:
        found.append("held")
    if next(c for c in checks if c["k"] == "designed")["v"] != YES:
        found.append("design")
    return found


def counts(rows):
    return {k: sum(1 for r in rows if k in r["in"]) for k in ("all", "gap", "held", "design")}


def lede(rows, tally, designs):
    """The line under the title, from the numbers the filters carry. Nothing here is a status the plan cannot back."""
    if not rows:
        return "No functional requirements are written yet, so there is nothing to check. /vela:requirements writes them."
    decided = sum(1 for r in rows if r["state"] == "decided")
    said = "none decided yet" if not decided else "all decided" if decided == len(rows) else f"{decided} decided"
    first = f"{plural(len(rows), 'requirement')}, {said}."
    if not tally["gap"]:
        return f"{first} Every one passes all six checks so far."
    done = len(rows) - tally["gap"]
    mid = f"{plural(done, 'passes', 'pass')} all six checks so far; " if done else ""
    gap = f"{mid}{tally['gap']} {'has' if tally['gap'] == 1 else 'have'} a gap"
    if tally["design"]:
        who = [d["title"] for d in designs]
        has = f"only {say.names_said(who)} {'has' if len(who) == 1 else 'have'} a tech design" if who else "no app has a tech design yet"
        gap += f", and for {tally['design']} the gap includes a design: {has}"
    held = f" {plural(tally['held'], 'waits', 'wait')} on an open question." if tally["held"] else ""
    return f"{first} {gap[:1].upper() + gap[1:]}.{held}"


def extract(vault, keys, entities, designs, plans, blocked, asks, today):
    """The section's whole payload. `designs` and `plans` are the dashboard's own, keyed by app page key, so a design the
    build did not find reads as "no tech design yet" and not as a quiet pass."""
    today = datetime.date.fromisoformat(today) if progress.is_date(today) else None  # a date in this year is said without its year
    said = say.Resolver(vault, today=today).plain
    open_ids = {u.id for u in model.open_unknowns(vault)}
    rows = [row_of(vault, keys, entities, designs, plans, blocked, open_ids, said, asks, today, req) for req in allocation.requirements(vault)]
    tally = counts(rows)
    return {"rows": rows, "counts": tally, "lede": lede(rows, tally, [entities[k] for k in designs]), "notKnown": NOT_KNOWN}
