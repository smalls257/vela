from planner.model import build
from planner.parse import parse_page

SHOP = """---
id: APP-shop
type: app-building-blocks
title: Shop
---
# Shop

### CON-001 Sale API

- **Consumers:** [[till-building-blocks|Till]], [[nowhere-building-blocks|Nowhere]]. Notes after the links.
- **State:** decided
- **State:** fact

## Contracts this app consumes

<!-- generated:contracts-consumed sha=00000000: do not edit, run planner render -->
- **State:** inside a block, ignored
<!-- /generated:contracts-consumed -->
"""
TILL = "---\nid: APP-till\ntype: app-building-blocks\ntitle: Till\n---\n# Till\n"
GOALS = """---
id: goals
type: initiative-section
title: Goals
---
# Goals

| ID | Goal | Measure | State |
|---|---|---|---|
| G1 | Sell | One till | decided |
"""
UNKNOWNS = """---
id: unknowns-and-risks
type: index
title: Unknowns
---
# Unknowns

### UNK-001 Till rig

- **Owner:** @qa
- **Blocks:** [[shop-building-blocks#CON-001 Sale API|CON-001]]

### R-01 One till

- **Owner:** @lead
"""
TESTING = """---
id: concern-testing
type: concern
title: Testing
---
# Testing

| App | State | Why |
|---|---|---|
| [[shop-building-blocks\\|Shop]] | addressed | Provider tests |
| Till | unknown | no link in the App column |
"""


def vault():
    pages = [parse_page("05/shop-building-blocks.md", SHOP), parse_page("05/till-building-blocks.md", TILL),
             parse_page("01-goals.md", GOALS), parse_page("11-unknowns-and-risks.md", UNKNOWNS),
             parse_page("08/concern-testing.md", TESTING)]
    return build(pages, {"initiative": "INI-900", "title": "Mini"}, other_names=["CONVENTIONS"])


def test_items_collect_their_own_bullets_and_first_label_wins():
    v = vault()
    contract = v.item("CON-001")
    assert (contract.kind, contract.name, contract.heading) == ("contract", "Sale API", "CON-001 Sale API")
    assert contract.fact("State") == "decided"
    assert [i.id for i in v.unknowns] == ["UNK-001"] and [i.id for i in v.risks] == ["R-01"]


def test_consumers_are_the_linked_app_pages_that_exist():
    v = vault()
    assert [p.id for p in v.consumers(v.item("CON-001"))] == ["APP-till"]


def test_rows_pages_and_items_are_known_ids():
    v = vault()
    assert {"G1", "CON-001", "UNK-001", "R-01", "APP-shop", "goals"} <= v.known_ids()


def test_cells_come_from_the_app_state_table():
    v = vault()
    cells = [(c.app, c.state, c.text) for c in v.cells]
    assert cells == [("shop-building-blocks", "addressed", "Provider tests"), ("", "unknown", "no link in the App column")]


def test_lookups_ignore_case_and_know_other_files():
    v = vault()
    assert v.page("SHOP-building-blocks").id == "APP-shop"
    assert "conventions" in v.other_names
    assert [a.id for a in v.apps] == ["APP-shop", "APP-till"]
