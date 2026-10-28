"""The grills waiting: which items could be settled or grilled now, who runs each, and what stands in the way. Pure.

The Violation this exists to prevent is a Distributed Monolith between three readers of one question. "Is this ready
to decide?" is `gates.verdict`; "did the lead already say yes?" is the Ready to decide lines in the session records;
"who owns it?" is the item's owner or a grill owner in `.vela.yaml`. A dashboard that asked each in its own way would
list a grill the gate refuses, or hide one the lead already agreed to. Here the three are joined once, in the
dashboard's words, and the page only draws the result (Filter).

A grill appears in one of three groups, and an item more than one thing away appears in none (a list of everything
unsettled is the plan itself, not a queue):

- `said-yes`: a yes the lead gave and didn't settle (`## Ready to decide`) and the item is still not decided. Only
  the date rides along; the words stay in the private file, so settling opens by asking the lead to say it again.
- `ready`: the grill gate passes.
- `one-away`: the gate names exactly one missing thing. It says who owes it and by when, where the plan knows.

`waiting(vault, verdicts, today)` takes the verdicts the shell computed (`judged_ids` names the items to judge, so
the shell reads the flow checker's record only for those). It reads no disk and no clock.
"""
import re
from dataclasses import dataclass

from vela import gates, grillowners, privaterecord, progress, say, schema, slices, trace
from vela.decisions import ready

SAID_YES, READY, ONE_AWAY = "said-yes", "ready", "one-away"
GROUPS = (SAID_YES, READY, ONE_AWAY)
DECIDED = ("decided", "fact")
HANDLE = re.compile(schema.HANDLE)
SOURCE = re.compile(schema.SOURCE_TOKEN_RE.pattern)
OPTIONS_SPLIT = re.compile(r";\s+")


@dataclass(frozen=True)
class Grill:
    id: str
    name: str
    kind: str  # the item's kind ("contract", "requirement") or its page's type ("epic", "app-building-blocks")
    group: str
    state: str
    since: dict  # {"date", "session", "title", "kept"}; {} when no session names it
    agrees: dict  # what settling agrees to, in the plan's words; see `agrees`
    settles: tuple  # plain sentences: the options on the table, else what the item says it is
    holds_up: tuple  # IDs of the epics, slices and apps that wait on it
    apps: tuple  # IDs of the apps it sits on (for the App filter)
    sources: tuple  # SRC IDs it rests on
    missing: dict  # {} unless one-away: {"rule", "plain", "fix", "owed_by", "ask", "due", "question"}
    open_question: dict  # {} unless an open question sits under it: {"question", "ask", "owed_by", "due"}; settling notes it
    owner: tuple  # handles who run it: the grill owner, else the item's own owners
    owner_set: bool  # True when a grill owner was set with `vela grill owner`
    join: tuple  # handles asked to join
    yes: dict  # {} unless said-yes: {"session", "date", "title"}

    def as_json(self):
        return {"id": self.id, "name": self.name, "kind": self.kind, "group": self.group, "state": self.state,
                "since": self.since, "settles": [settle_line(x) for x in self.settles], "agrees": self.agrees, "holdsUp": list(self.holds_up),
                "apps": list(self.apps), "sources": list(self.sources), "missing": self.missing,
                "openQuestion": self.open_question,
                "owner": list(self.owner), "ownerSet": self.owner_set, "join": list(self.join), "yes": self.yes}


# ------------------------------------------------------------------ what is waiting on a yes

def _session_info(vault):
    """{session name: (date, title, stub header)} for every session record, so a yes can be dated."""
    return {s.name: (str(s.meta.get("date", "")), str(s.meta.get("title", s.name)), s.meta) for s in vault.sessions}


def _state(vault, ident):
    item = vault.item(ident)
    if item is not None:
        return item.fact("State")
    pages = vault.by_id.get(ident)
    return progress.text(pages[0].meta.get("state")) if pages else ""


def _exists(vault, ident):
    return vault.item(ident) is not None or bool(vault.by_id.get(ident))


def yes_marks(vault):
    """[{id, session, date, title}]: each item a lead's kept yes still waits on, once. Items that are decided now, or
    are no longer in the plan, are left out. The lead's words are not here: a stub carries the date, never the words."""
    sessions = _session_info(vault)
    metas = [s.meta for s in sorted(vault.sessions, key=lambda s: s.name)]
    waiting = ready.waiting(metas, lambda ident: not _exists(vault, ident) or _state(vault, ident) in DECIDED)
    out = []
    for entry in waiting:
        date, title, _ = sessions.get(entry["session"], ("", entry["session"], ""))
        out.append({"id": entry["id"], "session": entry["session"], "date": date, "title": title})
    return out


def judged_ids(vault):
    """The items to judge: every grill candidate, and each item a lead's yes still waits on."""
    return sorted(set(gates.candidates(vault)) | {m["id"] for m in yes_marks(vault)})


# ------------------------------------------------------------------ one item's parts

def _unit(vault, ident):
    """(item or None, page) for an ID; the page is the one that holds it."""
    item = vault.item(ident)
    if item is not None:
        return item, item.page
    pages = vault.by_id.get(ident)
    return None, (pages[0] if pages else None)


def _handles(text):
    return tuple(dict.fromkeys(HANDLE.findall(str(text or ""))))


def default_owners(vault, ident):
    """The handles that own the item: its own Owner fact, else its page's owner."""
    item, page = _unit(vault, ident)
    own = _handles(item.fact("Owner")) if item is not None else ()
    return own or (_handles(page.meta.get("owner")) if page is not None else ())


def _options_of(item, page, resolver):
    """The options Shape put on the table, in the plan's words: ["Keep it in the shop (picked)", "x: rejected, why"], or []."""
    bullet = (item.facts.get(schema.OPTIONS_LABEL) if item is not None else None) or (
        next(iter(page.page_bullets(schema.OPTIONS_LABEL)), None) if page is not None else None)
    if bullet is None:
        return []
    return [resolver.plain(o.strip().rstrip(".")) for o in OPTIONS_SPLIT.split(bullet.value.strip()) if o.strip()]


def settles(vault, ident, resolver):
    """What the grill would settle, in sentences: the options Shape put on the table, else what the item says it is."""
    item, page = _unit(vault, ident)
    options = _options_of(item, page, resolver)
    if options:
        return tuple(options)
    crossing = item.fact("Crosses the boundary") if item is not None else ""
    if crossing:
        return (resolver.plain(crossing),)
    opening = _opening(page.text) if page is not None and item is None else ""
    return (resolver.plain(opening),) if opening else ()


def _plain_paragraphs(text):
    body = re.sub(r"\A---\n.*?\n---\n", "", text, count=1, flags=re.S)
    for paragraph in re.split(r"\n\s*\n", body):
        paragraph = paragraph.strip()
        if paragraph and not paragraph.startswith(("#", "-", "|", "*", "<", "_", ">", "!", "```")):
            yield " ".join(paragraph.split())


ABBREVIATIONS = frozenset(("e.g.", "i.e.", "dr.", "mr.", "mrs.", "ms.", "vs.", "u.s.", "u.k.", "a.m.", "p.m.", "st.", "approx.", "no.", "inc.", "ltd."))


def _sentences(paragraph):
    """Split at sentence ends, but not after an abbreviation: "i.e. The" stays in one sentence (a cut there would
    quote the plan as saying something it does not)."""
    out = []
    for piece in re.split(r"(?<=[.!?])\s+(?=[A-Z\[])", paragraph):
        if out and out[-1].split()[-1].lower() in ABBREVIATIONS:
            out[-1] = f"{out[-1]} {piece}"
        else:
            out.append(piece)
    return out


def _bullets_after_opening(text):
    """The top-level bullets in the list that follows the page's opening paragraph, each as one line (wrapped lines
    joined); [] when the opening is not followed by a list."""
    body = re.sub(r"\A---\n.*?\n---\n", "", text, count=1, flags=re.S)
    blocks = [b.strip("\n") for b in re.split(r"\n\s*\n", body) if b.strip()]
    plain = [i for i, b in enumerate(blocks) if b.strip() and not b.strip().startswith(("#", "-", "|", "*", "<", "_", ">", "!", "```"))]
    if not plain or plain[0] + 1 >= len(blocks) or not blocks[plain[0] + 1].startswith("- "):
        return []
    bullets = []
    for line in blocks[plain[0] + 1].split("\n"):
        if line.startswith("- "):
            bullets.append(line[2:].strip())
        elif line.startswith(" ") and line.strip() and not line.lstrip().startswith("- ") and bullets:
            bullets[-1] += " " + line.strip()
    return bullets


def _opening(text, sentences=1):
    """The first `sentences` sentences of a page's first plain paragraph (all of it when `sentences` is None), or "":
    what the page says it is, when nothing lists options."""
    for paragraph in _plain_paragraphs(text):
        if sentences is None:
            return paragraph
        return " ".join(_sentences(paragraph)[:sentences]) if sentences > 1 else _sentences(paragraph)[0][:240]
    return ""


OPENING_SENTENCES, DOES_NOT_CAP, DETAILS_SHOWN = 3, 3, 2
DOES_NOT = re.compile(r"It (?:does not|doesn't)\b")


def _item_section(item):
    """The item's section below its heading: up to the next heading at level 3 or above."""
    lines = item.page.text.split("\n")
    later = [h.line for h in item.page.headings if h.line > item.line and h.level <= 3]
    return lines[item.line:(later[0] - 1) if later else len(lines)]


def _detail_bullets(item):
    """The requirement's own detail bullets (top level, not a **Label:** fact), in the plan's words."""
    return [line[2:].strip() for line in _item_section(item) if line.startswith("- ") and not line.startswith("- **")]


PICKED = re.compile(r"\s*\(picked\)\s*$", re.I)


def settle_line(text):
    """One option as a line of the settle prompt and panel: the pick is "Proposed: X", a rejected one "Set aside: X,
    because why". The (picked) rule lives here so the page only draws it."""
    if PICKED.search(text):
        return f"Proposed: {PICKED.sub('', text)}"
    parts = re.split(r":\s*rejected,?\s*", text, maxsplit=1, flags=re.I)
    if len(parts) == 2:
        return f"Set aside: {parts[0][:1].upper() + parts[0][1:]}, because {parts[1].rstrip('.')}"
    return text[:1].upper() + text[1:]


def _agrees_option_line(options):
    """{"picked", "setAside"} when one option is picked, else {"choosing": [...]} for two or more, else {}."""
    picked = [o for o in options if PICKED.search(o)]
    if picked:
        return {"picked": PICKED.sub("", picked[0]), "setAside": len(options) - 1}
    names = [o.split(":")[0].strip() for o in options]
    return {"choosing": names} if len(names) > 1 else {}


def agrees(vault, ident, resolver):
    """What settling the item agrees to, copied from the plan: {"lead", "points", "details", "more", "page", plus
    "picked"/"setAside" or "choosing" when options sit on the table}. A requirement gives its statement and its first
    two detail bullets (the rest in "more"); a contract its description and what crosses the boundary; a page its
    opening and the "It does not" sentences it states; "page" is True when the whole page is there to read."""
    item, page = _unit(vault, ident)
    out = {"lead": "", "points": [], "details": [], "more": [], "page": item is None and page is not None}
    if item is not None:
        out["lead"] = resolver.plain(_opening("\n".join(_item_section(item)), None))
        if item.kind == "contract" and item.fact("Crosses the boundary"):
            out["points"] = [f"Crosses the boundary: {resolver.plain(item.fact('Crosses the boundary'))}"]
        if item.kind == "requirement":
            details = [resolver.plain(d) for d in _detail_bullets(item)]
            out["details"], out["more"] = details[:DETAILS_SHOWN], details[DETAILS_SHOWN:]
    elif page is not None:
        paragraphs = list(_plain_paragraphs(page.text))
        shown = _sentences(paragraphs[0])[:OPENING_SENTENCES] if paragraphs else []
        out["lead"] = resolver.plain(" ".join(shown))
        written = paragraphs + _bullets_after_opening(page.text)
        says = [x for p in written for x in _sentences(p) if DOES_NOT.match(x) and x not in shown]
        out["points"] = [resolver.plain(x) for x in dict.fromkeys(says)][:DOES_NOT_CAP]
    out.update(_agrees_option_line(_options_of(item, page, resolver)))
    return out


def since(vault, ident, state, sessions):
    """The first session whose stub lists the item as ready to decide (a kept yes), else the first whose stub lists
    it as a challenge; {} when none does. The words of a session are on the lead's machine, so the stubs' lists are
    all a clone can read; `state` is the item's present state, and a yes only waits while the item is at assumption."""
    first = None
    for name, (date, title, meta) in sorted(sessions.items()):
        if state == ready.KEPT_AT and ident in privaterecord.listed(meta, "ready"):
            return {"date": date, "session": name, "title": title, "kept": True}
        if first is None and ident in (privaterecord.listed(meta, "ready") + privaterecord.listed(meta, "challenges")):
            first = {"date": date, "session": name, "title": title, "kept": False}
    return first or {}


def sources_of(vault, ident):
    item, page = _unit(vault, ident)
    if item is not None:
        text = " ".join(item.fact(label) for label in ("Source", "Sources"))
        return tuple(dict.fromkeys(SOURCE.findall(text)))
    listed = page.meta.get("sources") if page is not None else None
    return tuple(dict.fromkeys(SOURCE.findall(" ".join(str(s) for s in listed)))) if isinstance(listed, list) else ()


def apps_of(vault, ident):
    """The app pages the item sits on or is delivered by: its own page for an app, the providing and consuming apps for
    a contract, the listed apps for an epic."""
    item, page = _unit(vault, ident)
    if page is None:
        return ()
    found = []
    if page.type == "app-building-blocks":
        found.append(page.id)
    elif page.type == "app-runtime":
        app = vault.page(page.name[: -len("-runtime")] + "-building-blocks") if page.name.endswith("-runtime") else None
        found.append(app.id if app is not None else "")
    elif page.type == "epic":
        found += trace.listed(page, "apps")
    if item is not None and item.kind == "contract":
        found += [a.id for a in vault.consumers(item)]
    return tuple(dict.fromkeys(a for a in found if a))


def holds_up(vault, ident):
    """The IDs of what waits on this being decided: the epics that list its app or deliver it, and the slices whose
    flows cross it. A page ID for an epic or slice, never a heading."""
    item, page = _unit(vault, ident)
    apps = set(apps_of(vault, ident))
    base = ident.split(".")[0]
    found = [] if page is not None and page.type == "epic" else [  # an epic does not wait on another epic that shares an app
        e.id for e in trace.epics(vault) if apps & set(trace.listed(e, "apps")) or {ident, base} & set(trace.listed(e, "delivers"))]
    found += [s.id for s in slices.read_slices(vault) if s.id and (ident in s.joins or ident in s.flows)]
    return tuple(dict.fromkeys(i for i in found if i != ident))


def missing_thing(vault, verdict, owners, resolver):
    """The one thing in the way, with who owes it. The owner of the item owes it and no date is known."""
    reason = verdict.reasons[0]
    out = {"rule": reason.rule, "plain": resolver.plain(reason.plain), "fix": resolver.plain(reason.fix),
           "owed_by": list(owners), "ask": "", "due": "", "question": ""}
    return out


def open_question_of(vault, verdict, owners, resolver):
    """The first open question under the item, with who owes the answer and by when, for its card: {} when none. The
    item is ready all the same; settling it notes the question as still open."""
    blocking = vault.item(verdict.open_blockers[0]) if verdict.open_blockers else None
    if blocking is None:
        return {}
    due = blocking.fact("Ask by")
    return {"question": resolver.plain(blocking.fact("Question")), "ask": resolver.plain(blocking.fact("Ask")),
            "owed_by": list(_handles(blocking.fact("Owner")) or owners), "due": due if progress.is_date(due) else ""}


# ------------------------------------------------------------------ the list

def waiting(vault, verdicts, today):
    """[Grill]: the said-yes first, then the ready, then those one thing away; most held up first inside each group.
    `verdicts` is {ID: gates.Verdict}. An item with more than one thing in the way and no kept yes is left out."""
    resolver = say.Resolver(vault)
    owners, _ = grillowners.read(vault.config)
    yes = {m["id"]: m for m in yes_marks(vault)}
    sessions = _session_info(vault)
    found = []
    for ident, verdict in sorted(verdicts.items()):
        group = SAID_YES if ident in yes else READY if verdict.ready else ONE_AWAY if len(verdict.reasons) == 1 else ""
        if not group or not _exists(vault, ident):
            continue
        item, page = _unit(vault, ident)
        state = _state(vault, ident)
        own = default_owners(vault, ident)
        entry = owners.get(ident)
        run_by = (entry.owner,) if entry is not None and entry.owner else own
        mark = yes.get(ident)
        found.append(Grill(
            id=ident, name=verdict.name, kind=item.kind if item is not None else page.type, group=group, state=state,
            since=since(vault, ident, state, sessions), settles=settles(vault, ident, resolver),
            agrees=agrees(vault, ident, resolver),
            holds_up=holds_up(vault, ident), apps=apps_of(vault, ident), sources=sources_of(vault, ident),
            missing=missing_thing(vault, verdict, run_by, resolver) if group == ONE_AWAY else {},
            open_question=open_question_of(vault, verdict, run_by, resolver),
            owner=run_by, owner_set=entry is not None and bool(entry.owner), join=entry.join if entry is not None else (),
            yes={k: mark[k] for k in ("session", "date", "title")} if mark else {}))
    return sorted(found, key=lambda g: (GROUPS.index(g.group), -len(g.holds_up), g.id))
