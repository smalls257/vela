#!/usr/bin/env python3
"""The complexity, naming and comment gates as one command.

  python3 tools/quality_gate.py [FILES...] [--today YYYY-MM-DD] [--staged | --base REV]

Exit 0 clean, 1 findings (one `<path>:<line>: <GATE-ID> <message>` per line), 2 could not run. The Violation it
refuses is Silent Fallback: a missing lizard, a missing or malformed waiver file, a file it cannot parse, or no
base to check the waiver file against is exit 2 with the fix named, never a pass for a gate that did not run.

With FILES it judges only those (the edit hook and pre-commit); without, the whole scope (the `static` gate and
CI), which also needs a base to prove the waiver file only shrank. With --staged and no FILES it judges no file, only
the staged waiver file against HEAD. A changed waiver line must be one a seed of this tree would write, so edits to
the waiver file are the owner's.
"""
from __future__ import annotations

import argparse
import ast
import datetime
import os
import pathlib
import shutil
import subprocess
import sys
import tokenize

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

import quality_comments  # noqa: E402 -- after the sys.path insert above, which makes the sibling tools importable
import quality_complexity  # noqa: E402 -- after the sys.path insert above, which makes the sibling tools importable
import quality_names  # noqa: E402 -- after the sys.path insert above, which makes the sibling tools importable
import quality_waivers  # noqa: E402 -- after the sys.path insert above, which makes the sibling tools importable
from quality_report import Finding, render  # noqa: E402 -- after the sys.path insert above, which makes the sibling tools importable

LIZARD_FIX = "lizard is not installed; brew install lizard, or pip install lizard==1.21.3"
NO_BASE = "no base to check the waiver file against; pass --base or set GATE_BASE"
GIT_TIMEOUT = 30
LIZARD_TIMEOUT = 60


class GateCannotRun(RuntimeError):
    pass


def _run(argv: list[str], root: pathlib.Path, timeout: int, env: dict | None = None) -> subprocess.CompletedProcess:
    try:
        return subprocess.run(argv, cwd=root, capture_output=True, text=True, timeout=timeout, env=env)
    except OSError as exc:
        raise GateCannotRun(f"could not start {argv[0]}: {exc}") from exc


def _git(root: pathlib.Path, *args: str) -> subprocess.CompletedProcess:
    return _run(["git", *args], root, GIT_TIMEOUT)


def find_root() -> pathlib.Path:
    """The checkout this file belongs to, by git, so the caller's cwd cannot change what is judged. A git hook
    runs with GIT_DIR set, which makes the directory it asks from the work tree; drop that one variable here."""
    env = {k: v for k, v in os.environ.items() if k not in ("GIT_DIR", "GIT_WORK_TREE")}
    done = _run(["git", "rev-parse", "--show-toplevel"], pathlib.Path(__file__).resolve().parent, GIT_TIMEOUT, env)
    if done.returncode != 0:
        raise GateCannotRun(f"not a git checkout: {done.stderr.strip()}")
    return pathlib.Path(done.stdout.strip())


def choose_files(root: pathlib.Path, files: list[str]) -> list[str]:
    """The Python files in scope that sit in a layer: the named ones that exist, or every tracked and untracked one."""
    if not files:
        tracked = _git(root, "ls-files").stdout.split("\n")
        loose = _git(root, "ls-files", "--others", "--exclude-standard").stdout.split("\n")
        files = [p for p in tracked + loose if p]
    return sorted({f for f in files if f.endswith(".py") and quality_complexity.layer_of(f) and (root / f).is_file()})


def run_lizard(root: pathlib.Path, files: list[str]) -> dict:
    if not shutil.which("lizard"):
        raise GateCannotRun(LIZARD_FIX)
    if not files:
        return {}
    done = _run(["lizard", "-l", "python", "--csv", "-t", "4", *files], root, LIZARD_TIMEOUT)
    if done.returncode != 0:
        raise GateCannotRun(f"lizard failed (exit {done.returncode}): {done.stderr.strip()[:200]}")
    return quality_complexity.parse_lizard_csv(done.stdout)


MISSING_WAIVER_FILE = (f"{quality_waivers.WAIVER_FILE} is missing; restore it with "
                       f"`git checkout -- {quality_waivers.WAIVER_FILE}`. Do not reseed: that resets every expiry")


def read_waivers(root: pathlib.Path, text: str | None = None) -> dict:
    """The waivers, from `text` when the caller already holds the version to judge (the index, in --staged)."""
    if text is None:
        path = root / quality_waivers.WAIVER_FILE
        text = path.read_text(encoding="utf-8") if path.is_file() else ""
    if not text:
        raise GateCannotRun(MISSING_WAIVER_FILE)
    try:
        return quality_waivers.parse_waivers(text)
    except quality_waivers.WaiverFileError as exc:
        raise GateCannotRun(str(exc)) from exc


def _file_findings(path: str, source: str, tree: ast.Module) -> list[Finding]:
    return (quality_names.vague_names(path, tree) + quality_comments.what_comments(path, source)
            + quality_comments.restating_docstrings(path, tree)
            + quality_comments.unexplained_suppressions(path, source))


def scan(root: pathlib.Path, files: list[str]) -> tuple[list[quality_complexity.Measure], list[Finding]]:
    """Complexity measures for the files, plus the naming and comment findings."""
    rows = run_lizard(root, files)
    measures: list[quality_complexity.Measure] = []
    findings: list[Finding] = []
    for path in files:
        source = (root / path).read_text(encoding="utf-8")
        try:
            tree = ast.parse(source)
            findings += _file_findings(path, source, tree)
        except (SyntaxError, tokenize.TokenError) as exc:
            raise GateCannotRun(f"{path} cannot be parsed ({exc}), so it cannot be measured") from exc
        measures += quality_complexity.function_measures(path, source, rows)
        measures.append(quality_complexity.file_measure(path, source))
    return measures, findings


def dated_todo_findings(root: pathlib.Path, today: datetime.date) -> list[Finding]:
    # nosemgrep: todo-needs-owner-and-date -- the pattern names the marker words it searches for
    done = _git(root, "grep", "-InE", r"(TODO|FIXME|HACK)\(", "--", ":!.semgrep")
    if done.returncode not in (0, 1):
        raise GateCannotRun(f"git grep failed: {done.stderr.strip()}")
    return quality_waivers.expired_todos([line for line in done.stdout.split("\n") if line], today)


def _show(root: pathlib.Path, spec: str) -> str:
    """The text of `REV:path` or `:path`; empty when git has no such blob (the file is new)."""
    if _git(root, "cat-file", "-e", spec).returncode != 0:
        return ""
    return _git(root, "show", spec).stdout


def waiver_texts(root: pathlib.Path, staged: bool, base: str | None) -> tuple[str, str] | None:
    """(base text, head text) of the waiver file for the chosen comparison, or None when none was asked for."""
    name = quality_waivers.WAIVER_FILE
    if staged:
        return _show(root, f"HEAD:{name}"), _show(root, f":{name}")
    if base is None:
        return None
    merge_base = _git(root, "merge-base", "HEAD", base).stdout.strip() if base else ""
    if not merge_base:
        raise GateCannotRun(NO_BASE)
    return _show(root, f"{merge_base}:{name}"), (root / name).read_text(encoding="utf-8")


def over_cap_by_key(measures: list[quality_complexity.Measure]) -> dict:
    """What a seed would record: each measure over its layer's caps, with the values that are over."""
    found = {}
    for measure in measures:
        over = quality_complexity.over_caps(measure, quality_complexity.CAPS[quality_complexity.layer_of(measure.path)])
        if over:
            found[measure.key] = over
    return found


def unproduced_reason(waiver: quality_waivers.Waiver, produced: dict, today: datetime.date) -> str | None:
    """Why a seed of this tree would not have written this line, or None when it would have."""
    over = produced.get(waiver.key)
    if over is None:
        return "is not over its cap in this tree"
    if waiver.limits != over:
        return f"records {waiver.limits} where the tree measures {over}"
    if waiver.expires > today + datetime.timedelta(days=quality_waivers.MAX_RENEWAL_DAYS):
        return "expires more than a year out"
    return None


def unproduced_findings(root: pathlib.Path, texts: tuple[str, str], today: datetime.date) -> list[Finding]:
    """A changed waiver line is accepted only when a seed of the whole tree would write it. Proving it beats
    trusting the `# seeded` label, which anyone who can write the file can forge (Silent Fallback)."""
    changed = quality_waivers.changed_entries(*texts)
    if not changed:
        return []
    measures, _ = scan(root, choose_files(root, []))
    produced = over_cap_by_key(measures)
    found = []
    for waiver in changed:
        why = unproduced_reason(waiver, produced, today)
        if why:
            found.append(Finding(quality_waivers.WAIVER_FILE, waiver.line, "QG-WAIVER",
                                 f"waiver line for {waiver.key} {why}, so a seed would not write it: delete the line, "
                                 "or ask the owner to run python3 tools/quality_seed.py"))
    return found


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(prog="quality_gate.py", description=__doc__.split("\n")[0])
    parser.add_argument("files", nargs="*")
    parser.add_argument("--today", type=datetime.date.fromisoformat)
    where = parser.add_mutually_exclusive_group()
    where.add_argument("--staged", action="store_true")
    where.add_argument("--base")
    return parser.parse_args(argv)


def _files_in_scope(root: pathlib.Path, args: argparse.Namespace) -> list[str]:
    """--staged with no Python file staged checks no file: a docs-only commit is never failed by the whole tree's waivers."""
    if args.staged and not args.files:
        return []
    return choose_files(root, args.files)


def judge_tree(root: pathlib.Path, args: argparse.Namespace, today: datetime.date) -> list[Finding]:
    texts = waiver_texts(root, args.staged, args.base)
    if texts is None and not args.files:
        raise GateCannotRun(NO_BASE)
    files = _files_in_scope(root, args)
    waivers = read_waivers(root, texts[1] if args.staged else None)
    measures, findings = scan(root, files)
    findings += quality_complexity.judge(measures, waivers, set(files), today)
    if not args.files and not args.staged:
        findings += dated_todo_findings(root, today)
    return findings + (unproduced_findings(root, texts, today) if texts else [])


def main(argv: list[str], root: pathlib.Path | None = None) -> int:
    args = parse_args(argv)
    today = args.today or datetime.date.today()
    try:
        findings = judge_tree(root or find_root(), args, today)
    except (GateCannotRun, quality_complexity.MeasureError, subprocess.TimeoutExpired, UnicodeDecodeError) as exc:
        print(f"quality gate: could not run: {exc}", file=sys.stderr)
        return 2
    print("\n".join(render(findings)))
    return 1 if findings else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
