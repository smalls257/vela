"""The recorded result of each slice's check, and the fingerprint that says whether it still holds. Pure.

Exploring is the part of a check that costs; building and judging statically take milliseconds. So what is recorded
is the exploration (`Explored`), keyed by a fingerprint of everything it depended on: the compiled program (every
flow's steps, the case tables and bullets of the contracts it calls, the entities and their invariants, the events,
the apps), the static findings, the runs planned, the budgets, the journeys at once, and the checker's own version.
Overrides and today's date are left out on purpose: they are applied fresh on every run (`flowcheck.finish`), so an
override that ends tomorrow ends tomorrow whether or not the slice was reused. F4 is recomputed too, since it is
judged across the whole initiative.

The store is one JSON file the CLI keeps at .planner/flowcheck-cache.json. It is advisory: a file that does not
read is ignored with a warning and rebuilt, never trusted and never a reason to fail (`read_store`). It is also the
record the dashboard and the handoff read for where a slice's check stands (`standing.standing`), without running
it: a record whose fingerprint no longer matches says "not checked since", and "not fully checked" is kept as
itself, never as a pass.
"""
import dataclasses
import hashlib
import json

from planner.flowcheck import Explored
from planner.flowcheck.findings import Finding
from planner.flowcheck.tables import Flow

FORMAT = 1
PATH = ".planner/flowcheck-cache.json"


def canonical(value):
    """A value as plain JSON with one spelling: dataclasses as [name, fields...], sets and dicts sorted, so the same
    model gives the same bytes in every process (Python's set order is not stable across runs). A flow's overrides
    are left out: they are applied after exploring."""
    if dataclasses.is_dataclass(value) and not isinstance(value, type):
        return [type(value).__name__] + [canonical(getattr(value, f.name)) for f in dataclasses.fields(value)
                                         if not (isinstance(value, Flow) and f.name == "overrides")]
    if isinstance(value, dict):
        return sorted(([canonical(k), canonical(v)] for k, v in value.items()), key=_key)
    if isinstance(value, (set, frozenset)):
        return sorted((canonical(v) for v in value), key=_key)
    if isinstance(value, (list, tuple)):
        return [canonical(v) for v in value]
    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    raise TypeError(f"no canonical form for {type(value).__name__}")


def _key(value):
    return json.dumps(value, sort_keys=True)


def fingerprint(prepared, max_states, max_seconds, version):
    """The hex digest of everything a recorded exploration of `prepared` rests on (see the module doc)."""
    data = canonical([FORMAT, version, max_states, max_seconds, prepared.journeys, prepared.flows, prepared.runs,
                      prepared.program, prepared.static, prepared.apps])
    return hashlib.sha256(_key(data).encode("utf-8")).hexdigest()


# --- one slice's record ----------------------------------------------------------------------------------------------

def to_record(result, explored, fingerprint_, checked, budget=None):
    """What is kept for one slice: the exploration to reuse, and the result as it stood on `checked`, for readers.
    `budget` is (max states, max seconds) it was explored with, so a reader can tell whether the record still holds
    (`standing.standing`) without guessing the budget."""
    return {"fingerprint": fingerprint_, "checked": checked, "budget": list(budget) if budget else None,
            "name": result.name, "flows": list(result.flows),
            "status": result.status, "open": sorted({f.code for f in result.open}),
            "openTitles": sorted({_title(f.code) for f in result.open}), "limits": list(result.limits),
            "journeys": result.journeys,
            "explored": {"findings": [_finding_out(f) for f in explored.findings], "states": explored.states,
                         "transitions": explored.transitions, "seconds": round(explored.seconds, 4),
                         "runs": [[list(ids), states, moves, complete] for ids, states, moves, complete in explored.runs],
                         "skipped": [list(ids) for ids in explored.skipped]}}


def explored_of(record):
    """The Explored a record holds. Raises ValueError when it does not read, so the caller checks the slice afresh."""
    try:
        data = record["explored"]
        return Explored([_finding_in(f) for f in data["findings"]], int(data["states"]), int(data["transitions"]),
                        float(data["seconds"]),
                        [(tuple(ids), int(states), int(moves), bool(complete)) for ids, states, moves, complete in data["runs"]],
                        [tuple(ids) for ids in data["skipped"]])
    except (KeyError, TypeError, ValueError) as exc:
        raise ValueError(f"the record does not read: {exc}") from exc


def _finding_out(f):
    return {k: list(v) if isinstance(v, tuple) else v for k, v in dataclasses.asdict(f).items()}


def _finding_in(data):
    fields = {f.name for f in dataclasses.fields(Finding)}
    if not isinstance(data, dict) or set(data) - fields or "code" not in data:
        raise ValueError("a finding with unknown fields")
    return Finding(**{k: tuple(v) if isinstance(v, list) else v for k, v in data.items()})


def _title(code):
    from planner.flowcheck.findings import TITLES
    return TITLES.get(code, code).lower()


# --- the store ---------------------------------------------------------------------------------------------------------

def read_store(text):
    """(store, warning). `text` None is no file yet: an empty store, no warning. A file that is not the store's shape
    is ignored with a warning saying so, and the store starts empty, so a corrupt cache costs one full check and
    nothing else (advisory, never trusted)."""
    empty = {"format": FORMAT, "slices": {}}
    if text is None:
        return empty, ""
    try:
        data = json.loads(text)
    except ValueError as exc:
        return empty, f"{PATH} is not JSON ({exc}), so it was ignored and every slice is checked afresh."
    if not isinstance(data, dict) or data.get("format") != FORMAT or not isinstance(data.get("slices"), dict) or \
            not all(isinstance(r, dict) for r in data["slices"].values()):
        return empty, f"{PATH} is not a flow-check record this planner reads, so it was ignored and every slice is checked afresh."
    return data, ""


def dump_store(store):
    return json.dumps(store, indent=1, sort_keys=True) + "\n"
