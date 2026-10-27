"""Ticket copy in the build plan: the Summary line and the Ticket criteria block a session writes, read by the one
reader (breakdown.py), checked by ticketcopy.py against the plan's own criteria, and copied into each ticket with what
the story relies on from the vault (ticketrefs.py).

    python3 -m pytest -p no:cacheprovider tests/test_ticket_copy.py -q
"""
from conftest import REPO
from vela import breakdown

FIXTURES = REPO / "tests" / "fixtures" / "team-skills"
VAULT = FIXTURES / "heron-plan"
PLAN = VAULT / "docs" / "plan" / "desktop-agent-breakdown.md"

MINI = """---
status: complete
---

## Summary
| Story | Traces to | Size total | Blocked by |
|---|---|---|---|
| S-01 Go | CON-001 | 1 S | none |

## Stories

### S-01 Go
Summary: It goes. It stops.
Traces to: CON-001
Acceptance criteria:
- It goes.
- It stops.
Ticket criteria (from STAMP):
Moving:
- It goes, and then it
  stops. (covers AC1, AC2)

Stopping:
- It stops. (covers AC2)

| Task | Size | Component |
|---|---|---|
| Build it | S | Core |

Blocked by: none

## Build order
1. S-01: first
"""


def plan_text():
    return PLAN.read_text(encoding="utf-8")


def stories(text=None):
    return {s.id: s for s in breakdown.read(text or plan_text())["stories"]}


def mini(stamp=None):
    return MINI.replace("STAMP", stamp or breakdown.criteria_stamp(["It goes.", "It stops."]))


# ---- the reader

def test_the_reader_keeps_the_summary_and_the_ticket_criteria_apart_from_the_plans_criteria():
    s = stories()["S-02"]
    assert s.summary.startswith("When a person turns Heron on, the Desktop agent asks them two separate questions")
    assert len(s.criteria) == 6 and not any("covers" in c for c in s.criteria)
    assert s.ticket_label and s.ticket_stamp == "7d05f2" == breakdown.criteria_stamp(s.criteria)
    assert [h for h, _ in s.ticket_groups] == ["Choosing what Heron reads", "Recording the choice", "When it doesn't go through"]
    assert [len(lines) for _, lines in s.ticket_groups] == [1, 2, 2]
    assert s.ticket_groups[1][1][1] == "A choice counts only once Consent and identity confirms it. (covers AC3, AC6)"


def test_the_plan_with_ticket_copy_reads_with_nothing_unmapped():
    assert breakdown.read(plan_text())["problems"] == []


def test_a_story_without_ticket_copy_reads_as_before():
    s = stories()["S-03"]
    assert (s.summary, s.ticket_stamp, s.ticket_groups, s.ticket_label) == (None, None, [], False)
    assert len(s.criteria) == 4


def test_a_wrapped_ticket_line_and_a_blank_line_between_groups():
    plan = breakdown.read(mini())
    s = plan["stories"][0]
    assert plan["problems"] == []
    assert s.summary == "It goes. It stops." and s.criteria == ["It goes.", "It stops."] and len(s.tasks) == 1
    assert s.ticket_groups == [["Moving", ["It goes, and then it stops. (covers AC1, AC2)"]], ["Stopping", ["It stops. (covers AC2)"]]]


def test_the_stamp_changes_with_the_words_and_not_with_the_wrapping():
    assert breakdown.criteria_stamp(["It goes.", "It stops."]) == breakdown.criteria_stamp(["It  goes.", "It\nstops."])
    assert breakdown.criteria_stamp(["It goes.", "It stops."]) != breakdown.criteria_stamp(["It goes.", "It halts."])
    assert breakdown.criteria_stamp(["It goes.", "It stops."]) != breakdown.criteria_stamp(["It stops.", "It goes."])
