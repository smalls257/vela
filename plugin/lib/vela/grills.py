"""The grills waiting: which items a Grill could run on now, who runs each, and what stands in the way. Pure.

The Violation this exists to prevent is a Distributed Monolith between three readers of one question. "Is this ready
to decide?" is `gates.verdict`; "did the lead already say yes?" is the Ready to decide lines in the session records;
"who owns it?" is the item's owner or a grill owner in `.vela.yaml`. A dashboard that asked each in its own way would
list a grill the gate refuses, or hide one the lead already agreed to. Here the three are joined once, in the
dashboard's words, and the page only draws the result (Filter).

A grill appears in one of three groups, and an item more than one thing away appears in none (a list of everything
unsettled is the plan itself, not a queue):

- `said-yes`: a session that could not decide kept the lead's yes (`## Ready to decide`) and the item is still not
  decided. Only the date rides along; the words stay in the private file, so the grill opens by asking the lead to say it again.
- `ready`: the grill gate passes.
- `one-away`: the gate names exactly one missing thing. It says who owes it and by when, where the plan knows.

`waiting(vault, verdicts, today)` takes the verdicts the shell computed (`judged_ids` names the items to judge, so
the shell reads the flow checker's record only for those). It reads no disk and no clock.
"""
import re
from dataclasses import dataclass

from vela import gates, grillowners, progress, say, schema, slices, trace
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
    settles: tuple  # plain sentences: the options on the table, else what the item says it is
    holds_up: tuple  # IDs of the epics, slices and apps that wait on it
    apps: tuple  # IDs of the apps it sits on (for the App filter)
    sources: tuple  # SRC IDs it rests on
    missing: dict  # {} unless one-away: {"rule", "plain", "fix", "owed_by", "ask", "due", "question"}
    owner: tuple  # handles who run it: the grill owner, else the item's own owners
    owner_set: bool  # True when a grill owner was set with `vela grill owner`
    join: tuple  # handles asked to join
    yes: dict  # {} unless said-yes: {"session", "date", "title"}

    def as_json(self):
        return {"id": self.id, "name": self.name, "kind": self.kind, "group": self.group, "state": self.state,
                "since": self.since, "settles": list(self.settles), "holdsUp": list(self.holds_up),
                "apps": list(self.apps), "sources": list(self.sources), "missing": self.missing,
                "owner": list(self.owner), "ownerSet": self.owner_set, "join": list(self.join), "yes": self.yes}


# ------------------------------------------------------------------ what is waiting on a yes

def _session_info(vault):
    """{session name: (date, title, text)} for every session record, so a yes can be dated."""
    return {s.name: (str(s.meta.get("date", "")), str(s.meta.get("title", s.name)), s.text) for s in vault.sessions}


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


def settles(vault, ident, resolver):
    """What the grill would settle, in sentences: the options Shape put on the table, else what the item says it is."""
    item, page = _unit(vault, ident)
    bullet = (item.facts.get(schema.OPTIONS_LABEL) if item is not None else None) or (
        next(iter(page.page_bullets(schema.OPTIONS_LABEL)), None) if page is not None else None)
    if bullet is not None:
        options = [resolver.plain(o.strip().rstrip(".")) for o in OPTIONS_SPLIT.split(bullet.value.strip()) if o.strip()]
        if options:
            return tuple(options)
    crossing = item.fact("Crosses the boundary") if item is not None else ""
    if crossing:
        return (resolver.plain(crossing),)
    opening = _opening(page.text) if page is not None and item is None else ""
    return (resolver.plain(opening),) if opening else ()


def _opening(text):
    """The first sentence of a page's first plain paragraph, or "": what the page says it is, when nothing lists options."""
    body = re.sub(r"\A---\n.*?\n---\n", "", text, count=1, flags=re.S)
    for paragraph in re.split(r"\n\s*\n", body):
        paragraph = paragraph.strip()
        if paragraph and not paragraph.startswith(("#", "-", "|", "*", "<", "_", ">", "!", "```")):
            sentence = re.split(r"(?<=[.!?])\s", " ".join(paragraph.split()), maxsplit=1)[0]
            return sentence[:240]
    return ""


def since(vault, ident, state, sessions):
    """The first session that kept the item at its present state, else the first that names it; {} when none does."""
    _, page = _unit(vault, ident)
    named = re.compile(rf"\b{re.escape(ident)}\b" + (rf"|\[\[{re.escape(page.name)}[#|\]]" if page is not None and not vault.item(ident) else ""))
    kept = re.compile(rf"(?:\|{re.escape(ident)}\]\]|\[\[{re.escape(page.name if page is not None else ident)}#[^\]]*\]\])\s*\({re.escape(state)}\)") if state else None
    first = None
    for name, (date, title, text) in sorted(sessions.items()):
        if kept is not None and kept.search(text):
            return {"date": date, "session": name, "title": title, "kept": True}
        if first is None and named.search(text):
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
    """The one thing in the way, with who owes it and by when. Only a question carries both; for any other rule the
    owner of the item owes it and no date is known."""
    reason = verdict.reasons[0]
    out = {"rule": reason.rule, "plain": resolver.plain(reason.plain), "fix": resolver.plain(reason.fix),
           "owed_by": list(owners), "ask": "", "due": "", "question": ""}
    blocking = vault.item(reason.blocked_by[0]) if reason.blocked_by else None
    if blocking is not None:
        out["owed_by"] = list(_handles(blocking.fact("Owner")) or owners)
        out["ask"] = resolver.plain(blocking.fact("Ask"))
        out["question"] = resolver.plain(blocking.fact("Question"))
        due = blocking.fact("Ask by")
        out["due"] = due if progress.is_date(due) else ""
    return out


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
            holds_up=holds_up(vault, ident), apps=apps_of(vault, ident), sources=sources_of(vault, ident),
            missing=missing_thing(vault, verdict, run_by, resolver) if group == ONE_AWAY else {},
            owner=run_by, owner_set=entry is not None and bool(entry.owner), join=entry.join if entry is not None else (),
            yes={k: mark[k] for k in ("session", "date", "title")} if mark else {}))
    return sorted(found, key=lambda g: (GROUPS.index(g.group), -len(g.holds_up), g.id))
