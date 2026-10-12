"""The stage-6 generated blocks: traces-to, epics-for-app, delivered-by, traceability, and the
where-it-stands additions, on the mini vault plus one epic."""
from conftest import check, edit, findings, run

EPIC = "13-epics/EPC-001-sell-at-the-till.md"
EPIC_TEXT = """---
id: EPC-001
type: epic
title: Sell at the till
initiative: INI-900
state: draft
owner: "@mini/shop-team"
authored: mixed
apps: [APP-shop]
delivers: [CON-001, G1]
---

# EPC-001 Sell at the till

## Acceptance criteria

1. A basket sent to the sale API returns a receipt with the till's sale number. [testing]
   - Trace: CON-001
2. A sale that fails leaves the stock level as it was.

## Traces to

<!-- generated:traces-to sha=00000000: do not edit, run planner render -->
<!-- /generated:traces-to -->
"""
SHOP = "05-building-blocks/shop-building-blocks.md"
NEW_BLOCK = "<!-- generated:{0} sha=00000000: do not edit, run planner render -->\n<!-- /generated:{0} -->\n"


def render(vault):
    code, out = run("render", "--vault", str(vault))
    assert code == 0, out
    return out


def add_epic(vault, text=EPIC_TEXT):
    (vault / "13-epics").mkdir(exist_ok=True)
    (vault / EPIC).write_text(text, encoding="utf-8")
    render(vault)


def test_traces_to_links_every_list_and_the_marked_concerns(mini):
    add_epic(mini)
    text = (mini / EPIC).read_text(encoding="utf-8")
    assert "| Apps | [[shop-building-blocks\\|Shop]] |" in text
    assert "| Delivers | [[shop-building-blocks#CON-001 Sale API\\|CON-001 Sale API]], [[01-goals\\|G1]] |" in text
    assert "| Consumes | none |" in text
    assert "| Concerns | [[concern-testing\\|Testing]] |" in text
    assert findings(check(mini)[1]) == []


def test_traces_to_shows_a_marker_with_no_concern_page(mini):
    add_epic(mini, EPIC_TEXT.replace("[testing]", "[testing] [observabilty]"))
    assert "[observabilty] matches no concern page" in (mini / EPIC).read_text(encoding="utf-8")


def test_epics_for_app(mini):
    add_epic(mini)
    edit(mini / SHOP, "## Contracts this app consumes", "## Epics\n\n" + NEW_BLOCK.format("epics-for-app") + "\n## Contracts this app consumes")
    render(mini)
    text = (mini / SHOP).read_text(encoding="utf-8")
    assert "| [[EPC-001-sell-at-the-till\\|EPC-001 Sell at the till]] | @mini/shop-team | draft |" in text
    assert findings(check(mini)[1]) == []


def test_epics_for_app_with_no_epic_says_none(mini):
    edit(mini / SHOP, "## Contracts this app consumes", "## Epics\n\n" + NEW_BLOCK.format("epics-for-app") + "\n## Contracts this app consumes")
    render(mini)
    assert "<!-- generated:epics-for-app sha=" in (mini / SHOP).read_text(encoding="utf-8")
    assert "\nnone\n<!-- /generated:epics-for-app -->" in (mini / SHOP).read_text(encoding="utf-8")


def test_traceability_block_on_an_index(mini):
    add_epic(mini, EPIC_TEXT.replace(" [testing]", ""))
    (mini / "13-epics" / "13-epics.md").write_text(
        "---\nid: epics\ntype: index\ntitle: Epics\nauthored: mixed\n---\n\n# Epics\n\n" + NEW_BLOCK.format("traceability"), encoding="utf-8")
    render(mini)
    text = (mini / "13-epics" / "13-epics.md").read_text(encoding="utf-8")
    assert "**Traceability:** 1 gap. 2 checks pass." in text
    assert "| T4 | [[concern-testing\\|concern-testing × APP-shop]] |" in text
    goals = (mini / "01-goals.md").read_text(encoding="utf-8")
    assert "**Coverage gaps:** 1, listed on [[13-epics|Epics]]" in goals


def test_traceability_block_with_nothing_to_trace(mini):
    (mini / "13-epics").mkdir()
    (mini / "13-epics" / "13-epics.md").write_text(
        "---\nid: epics\ntype: index\ntitle: Epics\nauthored: mixed\n---\n\n# Epics\n\n" + NEW_BLOCK.format("traceability"), encoding="utf-8")
    edit(mini / "08-concerns/concern-testing.md", "| addressed | Provider tests for CON-001 |", "| unchanged | Provider tests for CON-001 |")
    edit(mini / SHOP, "- **Change:** new", "- **Change:** unchanged")
    render(mini)
    assert "**Traceability:** nothing to trace yet." in (mini / "13-epics" / "13-epics.md").read_text(encoding="utf-8")


def test_where_it_stands_shows_a_handoff_and_skips_a_malformed_one(mini):
    edit(mini / SHOP, "stage: contracts\n", 'stage: contracts\nhanded_off: "Shop senior, 2026-01-12, PR #4"\n')
    render(mini)
    goals = (mini / "01-goals.md").read_text(encoding="utf-8")
    assert "**Handed off:** [[shop-building-blocks|Shop]] (Shop senior, 2026-01-12, PR #4)" in goals
    edit(mini / SHOP, 'handed_off: "Shop senior, 2026-01-12, PR #4"', 'handed_off: "Shop senior"')
    render(mini)
    assert "**Handed off:**" not in (mini / "01-goals.md").read_text(encoding="utf-8")
