"""Trace rules T1, T2, T4 and T6 and the epics gate, on the mini vault plus one epic."""
from conftest import check, edit, findings, run
from planner import parse, trace

EPIC = "13-epics/EPC-001-sell-at-the-till.md"
EPIC_TEXT = """---
id: EPC-001
type: epic
title: Sell at the till
initiative: INI-900
state: draft
owner: "@mini/shop-team"
authored: authored
apps: [APP-shop]
delivers: [CON-001, G1]
---

# EPC-001 Sell at the till

## Acceptance criteria

1. A basket sent on CON-001 returns a receipt with the till's sale number. [testing]
2. A sale that fails leaves the stock level as it was.
"""
SHOP = "05-building-blocks/shop-building-blocks.md"
TESTING = "08-concerns/concern-testing.md"


def gated(vault, today="2026-01-15"):
    return run("check", "--vault", str(vault), "--today", today, "--gate", "epics")


def add_epic(vault, text=EPIC_TEXT):
    """Write the epic, then render, as a session close would, so where-it-stands is current."""
    (vault / "13-epics").mkdir(exist_ok=True)
    (vault / EPIC).write_text(text, encoding="utf-8")
    code, out = run("render", "--vault", str(vault))
    assert code == 0, out


def test_no_epic_means_no_trace_warnings(mini):
    code, out = check(mini)
    assert code == 0 and findings(out) == []


def test_gate_turns_gaps_into_errors_even_with_no_epic(mini):
    code, out = gated(mini)
    assert code == 1
    assert findings(out) == [("E502", SHOP), ("E503", TESTING)]
    assert out.splitlines()[0].endswith("Gate: epics.")


def test_an_epic_that_covers_everything_is_clean_under_the_gate(mini):
    add_epic(mini)
    assert findings(check(mini)[1]) == []
    code, out = gated(mini)
    assert code == 0, out


def test_t2_new_contract_with_no_provider_epic(mini):
    add_epic(mini, EPIC_TEXT.replace("delivers: [CON-001, G1]", "delivers: [G1]"))
    code, out = check(mini)
    assert code == 0
    assert findings(out) == [("W502", SHOP)]
    assert "T2: CON-001 is new, but no epic delivers its provider side." in out
    assert findings(gated(mini)[1]) == [("E502", SHOP)]


def test_t4_cell_with_work_and_no_marker(mini):
    add_epic(mini, EPIC_TEXT.replace(" [testing]", ""))
    assert findings(check(mini)[1]) == [("W503", TESTING)]


def test_t4_marker_on_an_epic_for_another_app_does_not_cover(mini):
    add_epic(mini, EPIC_TEXT.replace("apps: [APP-shop]", "apps: [APP-till]"))
    assert findings(check(mini)[1]) == [("W503", TESTING)]


def test_t4_struck_criterion_covers_nothing(mini):
    add_epic(mini, EPIC_TEXT.replace("1. A basket", "1. ~~A basket").replace("number. [testing]", "number.~~ [testing]"))
    assert findings(check(mini)[1]) == [("W503", TESTING)]


def test_t4_waiver_covers_and_a_malformed_waiver_does_not(mini):
    add_epic(mini, EPIC_TEXT.replace(" [testing]", ""))
    edit(mini / TESTING, "| addressed | Provider tests for CON-001 |",
         "| addressed | no work (@mini-qa, review 2026-06-01): the till team's tests cover it |")
    run("render", "--vault", str(mini))
    assert findings(check(mini)[1]) == []
    edit(mini / TESTING, "no work (@mini-qa, review 2026-06-01):", "no work:")
    run("render", "--vault", str(mini))
    code, out = check(mini)
    assert findings(out) == [("W503", TESTING)]
    assert "reads like a waiver, but not in the waiver form" in out


def test_t6_epic_that_delivers_nothing(mini):
    add_epic(mini, EPIC_TEXT.replace("delivers: [CON-001, G1]", "delivers: []"))
    assert sorted(findings(check(mini)[1])) == [("W502", SHOP), ("W504", EPIC)]


def test_unknown_gate_is_a_tool_failure(mini):
    code, _ = run("check", "--vault", str(mini), "--gate", "release")
    assert code == 2


def test_markers_ignore_wikilinks_fences_blocks_and_bullets():
    page = parse.parse_page("13-epics/EPC-002-x.md", "\n".join([
        "---", "id: EPC-002", "type: epic", "---",
        "## Epic acceptance criteria",
        "1. Calls CON-001. [security] [data]",
        "2. Reaches [[concern-testing]]",
        "3. Ends with a link [[01-goals|G1]]",
        "```", "4. In a fence. [cost]", "```",
        "<!-- generated:traces-to sha=00000000: do not edit, run planner render -->",
        "5. In a block. [rollout]",
        "<!-- /generated:traces-to -->",
        "- Not numbered. [operations]",
    ]))
    assert trace.ac_markers(page) == {"security", "data"}


def test_markers_count_only_under_the_acceptance_criteria_heading():
    page = parse.parse_page("13-epics/EPC-002-x.md", "\n".join([
        "---", "id: EPC-002", "type: epic", "---",
        "## Epic acceptance criteria",
        "1. Calls CON-001. [security]",
        "### Detail",
        "2. Still in the section. [data]",
        "## Out of scope",
        "1. Not this release. [testing]",
    ]))
    assert trace.ac_markers(page) == {"security", "data"}


# Review Focus: the ways people actually type markers and waivers.

def test_marker_case_and_a_trailing_full_stop_do_not_matter(mini):
    add_epic(mini, EPIC_TEXT.replace("number. [testing]", "number [Testing]."))
    assert findings(check(mini)[1]) == []


def test_bulleted_criteria_carry_no_markers_and_the_fix_says_numbered(mini):
    add_epic(mini, EPIC_TEXT.replace("1. A basket", "- A basket"))
    code, out = check(mini)
    assert findings(out) == [("W503", TESTING)]
    assert "End the numbered acceptance criterion" in out


def test_markers_are_read_from_a_crlf_epic(mini):
    add_epic(mini)
    path = mini / EPIC
    path.write_bytes(path.read_bytes().replace(b"\n", b"\r\n"))
    assert findings(check(mini)[1]) == []


def test_waiver_by_a_team_handle_covers(mini):
    add_epic(mini, EPIC_TEXT.replace(" [testing]", ""))
    edit(mini / TESTING, "| addressed | Provider tests for CON-001 |",
         "| addressed | no work (@mini/qa-team @mini-qa, review 2026-06-01): covered by the till's tests |")
    run("render", "--vault", str(mini))
    assert findings(check(mini)[1]) == []
