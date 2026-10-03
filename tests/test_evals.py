"""The plugin-eval cases and their wrapper. Nothing here runs a model: the paid runs are by hand."""
import shutil
import subprocess
import sys

import pytest
import yaml

from conftest import REPO

EVALS = REPO / "tests" / "evals"
sys.path.insert(0, str(EVALS))
import run  # noqa: E402

ARMS = {"plugin": REPO / "plugin", "stub": REPO / "tests" / "stub-conventions"}
GRADER_TYPES = {"regex", "tool_used", "tool_order", "file_exists", "llm", "baseline"}
VAULTS = ("template", "discover-docs", "close-dump", "fixture", "grill-refused", "epics-empty")


def cases(arm):
    return sorted(p.name for p in (EVALS / arm).iterdir() if p.is_dir())


def test_both_arms_hold_the_same_cases_and_the_wrapper_knows_them():
    assert cases("plugin") == cases("stub") == sorted(run.CASES)
    assert {"e1-dump", "e1-close", "e2-discover", "e3-grill-refused", "e4-shape", "e5-ask", "e6-epics"} == set(run.CASES)


@pytest.mark.parametrize("arm", ARMS)
def test_case_files(arm):
    for name in cases(arm):
        folder = EVALS / arm / name
        data = yaml.safe_load((folder / "case.yaml").read_text(encoding="utf-8"))
        assert data["schema_version"] == "1.1"
        assert data["name"] == f"{name}-{arm}"
        assert [(folder / p).resolve() for p in data["plugins"]] == [ARMS[arm].resolve()]
        assert data["execution"]["prompt"].strip()
        assert data["context"]["scaffold_script"] == "fixture.sh"
        assert data["graders"], f"{name} has no grader"
        for grader in data["graders"]:
            assert grader["type"] in GRADER_TYPES, grader
        script = (folder / "fixture.sh").read_text(encoding="utf-8")
        assert script.startswith("#!/usr/bin/env bash")
        assert script.rstrip().split()[-1] == arm
        assert script.rstrip().split()[-2] in VAULTS


def test_plugin_arm_prompts_call_a_planner_skill_and_stub_prompts_do_not():
    for name in cases("plugin"):
        plugin = yaml.safe_load((EVALS / "plugin" / name / "case.yaml").read_text(encoding="utf-8"))
        stub = yaml.safe_load((EVALS / "stub" / name / "case.yaml").read_text(encoding="utf-8"))
        assert plugin["execution"]["prompt"].startswith("/planner:")
        assert "/planner:" not in stub["execution"]["prompt"]


@pytest.mark.skipif(shutil.which("git") is None, reason="git is not installed")
@pytest.mark.parametrize("vault", VAULTS)
@pytest.mark.parametrize("arm", ARMS)
def test_scaffold_builds_a_clean_vault(tmp_path, vault, arm):
    result = subprocess.run([sys.executable, str(EVALS / "scaffold.py"), vault, arm], cwd=tmp_path, capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    installed = tmp_path / ".claude" / "skills" / "planner"
    assert (installed / "bin" / "planner").is_file()
    assert (installed / "skills").is_dir() == (arm == "plugin"), "the stub arm must see no skill text"
    check = subprocess.run([sys.executable, str(installed / "bin" / "planner"), "check", "--today", "2026-11-20"],
                           cwd=tmp_path, capture_output=True, text=True)
    assert check.returncode == 0, check.stdout
    status = subprocess.run(["git", "status", "--porcelain"], cwd=tmp_path, capture_output=True, text=True)
    assert status.stdout == ""


def test_find_workspaces_reads_only_the_printed_paths(tmp_path):
    kept = tmp_path / "run-1" / "work"
    kept.mkdir(parents=True)
    (kept / ".planner.yaml").write_text("initiative: INI-001\ntitle: x\n", encoding="utf-8")
    assert run.find_workspaces(f"kept: {kept}\nkept again {kept}.\nsome other line /no/such/dir\n") == [kept.resolve()]
    assert run.find_workspaces(f"kept: {tmp_path / 'run-1'}") == [], "a parent of the workspace is not a kept workspace"
    assert run.find_workspaces("nothing kept") == []


def test_file_checks_report_hits_and_misses(tmp_path):
    (tmp_path / "sessions").mkdir()
    (tmp_path / "sessions" / "s.md").write_text("- [thought] (lead) that's decided, grill to confirm ^c01\n", encoding="utf-8")
    assert run.file_checks(tmp_path, [("sessions/*.md", "grill to confirm")], True)[0].startswith("pass")
    assert run.file_checks(tmp_path, [("sessions/*.md", "grill to confirm")], False)[0].startswith("FAIL")
    assert run.file_checks(tmp_path, [("missing/*.md", "x")], True)[0].startswith("FAIL")


def test_wrapper_refuses_unpinned_models():
    with pytest.raises(SystemExit):
        run.main(["e1-dump"])


def scaffolded(tmp_path, vault, arm="plugin"):
    result = subprocess.run([sys.executable, str(EVALS / "scaffold.py"), vault, arm], cwd=tmp_path, capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    return tmp_path


def vault_of(name):
    return (EVALS / "plugin" / name / "fixture.sh").read_text(encoding="utf-8").split()[-2]


@pytest.mark.skipif(shutil.which("git") is None, reason="git is not installed")
@pytest.mark.parametrize("name", sorted(run.CASES))
def test_forbid_and_expect_checks_cannot_pass_or_fail_on_the_untouched_scaffold(tmp_path, name):
    workspace = scaffolded(tmp_path, vault_of(name))
    spec = run.CASES[name]
    assert all(line.startswith("pass") for line in run.file_checks(workspace, spec["forbid"], False)), "forbid hits the scaffold"
    assert all(line.startswith("FAIL") for line in run.file_checks(workspace, spec["expect"], True)), "expect already met by the scaffold"


@pytest.mark.skipif(shutil.which("git") is None, reason="git is not installed")
def test_grade_passes_a_clean_scaffold_and_fails_an_invented_id_and_a_new_decided(tmp_path):
    workspace = scaffolded(tmp_path, "fixture")
    spec = {"today": "2026-11-20", "gate": False, "readonly": True, "expect": [], "forbid": []}
    assert not run.failed(run.grade(workspace, spec))
    unknowns = workspace / "11-unknowns-and-risks.md"
    unknowns.write_text(unknowns.read_text(encoding="utf-8") + "\n### UNK-099 Invented\n", encoding="utf-8")
    lines = run.grade(workspace, spec)
    assert any("invented ID UNK-099" in line and line.startswith("- FAIL") for line in lines), lines
    assert any(line.startswith("- FAIL: git status DIRTY") for line in lines), "a read-only case must stay clean"


@pytest.mark.skipif(shutil.which("git") is None, reason="git is not installed")
def test_grade_fails_a_new_decided_state(tmp_path):
    workspace = scaffolded(tmp_path, "grill-refused")
    spec = {"today": "2026-11-20", "gate": False, "expect": [], "forbid": []}
    cap = workspace / "capabilities" / "CAP-021-amend-or-cancel.md"
    cap.write_text(cap.read_text(encoding="utf-8").replace("state: assumption", "state: decided"), encoding="utf-8")
    assert any(line.startswith("- FAIL: decided states") for line in run.grade(workspace, spec))


@pytest.mark.skipif(shutil.which("git") is None, reason="git is not installed")
def test_an_invented_id_recorded_in_changes_passes(tmp_path):
    workspace = scaffolded(tmp_path, "close-dump")
    unknowns = workspace / "11-unknowns-and-risks.md"
    unknowns.write_text(unknowns.read_text(encoding="utf-8") + "\n### UNK-001 Real one\n", encoding="utf-8")
    assert any("invented ID UNK-001" in line for line in run.invented_ids(workspace))
    record = workspace / "sessions" / "2026-10-05-mainframe-breaks-booking.md"
    record.write_text(record.read_text(encoding="utf-8") + "| UNK-001 | none | open | c02 |\n", encoding="utf-8")
    assert run.invented_ids(workspace)[0].startswith("pass")


class Done:
    def __init__(self, returncode=0, stdout="", stderr=""):
        self.returncode, self.stdout, self.stderr = returncode, stdout, stderr


def fake_eval(monkeypatch, tmp_path, returncode=0, log="", graded=None):
    """Replace only the paid call. Everything else in main() runs for real."""
    real = subprocess.run
    monkeypatch.setattr(run, "RESULTS", tmp_path / "results")
    monkeypatch.setattr(run.subprocess, "run", lambda argv, **kw: Done(returncode, log) if argv[0] == "claude" else real(argv, **kw))
    if graded is not None:
        monkeypatch.setattr(run, "grade", lambda workspace, spec: graded)


def kept_workspaces(tmp_path, count):
    paths = []
    for n in range(count):
        path = tmp_path / f"run-{n}"
        path.mkdir(exist_ok=True)
        (path / ".planner.yaml").write_text("initiative: INI-001\ntitle: x\n", encoding="utf-8")
        paths.append(str(path))
    return "\n".join(f"kept: {p}" for p in paths)


ARGV = ["e5-ask", "--model", "m", "--judge-model", "j", "--runs", "2"]


def test_main_returns_2_when_no_workspace_is_found(monkeypatch, tmp_path):
    fake_eval(monkeypatch, tmp_path, log="nothing here")
    assert run.main(ARGV) == 2


def test_main_returns_2_when_plugin_eval_exits_2(monkeypatch, tmp_path):
    fake_eval(monkeypatch, tmp_path, returncode=2, log=kept_workspaces(tmp_path, 2), graded=["- pass: x"])
    assert run.main(ARGV) == 2


def test_main_returns_2_when_workspaces_are_fewer_than_runs(monkeypatch, tmp_path):
    fake_eval(monkeypatch, tmp_path, log=kept_workspaces(tmp_path, 1), graded=["- pass: x"])
    assert run.main(ARGV) == 2


def test_main_returns_1_on_a_failed_grade_and_0_when_all_pass(monkeypatch, tmp_path):
    fake_eval(monkeypatch, tmp_path, log=kept_workspaces(tmp_path, 2), graded=["- FAIL: forbid /x/ in y"])
    assert run.main(ARGV) == 1
    fake_eval(monkeypatch, tmp_path, log=kept_workspaces(tmp_path, 2), graded=["- pass: x"])
    assert run.main(ARGV) == 0
