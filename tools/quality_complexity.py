"""Complexity caps per layer, and the verdicts against the waiver file.

The Violation this prevents is God Method (and God Class for file length): one unit that knows and does too much.
Lizard supplies CCN, NLOC and parameter count; `ast` supplies nesting, which lizard does not measure. Every `def`
the parser sees must have a lizard row, because lizard exits 0 on a file it could not read, and a green gate that
measured nothing is the failure this module refuses (Sensor).

Everything here is pure over strings and numbers, so tests drive it without lizard or git; only
`tools/quality_gate.py` runs the processes.
"""
from __future__ import annotations

import ast
import csv
import datetime
import io
from dataclasses import dataclass
from typing import Iterator

from quality_report import Finding
from quality_waivers import METRICS, WAIVER_FILE, Waiver

LABELS = {"ccn": "CCN", "nloc": "NLOC", "params": "PARAMS", "nesting": "NESTING", "lines": "LINES"}
LIZARD_COLUMNS = 11


@dataclass(frozen=True)
class Caps:
    ccn: int
    nloc: int
    params: int
    nesting: int
    lines: int


# Why each layer's numbers. A function has to fit in the reader's head: ten independent paths and a screenful
# of statements is about what a person can hold while checking one change, so the core and shell start there.
# Nesting is capped one lower in the shell (4 core, 3 shell) because the shell is argument handling and glue,
# where a third level is almost always a missing helper.
# The edge talks to disk and git, where every branch needs a fake to test, so it is the tightest: 8, 40, 5, 3.
# Hooks run on every edit and decide in one reading, so they keep core's CCN and shrink the rest: 10, 40, 5, 3.
# Tools are scripts that orchestrate and parse, which reads longer than it thinks, so they get the most room:
# 12, 60, 6, 4. Files stop at 500 lines in every layer: past that a module has more than one reason to change.
CAPS = {
    "core": Caps(10, 50, 6, 4, 500),
    "shell": Caps(10, 50, 6, 3, 500),
    "edge": Caps(8, 40, 5, 3, 500),
    "tools": Caps(12, 60, 6, 4, 500),
    "hooks": Caps(10, 40, 5, 3, 500),
}


class MeasureError(ValueError):
    pass


@dataclass(frozen=True)
class Measure:
    key: str
    path: str
    line: int
    values: dict


def layer_of(path: str) -> str | None:
    """Which layer's caps apply to this repo-relative path, or None when no gate covers it."""
    if "__pycache__" in path:
        return None
    if path.startswith("plugin/lib/vela/edge/"):
        return "edge"
    if path.startswith("plugin/lib/vela/commands/") or path == "plugin/lib/vela/cli.py":
        return "shell"
    if path.startswith("plugin/lib/vela/") and path.endswith(".py"):
        return "core"
    if path.startswith("tools/"):
        return "tools"
    if path.startswith(".claude/hooks/"):
        return "hooks"
    return None


def parse_lizard_csv(text: str) -> dict[tuple[str, int], dict]:
    """Lizard's headerless CSV as {(file, start line): {nloc, ccn, params}}."""
    rows = {}
    for row in csv.reader(io.StringIO(text)):
        if not row:
            continue
        try:
            if len(row) < LIZARD_COLUMNS:
                raise ValueError(f"{len(row)} columns")
            rows[(row[6], int(row[9]))] = {"nloc": int(row[0]), "ccn": int(row[1]), "params": int(row[3])}
        except ValueError as exc:
            raise MeasureError(f"lizard printed a row this tool cannot read ({exc}): {row!r}") from exc
    return rows


# ---------------------------------------------------------------- nesting, which lizard does not count

def _node_types(*names: str) -> tuple:
    return tuple(t for t in (getattr(ast, n, None) for n in names) if t)


NESTERS = _node_types("If", "For", "AsyncFor", "While", "With", "AsyncWith", "Try", "TryStar", "Match")
SCOPES = (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)


def _blocks(stmt: ast.stmt) -> list[list]:
    """The statement lists directly under one nesting statement."""
    if hasattr(stmt, "handlers"):
        return [stmt.body, *[h.body for h in stmt.handlers], stmt.orelse, stmt.finalbody]
    if hasattr(stmt, "cases"):
        return [case.body for case in stmt.cases]
    return [stmt.body, getattr(stmt, "orelse", [])]


def _is_elif(stmt: ast.stmt, block: list) -> bool:
    return isinstance(stmt, ast.If) and block is stmt.orelse and len(block) == 1 and isinstance(block[0], ast.If)


def _chain(stmt: ast.stmt, depth: int) -> int:
    """Deepest nesting under `stmt`, which already sits at `depth`. An elif stays at its parent's depth."""
    best = depth
    for block in _blocks(stmt):
        if _is_elif(stmt, block):
            best = max(best, _chain(block[0], depth))
        else:
            best = max(best, _deepest(block, depth))
    return best


def _deepest(stmts: list, depth: int) -> int:
    best = depth
    for stmt in stmts:
        if isinstance(stmt, NESTERS):
            best = max(best, _chain(stmt, depth + 1))
    return best


# ---------------------------------------------------------------- measures

def _defs(node: ast.AST, prefix: str = "") -> Iterator[tuple[str, ast.AST]]:
    """(qualname, node) for every def: a class adds `Name.`, a function adds `name.<locals>.` for its children."""
    for child in ast.iter_child_nodes(node):
        if isinstance(child, ast.ClassDef):
            yield from _defs(child, f"{prefix}{child.name}.")
        elif isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
            yield f"{prefix}{child.name}", child
            yield from _defs(child, f"{prefix}{child.name}.<locals>.")
        else:
            yield from _defs(child, prefix)


def _merge(first: Measure, other: Measure) -> Measure:
    values = {m: max(first.values[m], other.values[m]) for m in first.values}
    return Measure(first.key, first.path, first.line, values)


def function_measures(path: str, source: str, rows: dict) -> list[Measure]:
    """One Measure per qualified function name. A def with no lizard row raises, never passes unmeasured."""
    merged: dict[str, Measure] = {}
    try:
        tree = ast.parse(source)
    except SyntaxError as exc:
        raise MeasureError(f"{path} cannot be parsed ({exc}), so it cannot be measured") from exc
    for qualname, node in _defs(tree):
        row = rows.get((path, node.lineno))
        if row is None:
            raise MeasureError(f"lizard did not measure {path}:{node.lineno} {qualname}")
        key = f"{path}::{qualname}"
        found = Measure(key, path, node.lineno, {**row, "nesting": _deepest(node.body, 0)})
        merged[key] = _merge(merged[key], found) if key in merged else found
    return list(merged.values())


def file_measure(path: str, source: str) -> Measure:
    return Measure(path, path, 1, {"lines": len(source.splitlines())})


def over_caps(measure: Measure, caps: Caps) -> dict[str, int]:
    """The metrics of this measure that exceed the layer's cap, with their values."""
    return {m: v for m, v in measure.values.items() if v > getattr(caps, m)}


# ---------------------------------------------------------------- verdicts

def _list_over(over: dict, limit_for) -> str:
    return ", ".join(f"{LABELS[m]} {over[m]} > {limit_for(m)}" for m in METRICS if m in over)


def _unwaived(measure: Measure, layer: str, over: dict) -> Finding:
    caps = CAPS[layer]
    gate = "QG-LEN" if "lines" in measure.values else "QG-CPX"
    detail = _list_over(over, lambda m: getattr(caps, m))
    return Finding(measure.path, measure.line, gate,
                   f"{measure.key} {detail} ({layer} cap). Split it into named helpers; caps are in tools/quality_complexity.py")


def _grown(measure: Measure, caps: Caps, waiver: Waiver) -> Finding | None:
    grown = {m: v for m, v in measure.values.items() if v > waiver.limits.get(m, getattr(caps, m))}
    if not grown:
        return None
    detail = _list_over(grown, lambda m: waiver.limits.get(m, getattr(caps, m)))
    gate = "QG-LEN" if "lines" in measure.values else "QG-CPX"
    return Finding(measure.path, measure.line, gate,
                   f"{measure.key} grew past its waiver: {detail} recorded. Bring it back under, or ask the owner to reseed")


def _waived(measure: Measure, layer: str, over: dict, waiver: Waiver, today: datetime.date) -> list[Finding]:
    found = []
    if waiver.expires < today:
        found.append(Finding(WAIVER_FILE, waiver.line, "QG-WAIVER",
                             f"waiver for {measure.key} (owner {waiver.owner}) expired on {waiver.expires.isoformat()}: "
                             "fix it, or renew the date and reason in a reviewed commit"))
    if not over:
        found.append(Finding(WAIVER_FILE, waiver.line, "QG-WAIVER",
                             f"{measure.key} meets its caps now: delete its line in {WAIVER_FILE}"))
        return found
    grown = _grown(measure, CAPS[layer], waiver)
    return found + ([grown] if grown else [])


def _vanished(waivers: dict[str, Waiver], measured: set, scanned_paths: set) -> list[Finding]:
    return [Finding(WAIVER_FILE, w.line, "QG-WAIVER",
                    f"{key} no longer exists: delete its line; if it was renamed, ask the owner to reseed "
                    "(python3 tools/quality_seed.py)")
            for key, w in waivers.items() if key.split("::")[0] in scanned_paths and key not in measured]


def judge(measures: list[Measure], waivers: dict[str, Waiver], scanned_paths: set[str],
          today: datetime.date) -> list[Finding]:
    """The findings for measures of the scanned files, against the layer caps and the waiver file."""
    found = []
    for measure in measures:
        layer = layer_of(measure.path)
        if layer is None or measure.path not in scanned_paths:
            continue
        over = over_caps(measure, CAPS[layer])
        waiver = waivers.get(measure.key)
        if waiver:
            found += _waived(measure, layer, over, waiver, today)
        elif over:
            found.append(_unwaived(measure, layer, over))
    return found + _vanished(waivers, {m.key for m in measures}, scanned_paths)
