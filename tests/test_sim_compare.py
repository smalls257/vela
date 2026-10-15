"""tests/sim/compare_runs.py, the one tool that compares two sim runs: a run recorded before the rename compares with a
new one, and each figure the mid-point gate reads is measured the way the 2026-10-14 diagnosis showed it must be.

The Paper Tiger this guards against: a comparison that runs, prints a verdict, and is wrong for reasons nobody sees,
such as an old run's tool names counting differently from today's, or a final vault read from a stale branch.
Every run here is built in tmp_path from a few pages and a transcript. Nothing calls a model.
"""
import importlib.util
import json
import subprocess
import sys

import pytest

from conftest import REPO

SIM = REPO / "tests" / "sim"
GIT = ["git", "-c", "user.name=T", "-c", "user.email=t@example.invalid", "-c", "commit.gpgsign=false",
       "-c", "init.defaultBranch=main"]


def load(name):
    spec = importlib.util.spec_from_file_location(f"sim_{name}", SIM / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


compare = load("compare_runs")
legacy = load("legacy_lines")


def git(cwd, *args):
    done = subprocess.run([*GIT, *args], cwd=cwd, capture_output=True, text=True, timeout=60)
    assert done.returncode == 0, done.stderr
    return done.stdout


def write_pages(vault, pages):
    for rel, text in pages.items():
        path = vault / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")


def make_run(folder, arm, turns, pages=None, raw=None):
    """A finished run as run.py leaves it: run.json, the arm's transcript, raw/ calls, and a vault pushed to the arm's
    origin.git. `turns` are (speaker, text) or (speaker, text, session, mode); `raw` is one list of Bash commands per
    assistant turn. Returns the vault."""
    arm_dir = folder / arm
    arm_dir.mkdir(parents=True)
    lines, n, endings = [], 0, {}
    for turn in turns:
        speaker, text, session, mode = (*turn, 1, "dump")[:4] if len(turn) == 2 else turn
        n += 1
        if session not in endings:
            lines.append({"speaker": "driver", "session": session, "mode": mode, "event": "session-start"})
            endings[session] = mode
        lines.append({"turn": n, "speaker": speaker, "session": session, "mode": mode, "text": text,
                      "session_id": f"s{session}", "cost_usd": 0.1})
    ends = [{"session": s, "mode": m, "reason": "persona-end", "turns": 2} for s, m in endings.items()]
    for s in endings:
        lines.append({"speaker": "driver", "session": s, "event": "session-end", "reason": "persona-end"})
    (arm_dir / "transcript.jsonl").write_text("\n".join(json.dumps(x) for x in lines) + "\n", encoding="utf-8")
    (folder / "run.json").write_text(json.dumps({"run_id": folder.name, "exit": 0, "arms": [arm], "spent_usd": 1.0,
                                                 "per_arm": {arm: {"spent_usd": 1.0, "endings": ends}}}),
                                     encoding="utf-8")
    if raw is not None:
        (arm_dir / "raw").mkdir()
        for i, commands in enumerate(raw, 1):
            events = [{"type": "assistant", "message": {"content": [
                {"type": "tool_use", "name": "Bash", "input": {"command": c}} for c in commands]}}]
            (arm_dir / "raw" / f"{i:03d}-assistant.txt").write_text("\n".join(json.dumps(e) for e in events) + "\n",
                                                                    encoding="utf-8")
    vault = arm_dir / "vault"
    vault.mkdir()
    git(vault, "init", "-q")
    write_pages(vault, pages or {"01-goals.md": "---\ntype: goals\n---\n# Goals\n\nHeron helps.\n"})
    git(vault, "add", "-A")
    git(vault, "commit", "-q", "-m", "start")
    git(arm_dir, "init", "-q", "--bare", "origin.git")
    git(vault, "remote", "add", "origin", str(arm_dir / "origin.git"))
    git(vault, "push", "-q", "origin", "main")
    return vault


def run_tool(base, mid, *extra):
    out = base.parent / "report.json"
    done = subprocess.run([sys.executable, str(SIM / "compare_runs.py"), str(base), str(mid), "--baseline-checkout",
                           str(REPO), "--midpoint-checkout", str(REPO), "--json", str(out), *extra],
                          capture_output=True, text=True, timeout=300)
    assert done.returncode in (0, 1, 3), done.stderr
    return done, json.loads(out.read_text(encoding="utf-8"))


# ------------------------------------------------------------------ one ruler for old and new names

@pytest.mark.parametrize("turn,old,twin", legacy.LINES, ids=[str(t) for t, _, _ in legacy.LINES])
def test_an_old_line_counts_the_same_as_its_hand_renamed_twin(turn, old, twin):
    """The leak patterns name both the old tool and vela, so an old run needs no rewriting to be read alike."""
    counted = lambda text: {k: len(v) for k, v in compare.leaks_in(text).items()}
    assert counted(old) == counted(twin)
    assert counted(old), "every copied line names the tool, so each is a real test of the old name"


def test_an_old_arm_folder_is_found_by_todays_arm_name(tmp_path):
    (tmp_path / "old" / legacy.OLD_ARM).mkdir(parents=True)
    (tmp_path / "new" / "vela").mkdir(parents=True)
    assert compare.stored_arm(tmp_path / "old", "vela") == legacy.OLD_ARM
    assert compare.stored_arm(tmp_path / "new", "vela") == "vela"
    assert compare.stored_arm(tmp_path / "new", "baseline") is None


def test_an_old_run_compares_with_a_new_one_and_the_report_says_how_it_paired(tmp_path):
    base, mid = tmp_path / "old-run", tmp_path / "new-run"
    make_run(base, legacy.OLD_ARM, [("lead", "Start."), *[("assistant", old) for _, old, _ in legacy.LINES]])
    make_run(mid, "vela", [("lead", "Start."), *[("assistant", twin) for _, _, twin in legacy.LINES]])
    done, report = run_tool(base, mid)
    assert report["baseline"]["arm"] == legacy.OLD_ARM and report["midpoint"]["arm"] == "vela"
    assert any("LEGACY_NAMES" in n for n in report["baseline"]["notes"])
    leaks = {r["measure"]: r for r in report["rows"]["Codes, IDs and tool names in lead-facing turns"]}
    assert leaks["Leaks per lead-facing turn"]["status"] == "same", "the lead read the same lines"
    assert "## Verdict:" in done.stdout


def test_two_runs_are_given_once_each(tmp_path):
    done = subprocess.run([sys.executable, str(SIM / "compare_runs.py"), "a", "b", "--baseline", "c"],
                          capture_output=True, text=True, timeout=60)
    assert done.returncode == 2 and "give each run once" in done.stderr
    missing = subprocess.run([sys.executable, str(SIM / "compare_runs.py"), str(tmp_path), str(tmp_path)],
                             capture_output=True, text=True, timeout=60)
    assert missing.returncode == 2 and "no baseline run folder" in missing.stderr
