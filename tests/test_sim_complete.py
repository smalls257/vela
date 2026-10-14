"""Task 29: the near-complete Heron script, its outsider personas and the scorecard's completeness gate. Nothing here
calls a model: the one run is --stub."""
import importlib.util
import json
import os
import pathlib
import re
import shutil
import subprocess
import sys
from types import SimpleNamespace

import pytest
import yaml

from conftest import REPO

SIM = REPO / "tests" / "sim"
spec = importlib.util.spec_from_file_location("sim_run_complete", SIM / "run.py")
sim = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sim)

MODELS = ["--model", "test-model", "--persona-model", "test-persona", "--judge-model", "test-judge"]


def status_line(percent):
    return (f"Completeness: {percent}%, the average of 15 of 18 items settled, 20 of 28 open questions answered, "
            f"18 of 24 cross-cutting concern checks made, 121 of 121 standard questions dealt with, 22 of 22 pages written.")


def test_the_gate_fails_a_vault_at_79_percent_and_names_what_held_it_back():
    verdict = sim.completeness_verdict(sim.parse_completeness(status_line(79)), 80)
    assert verdict["passed"] is False and verdict["fails_run"] is True
    # weakest share first; a share at 100% held nothing back
    assert verdict["held_back"] == ["open questions answered: 20 of 28 (71%)",
                                    "cross-cutting concern checks made: 18 of 24 (75%)", "items settled: 15 of 18 (83%)"]


def test_the_gate_passes_a_vault_at_80_percent():
    verdict = sim.completeness_verdict(sim.parse_completeness(status_line(80)), 80)
    assert verdict["passed"] is True and verdict["fails_run"] is False


def test_a_missing_completeness_figure_fails_the_gate_rather_than_passing_it():
    verdict = sim.completeness_verdict(sim.parse_completeness("planner status: 3 apps"), 80)
    assert verdict["passed"] is False and verdict["fails_run"] and verdict["held_back"][0].startswith("no figure")


def test_a_stub_run_reports_the_gate_without_failing_the_run():
    verdict = sim.completeness_verdict(sim.parse_completeness(status_line(46)), 80, enforced=False)
    assert verdict["passed"] is False and verdict["fails_run"] is False


def test_under_the_gate_exits_3_and_a_tool_failure_still_outranks_it():
    assert sim.run_exit(False, False, ["arm"]) == 3
    assert sim.run_exit(False, True, ["arm"]) == 3, "an early stop does not hide a run that does not count"
    assert sim.run_exit(True, False, ["arm"]) == 2
    assert sim.run_exit(False, True, []) == 1 and sim.run_exit(False, False, []) == 0


def test_the_scorecard_reads_the_completeness_line_planner_status_prints_for_the_vault(tmp_path):
    vault = tmp_path / "vault"
    shutil.copytree(SIM / "snapshots" / "heron-desk" / "after-design-2", vault)
    found = sim.completeness_of(vault)
    assert "error" not in found, found
    assert found["line"].startswith(f"Completeness: {found['percent']}%") and len(found["shares"]) == 5
    arm = SimpleNamespace(vault=vault, completeness_gate=80, args=SimpleNamespace(stub=False))
    md = "\n".join(sim.render_completeness({"completeness": found,
                                            "completeness_gate": sim.completeness_verdict(found, arm.completeness_gate)}))
    assert "## Completeness" in md and "Gate 80%: FAIL" in md and "held back by open questions answered" in md
