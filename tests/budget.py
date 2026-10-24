"""Time a vela command the way a person waits for it: from an installed-shape copy of the plugin (no __pycache__),
after one warm-up run that fills the bytecode cache, by the child's CPU time. Wall time swings threefold when other
agents load this machine, so it is reported, never asserted (plan ruling 4)."""
import pathlib
import resource
import shutil
import statistics
import subprocess
import time

from conftest import REPO

BUDGET = 0.5  # seconds of CPU: the owner's "next to no added latency", design section "Owner decisions"


def installed_copy(tmp_path):
    target = pathlib.Path(tmp_path) / "installed" / "plugin"
    shutil.copytree(REPO / "plugin", target, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    return target


def cpu_run(argv, env=None, stdin=""):
    """(CPU seconds of the child and everything it waited for, wall seconds, CompletedProcess)."""
    before = resource.getrusage(resource.RUSAGE_CHILDREN)
    started = time.perf_counter()
    done = subprocess.run(argv, input=stdin, capture_output=True, text=True, env=env, timeout=120)
    wall = time.perf_counter() - started
    after = resource.getrusage(resource.RUSAGE_CHILDREN)
    return (after.ru_utime - before.ru_utime) + (after.ru_stime - before.ru_stime), wall, done


def measure(plugin, args, env, runs=5, stdin=""):
    """{"cpu": least CPU, "wall": median wall, "codes": exit codes}; the warm-up run is not counted. CPU is the least of the
    runs, not the median: other work on the machine only ever adds to it (the full gate runs dozens of workers at once,
    which pushed a 0.15 s hook to 0.20 s), so the least run is the closest to what the command itself costs."""
    argv = ["sh", str(plugin / "scripts" / "run-vela"), *args]
    cpu_run(argv, env, stdin)
    found = [cpu_run(argv, env, stdin) for _ in range(runs)]
    return {"cpu": min(c for c, _, _ in found), "wall": statistics.median(w for _, w, _ in found),
            "codes": [d.returncode for _, _, d in found], "out": found[-1][2].stdout}
