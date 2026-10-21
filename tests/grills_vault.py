"""A small vault with one grill in each group, for the tests of the Grills waiting list, its owner command and the page.

On top of the mini shop: CON-010 is ready, CON-011 waits on one open question, CON-012 is two things away (no options,
no case table), CON-013 is an item the lead said yes to in a shape session. EPC-001 waits on the shop's contracts.
"""
import shutil

from conftest import MINI, edit

TODAY = "2026-01-15"
TABLE = """
| Case | When | Status | Answer | Emits | Sets |
|---|---|---|---|---|---|
| done | | 200 | it worked | | |
| refused | | 422 | the request is refused | | |
"""


def contract(ident, name, options=True, table=True):
    lines = [f"### {ident} {name}", "", f"- **Crosses the boundary:** {name.lower()} in; an answer out.",
             "- **Consumers:** [[till-building-blocks|Till]]", "- **Change policy:** versioned.", "- **Change:** new",
             "- **Tested by:** consumer tests in the till pipeline.", "- **State:** assumption"]
    if options:
        lines.append(f"- **Options considered:** Keep it in the shop (picked); {name.lower()} in the till: rejected, the shop has the data.")
    return "\n".join(lines) + "\n" + (TABLE if table else "") + "\n"


SESSION = """---
id: 2026-01-12-shape-extras
type: session
date: 2026-01-12
title: "Shape: the shop's extras"
modes: [shape]
status: closed
summary: Shaped the shop's extras.
---

# 2026-01-12 Shape: the shop's extras

## Ready to decide

- CON-013: the lead said yes in 2026-01-12-shape-extras (^c01)

## Captures

- [decision] (@mini-lead) Yes, loyalty points stay in the shop. → keep: [[shop-building-blocks#CON-013 Loyalty points|CON-013]] (assumption) ^c01

## Changes

| ID | From | To | Source |
|---|---|---|---|
| CON-013 | inkling | assumption | [[2026-01-12-shape-extras#^c01]] |
"""

EPIC = """---
id: EPC-001
type: epic
title: Sell with loyalty points
state: draft
owner: "@mini-lead"
authored: mixed
apps: [APP-shop]
delivers: []
consumes: []
---

# EPC-001 Sell with loyalty points

Points are added when a sale goes through.
"""


def make(tmp_path):
    root = tmp_path / "grills"
    shutil.copytree(MINI, root)
    shop = root / "05-building-blocks" / "shop-building-blocks.md"
    extra = (contract("CON-010", "Receipt delivery") + contract("CON-011", "Refund window")
             + contract("CON-012", "Gift cards", options=False, table=False) + contract("CON-013", "Loyalty points"))
    edit(shop, "## Contracts this app consumes", extra + "## Contracts this app consumes")
    edit(root / "11-unknowns-and-risks.md", "- **Question:** Is there a test till we can use?\n",
         "- **Question:** Is there a test till we can use?\n- **Blocks:** [[shop-building-blocks#CON-011 Refund window|CON-011]]\n")
    (root / "sessions" / "2026-01-12-shape-extras.md").write_text(SESSION, encoding="utf-8")
    (root / "13-epics").mkdir()
    (root / "13-epics" / "EPC-001-loyalty.md").write_text(EPIC, encoding="utf-8")
    return root
