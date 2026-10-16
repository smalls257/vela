#!/usr/bin/env python3
"""List sim and probe runs that have stalled: a run folder not yet finished, with no file written for N minutes, and
no `tests/sim/run.py` or `probe.py` process working in its checkout. Read-only, and free (no model call).

    python3 tools/stall_check.py                 # this checkout and every agent worktree, quiet for 25 minutes
    python3 tools/stall_check.py --minutes 40 --results /tmp/x-wt/tests/sim/results

The Violation this exists to prevent is a Black Box: a detached run that hangs (a claude call that never returns, a
killed shell) looks exactly like one still working, so nobody notices until hours of budget have passed. It replaces
/tmp/stall-check.sh, which said only how old the newest file in each results folder was and whether any sim process
ran anywhere on the machine, so a finished run read as stalled and a hung one in worktree A read as alive while
worktree B worked.

A run folder is finished when it says so: a sim run's run.json holds "exit" (write_summary, at the end); a probe run's
probe.json exists (write_outputs, after its last turn). Folders with no write in the last --window hours are left
out, so old results don't fill the list. A process list that can't be read is a tool failure (exit 2), never "nothing
is running": that guess would call every quiet run stalled, or worse, every stalled run fine. A sim process whose
folder can't be told keeps every quiet run "maybe running", not stalled.

Exit codes: 0 nothing stalled; 1 at least one stalled run (each listed); 2 the check couldn't run.
"""
import argparse
import json
import pathlib
import re
import subprocess
import sys
import time
from dataclasses import dataclass

REPO = pathlib.Path(__file__).resolve().parents[1]
# Run from an agent worktree (<main>/.claude/worktrees/<name>), the other worktrees sit under the main checkout.
MAIN = REPO.parents[2] if REPO.parent.name == "worktrees" and REPO.parents[1].name == ".claude" else REPO
SIM_PROCESS = re.compile(r"(?:^|/|\s)(?:tests/sim/run\.py|probe\.py)(?:\s|$)")
STALLED, MAYBE, WORKING, QUIET_OK = "stalled", "maybe running", "working", "quiet, process running"


class CheckFailed(Exception):
    """The machine couldn't be read (ps or lsof failed): exit 2, with the reason."""


@dataclass(frozen=True)
class RunFolder:
    path: pathlib.Path
    checkout: pathlib.Path  # the checkout whose tests/sim/results holds it
    last_write: float  # newest mtime of any file inside, seconds since the epoch
    finished: bool


@dataclass(frozen=True)
class Finding:
    run: RunFolder
    quiet_minutes: int
    verdict: str


# ------------------------------------------------------------------ the decision (no disk, no processes)

def judge(runs, busy_checkouts, unplaced_processes, now, minutes, window_hours):
    """Each unfinished run written to within the window, with its verdict. `busy_checkouts` are the checkouts a sim
    process works in; `unplaced_processes` counts sim processes whose checkout couldn't be told."""
    found = []
    for run in runs:
        quiet = int((now - run.last_write) // 60)
        if run.finished or now - run.last_write > window_hours * 3600:
            continue
        if quiet < minutes:
            verdict = WORKING
        elif run.checkout in busy_checkouts:
            verdict = QUIET_OK
        elif unplaced_processes:
            verdict = MAYBE
        else:
            verdict = STALLED
        found.append(Finding(run, quiet, verdict))
    return sorted(found, key=lambda f: (f.verdict != STALLED, -f.quiet_minutes))


def finished(folder):
    """A sim run folder (run.json) is finished once run.json holds "exit"; a probe run folder once probe.json exists."""
    if (folder / "probe.json").is_file():
        return True
    summary = folder / "run.json"
    if not summary.is_file():
        return False
    try:
        return "exit" in json.loads(summary.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return False  # being rewritten (write_summary replaces it whole) or broken: not a finished run


# ------------------------------------------------------------------ the disk

def results_folders(given):
    if given:
        return [pathlib.Path(p).resolve() for p in given]
    roots = [MAIN / "tests" / "sim" / "results", *sorted((MAIN / ".claude" / "worktrees").glob("*/tests/sim/results")),
             *sorted(pathlib.Path("/tmp").glob("*-wt/tests/sim/results"))]
    return [r.resolve() for r in roots if r.is_dir()]


def run_folders(results):
    """Each run folder under results/ (sim runs) and results/probes/ (probe runs)."""
    for parent in (results, results / "probes"):
        if not parent.is_dir():
            continue
        for folder in sorted(p for p in parent.iterdir() if p.is_dir() and p.name != "probes"):
            if (folder / "run.json").is_file() or (folder / "transcript.jsonl").is_file() or parent.name == "probes":
                yield folder


def newest_write(folder):
    newest = folder.stat().st_mtime
    for path in folder.rglob("*"):
        try:  # nosemgrep: except-pass -- a file removed mid-walk (a temp file) says nothing about the run
            if path.is_file() and not path.is_symlink():
                newest = max(newest, path.stat().st_mtime)
        except OSError:
            continue
    return newest


def scan(results_list):
    runs = []
    for results in results_list:
        checkout = results.parents[2]
        for folder in run_folders(results):
            if finished(folder):  # checked first: a finished run's tree is never walked (results hold whole vaults)
                continue
            runs.append(RunFolder(folder, checkout, newest_write(folder), False))
    return runs


# ------------------------------------------------------------------ the processes

def _run(argv):
    try:
        done = subprocess.run(argv, capture_output=True, text=True, timeout=20)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise CheckFailed(f"{argv[0]} couldn't run: {exc}") from exc
    return done


def sim_processes():
    """(pid, command line) of each sim or probe process on this machine."""
    done = _run(["ps", "-axo", "pid=,command="])
    if done.returncode != 0:
        raise CheckFailed(f"ps failed: {done.stderr.strip() or done.returncode}")
    found = []
    for line in done.stdout.splitlines():
        pid, _, command = line.strip().partition(" ")
        if pid.isdigit() and SIM_PROCESS.search(command) and "stall_check" not in command:
            found.append((int(pid), command))
    return found


def cwd_of(pid):
    """The process's working folder, or None when lsof can't say (it exited, or isn't ours)."""
    done = _run(["lsof", "-a", "-d", "cwd", "-p", str(pid), "-Fn"])
    names = [line[1:] for line in done.stdout.splitlines() if line.startswith("n")]
    return pathlib.Path(names[0]).resolve() if done.returncode == 0 and names else None


def place(processes, checkouts, cwd=cwd_of):
    """(checkouts a process works in, how many processes couldn't be placed). A process belongs to a checkout when
    its working folder is inside it, or its command line names the checkout's path (an --out under it)."""
    busy, unplaced = set(), 0
    for pid, command in processes:
        where = cwd(pid)
        hits = {c for c in checkouts if (where and (where == c or c in where.parents)) or f"{c}/" in f"{command}/"}
        if hits:
            busy |= {max(hits, key=lambda c: len(c.parts))}  # the deepest: a worktree sits inside the main checkout
        else:
            unplaced += 1
    return busy, unplaced


# ------------------------------------------------------------------ main

def line_for(f):
    return f"{f.verdict}: {f.quiet_minutes} min since the last write: {f.run.path}"


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--minutes", type=int, default=25, help="quiet this long with no process is stalled (25)")
    parser.add_argument("--window", type=float, default=10, help="hours: folders quiet longer are left out (10)")
    parser.add_argument("--results", action="append", default=[], metavar="DIR",
                        help="a tests/sim/results folder to read (repeatable); default: this checkout, every agent "
                             "worktree and /tmp/*-wt")
    args = parser.parse_args(argv)
    if args.minutes < 1 or args.window <= 0:
        parser.error("--minutes must be at least 1 and --window more than 0")
    try:
        results = results_folders(args.results)
        runs = scan(results)
        busy, unplaced = place(sim_processes(), {r.parents[2] for r in results})
    except CheckFailed as exc:
        print(f"stall_check: {exc}", file=sys.stderr)
        return 2
    findings = judge(runs, busy, unplaced, time.time(), args.minutes, args.window)
    for f in findings:
        print(line_for(f))
    stalled = sum(f.verdict == STALLED for f in findings)
    print(f"stall_check: {len(results)} results folder(s), {len(findings)} unfinished run(s) in the last "
          f"{args.window:g} h, {stalled} stalled; {len(busy)} checkout(s) with a sim process"
          + (f", {unplaced} process(es) I couldn't place" if unplaced else "") + ".")
    return 1 if stalled else 0


if __name__ == "__main__":
    sys.exit(main())
