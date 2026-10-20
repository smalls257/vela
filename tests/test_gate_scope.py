"""The gate's scoping says a family is untouched only when it is.

The Violation is a Silent Fallback: `printf "$files" | grep -q` under `set -o pipefail` read grep's early exit (the
writer's SIGPIPE) as "no match" once the list was large, so the gate skipped the sim and browser tests on exactly the
biggest merges (E85).
"""
import subprocess

from conftest import REPO

GATE = REPO / ".githooks" / "gate"


def scoped_args(files):
    body = GATE.read_text(encoding="utf-8")
    defs = "\n".join(body[body.index(start):] .split("\n}\n", 1)[0] + "\n}" for start in (
        "BROWSER_PATHS=", "scoped_pytest_args() {"))
    script = f"set -uo pipefail\n{defs}\nchanged_files() {{ cat <<'LIST'\n{files}\nLIST\n}}\nscoped_pytest_args"
    return subprocess.run(["bash", "-c", script], capture_output=True, text=True)


def test_a_large_change_list_that_touches_both_families_skips_nothing():
    files = "\n".join(["plugin/lib/vela/explorer/build.py"] + [f"docs/n{i}.md" for i in range(20000)])
    result = scoped_args(files)
    assert "SKIPPED" not in result.stderr, result.stderr
    assert result.stdout.strip() == ""


def test_a_change_list_that_touches_neither_family_skips_both():
    result = scoped_args("docs/one.md\nREADME.md")
    assert "SKIPPED browser" in result.stderr and "SKIPPED sim" in result.stderr
