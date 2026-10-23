"""The flow checker (design 19, revision 2): prove a slice's logic before it is built. Pure.

    check_slice(files, "Release one", today="2026-10-13") -> SliceResult
    check_catalog(catalog, "Release one", today) -> SliceResult       (the same, from a Catalog already read)

`files` is {vault-relative posix path: text}; the CLI reads the disk, nothing here does, and the clock is handed in
(frozen by default). The pipeline is replaceable stages, each a pure function over the one before:

    readers.read_vault      files -> Catalog of normalized case and event tables (the only input the rest sees, D7)
    build.build             Catalog + slice -> compiled Program + static findings (F1, F2, F3, F10, F12)
    semantics.Semantics     Program + journeys -> transition system
    explore.explore         transition system -> state graph (BFS, budgets)
    properties.judge_graph  state graph -> explored findings (F5 to F9); render.Renderer words their traces

check_catalog runs three stages of its own, so the costly middle can be recorded and reused (record, impact, changed):

    prepare           Catalog + slice -> Prepared (the program, static findings, the runs to explore)
    explore_prepared  Prepared -> Explored (explored findings, counts, the runs a budget stop skipped)
    finish            Prepared + Explored + today -> SliceResult (F4, overrides as of today, limits)

R0 throughout: an unreadable line, a missing property or a budget run out makes the slice "not fully checked", never
a pass. With any F10, exploration does not run at all: a model with a hole in it proves nothing.
"""
import dataclasses

from vela.flowcheck import build, explore, properties, readers, render, semantics
from vela.flowcheck.findings import TITLES, Finding, SliceResult
from vela.flowcheck.semantics import ALL_REDUCTIONS

DEFAULT_MAX_STATES = 200_000
DEFAULT_MAX_SECONDS = 10.0
PAIRS, TRIPLES = 2, 3  # journeys at once over a shared entity: pairs by default, triples on request (ledger C39)


class SliceNotFound(ValueError):
    """The argument names no release and no flow."""


def frozen_clock():
    """A clock that never moves: the time budget never runs out, so results depend on the state budget alone."""
    return 0.0


def resolve_slice(catalog, target):
    """(name, flow ids, slice order or None). A flow ID checks that flow alone; anything else names a slice by its ID
    or the start of its name ("Release one"), ignoring case. Slices come from `slices.read_slices`, nowhere else."""
    wanted = target.strip()
    if wanted.upper().startswith("FLO-"):
        fid = wanted.upper()
        order = next((s.order for s in catalog.slices if fid in s.flows), None)
        return fid, (fid,), order
    exact = [s for s in catalog.slices if wanted.lower() in (s.id.lower(), s.name.lower())]
    found = exact or [s for s in catalog.slices if s.name.lower().startswith(wanted.lower())]
    if not found:
        names = "; ".join(s.label for s in catalog.slices) or "none yet: write a slice page in slices/, SLC-001 first"
        raise SliceNotFound(f"'{target}' names no flow ID and no slice. Slices: {names}.")
    if len(found) > 1:
        raise SliceNotFound(f"'{target}' starts more than one slice: {'; '.join(s.name for s in found)}.")
    return found[0].name, found[0].flows, found[0].order


def plan_runs(program, journeys=None):
    """Which journeys run together (review 1.8): a flow on its own, or, when it touches a shared entity, paired with
    each flow of the slice touching the same one (itself included). With `journeys` 3, the triples over a shared
    entity follow the pairs, so a budget stop still leaves the pairs explored. All flows at once is never explored.
    Triples do not replace pairs: a third journey can unblock or finish what two leave stuck."""
    journeys = PAIRS if journeys is None else journeys
    if journeys not in (PAIRS, TRIPLES):
        raise ValueError(f"journeys must be {PAIRS} or {TRIPLES}, not {journeys}")
    shared = _shared_touched(program)
    runs = []
    n = len(program.flows)
    for i in range(n):
        partners = [j for j in range(i, n) if shared[i] & shared[j]]
        runs += [(i, j) for j in partners] if partners else [(i,)]
    if journeys == TRIPLES:
        runs += [(i, j, k) for i in range(n) for j in range(i, n) for k in range(j, n) if shared[i] & shared[j] & shared[k]]
    return runs


def _shared_touched(program):
    """{flow index: the shared entities it touches}."""
    touched = {}
    for ins in program.code:
        touched.setdefault(ins.flow, set()).update(semantics._entities_of(ins, program))
    for index, (_, _, givens) in enumerate(program.flows):
        touched.setdefault(index, set()).update(givens)
    return {i: {s for s in touched.get(i, ()) if program.entities[s].shared} for i in range(len(program.flows))}


@dataclasses.dataclass
class Prepared:
    """A slice built and statically judged, before any exploration: everything the exploration depends on, so a
    fingerprint of it (record.fingerprint) says whether a recorded exploration still holds."""
    name: str
    flows: tuple
    order: object
    program: object
    static: list  # static findings, F13 included, before overrides
    runs: list  # plan_runs: tuples of flow indexes
    journeys: int
    apps: dict  # the catalog's apps, for the owners a trace names


@dataclasses.dataclass
class Explored:
    """What exploring a Prepared slice found: the part of a result worth recording, since it is the part that costs."""
    findings: list = dataclasses.field(default_factory=list)
    states: int = 0
    transitions: int = 0
    seconds: float = 0.0
    runs: list = dataclasses.field(default_factory=list)  # [(flow ids, states, transitions, complete)]
    skipped: list = dataclasses.field(default_factory=list)  # [flow ids] of runs a budget stop left unexplored


def prepare(catalog, target, today, journeys=None):
    journeys = PAIRS if journeys is None else journeys
    name, flow_ids, order = resolve_slice(catalog, target)
    program, findings = build.build(catalog, flow_ids, today)
    findings += properties.loose_ends(catalog, order, [catalog.flows[f] for f in flow_ids if f in catalog.flows])
    return Prepared(name, tuple(flow_ids), order, program, findings, plan_runs(program, journeys), journeys, catalog.apps)


def explore_prepared(prepared, max_states=DEFAULT_MAX_STATES, max_seconds=DEFAULT_MAX_SECONDS, clock=frozen_clock,
                     reductions=ALL_REDUCTIONS):
    """Every run of the slice in turn, on one shared budget. With any F10 nothing is explored. A budget stop ends the
    slice: the run it stopped in is F11, and the runs after it are listed in `skipped`, so the result can say which
    journeys nobody looked at instead of leaving them out without a word."""
    program, out = prepared.program, Explored()
    if any(f.code == "F10" for f in prepared.static):
        return out
    began = clock()
    for index, journeys in enumerate(prepared.runs):
        sem = semantics.Semantics(program, journeys, reductions)
        graph = explore.explore(sem, max_states - out.states, max_seconds - (clock() - began), clock)
        out.states += len(graph.states)
        out.transitions += graph.transitions
        ids = tuple(program.flows[j][0].id for j in journeys)
        out.runs.append((ids, len(graph.states), graph.transitions, graph.complete))
        paths = [program.flows[j][0].path for j in journeys]
        out.findings += properties.judge_graph(graph, sem, render.Renderer(program, sem, prepared.apps), paths)
        if not graph.complete:
            budget = f"{max_states:,} states" if graph.stopped_by == "states" else f"{max_seconds:g} seconds"
            out.findings.append(Finding("F11", paths[0], f"Not fully checked: the budget of {budget} ran out after "
                                        f"{out.states:,} states and {out.transitions:,} transitions, while checking "
                                        f"{run_words(ids)}. Nothing past that is claimed, and what was not explored is not a pass."))
            out.skipped = [tuple(program.flows[j][0].id for j in later) for later in prepared.runs[index + 1:]]
            break
    out.seconds = clock() - began
    return out


def finish(catalog, prepared, explored, today):
    """The result: static and explored findings, F4 for the initiative, overrides as of `today`, and the limits the
    result rests on, said out loud (ledger C39)."""
    result = SliceResult(prepared.name, prepared.flows, journeys=prepared.journeys)
    result.states, result.transitions, result.seconds = explored.states, explored.transitions, explored.seconds
    result.runs = list(explored.runs)
    result.skipped = list(explored.skipped)
    found = prepared.static + list(explored.findings) + _unused(catalog, prepared.static)
    result.findings = apply_overrides(_ordered(found), catalog, prepared.flows, today, prepared.order)
    result.limits = limits(prepared, explored)
    return result


def limits(prepared, explored):
    """What a result rests on and does not claim, one sentence each, whenever it applies: how many journeys ran at once
    over a shared entity, that timers are taken to fire in the end, and which runs a budget stop left unexplored."""
    program, out = prepared.program, []
    shared = _shared_touched(program)
    together = [r for r in prepared.runs if len(r) > 1]
    if together:
        names = sorted({program.entities[s].title for r in together for i in r for s in shared[i]})
        verb, them = ("is", "it") if len(names) == 1 else ("are", "them")
        if prepared.journeys == TRIPLES:
            out.append(f"{_and(names)} {verb} shared, so the flows that touch {them} ran two and three journeys at once, "
                       "never four.")
        else:
            out.append(f"{_and(names)} {verb} shared, so the flows that touch {them} ran two journeys at once, not three "
                       "(--journeys 3 tries three).")
    if program.timers:
        out.append("A timer is taken to fire in the end: an order of events in which a timer never fires is not explored.")
    if explored.skipped:
        out.append(f"Not explored, because the budget ran out first: {'; '.join(run_words(r) for r in explored.skipped)}.")
    return out


def run_words(ids):
    """One run in words: "FLO-001 alone", "FLO-006 twice", "FLO-211 and FLO-212", "FLO-006 three times"."""
    counts = {}
    for fid in ids:
        counts[fid] = counts.get(fid, 0) + 1
    if len(ids) == 1:
        return f"{ids[0]} alone"
    times = {1: "", 2: " twice", 3: " three times"}
    if len(counts) == 1:
        return f"{ids[0]}{times[len(ids)]}"
    return _and([f"{fid}{times[n]}" for fid, n in counts.items()]) + " together"


def _and(items):
    items = list(items)
    if len(items) <= 1:
        return "".join(items)
    if len(items) == 2:
        return f"{items[0]} and {items[1]}"
    return ", ".join(items[:-1]) + f" and {items[-1]}"


def check_slice(files, target, today, max_states=DEFAULT_MAX_STATES, max_seconds=DEFAULT_MAX_SECONDS,
                clock=frozen_clock, reductions=ALL_REDUCTIONS, journeys=None):
    return check_catalog(readers.read_vault(files), target, today, max_states, max_seconds, clock, reductions, journeys)


def check_catalog(catalog, target, today, max_states=DEFAULT_MAX_STATES, max_seconds=DEFAULT_MAX_SECONDS,
                  clock=frozen_clock, reductions=ALL_REDUCTIONS, journeys=None):
    prepared = prepare(catalog, target, today, journeys)
    return finish(catalog, prepared, explore_prepared(prepared, max_states, max_seconds, clock, reductions), today)


def apply_overrides(findings, catalog, flow_ids, today, order=None):
    """Each finding an override covers, marked covered until the override's date (revision 2, item 21). One on a flow
    page is scoped to that flow, the code, the item and the case; one on the slice page (the slice at `order`, the one
    being checked or the first holding the flow checked alone) to any flow of that slice. An override past its date
    covers nothing: the finding blocks the slice again, and says when the override ended, so nobody believes it is
    still covered."""
    rules = [o for fid in flow_ids if fid in catalog.flows for o in catalog.flows[fid].overrides]
    owner = catalog.slices[order] if order is not None and order < len(catalog.slices) else None
    sliced = catalog.slice_overrides.get(owner.key, ()) if owner is not None else ()
    out = []
    for f in findings:
        paths = {f.where.split(":", 1)[0], f.call_line.split(":", 1)[0]}
        hit = next((o for o in rules if o.code == f.code and o.item in f.items and o.case == f.case
                    and o.where.split(":", 1)[0] in paths), None)
        hit = hit or next((o for o in sliced if o.code == f.code and o.item in f.items and o.case == f.case), None)
        if hit is None:
            out.append(f)
        elif hit.until >= today:
            out.append(dataclasses.replace(f, covered=hit.until))
        else:
            out.append(dataclasses.replace(f, summary=f"{f.summary} The override for it ended on {hit.until}, so it blocks the slice again."))
    return out


def _unused(catalog, findings=()):
    """F4 for the initiative, less each case an F1 of this result already names: one missing branch is one finding,
    not an unhandled case and an unused one."""
    trees = []
    for fid in sorted(catalog.flows):
        flow = catalog.flows[fid]
        if flow.has_diagram:
            trees.append((flow, build.mermaid.parse_tree(flow, [])))
    unhandled = {(item, f.case) for f in findings if f.code == "F1" for item in f.items}
    return [f for f in properties.unused_cases(catalog, trees) if (f.items[0], f.case) not in unhandled]


def _ordered(findings):
    """Static findings in walk order, explored after; the same finding from two runs once."""
    out, seen = [], set()
    for f in findings:
        key = (f.code, f.where, f.summary)
        if key not in seen:
            seen.add(key)
            out.append(f)
    return out


__all__ = ["check_slice", "check_catalog", "prepare", "explore_prepared", "finish", "apply_overrides", "resolve_slice",
           "plan_runs", "limits", "run_words", "Prepared", "Explored", "SliceResult", "Finding", "SliceNotFound",
           "frozen_clock", "PAIRS", "TRIPLES"]
