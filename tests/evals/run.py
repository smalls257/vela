#!/usr/bin/env python3
"""Run plugin-eval cases by hand in both arms, then grade every kept workspace with planner check.

This costs money: each run is a real Claude session on your account. Run it before a skill ships,
after a SKILL.md or reference change, and when the default model changes.

Usage:
  python3 tests/evals/run.py --model <model> --judge-model <model> [--runs 3] [--max-cost-usd 10] [CASE ...]

CASE is a case name such as e1-dump. With none, every case runs. Each case runs twice: the plugin arm
(tests/evals/plugin/<case>) and the conventions-only arm (tests/evals/stub/<case>). Results, one Markdown
file per case, go to tests/evals/.results/, which git ignores.
"""
import argparse
import datetime
import pathlib
import re
import subprocess
import sys

HERE = pathlib.Path(__file__).resolve().parent
REPO = HERE.parent.parent
PLANNER = REPO / "plugin" / "bin" / "planner"
ARMS = ("plugin", "stub")

# Per case: the date check judges by, whether the epics gate applies, and file checks on the kept
# workspace. "expect" patterns must match in some file the glob names; "forbid" patterns must match in none.
CASES = {
    "e1-dump": {"today": "2026-10-05", "gate": False,
                "expect": [("sessions/*.md", r"\[unknown\]")],
                "forbid": [("[0-9]*.md", r"state: decided")]},
    "e1-close": {"today": "2026-10-05", "gate": False,
                 "expect": [("sessions/2026-10-05-mainframe-breaks-booking.md", r"^status: closed$"),
                            ("11-unknowns-and-risks.md", r"\*\*Owner:\*\* @")],
                 "forbid": [("**/*.md", r"state: decided")]},
    "e2-discover": {"today": "2026-10-05", "gate": False,
                    "expect": [("sources.md", r"\| SRC-01 \|")],
                    "forbid": [("**/*.md", r"(?i)event bus[^\n]*(ready|Q4)[^\n]*\bfact\b")]},
    "e3-grill-refused": {"today": "2026-11-20", "gate": False,
                         "expect": [],
                         "forbid": [("capabilities/CAP-021-*.md", r"^state: decided$")]},
    "e4-shape": {"today": "2026-11-20", "gate": False,
                 "expect": [("sessions/*.md", r"(?i)grill to confirm")],
                 "forbid": []},
    "e5-ask": {"today": "2026-11-20", "gate": False, "expect": [], "forbid": []},
    "e6-epics": {"today": "2026-11-20", "gate": True,
                 "expect": [("13-epics/EPC-*.md", r"^type: epic$")],
                 "forbid": [("13-epics/EPC-*.md", r"^state: decided$")]},
}

PATH = re.compile(r"(/[^\s'\"`,;)]+)")


class EvalError(Exception):
    """The wrapper cannot grade the run. It never guesses a result."""


def find_workspaces(log):
    """Kept workspaces named in the eval's output: existing directories holding a .planner.yaml within 3 levels."""
    found = []
    for raw in PATH.findall(log):
        path = pathlib.Path(raw.rstrip("."))
        if not path.is_dir():
            continue
        for depth in ("", "*", "*/*", "*/*/*"):
            for config in path.glob(f"{depth}/.planner.yaml" if depth else ".planner.yaml"):
                vault = config.parent.resolve()
                if vault not in found:
                    found.append(vault)
    return found


def file_checks(workspace, checks, want):
    """Each (glob, pattern) with the files it matched. want=True: a hit is required. want=False: a hit is a failure."""
    lines = []
    for glob, pattern in checks:
        regex = re.compile(pattern, re.M)
        hits = [p.relative_to(workspace).as_posix() for p in sorted(workspace.glob(glob))
                if p.is_file() and ".claude" not in p.parts and regex.search(p.read_text(encoding="utf-8", errors="replace"))]
        ok = bool(hits) if want else not hits
        lines.append(f"{'pass' if ok else 'FAIL'}: {'expect' if want else 'forbid'} /{pattern}/ in {glob}"
                     + (f" ({', '.join(hits)})" if hits else ""))
    return lines


def grade(workspace, spec):
    """Mechanical grades for one kept workspace, as Markdown lines."""
    argv = [sys.executable, str(PLANNER), "check", "--vault", str(workspace), "--today", spec["today"]]
    if spec["gate"]:
        argv += ["--gate", "epics"]
    check = subprocess.run(argv, capture_output=True, text=True)
    status = subprocess.run(["git", "-C", str(workspace), "status", "--porcelain"], capture_output=True, text=True)
    inbox = subprocess.run(["git", "-C", str(workspace), "ls-files", ".inbox"], capture_output=True, text=True)
    lines = [f"- workspace: `{workspace}`",
             f"- check exit {check.returncode}: {check.stdout.splitlines()[0] if check.stdout else check.stderr.strip()}"]
    lines += [f"  - {f}" for f in check.stdout.splitlines()[1:]]
    lines.append(f"- git status: {'clean' if not status.stdout.strip() else 'DIRTY: ' + ' '.join(status.stdout.split())}")
    lines.append(f"- .inbox in git: {'no' if not inbox.stdout.strip() else 'YES: ' + ' '.join(inbox.stdout.split())}")
    lines += [f"- {line}" for line in file_checks(workspace, spec["expect"], True) + file_checks(workspace, spec["forbid"], False)]
    return lines


def run_arm(case, arm, args, out_dir):
    case_yaml = HERE / arm / case / "case.yaml"
    if not case_yaml.is_file():
        raise EvalError(f"{case_yaml} is missing")
    argv = ["claude", "plugin", "eval", str(case_yaml), "--no-publish", "--keep-temp", "--scaffold", "--trust-plugin",
            "--ablation", "none", "--runs", str(args.runs), "--max-cost-usd", str(args.max_cost_usd),
            "--model", args.model, "--judge-model", args.judge_model,
            "--output-dir", str(out_dir / f"{case}-{arm}"), "--report", str(out_dir / f"{case}-{arm}.html"),
            "--allow-tools", "Write", "Edit", "Bash"]
    result = subprocess.run(argv, capture_output=True, text=True)
    log = result.stdout + "\n" + result.stderr
    (out_dir / f"{case}-{arm}.log").write_text(log, encoding="utf-8")
    workspaces = find_workspaces(log)
    if not workspaces:
        raise EvalError(f"no kept workspace found for {case} ({arm}). The eval exited {result.returncode}; read "
                        f"{out_dir / f'{case}-{arm}.log'} and, if --keep-temp now prints paths differently, update find_workspaces().")
    lines = [f"### {arm} arm", "", f"- plugin eval exit {result.returncode}, {len(workspaces)} kept workspaces", ""]
    for workspace in workspaces:
        lines += grade(workspace, CASES[case]) + [""]
    return lines


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("cases", nargs="*", help="case names; default: all")
    parser.add_argument("--model", required=True, help="model under test, pinned for the whole run")
    parser.add_argument("--judge-model", required=True, help="model for llm graders, pinned for the whole run")
    parser.add_argument("--runs", type=int, default=3)
    parser.add_argument("--max-cost-usd", type=float, default=10)
    args = parser.parse_args(argv)
    unknown = [c for c in args.cases if c not in CASES]
    if unknown:
        parser.error(f"unknown cases: {', '.join(unknown)}. Known: {', '.join(CASES)}")
    stamp = datetime.datetime.now().strftime("%Y-%m-%d-%H%M")
    out_dir = HERE / ".results" / stamp
    out_dir.mkdir(parents=True, exist_ok=True)
    failed = False
    for case in args.cases or list(CASES):
        lines = [f"# {case}", "", f"Model {args.model}, judge {args.judge_model}, {args.runs} runs per arm, {stamp}.", ""]
        for arm in ARMS:
            try:
                lines += run_arm(case, arm, args, out_dir)
            except EvalError as exc:
                failed = True
                lines += [f"### {arm} arm", "", f"- could not grade: {exc}", ""]
        report = out_dir / f"{case}.md"
        report.write_text("\n".join(lines), encoding="utf-8")
        print("\n".join(lines))
    print(f"Results: {out_dir}")
    return 2 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
