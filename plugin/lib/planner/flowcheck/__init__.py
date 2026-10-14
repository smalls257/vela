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

R0 throughout: an unreadable line, a missing property or a budget run out makes the slice "not fully checked", never
a pass. With any F10, exploration does not run at all: a model with a hole in it proves nothing.
"""
import dataclasses

from planner.flowcheck import build, explore, properties, readers, render, semantics
from planner.flowcheck.findings import Finding, SliceResult
from planner.flowcheck.semantics import ALL_REDUCTIONS

DEFAULT_MAX_STATES = 200_000
DEFAULT_MAX_SECONDS = 10.0


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
    found = [s for s in catalog.slices if (s.id and s.id.lower() == wanted.lower()) or s.name.lower().startswith(wanted.lower())]
    if not found:
        names = "; ".join(s.name for s in catalog.slices) or "none: release one needs a Tracer bullet, later ones a Flows bullet"
        raise SliceNotFound(f"'{target}' names no flow ID and no slice. Slices: {names}.")
    if len(found) > 1:
        raise SliceNotFound(f"'{target}' starts more than one slice: {'; '.join(s.name for s in found)}.")
    return found[0].name, found[0].flows, found[0].order


def plan_runs(program):
    """Which journeys run together (review 1.8): a flow on its own, or, when it touches a shared entity, paired with
    each flow of the slice touching the same one (itself included). All flows twice at once is not explored."""
    touched = {}
    for ins in program.code:
        touched.setdefault(ins.flow, set()).update(semantics._entities_of(ins, program))
    for index, (_, _, givens) in enumerate(program.flows):
        touched.setdefault(index, set()).update(givens)
    shared = {i: {s for s in touched.get(i, ()) if program.entities[s].shared} for i in range(len(program.flows))}
    runs = []
    for i in range(len(program.flows)):
        partners = [j for j in range(i, len(program.flows)) if shared[i] & shared[j]]
        runs += [(i, j) for j in partners] if partners else [(i,)]
    return runs


def check_slice(files, target, today, max_states=DEFAULT_MAX_STATES, max_seconds=DEFAULT_MAX_SECONDS,
                clock=frozen_clock, reductions=ALL_REDUCTIONS):
    return check_catalog(readers.read_vault(files), target, today, max_states, max_seconds, clock, reductions)


def check_catalog(catalog, target, today, max_states=DEFAULT_MAX_STATES, max_seconds=DEFAULT_MAX_SECONDS,
                  clock=frozen_clock, reductions=ALL_REDUCTIONS):
    name, flow_ids, order = resolve_slice(catalog, target)
    program, findings = build.build(catalog, flow_ids, today)
    findings += properties.loose_ends(catalog, order, [catalog.flows[f] for f in flow_ids if f in catalog.flows])
    result = SliceResult(name, tuple(flow_ids))
    if any(f.code == "F10" for f in findings):
        result.findings = apply_overrides(_ordered(findings + _unused(catalog)), catalog, flow_ids, today)
        return result
    began, explored = clock(), []
    for journeys in plan_runs(program):
        sem = semantics.Semantics(program, journeys, reductions)
        states_left = max_states - result.states
        seconds_left = max_seconds - (clock() - began)
        graph = explore.explore(sem, states_left, seconds_left, clock)
        result.states += len(graph.states)
        result.transitions += graph.transitions
        result.runs.append((tuple(program.flows[j][0].id for j in journeys), len(graph.states), graph.transitions, graph.complete))
        paths = [program.flows[j][0].path for j in journeys]
        explored += properties.judge_graph(graph, sem, render.Renderer(program, sem, catalog.apps), paths)
        if not graph.complete:
            budget = f"{max_states:,} states" if graph.stopped_by == "states" else f"{max_seconds:g} seconds"
            explored.append(Finding("F11", paths[0], f"Not fully checked: the budget of {budget} ran out after "
                                    f"{result.states:,} states and {result.transitions:,} transitions. Nothing past that is "
                                    "claimed, and what was not explored is not a pass."))
            break
    result.seconds = clock() - began
    result.findings = apply_overrides(_ordered(findings + explored + _unused(catalog)), catalog, flow_ids, today)
    return result


def apply_overrides(findings, catalog, flow_ids, today):
    """Each finding an override on its flow page covers, marked covered until the override's date (revision 2, item
    21). Scope is the flow, the code, the item and the case. An override past its date covers nothing: the finding
    blocks the slice again, and says when the override ended, so nobody believes it is still covered."""
    rules = [o for fid in flow_ids if fid in catalog.flows for o in catalog.flows[fid].overrides]
    out = []
    for f in findings:
        paths = {f.where.split(":", 1)[0], f.call_line.split(":", 1)[0]}
        hit = next((o for o in rules if o.code == f.code and o.item in f.items and o.case == f.case
                    and o.where.split(":", 1)[0] in paths), None)
        if hit is None:
            out.append(f)
        elif hit.until >= today:
            out.append(dataclasses.replace(f, covered=hit.until))
        else:
            out.append(dataclasses.replace(f, summary=f"{f.summary} The override for it ended on {hit.until}, so it blocks the slice again."))
    return out


def _unused(catalog):
    trees = []
    for fid in sorted(catalog.flows):
        flow = catalog.flows[fid]
        if flow.has_diagram:
            trees.append((flow, build.mermaid.parse_tree(flow, [])))
    return properties.unused_cases(catalog, trees)


def _ordered(findings):
    """Static findings in walk order, explored after; the same finding from two runs once."""
    out, seen = [], set()
    for f in findings:
        key = (f.code, f.where, f.summary)
        if key not in seen:
            seen.add(key)
            out.append(f)
    return out


__all__ = ["check_slice", "check_catalog", "apply_overrides", "resolve_slice", "plan_runs", "SliceResult", "Finding", "SliceNotFound", "frozen_clock"]
