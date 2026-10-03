"""The migrated reference fixture: clean, render-stable, Jira-free, and each
check rule caught by one broken copy.

Broken copies are made in tmp_path. After the edit the test runs render, as a
session close would, so the stale-block echo of a source change is gone and
the finding under test is the only one left.
"""
import re
import shutil
import subprocess
import sys
import time

import pytest

from conftest import REPO, check, edit, findings, run

FIXTURE = REPO / "examples" / "unified-booking"
TODAY = "2026-11-20"


@pytest.fixture
def ub(tmp_path):
    dest = tmp_path / "unified-booking"
    shutil.copytree(FIXTURE, dest)
    return dest


def broken(vault):
    """Render, then check. Returns the findings."""
    code, out = run("render", "--vault", str(vault))
    assert code == 0, out
    return findings(check(vault, TODAY)[1])


def snapshot(vault):
    return {p.relative_to(vault).as_posix(): p.read_bytes() for p in vault.rglob("*.md")}


def test_fixture_is_clean_and_fast():
    started = time.perf_counter()
    result = subprocess.run([sys.executable, str(REPO / "plugin" / "bin" / "planner"), "check",
                             "--vault", str(FIXTURE), "--today", TODAY], capture_output=True, text=True)
    elapsed = time.perf_counter() - started
    assert result.returncode == 0, result.stdout
    assert result.stdout.startswith("planner check: 0 errors, 0 warnings in ")
    assert findings(result.stdout) == []
    assert elapsed < 1.0, f"check took {elapsed:.2f} s"


def test_render_changes_no_bytes(ub):
    before = snapshot(ub)
    code, out = run("render", "--vault", str(ub))
    assert code == 0 and "0 blocks changed" in out, out
    assert snapshot(ub) == before
    run("render", "--vault", str(ub))
    assert snapshot(ub) == before


def test_no_jira_anywhere():
    roots = [REPO / "examples" / "unified-booking", REPO / "template", REPO / "plugin" / "skills"]
    hits = [f"{p}" for root in roots for p in root.rglob("*") if p.is_file()
            and re.search(r"jira|\bHB-\d", p.read_text(encoding="utf-8", errors="ignore"), re.I)]
    assert hits == []


def test_conventions_copy_matches_the_template():
    assert (FIXTURE / "CONVENTIONS.md").read_bytes() == (REPO / "template" / "CONVENTIONS.md").read_bytes()


def test_where_it_stands_lists_unk_006_and_holds_no_prose():
    text = (FIXTURE / "01-goals.md").read_text(encoding="utf-8")
    block = text[text.index("<!-- generated:where-it-stands"):text.index("<!-- /generated:where-it-stands -->")]
    lines = block.splitlines()[1:]
    assert "| [[11-unknowns-and-risks#UNK-006 Finance on Booking events\\|UNK-006]] | @hl-platform-lead (Platform lead) | 2027-03-01 | nothing |" in lines
    for line in lines:
        assert line == "" or line.startswith("|") or re.match(r"^\*\*[A-Za-z ]+(:\*\* .+|\*\*)$", line), line


# One broken copy per rule. Spec 13's four floor cases come first.

def test_missing_anchor(ub):
    edit(ub / "03-context-and-scope.md", "#UNK-006 Finance on Booking events|", "#UNK-006 Finance|")
    assert broken(ub) == [("E202", "03-context-and-scope.md")]


def test_unknown_with_no_owner(ub):
    edit(ub / "11-unknowns-and-risks.md", "- **Owner:** @hl-platform-lead (Platform lead)\n- **Opened:** 2026-10-07 Grill\n",
         "- **Opened:** 2026-10-07 Grill\n")
    assert broken(ub) == [("E302", "11-unknowns-and-risks.md")]


def test_oversized_diagram(ub):
    extra = "".join(f"  X{i}[Extra {i}] --> B\n" for i in range(10))
    edit(ub / "03-context-and-scope.md", "  EB -.-> N[Notifications]\n", "  EB -.-> N[Notifications]\n" + extra)
    assert broken(ub) == [("E601", "03-context-and-scope.md")]


def test_gate_four_cap_021_decided_while_unk_001_blocks_it(ub):
    edit(ub / "11-unknowns-and-risks.md",
         "- **State:** resolved\n- **Blocks:** [[FLO-001-hold-pay-confirm|FLO-001]] design, "
         "[[ADR-0002-ferrymaster-ledger-of-record|ADR-0002]], [[EPC-031-holds-and-confirms|EPC-031]]\n",
         "- **State:** open\n- **Ask by:** 2026-12-01\n- **Blocks:** [[CAP-021-amend-or-cancel|CAP-021]]\n")
    assert broken(ub) == [("E316", "capabilities/CAP-021-amend-or-cancel.md")]


def test_requirements_session_as_decider(ub):
    (ub / "sessions" / "2026-11-10-amend-requirements.md").write_text(
        "---\nid: 2026-11-10-amend-requirements\ntype: session\ndate: 2026-11-10\nmodes: [requirements]\n"
        "status: closed\nsummary: Wrote amend and cancel requirements as assumptions.\n---\n\n# Requirements: amend\n",
        encoding="utf-8")
    edit(ub / "capabilities" / "CAP-021-amend-or-cancel.md", "- **Decision:** [[2026-08-12-goals-and-data]]",
         "- **Decision:** [[2026-11-10-amend-requirements]]")
    assert broken(ub) == [("E317", "capabilities/CAP-021-amend-or-cancel.md")]


def test_decided_with_no_grill_link(ub):
    edit(ub / "capabilities" / "CAP-021-amend-or-cancel.md", "- **Decision:** [[2026-08-12-goals-and-data]]\n\n", "")
    assert broken(ub) == [("E303", "capabilities/CAP-021-amend-or-cancel.md")]


def test_fact_with_no_source(ub):
    edit(ub / "05-building-blocks" / "vessel-schedule-building-blocks.md", "- **Source:** SRC-06\n", "")
    assert broken(ub) == [("E304", "05-building-blocks/vessel-schedule-building-blocks.md")]


def test_missing_concern_cell(ub):
    edit(ub / "08-concerns" / "concern-security.md",
         "| [[website-building-blocks\\|Website]] | addressed | Calls Booking with a service token. Tidepay hosted page as today. |\n", "")
    assert broken(ub) == [("E315", "08-concerns/concern-security.md")]
    matrix = (ub / "08-concerns" / "08-concerns.md").read_text(encoding="utf-8")
    row = next(l for l in matrix.splitlines() if l.startswith("| [[website-building-blocks"))
    assert "unexamined (no row)" in row


def test_contract_with_no_tested_by(ub):
    edit(ub / "05-building-blocks" / "booking-building-blocks.md",
         "- **Tested by:** each channel runs consumer-driven contract tests in its own pipeline.", "- **Notes:** each channel runs consumer-driven contract tests in its own pipeline.")
    assert broken(ub) == [("E318", "05-building-blocks/booking-building-blocks.md")]


def test_hand_edit_inside_a_generated_block(ub):
    edit(ub / "11-unknowns-and-risks.md", "| Event bus readiness |", "| Event bus ready |")
    assert findings(check(ub, TODAY)[1]) == [("E401", "11-unknowns-and-risks.md")]


def test_source_change_makes_a_block_stale(ub):
    edit(ub / "11-unknowns-and-risks.md", "- **Ask by:** 2027-03-01", "- **Ask by:** 2027-04-01")
    assert sorted(findings(check(ub, TODAY)[1])) == [("W402", "01-goals.md"), ("W402", "11-unknowns-and-risks.md")]


def test_overdue_unknown_is_a_warning_on_a_later_date():
    code, out = check(FIXTURE, today="2027-03-02")
    assert code == 0
    assert findings(out) == [("W705", "11-unknowns-and-risks.md")]


# Stage 6: the fixture is clean under --gate epics, and each trace rule is caught by one broken copy.

def gated(vault):
    return run("check", "--vault", str(vault), "--today", TODAY, "--gate", "epics")


def test_fixture_is_clean_under_the_epics_gate():
    code, out = gated(FIXTURE)
    assert code == 0, out
    assert findings(out) == []


def test_t1_capability_delta_row_with_no_epic(ub):
    edit(ub / "13-epics" / "EPC-031-holds-and-confirms.md", "delivers: [CAP-013, CAP-014, CON-001", "delivers: [CAP-013, CON-001")
    assert broken(ub) == [("W501", "capabilities/CAP-014-hold-a-seat.md")]
    assert findings(gated(ub)[1]) == [("E501", "capabilities/CAP-014-hold-a-seat.md")]


def test_t2_changed_contract_with_no_epic(ub):
    edit(ub / "13-epics" / "EPC-038-pricing-serves-booking.md", "delivers: [CAP-012, CON-003]", "delivers: [CAP-012]")
    assert broken(ub) == [("W502", "05-building-blocks/pricing-building-blocks.md")]
    assert findings(gated(ub)[1]) == [("E502", "05-building-blocks/pricing-building-blocks.md")]


def test_t4_concern_cell_with_work_and_no_epic(ub):
    edit(ub / "13-epics" / "EPC-033-website-to-booking.md", "call. [security] [observability]", "call. [security]")
    assert broken(ub) == [("W503", "08-concerns/concern-observability.md")]
    assert findings(gated(ub)[1]) == [("E503", "08-concerns/concern-observability.md")]


def test_t4_reads_waivers(ub):
    edit(ub / "08-concerns" / "concern-cost.md", "no work (@hl-solution-lead, review 2027-03-01): standard", "no work: standard")
    assert broken(ub) == [("W503", "08-concerns/concern-cost.md")]


def test_t6_epic_tracing_to_nothing(ub):
    edit(ub / "13-epics" / "EPC-039-run-booking.md", "delivers: [G2]", "delivers: []")
    assert broken(ub) == [("W504", "13-epics/EPC-039-run-booking.md")]
    assert findings(gated(ub)[1]) == [("E504", "13-epics/EPC-039-run-booking.md")]
