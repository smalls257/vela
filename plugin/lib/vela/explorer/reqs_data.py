"""The Requirements section's data: every functional requirement and whether it is met so far.

    extract(vault, keys, entities, designs, plans, blocked, asks, today) -> {rows, counts, lede, notKnown, orphans}

The Violation this exists to prevent is a Distributed Monolith of rules: "is it carried, released, in an epic,
designed, built, free of open questions" decided once here, in Python, from the readers the rest of the dashboard
already uses (allocation, releases, trace and criteria, the designs and plans the build has read, model.blockers). The
page draws `rows` and never works a check out for itself, so a second view of the same requirements cannot disagree.
That includes the small flags the page draws from: a criterion's Trace chip says whether it waits on an open question,
a box says whether it is a gap, a row says which filters it falls in.

Two more failures are ruled out by how it speaks. A Paper Tiger: vela cannot see code or test results, so a row never
says "met"; it says how many of six checks are met so far, and `notKnown` says what the plan cannot see. A Silent
Fallback: a check that cannot be worked out (no tech design from an app, no breakdown at all) says so in words
("no tech design yet from Consent and identity or Summarizer") and counts as not met, never as a quiet green.

Each check is {k, v, short, long, next}: `v` is "yes", "part" or "no"; `short` is the table cell; `long` is the sentence
the panel and the focus view quote; `next` is what to do about it. Sentences carry names and American dates, never
codes or slash commands: IDs travel only as keys, and a session is named as the dashboard names it.

Each reader is read once, in `Reads`, not once per requirement.
"""
import datetime
import re

from vela import allocation, breakdown, criteria, model, progress, reading, releases, say, slices, trace

from .panel_data import short as clause
from .record import plain

CHECKS = ("carried", "release", "epic", "designed", "stories", "open")
YES, PART, NO = "yes", "part", "no"
NOT_KNOWN = "Built and tested: not something the plan knows; see the tracker."
FLOW_ID = re.compile(r"^FLO-\d+$")
CONTRACT_ID = re.compile(r"^CON-\d+$")
UNKNOWN_ID = re.compile(r"\bUNK-\d+\b")
ID_SHAPE = re.compile(reading.VAULT_ID + r"(?:@\S+)?")


def base(item_id):
    return item_id.split("@")[0]


def session(command):
    """"allocate" -> "the allocate session": a session is named as the dashboard names it (core.js sessionName)."""
    return f"the {command} session"


def check(k, v, short, long, nxt=""):
    return {"k": k, "v": v, "short": short, "long": long, "next": "" if v == YES else nxt}


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


# --------------------------------------------------------------------------- every reader, read once

class Reads:
    """What each existing reader says about every requirement, read once for the whole section."""

    def __init__(self, vault, keys, entities, designs, plans, blocked, asks, today):
        self.vault, self.keys, self.entities = vault, keys, entities
        self.designs, self.plans, self.blocked, self.asks = designs, plans, blocked, asks
        self.today = datetime.date.fromisoformat(today) if progress.is_date(today) else None  # a date in this year is said without its year
        self.said = say.Resolver(vault, today=self.today).plain
        self.open_ids = {u.id for u in model.open_unknowns(vault)}
        self.carried = allocation.carried(vault)
        self.rows = allocation.rows(vault)
        self.all_releases = releases.releases(vault)
        self.left_out = slices.left_out(vault)
        self.release_at = {}
        for index, release in enumerate(self.all_releases, 1):
            for row in release.rows:
                self.release_at.setdefault(row.requirement, (index, release, row))
        self.epic_at = self.read_epics()

    def read_epics(self):
        """{requirement ID: [(epic key, criteria that name it, their Trace IDs)]}: criteria.read is the reader of which epic
        criterion traces to a requirement."""
        found = {}
        for epic in trace.epics(self.vault):
            hits = {}
            for c in criteria.read(epic):
                if c.struck:
                    continue
                for req_id in dict.fromkeys(base(t) for t in c.trace if base(t) in self.vault.items):
                    hits.setdefault(req_id, []).append(c)
            for req_id, cs in hits.items():
                found.setdefault(req_id, []).append((self.keys.page(epic), len(cs), [t for c in cs for t in c.trace]))
        return found


# --------------------------------------------------------------------------- what each reader says about one requirement

def carriers(reads, req):
    """[{key, name, share, id}] for each app with a row at assumption or later; allocation.carried is the one rule for what
    carries. An app with two rows says both shares."""
    shares = {}
    for row in reads.carried.get(req.id, []):
        shares.setdefault(reads.keys.page(row.app), [row.app, []])[1].append(row.share)
    return [{"key": key, "name": reads.entities[key]["title"], "share": "; ".join(s for s in said if s), "id": app.id}
            for key, (app, said) in shares.items()]


def guessers(reads, req, carrying):
    """Names of the apps whose only row for it is an inkling: a guess at a share, which carries nothing."""
    have = {a["key"] for a in carrying}
    found = [reads.keys.page(r.app) for r in reads.rows if r.requirement == req.id and r.state == "inkling"]
    return [reads.entities[k]["title"] for k in dict.fromkeys(found) if k not in have]


def release_name(name):
    """The heading as the Releases view and the capability cards name it: "Release one: February pilot" is "February pilot"."""
    return re.sub(r"^[^:]*:\s*", "", name).strip() or name


def release_note(reads, row):
    """The Note cell in words. An open question named by ID is said as the question it is, so "Dropped if UNK-064 says
    ..." keeps reading as a sentence."""
    if not row.note:
        return ""
    asked = UNKNOWN_ID.sub(lambda m: f"the answer to “{reads.vault.name_of(m.group(0))}”", row.note)
    return reads.said(asked).rstrip(".")


def release_check(reads, req):
    found = reads.release_at.get(req.id)
    if found is None:
        why, where = reads.left_out.get(req.id, (None, ""))
        reason = (f"on no release, and {where} says why: {why.reason.rstrip('.')}" if why and why.reason
                  else "on no release, so nothing says when it ships")
        if not reads.all_releases:
            reason = "no release is planned yet"
        return None, check("release", NO, "none", reason, "Add it to the release that will deliver it, once nothing holds it back.")
    index, release, row = found
    when = say.date_words(release.target) if release.target else "no date yet"
    note = release_note(reads, row)
    partial = f"; only {'criterion' if len(row.criteria) == 1 else 'criteria'} {say.names_said([str(n) for n in row.criteria])} of it" if row.criteria else ""
    long = f"delivered in “{release.name}”, {when}{partial}" + (f"; {first_lower(note)}" if note else "")
    shown = release_name(release.name)
    return ({"name": release.name, "short": shown, "date": when, "note": note, "key": f"release:{index}"},
            check("release", YES, shown, long))


def design_entry(reads, carrier, req):
    """{app, designed, components, doc, title, say}: a design traces it when one of its components' trace entries names it
    (the requirement bare, or as CAP-nnn.FRn@APP-x for this app; an entry for another app's share is not this app's)."""
    design = reads.designs.get(carrier["key"])
    names = lambda e: base(e["id"]) == req.id and (e["id"] == base(e["id"]) or e["id"].endswith("@" + carrier["id"]))
    owners = [name for name, entries in (design["trace"] if design else {}).items() if any(names(e) for e in entries)]
    if owners:
        return {"app": carrier["key"], "name": carrier["name"], "designed": True, "components": owners, "doc": design["path"], "title": "", "say": ""}
    title, said = (("No design yet", f"{carrier['name']}: no tech design yet") if design is None
                   else ("Design does not trace it", f"{carrier['name']}: its tech design does not trace it"))
    return {"app": carrier["key"], "name": carrier["name"], "designed": False, "components": [], "doc": design["path"] if design else "",
            "title": title, "say": said, "noDesign": design is None}


def stories_entry(reads, carrier, req):
    """{app, breakdown, stories, putOff, reason, title, say}: the stories the app's breakdown credits with building it. A story
    that is deferred or merged, or a requirement the plan lists as not planned, is put off and counts as no story."""
    plan = reads.plans.get(carrier["key"])
    if plan is None:
        return {"app": carrier["key"], "name": carrier["name"], "breakdown": False, "stories": [], "names": {}, "putOff": False, "reason": "",
                "title": "No stories yet", "say": f"{carrier['name']}: no breakdown yet"}
    named = [i for t in plan["coverage"]["targets"] if base(t["target"]) == req.id for i in t["stories"]]
    state = {s["id"]: s for s in plan["stories"]}
    built = [i for i in dict.fromkeys(named) if state[i]["state"] not in breakdown.NOT_BUILT]
    parked = [i for i in dict.fromkeys(named) if i not in built]
    said = next((line for line in plan["notPlanned"] if re.search(rf"(?<![\w.-]){re.escape(req.id)}\b", line)), "")
    put_off = not built and bool(parked or said)
    shown = built or parked
    title = "" if built else "Put off" if put_off else "No stories yet"
    words = "" if built else f"{carrier['name']}: put off" if put_off else f"{carrier['name']}: no story builds it"
    return {"app": carrier["key"], "name": carrier["name"], "breakdown": True, "stories": shown, "names": {i: state[i]["name"] for i in shown},
            "putOff": put_off, "reason": said, "title": title, "say": words}


# --------------------------------------------------------------------------- a criterion's Trace line, said by the data

def trace_entry(reads, token, open_ids):
    """{id, key, said, waits}: one ID on a requirement criterion's Trace line, ready to draw. `waits` is the one flag the
    page draws "waits on:" from; `key` is what a click opens, "" when the plan holds nothing by that ID."""
    vault, keys, ident = reads.vault, reads.keys, base(token)
    entry = keys.names.lookup(ident)
    if entry is not None:
        key = keys.key_of(entry)
        if ident in open_ids:
            return {"id": ident, "key": key, "said": f"waits on: {entry.name}", "waits": True}
        return {"id": ident, "key": key, "said": entry.name, "waits": False}
    row = vault.row_ids.get(ident)  # a constraint or other table row: it opens its page, which is where the row is
    if row is not None:
        page = row[0]
        cells = next((t.rows[t.row_lines.index(row[1])] for t in page.tables if row[1] in t.row_lines), [])
        return {"id": ident, "key": "read:" + keys.page(page), "said": clause(cells[1], 56) if len(cells) > 1 else ident, "waits": False}
    return {"id": ident, "key": "", "said": "not in this plan", "waits": False}


def criteria_rows(reads, req):
    """[{text, trace: [trace_entry]}]: words in a Trace line that are not IDs ("the Summarizer runtime page") are prose, not chips."""
    out = []
    for text, tokens in releases.requirement_criteria(req):
        ids = [t for t in tokens if ID_SHAPE.fullmatch(t)]
        out.append({"text": plain(text), "trace": [trace_entry(reads, t, reads.open_ids) for t in ids]})
    return out


def open_questions(req, reads, epic_traces, criteria_list):
    """Open unknowns, each once: those whose Blocks lists it, those an epic criterion for it names, and those its own
    criteria's Trace lines name (CONVENTIONS: Requirements and allocation)."""
    held = [u.id for u in reads.blocked.get(req.id, [])]
    own = [t["id"] for c in criteria_list for t in c["trace"] if t["waits"]]
    return list(dict.fromkeys(held + [i for i in epic_traces if i in reads.open_ids] + own))


# --------------------------------------------------------------------------- the six checks, in the order work flows

def carried_check(carrying, guessed):
    names = [c["name"] for c in carrying]
    if names:
        return check("carried", YES, plural(len(names), "app"), f"carried by {say.names_said(names)}")
    long = "no app carries it yet: no app has taken it on at assumption or later"
    return check("carried", NO, "no app", long + (f"; {say.names_said(guessed)} only guessed at a share" if guessed else ""),
                 f"Divide it among the apps in {session('allocate')}.")


def epic_check(epics, entities):
    n = sum(e["criteria"] for e in epics)
    if not n:
        return check("epic", NO, "none", "no epic criterion traces to it", "Name it on the Trace line of the epic criterion that builds it.")
    where = say.names_said([entities[e["key"]]["title"] for e in epics])
    return check("epic", YES, plural(n, "criterion", "criteria"), f"{plural(n, 'epic criterion', 'epic criteria')} trace{'s' if n == 1 else ''} to it, in {where}")


def designed_check(designs, carrying):
    if not carrying:
        return check("designed", NO, "no app", "no app carries it, so no tech design can trace it", f"Divide it among the apps in {session('allocate')}.")
    done = [d for d in designs if d["designed"]]
    v = share_of(len(done), len(carrying))
    if v == YES:
        return check("designed", v, f"{len(done)} of {plural(len(carrying), 'app')}", "every app that carries it has a tech design that traces it")
    nodesign = [d["name"] for d in designs if not d["designed"] and d.get("noDesign")]
    notrace = [d["name"] for d in designs if not d["designed"] and not d.get("noDesign")]
    parts, steps = [], []
    if nodesign:
        parts.append(f"no tech design yet from {either_said(nodesign)}")
        steps.append(f"The teams of {say.names_said(nodesign)} run the design session from the plan's folder.")
    if notrace:
        parts.append(f"{say.names_said(notrace)}'s tech design does not trace it" if len(notrace) == 1 else f"the tech designs of {say.names_said(notrace)} do not trace it")
        steps.append(f"Add it to the Trace table of the tech design of {say.names_said(notrace)}.")
    if done:
        parts.append(f"{say.names_said([d['name'] for d in done])} {'traces' if len(done) == 1 else 'trace'} it")
    return check("designed", v, f"{len(done)} of {plural(len(carrying), 'app')}", "; ".join(parts), " ".join(steps))


def stories_check(entries, carrying):
    if not carrying:
        return check("stories", NO, "no app", "no app carries it, so no story can build it", f"Divide it among the apps in {session('allocate')}.")
    built = [e for e in entries if e["stories"] and not e["putOff"]]
    v = share_of(len(built), len(carrying))
    count = f"{len(built)} of {plural(len(carrying), 'app')}"
    if v == YES:
        return check("stories", v, count, "every app that carries it has a story that builds it")
    parked = [e for e in entries if e["putOff"]]
    nobreak = [e["name"] for e in entries if not e["breakdown"]]
    nostory = [e["name"] for e in entries if e["breakdown"] and not e["stories"] and not e["putOff"]]
    parts = []
    if parked:
        undated = ", and no review date is recorded" if any("no review date" in e["reason"] for e in parked) else ""
        parts.append(f"put off in the breakdown of {say.names_said([e['name'] for e in parked])}{undated}")
    if nobreak:
        parts.append(f"no breakdown yet from {either_said(nobreak)}")
    if nostory:
        parts.append(f"no story yet from {either_said(nostory)}")
    return check("stories", v, "put off" if parked and not built else count, "; ".join(parts),
                 "Those teams write the work breakdown once their design is done." if nobreak or nostory else "The team lead decides when the work comes back.")


def ask_words(questions, asks, today):
    """"Ask Legal counsel, by October 29." from the dashboard's own asks (who holds each answer, and by when)."""
    held = [a for a in asks if a["id"] in questions]
    who = list(dict.fromkeys(a["ask"]["name"] for a in held if a["ask"]["name"]))
    dates = sorted(a["askBy"] for a in held if a["askBy"])
    by = f", by {say.date_words(dates[0], today)}" if dates else ""
    return f"Ask {say.names_said(who)}{by}." if who else "Ask whoever owns each question."


def open_check(questions, reads):
    if not questions:
        return check("open", YES, "clear", "no open question holds it")
    names = [f"“{reads.vault.name_of(q)}”" for q in questions]
    return check("open", NO, plural(len(questions), "question"), f"waits on {say.names_said(names)}", ask_words(questions, reads.asks, reads.today))


def decided_check(state):
    words = {"decided": (YES, "decided: a Grill settled it"),
             "fact": (PART, "a fact the plan records, not yet decided: a Grill decides it"),
             "assumption": (PART, "still an assumption: a Grill decides it"),
             "inkling": (NO, "still an inkling: it is not yet an assumption")}
    v, long = words.get(state, (NO, "no state recorded"))
    return {"k": "decided", "v": v, "short": state or "none", "long": long, "next": ""}


# --------------------------------------------------------------------------- one requirement, and the page's words

def row_of(reads, req):
    entities, keys = reads.entities, reads.keys
    carrying = carriers(reads, req)
    hits = reads.epic_at.get(req.id, [])
    epics = [{"key": k, "criteria": n} for k, n, _ in hits]
    epic_traces = list(dict.fromkeys(t for _, _, ts in hits for t in ts))
    release, release_row = release_check(reads, req)
    crit = criteria_rows(reads, req)
    design_rows = [design_entry(reads, c, req) for c in carrying]
    story_rows = [stories_entry(reads, c, req) for c in carrying]
    questions = open_questions(req, reads, epic_traces, crit)
    checks = [carried_check(carrying, guessers(reads, req, carrying)), release_row, epic_check(epics, entities),
              designed_check(design_rows, carrying), stories_check(story_rows, carrying), open_check(questions, reads)]
    through = [c for c in dict.fromkeys([c for r in reads.carried.get(req.id, []) for c in r.through] + [t for t in epic_traces if CONTRACT_ID.match(t)]) if reads.vault.item(c)]
    flows = [keys.page(reads.vault.by_id[f][0]) for f in dict.fromkeys(t for t in epic_traces if FLOW_ID.match(t)) if f in reads.vault.by_id]
    page_key, state = keys.page(req.page), req.fact("State")
    return {"id": req.id, "key": req.id, "name": entities[req.id]["title"], "capability": req.page.id or page_key, "capabilityKey": page_key,
            "capabilityTitle": entities[page_key]["title"], "state": state,
            "text": entities[req.id]["text"], "criteria": crit,
            "apps": [{k: c[k] for k in ("key", "name", "share")} for c in carrying], "through": through, "flows": flows,
            "release": release, "releaseNote": release["note"] if release else "", "epics": epics, "designs": design_rows, "stories": story_rows,
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


def orphans(reads, written):
    """Requirements an app's allocation or a release names that no capability page writes: the section cannot list them as
    rows, so it says they are there. [{id, said}]."""
    named = {}
    for r in reads.rows:
        if r.requirement and r.requirement not in written:
            named.setdefault(r.requirement, []).append(f"{reads.entities[reads.keys.page(r.app)]['title']}'s allocation")
    for release in reads.all_releases:
        for row in release.rows:
            if row.requirement and row.requirement not in written:
                named.setdefault(row.requirement, []).append(f"“{release.name}”")
    return [{"id": i, "said": f"named by {say.names_said(list(dict.fromkeys(by)))}, but no requirement of that ID is written"} for i, by in sorted(named.items())]


def lede(rows, tally, designs):
    """The line under the title, from the numbers the filters carry. Nothing here is a status the plan cannot back."""
    if not rows:
        return f"No functional requirements are written yet, so there is nothing to check. {session('requirements').capitalize()} writes them."
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
    reads = Reads(vault, keys, entities, designs, plans, blocked, asks, today)
    written = allocation.requirements(vault)
    rows = [row_of(reads, req) for req in written]
    tally = counts(rows)
    return {"rows": rows, "counts": tally, "lede": lede(rows, tally, [entities[k] for k in designs]), "notKnown": NOT_KNOWN,
            "orphans": orphans(reads, {r.id for r in written})}
