"""A small vault with one grill in each group, for the tests of the Grills waiting list, its owner command and the page.

On top of the mini shop: CON-010 is ready, CON-011 waits on one open question, CON-012 is two things away (no options,
no case table), CON-013 is an item the lead said yes to in a shape session. EPC-001 waits on the shop's contracts.
"""
import shutil

from conftest import MINI, edit
import session_files

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
ready: ["CON-013"]
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
    session_files.write_record(root, "2026-01-12-shape-extras", SESSION)
    (root / "13-epics").mkdir()
    (root / "13-epics" / "EPC-001-loyalty.md").write_text(EPIC, encoding="utf-8")
    return root


# ------------------------------------------------------------------ the booking example, with grills waiting
# The example is fully decided, so three of its contracts are taken back to `assumption` with the options Shape weighed:
# CON-001 is ready, CON-002 waits on one open question (UNK-006, due 2027-03-01), and the lead said yes to CON-003 in a
# shape session. Two people run grills (the solution lead and the booking senior), each asked to join the other's.
def booking_grills(tmp_path):
    from conftest import REPO, run
    root = tmp_path / "booking"
    shutil.copytree(REPO / "examples" / "unified-booking", root)
    for page, ident, picked in (("booking", "CON-001", "Keep it as drawn"), ("booking", "CON-002", "Keep it as drawn"), ("pricing", "CON-003", "Quote from the pricing service")):
        path = root / "05-building-blocks" / f"{page}-building-blocks.md"
        text = path.read_text(encoding="utf-8")
        start = text.index(f"### {ident} ")
        at = text.index("- **State:** decided", start)
        options = f"- **State:** assumption\n- **Options considered:** {picked} (picked); split it in two: rejected, two calls double the failure points"
        options += "\n- **Source:** SRC-01" if ident == "CON-001" else ""
        path.write_text(text[:at] + options + text[at + len("- **State:** decided"):], encoding="utf-8")
    edit(root / "11-unknowns-and-risks.md", "- **Ask by:** 2027-03-01\n- **Notes:** Deferred to INI-005.",
         "- **Ask by:** 2027-03-01\n- **Blocks:** [[booking-building-blocks#CON-002 Booking state changed|CON-002]]\n- **Notes:** Deferred to INI-005.")
    edit(root / "13-epics" / "EPC-039-run-booking.md", "state: decided", "state: draft")  # an epic nothing waits on: the batch has a grill that unblocks none
    session_files.write_record(root, "2026-10-20-shape-pricing", BOOKING_SESSION)
    with open(root / ".vela.yaml", "a", encoding="utf-8") as config:
        config.write("roles:\n  hl-solution-lead: lead\n  hl-booking-senior: eng\n")
    for argv in (("CON-001", "--owner", "@hl-solution-lead", "--join", "@hl-booking-senior"), ("CON-002", "--owner", "@hl-solution-lead"),
                 ("CON-003", "--owner", "@hl-booking-senior", "--join", "@hl-solution-lead")):
        code, out = run("grill", "owner", *argv, "--vault", str(root))
        assert code == 0, out
    return root


BOOKING_SESSION = """---
id: 2026-10-20-shape-pricing
type: session
date: 2026-10-20
title: "Shape: how pricing answers"
modes: [shape]
status: closed
summary: Shaped how Booking asks Pricing for a fare.
ready: ["CON-003"]
---

# 2026-10-20 Shape: how pricing answers

## Ready to decide

- CON-003: the lead said yes in 2026-10-20-shape-pricing (^c01)

## Captures

- [decision] (@hl-solution-lead) Yes, Booking quotes from the pricing service and never works out a fare itself. → keep: [[pricing-building-blocks#CON-003 Quote a fare|CON-003]] (assumption) ^c01

## Changes

| ID | From | To | Source |
|---|---|---|---|
| CON-003 | inkling | assumption | [[2026-10-20-shape-pricing#^c01]] |
"""
