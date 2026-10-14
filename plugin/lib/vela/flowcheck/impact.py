"""The impact walk: which slices a change can touch, and why. Pure: two catalogs in, slices and reasons out.

What changed is read off the checker's own inputs, not guessed from file names: the catalog before the change and the
catalog after (`changes`). The catalog is everything the checker reads, so an edit that leaves it alike (a contract's
prose, a page the checker never reads) provably moves no result. Then the walk (`walk`) follows the links the checker
follows:

    contract -> the flows calling it -> their slices
    entity   -> the flows that set it, start from it or leave it, or call a contract whose cases set or guard on it,
                and the entities an invariant ties to it -> their slices (shared: its paired journeys)
    event    -> the flows publishing or awaiting it, or calling a contract whose cases emit it -> their slices
    app      -> the flows it takes part in, and the providers whose calls it makes (F12) -> their slices
    flow     -> its slices
    slice    -> itself, and the slices after it only when one of its flows now leaves different states (F13)

Each affected slice comes with its reason chains, in names: "Record consent changed → A person switches Heron on →
SLC-001 Switch Heron on". When the walk cannot tell (no catalog from before, a whole-file problem that came or went),
every slice is affected and `everything` says why: the walk never narrows on a guess (Silent Fallback). A change no
slice reaches is listed in `untouched`, so it is said rather than dropped.
"""
import json
from dataclasses import dataclass, field, replace

from vela import slices as slices_mod
from vela.flowcheck import record
from vela.flowcheck.tables import CaseTable, Entity, EventTable, Flow, FlowLine, Override, Problem

ARROW = " → "


@dataclass
class Changes:
    contracts: set = field(default_factory=set)
    events: set = field(default_factory=set)
    entities: set = field(default_factory=set)  # slugs
    flows: set = field(default_factory=set)
    slices: set = field(default_factory=set)  # keys
    apps: set = field(default_factory=set)  # keys whose title, outside-ness or calls changed
    unknown: list = field(default_factory=list)  # reasons the walk cannot tell what a change touches
    moved: object = None  # Changes: items that only moved on their page (their line numbers changed)

    def __bool__(self):
        return bool(self.contracts or self.events or self.entities or self.flows or self.slices or self.apps or self.unknown)


@dataclass
class Walk:
    affected: dict = field(default_factory=dict)  # slice key -> [reason chain]
    everything: str = ""  # why every slice is checked, when the walk cannot tell
    untouched: list = field(default_factory=list)  # changed items no slice reaches, in words


def _entities_by_slug(cat):
    return {e.slug: e for e in cat.entities.values()}


def unplaced(value):
    """A catalog record with where it sits on its page left out: line numbers, and the line part of "path:line". Two
    records alike but for this are the same item, moved."""
    if isinstance(value, FlowLine):
        return ["FlowLine", value.kind, record.canonical(value.parts)]
    if isinstance(value, slices_mod.Slice):
        return record.canonical(replace(value, line=0, lines={}))
    if isinstance(value, Entity):
        return record.canonical(replace(value, invariants=tuple((text, 0, expr) for text, _, expr in value.invariants)))
    if isinstance(value, (CaseTable, EventTable)):
        return record.canonical(replace(value, source=_path(value.source)))
    if isinstance(value, (Override, Problem)):
        return record.canonical(replace(value, where=_path(value.where)))
    if isinstance(value, Flow):
        return ["Flow", value.id, value.title, value.path, [unplaced(t) for t in value.lines],
                [unplaced(o) for o in value.overrides], value.has_diagram]
    if isinstance(value, tuple):
        return [unplaced(v) for v in value]
    return record.canonical(value)


def _path(where):
    head, _, tail = str(where).rpartition(":")
    return head if head and tail.isdigit() else where


def changes(old, new):
    """What differs between two catalogs, item by item, and, in `moved`, what only moved on its page. Both count: a
    finding names its line, so a moved line is a changed result; but a reason chain says "moved" for it, not
    "changed", so a lead is not sent looking for an edit to a contract nobody touched."""
    real = _changes(old, new, unplaced)
    full = _changes(old, new, record.canonical)
    real.moved = Changes(*(getattr(full, name) - getattr(real, name) for name in
                           ("contracts", "events", "entities", "flows", "slices", "apps")))
    return real


def _changes(old, new, form):
    def differs(a, b):
        return form(a) != form(b)

    out = Changes()
    for name in ("contracts", "events", "flows"):
        a, b = getattr(old, name), getattr(new, name)
        getattr(out, name).update(k for k in set(a) | set(b) if differs(a.get(k), b.get(k)))
    a, b = _entities_by_slug(old), _entities_by_slug(new)
    out.entities.update(k for k in set(a) | set(b) if differs(a.get(k), b.get(k)))
    a, b = {s.key: s for s in old.slices}, {s.key: s for s in new.slices}
    out.slices.update(k for k in set(a) | set(b) if differs(a.get(k), b.get(k)) or
                      differs(old.slice_overrides.get(k, ()), new.slice_overrides.get(k, ())))
    out.apps.update(k for k in set(old.apps) | set(new.apps) if differs(old.apps.get(k), new.apps.get(k)))
    out.apps.update(k for k in set(old.consumes) | set(new.consumes)
                    if set(old.consumes.get(k, ())) != set(new.consumes.get(k, ())))
    _problems(old, new, out, form)
    return out


def _problems(old, new, out, form):
    """A problem belongs to its item, so it changes that item. One that belongs to no item (a whole file that does not
    read) could touch anything: the walk cannot tell."""
    before = {_key(form(p)): p for p in old.problems}
    after = {_key(form(p)): p for p in new.problems}
    for key in sorted(set(before) ^ set(after)):
        p = before.get(key) or after.get(key)
        item = p.item
        if not item:
            out.unknown.append(f"{_path(p.where)} does not read the same as before ({p.text})")
        elif item.startswith("CON-"):
            out.contracts.add(item)
        elif item.startswith("EVT-"):
            out.events.add(item)
        elif item.startswith("FLO-"):
            out.flows.add(item)
        else:
            entity = new.entity(item) or old.entity(item)
            if entity is not None:
                out.entities.add(entity.slug)
            else:
                out.unknown.append(f"a problem on {item} ({p.text})")


def _key(value):
    return json.dumps(value, sort_keys=True)


# --- what a flow reaches -----------------------------------------------------------------------------------------------

@dataclass
class Reach:
    contracts: set = field(default_factory=set)
    events: set = field(default_factory=set)
    entities: dict = field(default_factory=dict)  # slug -> how the flow reaches it, for the chain
    apps: set = field(default_factory=set)


def reach(cat, flow):
    """Everything one flow's check reads, by ID, in one catalog."""
    out = Reach()
    names = {}
    for t in flow.lines:
        if t.kind == "participant":
            app = cat.app_named(t.parts[1] or t.parts[0])
            if app is not None:
                out.apps.add(app.key)
        elif t.kind == "call":
            out.contracts.add(t.parts[2])
        elif t.kind == "event":
            out.events.add(t.parts[2])
        elif t.kind == "await":
            (out.contracts if t.parts[1].startswith("CON-") else out.events).add(t.parts[1])
        elif t.kind in ("set", "given"):
            names.setdefault(t.parts[1], "")
        elif t.kind in ("finish", "on"):
            for entity, _ in t.parts[-1]:
                names.setdefault(entity, "")
    for cid in sorted(out.contracts):
        table = cat.contracts.get(cid)
        if table is None:
            continue
        out.apps.add(table.provider)
        for case in table.cases:
            out.events.update(case.emits)
            for name in [s[0] for s in case.sets] + [w[0] for w in case.when]:
                names.setdefault(name, table.title)
    for eid in sorted(out.events):
        event = cat.events.get(eid)
        if event is not None:
            out.apps.update(a for a, _ in event.subscribers)
            if event.producer:
                out.apps.add(event.producer)
            if event.key_of:
                names.setdefault(event.key_of, event.title)
    by_slug = _entities_by_slug(cat)
    for name, via in names.items():
        entity = cat.entity(name)
        if entity is not None:
            out.entities.setdefault(entity.slug, via)
    grown = True
    while grown:  # entities an invariant ties to the ones the flow reaches (Builder.add_invariant_entities)
        grown = False
        for slug, entity in sorted(by_slug.items()):
            for _, _, expr in entity.invariants:
                tied = {e.slug for e in (cat.entity(n) for n in _atoms(expr) | {slug}) if e is not None}
                if tied & set(out.entities) and not tied <= set(out.entities):
                    for other in sorted(tied - set(out.entities)):
                        out.entities[other] = f"an invariant of {entity.title}"
                    grown = True
    out.apps.update(by_slug[s].owner for s in out.entities if by_slug[s].owner)
    return out


def _atoms(expr):
    if expr[0] == "is":
        return {expr[1]}
    return set().union(*(_atoms(e) for e in expr[1:]))


def leaves(flow):
    """The (entity, state) pairs a flow says it leaves: what later slices may start from (F13)."""
    return {pair for t in (flow.lines if flow else ()) if t.kind in ("finish", "on") for pair in t.parts[-1]}


# --- the walk ----------------------------------------------------------------------------------------------------------

def walk(old, new, found):
    """The slices of `new` that `found` (Changes) can touch, with reasons. `old` None means there is no before to
    compare with, so every slice is checked."""
    if old is None or found.unknown:
        return everything(new, "; ".join(found.unknown) if old is not None else "there is no earlier version to compare with")
    out = Walk()
    reached = set()
    flows_seen = {}
    moved = found.moved or Changes()
    for s in new.slices:
        chains = _slice_chains(old, new, found, s, reached, flows_seen, "changed")
        chains = chains or _slice_chains(old, new, moved, s, set(), flows_seen, "moved on its page")
        if chains:
            out.affected[s.key] = list(dict.fromkeys(chains))
    out.untouched = _untouched(old, new, found, reached)
    return out


def _slice_chains(old, new, found, s, reached, flows_seen, verb):
    chains = []
    if s.key in found.slices:
        chains.append(f"{s.label} {verb}")
        reached.add(("slice", s.key))
    for fid in s.flows:
        chains += _flow_chains(old, new, found, fid, s, reached, flows_seen, verb)
    if verb == "changed":
        chains += _upstream_chains(old, new, s, reached)
    return chains


def everything(new, why):
    """Every slice, because the walk cannot tell what a change touches: `why` says so on the report."""
    return Walk({s.key: [f"the walk cannot tell what changed: {why}"] for s in new.slices}, why)


def _flow_chains(old, new, found, fid, s, reached, cache, verb="changed"):
    if fid not in cache:
        cache[fid] = [reach(cat, cat.flows[fid]) for cat in (old, new) if fid in cat.flows]
    seen = cache[fid]
    flow = new.flows.get(fid) or old.flows.get(fid)
    title = flow.title if flow else fid
    tail = f"{ARROW}{title}{ARROW}{s.label}"
    out = []
    if fid in found.flows:
        out.append(f"{title} {verb}{ARROW}{s.label}")
        reached.add(("flow", fid))
    for cid in sorted(set().union(*(r.contracts for r in seen)) & found.contracts if seen else ()):
        out.append(f"{_contract_title(old, new, cid)} {verb}{tail}")
        reached.add(("contract", cid))
    for eid in sorted(set().union(*(r.events for r in seen)) & found.events if seen else ()):
        out.append(f"{_event_title(old, new, eid)} {verb}{tail}")
        reached.add(("event", eid))
    entities = {}
    for r in seen:
        entities.update(r.entities)
    for slug in sorted(set(entities) & found.entities):
        entity = _entities_by_slug(new).get(slug) or _entities_by_slug(old).get(slug)
        shared = " (shared: its paired journeys)" if entity is not None and entity.shared else ""
        via = f"{ARROW}{entities[slug]}" if entities[slug] else ""
        out.append(f"{entity.title if entity else slug} {verb}{shared}{via}{tail}")
        reached.add(("entity", slug))
    for key in sorted(set().union(*(r.apps for r in seen)) & found.apps if seen else ()):
        app = new.apps.get(key) or old.apps.get(key)
        out.append(f"{app.title if app else key} {verb}{tail}")
        reached.add(("app", key))
    return out


def _upstream_chains(old, new, s, reached):
    """F13 judges a slice's GIVENs against what the slices it comes after leave: when a flow of one of those now leaves
    different states, this slice's result can move too."""
    out = []
    for key in sorted(slices_mod.upstream(new.slices, s) - {s.key}):
        earlier = next((u for u in new.slices if u.key == key), None)
        for fid in (earlier.flows if earlier else ()):
            if leaves(old.flows.get(fid)) != leaves(new.flows.get(fid)):
                flow = new.flows.get(fid) or old.flows.get(fid)
                out.append(f"{flow.title if flow else fid} now leaves different states{ARROW}{earlier.label}, "
                           f"which {s.label} comes after")
                reached.add(("flow", fid))
    return out


def _contract_title(old, new, cid):
    table = new.contracts.get(cid) or old.contracts.get(cid)
    return table.title if table else cid


def _event_title(old, new, eid):
    event = new.events.get(eid) or old.events.get(eid)
    return event.title if event else eid


def _untouched(old, new, found, reached):
    out = []
    for cid in sorted(found.contracts):
        if ("contract", cid) not in reached:
            out.append(f"{_contract_title(old, new, cid)} ({cid})")
    for eid in sorted(found.events):
        if ("event", eid) not in reached:
            out.append(f"{_event_title(old, new, eid)} ({eid})")
    for slug in sorted(found.entities):
        if ("entity", slug) not in reached:
            entity = _entities_by_slug(new).get(slug) or _entities_by_slug(old).get(slug)
            out.append(f"{entity.title} ({entity.id or slug})" if entity else slug)
    for fid in sorted(found.flows):
        if ("flow", fid) not in reached:
            flow = new.flows.get(fid) or old.flows.get(fid)
            out.append(f"{flow.title} ({fid})" if flow else fid)
    for key in sorted(found.apps):
        if ("app", key) not in reached:
            app = new.apps.get(key) or old.apps.get(key)
            out.append(app.title if app else key)
    out += [key for key in sorted(found.slices) if ("slice", key) not in reached]
    return out
