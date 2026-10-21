"""The example booking vault with one flow whose steps end in the three ways the dashboard used to get wrong.

FLO-009 holds a plain-text app, an outside actor the plan doesn't know, a recorded pair that names no contract, a step
inside one app, and a step that names two apps and records no pair.
"""
import shutil

from conftest import REPO

TODAY = "2026-10-21"
FLOW = """---
id: FLO-009
type: flow
title: Confirm by text
initiative: INI-002
state: assumption
authored: authored
capabilities: [CAP-022]
---

# FLO-009 Confirm by text

## Steps

1. [[website-building-blocks|Public website]] -> [[booking-building-blocks|Booking]]: asks to hold the seat over [[booking-building-blocks#CON-001 Booking API|Booking API]].
2. Booking -> Notifications: tells Notifications the seat is held.
3. Notifications -> Ferry passenger: sends the confirmation text.
4. Notifications records that the passenger opted in to texts.
5. Booking and Notifications agree on the wording of the text.
"""


def booking_with_flow_ends(root):
    """A copy of the example under `root` with FLO-009 added; returns the vault folder."""
    vault = root / "booking"
    shutil.copytree(REPO / "examples" / "unified-booking", vault)
    (vault / "06-runtime" / "flows" / "FLO-009-confirm-by-text.md").write_text(FLOW, encoding="utf-8")
    return vault
