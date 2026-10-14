from vela.parse import parse_page, split_row

PAGE = """---
id: APP-shop
type: app-building-blocks
title: Shop
---

# Shop

- **Decision:** [[2026-01-10-shop-api]]

Text with a [[till-building-blocks|Till]] link and `[[not-a-link]]` in code.

### CON-001 Sale API

- **Consumers:** [[till-building-blocks|Till]], [[other-building-blocks#CON-009 X|CON-009]]
- **State:** decided

## Table

| App | State | Why |
|---|---|---|
| [[till-building-blocks\\|Till]] | addressed | a \\| b |

```mermaid
flowchart LR
  a --> b
```

```python
- **State:** not a bullet
[[not-a-link-either]]
```

A capture line ^c01

<!-- generated:contracts-consumed sha=00000000: do not edit, run planner render -->
| Contract | State |
|---|---|
| x | y |
<!-- /generated:contracts-consumed -->
"""


def test_frontmatter_is_read_and_dates_become_text():
    page = parse_page("a/b.md", "---\nid: x\ndate: 2026-01-10\n---\n# X\n")
    assert page.name == "b"
    assert page.meta == {"id": "x", "date": "2026-01-10"}
    assert page.errors == []


def test_missing_frontmatter_is_e101():
    page = parse_page("x.md", "# No frontmatter\n")
    assert [e.code for e in page.errors] == ["E101"]
    assert page.meta == {}


def test_bad_yaml_is_e102_and_body_still_parses():
    page = parse_page("x.md", "---\ntitle: a: b\n---\n# Heading\n[[link]]\n")
    assert [e.code for e in page.errors] == ["E102"]
    assert [h.text for h in page.headings] == ["Heading"]
    assert [l.target for l in page.links] == ["link"]


def test_links_skip_code_and_unescape_table_pipes():
    page = parse_page("05/shop-building-blocks.md", PAGE)
    targets = [(l.target, l.anchor, l.label) for l in page.links]
    assert ("till-building-blocks", "", "Till") in targets
    assert ("other-building-blocks", "CON-009 X", "CON-009") in targets
    assert all(t[0] not in ("not-a-link", "not-a-link-either") for t in targets)


def test_bullets_carry_their_item_section():
    page = parse_page("05/shop-building-blocks.md", PAGE)
    by_label = {(b.label, b.item): b for b in page.bullets}
    assert ("Decision", "") in by_label
    assert by_label[("State", "CON-001")].value == "decided"
    assert len(by_label[("Consumers", "CON-001")].links) == 2
    assert ("State", "") not in by_label  # the one in the python fence is ignored


def test_tables_split_on_unescaped_pipes_only():
    page = parse_page("05/shop-building-blocks.md", PAGE)
    authored = [t for t in page.tables if not t.generated]
    assert authored[0].header == ("App", "State", "Why")
    assert authored[0].rows == (("[[till-building-blocks|Till]]", "addressed", "a | b"),)
    assert split_row("| a | b \\| c |") == ("a", "b | c")


def test_mermaid_fence_becomes_a_diagram():
    page = parse_page("05/shop-building-blocks.md", PAGE)
    assert [(d.kind, d.lines) for d in page.diagrams] == [("flowchart", ("flowchart LR", "  a --> b"))]


def test_generated_block_is_captured_and_its_table_marked_generated():
    page = parse_page("05/shop-building-blocks.md", PAGE)
    [block] = page.blocks
    assert (block.name, block.sha) == ("contracts-consumed", "00000000")
    assert block.content == "| Contract | State |\n|---|---|\n| x | y |"
    assert [t.generated for t in page.tables] == [False, True]


def test_block_ids_are_collected():
    page = parse_page("05/shop-building-blocks.md", PAGE)
    assert page.block_ids == {"c01"}


def test_old_style_marker_is_e404():
    page = parse_page("x.md", "---\nid: x\n---\n<!-- generated: do not edit -->\n| a |\n<!-- /generated -->\n")
    assert [e.code for e in page.errors] == ["E404", "E404"]


def test_unclosed_block_is_e404():
    text = "---\nid: x\n---\n<!-- generated:concern-matrix sha=00000000: do not edit, run planner render -->\nrow\n"
    page = parse_page("x.md", text)
    assert [e.code for e in page.errors] == ["E404"]
    assert page.blocks == []


def test_byte_order_mark_and_crlf_are_tolerated():
    page = parse_page("x.md", "﻿---\r\nid: x\r\ntype: index\r\n---\r\n# X\r\n[[y]]\r\n")
    assert page.errors == []
    assert page.meta == {"id": "x", "type": "index"}
    assert [(l.target, l.line) for l in page.links] == [("y", 6)]


def test_labels_match_in_any_case():
    page = parse_page("x.md", "---\nid: x\n---\n### CON-001 A\n\n- **Tested By:** both sides\n")
    assert [b.label for b in page.bullets] == ["Tested by"]
