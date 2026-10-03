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


def test_find_workspaces_reads_paths_from_the_log(tmp_path):
    kept = tmp_path / "run-1" / "work"
    kept.mkdir(parents=True)
    (kept / ".planner.yaml").write_text("initiative: INI-001\ntitle: x\n", encoding="utf-8")
    log = f"kept: {tmp_path / 'run-1'}\nsome other line /no/such/dir\n"
    assert run.find_workspaces(log) == [kept.resolve()]
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
