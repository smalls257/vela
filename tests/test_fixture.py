"""The migrated reference fixture: clean, render-stable, Jira-free, and each
check rule caught by one broken copy.

Broken copies are made in tmp_path. After the edit the test runs render, as a
session close would, so the stale-block echo of a source change is gone and
the finding under test is the only one left.
"""
import re
import resource
import shutil
import subprocess
import sys

import pytest

from conftest import OPEN_IN_THE_EXAMPLE, REPO, check, edit, findings, run
import session_files

FIXTURE = REPO / "examples" / "unified-booking"
TODAY = "2026-11-20"
CHECK_CPU_BUDGET_S = 2.0


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
    cpu_before = resource.getrusage(resource.RUSAGE_CHILDREN)
    result = subprocess.run([sys.executable, str(REPO / "plugin" / "scripts" / "vela"), "check",
                             "--vault", str(FIXTURE), "--today", TODAY], capture_output=True, text=True, timeout=120)
    cpu_after = resource.getrusage(resource.RUSAGE_CHILDREN)
    cpu = (cpu_after.ru_utime + cpu_after.ru_stime) - (cpu_before.ru_utime + cpu_before.ru_stime)
    assert result.returncode == 0, result.stdout
    assert result.stdout.startswith("vela check: 0 errors, ")
    assert findings(result.stdout) == []
    # what the example leaves open on purpose is its decided items' Why, which it carries for none (conftest.OPEN_IN_THE_EXAMPLE)
    assert all(code in OPEN_IN_THE_EXAMPLE for code, _ in findings(result.stdout, keep_open=True))
    # CPU seconds the check process itself burned, not wall clock: a loaded machine stretches the wall (2.2 s at load 95)
    # but not the work. The check takes about 0.45 s of CPU on 3.12 and 0.66 s on 3.9; 2.0 s still trips on a 3x regression.
    assert cpu < CHECK_CPU_BUDGET_S, f"check burned {cpu:.2f} s of CPU (budget {CHECK_CPU_BUDGET_S} s)"


def test_render_changes_no_bytes(ub):
    before = snapshot(ub)
    code, out = run("render", "--vault", str(ub))
    assert code == 0 and "0 blocks changed" in out, out
    assert snapshot(ub) == before
    run("render", "--vault", str(ub))
    assert snapshot(ub) == before


def test_no_jira_anywhere():
    roots = [REPO / "examples" / "unified-booking", REPO / "plugin" / "template", REPO / "plugin" / "skills"]
    # The tickets skill names Jira on purpose: it offers a Jira CSV and asks whether the person's own Jira tools may be used.
    hits = [f"{p}" for root in roots for p in root.rglob("*") if p.is_file() and p.parent.name != "tickets"
            and re.search(r"jira|\bHB-\d", p.read_text(encoding="utf-8", errors="ignore"), re.I)]
    assert hits == []


def test_conventions_copy_matches_the_template():
    assert (FIXTURE / "CONVENTIONS.md").read_bytes() == (REPO / "plugin" / "template" / "CONVENTIONS.md").read_bytes()


def test_where_it_stands_lists_unk_006_and_holds_no_prose():
    text = (FIXTURE / "01-goals.md").read_text(encoding="utf-8")
    block = text[text.index("<!-- generated:where-it-stands"):text.index("<!-- /generated:where-it-stands -->")]
    lines = block.splitlines()[1:]
    assert lines[0] == "_Kept up to date by vela from the pages it reads._"  # the one line saying the tool keeps it
    lines = lines[1:]
    assert "| [[11-unknowns-and-risks#UNK-006 Finance on Booking events\\|Finance on Booking events (UNK-006)]] | @hl-platform-lead (Platform lead) | 2027-03-01 | nothing yet |" in lines
    for line in lines:
        assert line == "" or line.startswith("|") or re.match(r"^\*\*[A-Za-z ]+(:\*\* .+|\*\*)$", line), line


# One broken copy per rule. Spec 13's four floor cases come first.

def test_missing_anchor(ub):
    edit(ub / "03-context-and-scope.md", "#UNK-006 Finance on Booking events|", "#UNK-006 Finance|")
    assert broken(ub) == [("E202", "03-context-and-scope.md")]


def test_unknown_with_no_owner(ub):
    edit(ub / "11-unknowns-and-risks.md", "- **Owner:** @hl-platform-lead (Platform lead)\n- **Opened:** 2026-10-07 Grill\n",
         "- **Opened:** 2026-10-07 Grill\n")
    # The two ledger rows that rest on UNK-006 lose their owner with it, so each says so (E802).
    assert broken(ub) == [("E302", "11-unknowns-and-risks.md"), ("E802", "11-unknowns-and-risks.md"),
                          ("E802", "11-unknowns-and-risks.md")]


def test_oversized_diagram(ub):
    extra = "".join(f"  X{i}[Extra {i}] --> Web\n" for i in range(15))
    edit(ub / "03-context-and-scope.md", "  K -- pay --> T\n", "  K -- pay --> T\n" + extra)
    assert broken(ub) == [("E601", "03-context-and-scope.md")]


def fixture_pages():
    return {p.relative_to(FIXTURE).as_posix(): p.read_text(encoding="utf-8") for p in FIXTURE.rglob("*.md")}


def generated_blocks(text):
    return re.findall(r"<!-- generated:([a-z-]+) sha=", text)


def hand_fences(text):
    """Mermaid fences outside generated blocks."""
    outside = re.sub(r"<!-- generated:([a-z-]+) sha=.*?<!-- /generated:\1 -->", "", text, flags=re.S)
    return outside.count("```mermaid")


def test_generated_diagrams_replace_the_hand_drawn_ones():
    pages = fixture_pages()
    assert "context-map" in generated_blocks(pages["05-building-blocks/05-building-blocks.md"])
    assert hand_fences(pages["05-building-blocks/05-building-blocks.md"]) == 0
    assert "system-context" in generated_blocks(pages["03-context-and-scope.md"])
    assert hand_fences(pages["03-context-and-scope.md"]) == 1  # Today has no generator, so it stays
    apps = [path for path, text in pages.items() if "\ntype: app-building-blocks\n" in text]
    assert len(apps) == 9
    for path in apps:
        assert "app-context" in generated_blocks(pages[path]), path
        slim = "\nchange: integrated\n" in pages[path] or "\nchange: unchanged\n" in pages[path]
        assert hand_fences(pages[path]) == (0 if slim else 1), path  # only the containers diagram is hand-drawn


def test_gate_four_cap_021_decided_while_unk_001_blocks_it(ub):
    edit(ub / "11-unknowns-and-risks.md",
         "- **State:** resolved\n- **Blocks:** [[FLO-001-hold-pay-confirm|FLO-001]] design, "
         "[[ADR-0002-ferrymaster-ledger-of-record|ADR-0002]], [[EPC-031-holds-and-confirms|EPC-031]]\n",
         "- **State:** open\n- **Ask by:** 2026-12-01\n- **Blocks:** [[CAP-021-amend-or-cancel|CAP-021]]\n")
    assert broken(ub) == [("E316", "capabilities/CAP-021-amend-or-cancel.md")]


def test_requirements_session_as_decider(ub):
    session_files.write_record(ub, "2026-11-10-amend-requirements",
        "---\nid: 2026-11-10-amend-requirements\ntype: session\ndate: 2026-11-10\nmodes: [requirements]\n"
        "status: closed\nsummary: Wrote amend and cancel requirements as assumptions.\n---\n\n# Requirements: amend\n")
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
    assert broken(ub) == []
    matrix = (ub / "08-concerns" / "08-concerns.md").read_text(encoding="utf-8")
    row = next(l for l in matrix.splitlines() if l.startswith("| [[website-building-blocks"))
    assert "not reviewed yet (no line for this app)" in row


def test_contract_with_no_tested_by(ub):
    edit(ub / "05-building-blocks" / "booking-building-blocks.md",
         "- **Tested by:** each channel runs consumer-driven contract tests in its own pipeline.", "- **Notes:** each channel runs consumer-driven contract tests in its own pipeline.")
    assert broken(ub) == [("E318", "05-building-blocks/booking-building-blocks.md")]


def test_hand_edit_inside_a_generated_block(ub):
    edit(ub / "11-unknowns-and-risks.md", "|Event bus readiness (UNK-005)]]", "|Event bus ready (UNK-005)]]")
    assert findings(check(ub, TODAY)[1]) == [("E401", "11-unknowns-and-risks.md")]


def test_source_change_makes_a_block_stale(ub):
    edit(ub / "11-unknowns-and-risks.md", "- **Ask by:** 2027-03-01", "- **Ask by:** 2027-04-01")
    assert sorted(findings(check(ub, TODAY)[1])) == [("W402", "01-goals.md"), ("W402", "11-unknowns-and-risks.md")]


def test_overdue_unknown_is_a_warning_on_a_later_date():
    code, out = check(FIXTURE, today="2027-03-02")
    assert code == 0
    found = findings(out)
    assert ("W705", "11-unknowns-and-risks.md") in found
    # Months later the sources and the last session are stale too. All of it stays a warning.
    assert {c for c, _ in found} == {"W705", "W711", "W716"}


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
    edit(ub / "13-epics" / "EPC-033-website-to-booking.md", "AC1  ·  [security] [observability]", "AC1  ·  [security]")
    assert broken(ub) == [("W503", "08-concerns/concern-observability.md")]
    assert findings(gated(ub)[1]) == [("E503", "08-concerns/concern-observability.md")]


def test_t4_reads_waivers(ub):
    edit(ub / "08-concerns" / "concern-cost.md", "no work (@hl-solution-lead, review 2027-03-01): standard", "no work: standard")
    assert broken(ub) == [("W503", "08-concerns/concern-cost.md")]


def test_t6_epic_tracing_to_nothing(ub):
    edit(ub / "13-epics" / "EPC-039-run-booking.md", "delivers: [G2]", "delivers: []")
    assert broken(ub) == [("W504", "13-epics/EPC-039-run-booking.md")]
    assert findings(gated(ub)[1]) == [("E504", "13-epics/EPC-039-run-booking.md")]


def test_traceability_block_lists_a_gap_in_full(ub):
    edit(ub / "13-epics" / "EPC-031-holds-and-confirms.md", "delivers: [CAP-013, CAP-014, CON-001", "delivers: [CAP-013, CON-001")
    broken(ub)
    text = (ub / "13-epics" / "13-epics.md").read_text(encoding="utf-8")
    assert "**Gaps in the planned work:** one; the table below lists them." in text
    assert "| [[CAP-014-hold-a-seat\\|Hold a seat during payment (CAP-014)]] | No epic delivers Hold a seat during payment (CAP-014), which this initiative adds, so nobody is planned to build it. |" in text
    goals = (ub / "01-goals.md").read_text(encoding="utf-8")
    assert "**Gaps in the planned work:** one; see [[13-epics|Epics]]" in goals


def test_booking_is_handed_off_on_the_goals_page():
    text = (FIXTURE / "01-goals.md").read_text(encoding="utf-8")
    assert "**Handed to its team:** [[booking-building-blocks|Booking]] (Booking senior, 2026-11-10, PR #23)" in text


def test_no_hand_kept_trace_lists_remain():
    for path in (FIXTURE / "05-building-blocks").glob("*-building-blocks.md"):
        assert "## Concerns this team carries" not in path.read_text(encoding="utf-8"), path.name
    for path in (FIXTURE / "13-epics").glob("EPC-*.md"):
        assert "<!-- generated:traces-to sha=" in path.read_text(encoding="utf-8"), path.name
    for path in (FIXTURE / "capabilities").glob("CAP-*.md"):
        assert "<!-- generated:delivered-by sha=" in path.read_text(encoding="utf-8"), path.name


def test_the_context_map_page_records_each_relationship_by_contract():
    text = fixture_pages()["05-building-blocks/05-building-blocks.md"]
    for words in ("customers of Booking", "customer of Pricing", "conforms to", "anticorruption layer"):
        assert words in text
    outside = re.sub(r"<!-- generated:([a-z-]+) sha=.*?<!-- /generated:\1 -->", "", text, flags=re.S)
    assert all(f"CON-00{n}" in outside for n in range(1, 8))


def test_capabilities_carry_a_domain_and_the_delta_page_draws_them():
    pages = fixture_pages()
    assert "capability-map" in generated_blocks(pages["04a-capability-delta.md"])
    capabilities = [path for path, text in pages.items() if "\ntype: capability\n" in text]
    assert len(capabilities) == 8
    for path in capabilities:
        assert re.search(r"^domain: \S", pages[path], re.M), path


def test_booking_handoff_manifest_matches_the_vault():
    code, out = run("handoff", "verify", "APP-booking", "--vault", str(FIXTURE))
    assert code == 0, out
    assert out.startswith("vela handoff verify APP-booking: since Booking was handed off on 2026-11-20 at example, 0 things changed, 0 added and 0 removed.")
