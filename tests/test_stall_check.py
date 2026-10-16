"""tools/stall_check.py: a sim or probe run that has gone quiet with nothing working on it is listed as stalled; a
finished run, a working one, or one whose checkout still has a sim process is not."""
import json
import os
import pathlib
import sys
import time

from conftest import REPO

sys.path.insert(0, str(REPO / "tools"))
import stall_check as sc  # noqa: E402

NOW = 1_800_000_000.0


def run_folder(name, minutes_quiet, finished=False, checkout=pathlib.Path("/a")):
    return sc.RunFolder(checkout / "tests/sim/results" / name, checkout, NOW - minutes_quiet * 60, finished)


def verdicts(runs, busy=(), unplaced=0, minutes=25, window=10):
    return {f.run.path.name: f.verdict for f in sc.judge(runs, set(busy), unplaced, NOW, minutes, window)}


def test_quiet_with_no_process_is_stalled_and_the_rest_are_not():
    runs = [run_folder("hung", 40), run_folder("busy", 3), run_folder("done", 90, finished=True),
            run_folder("old", 60 * 11)]
    assert verdicts(runs) == {"hung": sc.STALLED, "busy": sc.WORKING}


def test_a_process_in_the_runs_checkout_keeps_it_off_the_stalled_list_and_only_that_checkout():
    """The old shell check asked whether any sim process ran anywhere: a hang in one worktree read as alive while
    another worktree worked."""
    a, b = pathlib.Path("/a"), pathlib.Path("/b")
    runs = [run_folder("in-a", 40, checkout=a), run_folder("in-b", 40, checkout=b)]
    assert verdicts(runs, busy={a}) == {"in-a": sc.QUIET_OK, "in-b": sc.STALLED}


def test_a_process_that_cant_be_placed_makes_quiet_runs_maybe_not_stalled():
    assert verdicts([run_folder("quiet", 40)], unplaced=1) == {"quiet": sc.MAYBE}


def test_finished_reads_each_runs_own_end_marker(tmp_path):
    sim, probe, partial = tmp_path / "sim", tmp_path / "probe", tmp_path / "partial"
    for folder in (sim, probe, partial):
        folder.mkdir()
    (sim / "run.json").write_text(json.dumps({"spent_usd": 1, "exit": 0}), encoding="utf-8")
    (probe / "probe.json").write_text("{}", encoding="utf-8")
    (partial / "run.json").write_text(json.dumps({"spent_usd": 1}), encoding="utf-8")
    assert sc.finished(sim) and sc.finished(probe) and not sc.finished(partial)


def test_place_matches_a_process_to_the_deepest_checkout_by_cwd_or_command_line():
    main, worktree = pathlib.Path("/m"), pathlib.Path("/m/.claude/worktrees/w")
    cwds = {1: pathlib.Path("/m/.claude/worktrees/w/tests"), 2: None, 3: None}
    processes = [(1, "python3 tests/sim/probe.py x"), (2, "python3 /m/tests/sim/run.py --out /m/tests/sim/results"),
                 (3, "python3 tests/sim/run.py")]
    assert sc.place(processes, {main, worktree}, cwd=cwds.get) == ({worktree, main}, 1)


def test_the_tool_lists_a_stalled_probe_folder_and_exits_1(tmp_path, monkeypatch, capsys):
    results = tmp_path / "checkout" / "tests" / "sim" / "results"
    hung, done = results / "probes" / "2026-10-16-1-hung", results / "probes" / "2026-10-16-1-done"
    for folder in (hung, done):
        folder.mkdir(parents=True)
        (folder / "transcript.jsonl").write_text("{}\n", encoding="utf-8")
    (done / "probe.json").write_text("{}", encoding="utf-8")
    old = time.time() - 40 * 60
    for path in (hung, hung / "transcript.jsonl"):
        os.utime(path, (old, old))
    monkeypatch.setattr(sc, "sim_processes", lambda: [])
    assert sc.main(["--results", str(results)]) == 1
    out = capsys.readouterr().out
    assert f"stalled: 40 min since the last write: {hung.resolve()}" in out and "done" not in out.split("stall_check:")[0]


def test_a_process_list_that_cant_be_read_is_a_tool_failure_not_nothing_running(tmp_path, monkeypatch, capsys):
    def broken():
        raise sc.CheckFailed("ps failed: not permitted")
    monkeypatch.setattr(sc, "sim_processes", broken)
    assert sc.main(["--results", str(tmp_path)]) == 2
    assert "ps failed" in capsys.readouterr().err
