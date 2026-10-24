"""Settle anywhere: `vela decide` decides in any session, and every protection it carries still runs there."""
import json
import re

import pytest

import session_files
from conftest import REPO, run
from test_decide import (RECORD_ID, STOCK, TODAY, block_con_002, decide_con_002, git_init, git_log,
                         in_session_with_modes, make_vault)

LIB = REPO / "plugin" / "lib" / "vela"
EVERY_MODE = ["dump", "discover", "shape", "boundary", "requirements", "allocate", "releases", "grill", "epics",
              "answer", "shape, boundary"]


def decide(root, *flags):
    return run("decide", "CON-002", *flags, "--vault", str(root), "--today", TODAY, "--json")


@pytest.mark.parametrize("modes", EVERY_MODE)
def test_any_session_decides_with_a_read_back_a_yes_and_a_why(tmp_path, modes):
    root = make_vault(tmp_path)
    in_session_with_modes(root, modes)
    git_init(root)
    code, out = decide(root, "--readback", "^c01", "--yes", "^c02", "--why", "^c03", "--provider", "^c07")
    assert code == 0, out
    assert re.search(r"### CON-002[\s\S]*?- \*\*State:\*\* decided", (root / STOCK).read_text(encoding="utf-8"))
    assert git_log(root)[0] == f"{modes.split(',')[0].strip()}: CON-002 decided"
    assert "Ready to decide" not in session_files.record_text(root, RECORD_ID)


def test_outside_a_grill_the_read_back_and_the_yes_are_still_needed(tmp_path):
    root = make_vault(tmp_path)
    in_session_with_modes(root, "shape")
    code, out = decide(root, "--yes", "^c02", "--provider", "^c07")
    assert code == 1 and json.loads(out)["refusals"][0]["rule"] == "decide-unfilled"
    code, out = decide(root, "--readback", "^c03", "--yes", "^c02", "--provider", "^c07")
    assert code == 1 and "consent-yes-before-readback" in [r["rule"] for r in json.loads(out)["refusals"]]
    code, out = decide(root, "--readback", "^c01", "--yes", "^c04", "--provider", "^c07")  # ^c04 is a bare "ok"
    assert code == 1


def test_outside_a_grill_the_gate_still_runs_and_the_lead_can_set_it_aside(tmp_path):
    root = make_vault(tmp_path)
    in_session_with_modes(root, "boundary")
    block_con_002(root)
    code, out = decide(root, "--readback", "^c01", "--yes", "^c02", "--provider", "^c07")
    assert code == 1 and "GATE-4" in [r["rule"] for r in json.loads(out)["refusals"]]
    git_init(root)
    code, out = decide(root, "--readback", "^c01", "--yes", "^c02", "--provider", "^c07",
                       "--override", "GATE-4", "--reason-from", "^c06", "--until", "2026-11-01")
    assert code == 0, out


def test_later_lists_the_yes_and_decides_nothing(tmp_path):
    root = make_vault(tmp_path)
    in_session_with_modes(root, "shape")
    before = (root / STOCK).read_text(encoding="utf-8")
    code, out = decide(root, "--later", "--yes", "^c02")
    assert code == 0, out
    assert (root / STOCK).read_text(encoding="utf-8") == before
    assert f"## Ready to decide\n\n- CON-002: the lead said yes in {RECORD_ID} (^c02)" in session_files.record_text(root, RECORD_ID)
    brief = json.loads(run("session", "brief", "--vault", str(root), "--today", TODAY, "--json")[1])
    assert [(e["id"], e["session"]) for e in brief["ready_to_decide"]] == [("CON-002", RECORD_ID)]
    assert decide(root, "--later", "--yes", "^c02")[0] == 0
    assert session_files.record_text(root, RECORD_ID).count("- CON-002: the lead said yes") == 1, "listed once"


def test_later_needs_the_yes_and_is_not_a_settle(tmp_path):
    root = make_vault(tmp_path)
    in_session_with_modes(root, "shape")
    assert decide(root, "--later")[0] == 1
    assert decide(root, "--later", "--yes", "^c02", "--readback", "^c01")[0] == 1


def test_settling_later_drops_it_off_the_list(tmp_path):
    root = make_vault(tmp_path)
    in_session_with_modes(root, "shape")
    decide(root, "--later", "--yes", "^c02")
    git_init(root)
    assert decide_con_002(root)[0] == 0
    brief = json.loads(run("session", "brief", "--vault", str(root), "--today", TODAY, "--json")[1])
    assert brief["ready_to_decide"] == []


def test_nothing_reads_a_sessions_modes_to_decide():
    gone = ("can_decide", "CANNOT_DECIDE", "cannot_decide_here", "StubUnreadable", "decide-not-in-this-session")
    hits = [f"{p.relative_to(REPO)}:{n}" for p in LIB.rglob("*.py")
            for n, line in enumerate(p.read_text(encoding="utf-8").splitlines(), 1) if any(g in line for g in gone)]
    assert hits == []
