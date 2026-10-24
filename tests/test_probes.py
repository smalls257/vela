"""The probe plugins stay valid, so a rerun on a new Claude Code is one command (Tasks 1 and 2)."""
import json
import shutil
import subprocess

import pytest

from conftest import REPO

PROBES = REPO / "tools" / "probes"


def test_the_marketplace_lists_both_probes():
    listed = json.loads((PROBES / ".claude-plugin" / "marketplace.json").read_text(encoding="utf-8"))
    assert {p["name"] for p in listed["plugins"]} == {"vela-probe-placement", "vela-probe-timing"}


def test_the_placement_probe_mixes_settings_hooks_and_a_module():
    hooks = json.loads((PROBES / "mod-placement" / "hooks" / "hooks.json").read_text(encoding="utf-8"))
    assert hooks["modules"] == ["./probe.js"] and "SessionStart" in hooks["hooks"]


@pytest.mark.parametrize("name", [
    "mod-placement",
    "cowork-panel-timing",
])
def test_each_probe_validates(name):
    claude = shutil.which("claude")
    if claude is None:
        pytest.skip("claude is not on PATH, so `claude plugin validate` can't run here")
    done = subprocess.run([claude, "plugin", "validate", str(PROBES / name)], capture_output=True, text=True, timeout=120)
    assert done.returncode == 0, done.stdout + done.stderr


import importlib.util


def load_report():
    spec = importlib.util.spec_from_file_location("report", PROBES / "cowork-panel-timing" / "report.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_the_report_times_turns_per_arm_from_the_hook_stamps(tmp_path):
    report = load_report()
    hooks = [{"event": "prompt", "t": 0.0}, {"event": "stop", "t": 4.0},
             {"event": "prompt", "t": 10.0}, {"event": "stop", "t": 14.5},
             {"event": "prompt", "t": 20.0}, {"event": "stop", "t": 26.0}]
    writes = [{"arm": "A", "n": 1, "t": 1.0}, {"arm": "B", "n": 2, "t": 11.0}, {"arm": "C", "n": 3, "t": 21.0}]
    found = report.turns(hooks, writes)
    assert found == {"A": [4.0], "B": [4.5], "C": [6.0]}
    lines = report.summary(found)
    assert "B: median 4.5 s, gap to A 0.5 s, under 1.0 s: yes" in lines
    assert "C: median 6.0 s, gap to A 2.0 s, under 1.0 s: no" in lines


def test_the_report_says_when_no_hook_fired():
    assert "no hook stamps" in " ".join(load_report().summary({})).lower()


def test_the_probe_writes_a_panel_that_shows_the_count(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    script = PROBES / "cowork-panel-timing" / "probe.py"
    for arm in ("A", "B"):
        done = subprocess.run(["python3", str(script), "write", "--arm", arm], capture_output=True, text=True, cwd=tmp_path)
        assert done.returncode == 0, done.stderr
    assert done.stdout.strip() == "2"
    subprocess.run(["python3", str(script), "render"], check=True, capture_output=True, cwd=tmp_path)
    assert ">2<" in (tmp_path / ".vela-probe" / "panel.html").read_text(encoding="utf-8")
