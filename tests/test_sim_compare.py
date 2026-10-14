"""tests/sim/compare.py: a run recorded before the rename compares with a new one, arm for arm and count for count.

The Paper Tiger this guards against: the mid-point gate reads "codes and IDs per lead-facing turn" and tool names. If an
old run's slash commands and `scripts/...` paths were not read in today's names, its tool names would not count, and the
new run's would look like new leaks. The old lines are in tests/sim/legacy_lines.py. Nothing here calls a model.
"""
import importlib.util
import json
import subprocess
import sys

import pytest

from conftest import REPO

SIM = REPO / "tests" / "sim"


def load(name):
    spec = importlib.util.spec_from_file_location(f"sim_{name}", SIM / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


compare = load("compare")
legacy = load("legacy_lines")


@pytest.mark.parametrize("turn,old,twin", legacy.LINES, ids=[str(t) for t, _, _ in legacy.LINES])
def test_an_old_line_reads_as_its_hand_renamed_twin(turn, old, twin):
    assert compare.modern_text(old) == twin


def test_the_old_command_names_become_todays():
    mapped = {turn: compare.modern_text(old) for turn, old, _ in legacy.LINES}
    assert "`/vela:close`" in mapped[18]
    assert "`vela check`" in mapped[30]
    assert "plugin/scripts/vela questions" in mapped[56]
    assert "`.vela/`" in mapped[46]


@pytest.mark.parametrize("turn,old,twin", legacy.LINES, ids=[str(t) for t, _, _ in legacy.LINES])
def test_an_old_line_counts_the_same_as_its_twin(turn, old, twin):
    old_counts = compare.lead_counts([compare.modern_text(old)])
    assert old_counts == compare.lead_counts([twin])
    assert old_counts["tool_names"] >= 1, "every copied line names the tool"
    assert compare.lead_counts([old])["tool_names"] == 0, "unmapped, the old line's tool names would not count"


def test_codes_count_once_and_a_launcher_path_is_one_tool_name():
    by_turn = {turn: twin for turn, _, twin in legacy.LINES}
    counts = compare.lead_counts([by_turn[64]])
    assert counts["by_kind"]["check code"] == 1 and counts["codes_and_ids"] == 1
    assert compare.lead_counts([by_turn[56]])["tool_names"] == 1, "scripts/vela questions is one mention"
    assert compare.lead_counts(["Vela turns notes into a plan, and vela is not on PATH."])["tool_names"] == 0


def write_run(folder, arm, texts, scored=True):
    """A finished run as run.py leaves it: run.json with per_arm, and the arm's transcript and scorecard."""
    (folder / arm).mkdir(parents=True)
    endings = [{"session": 1, "mode": "dump", "reason": "persona-end", "turns": len(texts)}]
    (folder / "run.json").write_text(json.dumps({"run_id": folder.name, "arms": [arm],
                                                 "per_arm": {arm: {"spent_usd": 1.5, "endings": endings}}}))
    lines = []
    for n, text in enumerate(texts, 1):
        lines.append(json.dumps({"turn": 2 * n - 1, "speaker": "lead", "text": "/vela:dump UNK-001 W362"}))
        lines.append(json.dumps({"turn": 2 * n, "speaker": "assistant", "text": text}))
    (folder / arm / "transcript.jsonl").write_text("\n".join(lines) + "\n")
    if scored:
        card = {"capture": {"counts": {"unknowns": 26, "unknowns_with_ask": 6, "asks": ["@cio"]}},
                "knows": [{"id": "K1", "captured": True}, {"id": "K2", "captured": False}], "decided_without_yes": []}
        (folder / arm / "scorecard.json").write_text(json.dumps(card))


def test_an_old_results_folder_pairs_with_a_new_one(tmp_path):
    old_dir, new_dir = tmp_path / "old-run", tmp_path / "new-run"
    write_run(old_dir, legacy.OLD_ARM, [old for _, old, _ in legacy.LINES])
    write_run(new_dir, "vela", [twin for _, _, twin in legacy.LINES])
    result = compare.compare(old_dir, new_dir)
    assert list(result["pairs"]) == ["vela"] and result["unpaired"] == {"old": [], "new": []}
    old, new = result["pairs"]["vela"]["old"], result["pairs"]["vela"]["new"]
    assert old["stored_as"] == legacy.OLD_ARM and old["legacy_names_mapped"] and not new["legacy_names_mapped"]
    assert old["lead_facing"] == new["lead_facing"], "the lead read the same lines, so the counts are the same"
    assert old["lead_facing"]["turns"] == len(legacy.LINES), "lead turns are not lead-facing"
    assert old["detail"] == {"unknowns": 26, "unknowns_with_ask": 6}
    assert old["judged"]["knows captured"] == "1 of 2" and old["endings"] == "persona-end 1"
    assert "skipped close steps" in result["not_counted"]


def test_a_new_run_is_never_rewritten(tmp_path):
    """Only an arm stored under an old name is mapped: a new run that said an old name keeps it, and it doesn't count."""
    old_dir, new_dir = tmp_path / "old-run", tmp_path / "new-run"
    write_run(old_dir, "vela", ["`vela check` shows 0 errors."])
    write_run(new_dir, "vela", [legacy.LINES[1][1]])
    result = compare.compare(old_dir, new_dir)["pairs"]["vela"]
    assert result["old"]["lead_facing"]["tool_names"] == 1 and result["new"]["lead_facing"]["tool_names"] == 0


def test_a_stopped_run_without_scores_says_what_it_lacks(tmp_path):
    old_dir, new_dir = tmp_path / "old-run", tmp_path / "new-run"
    write_run(old_dir, legacy.OLD_ARM, [legacy.LINES[0][1]], scored=False)
    (old_dir / "run.json").unlink()
    write_run(new_dir, "vela", [legacy.LINES[0][2]])
    old = compare.compare(old_dir, new_dir)["pairs"]["vela"]["old"]
    assert "not_scored" in old and "detail" not in old and "per_arm" in old["note"]
    text = compare.report(compare.compare(old_dir, new_dir))
    assert "unknowns: not known -> 26" in text and "scorecard.json is missing" in text


def test_the_command_line_prints_the_pairs_and_refuses_runs_with_no_shared_arm(tmp_path):
    old_dir, new_dir, other = tmp_path / "old-run", tmp_path / "new-run", tmp_path / "other-run"
    write_run(old_dir, legacy.OLD_ARM, [legacy.LINES[0][1]])
    write_run(new_dir, "vela", [legacy.LINES[0][2]])
    write_run(other, "baseline", ["Done."])
    done = subprocess.run([sys.executable, str(SIM / "compare.py"), str(old_dir), str(new_dir)],
                          capture_output=True, text=True, timeout=60)
    assert done.returncode == 0, done.stderr
    assert "Arm vela" in done.stdout and "LEGACY_NAMES" in done.stdout and "tool_names_per_turn: 1.0 -> 1.0" in done.stdout
    as_json = subprocess.run([sys.executable, str(SIM / "compare.py"), str(old_dir), str(new_dir), "--json"],
                             capture_output=True, text=True, timeout=60)
    assert json.loads(as_json.stdout)["pairs"]["vela"]["old"]["stored_as"] == legacy.OLD_ARM
    refused = subprocess.run([sys.executable, str(SIM / "compare.py"), str(old_dir), str(other)],
                             capture_output=True, text=True, timeout=60)
    assert refused.returncode == 2 and "share no arm" in refused.stderr
