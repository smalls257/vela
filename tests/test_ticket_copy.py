"""Ticket copy in the build plan: the Summary line and the Ticket criteria block a session writes, read by the one
reader (breakdown.py), checked by ticketcopy.py against the plan's own criteria, and copied into each ticket with what
the story relies on from the vault (ticketrefs.py).

    python3 -m pytest -p no:cacheprovider tests/test_ticket_copy.py -q
"""
from conftest import REPO
from vela import breakdown, ticketcopy

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


def problems_of(text, sid="S-02"):
    return ticketcopy.problems(stories(text)[sid])


def flagged(found):
    return [t for t, flag in found if flag]


# ---- the check

def test_the_heron_story_with_copy_passes_and_one_without_is_flagged_with_its_flat_list():
    assert problems_of(plan_text()) == []
    found = problems_of(plan_text(), "S-03")
    assert len(found) == 1 and found[0][1] is True and "flat list" in found[0][0]
    assert ticketcopy.covered(stories()["S-03"]) == {1, 2, 3, 4}
    assert ticketcopy.covered(stories()["S-02"]) == {1, 2, 3, 4, 5, 6}


def test_a_criterion_no_line_covers_is_flagged_with_its_words():
    text = plan_text().replace("reads nothing. (covers AC5)", "reads nothing.")
    found = flagged(problems_of(text))
    assert any("no covers tag" in t for t in found)
    assert any(t.startswith("AC5 isn't covered") and "For a person who has not switched Heron on" in t for t in found)


def test_a_tag_naming_no_criterion_or_written_wrong_is_flagged():
    text = plan_text().replace("(covers AC5)", "(covers AC5, AC7)").replace("(covers AC3)", "(covers criterion 3)")
    found = flagged(problems_of(text))
    assert any("covers AC7, but the story has 6 acceptance criteria" in t for t in found)
    assert any("'criterion'" in t or "'3'" in t for t in found)


def test_a_changed_criterion_makes_the_copy_stale_and_the_flag_gives_the_new_stamp():
    text = plan_text().replace("Heron records no agreement and reads nothing.", "Heron records nothing and reads nothing.")
    new = breakdown.criteria_stamp(stories(text)["S-02"].criteria)
    found = flagged(problems_of(text))
    assert any("written for earlier acceptance criteria" in t and f"Ticket criteria (from {new}):" in t for t in found)
    unstamped = flagged(problems_of(plan_text().replace("Ticket criteria (from 7d05f2):", "Ticket criteria:")))
    assert any("no stamp" in t and "Ticket criteria (from 7d05f2):" in t for t in unstamped)


def test_ids_in_the_model_written_words_are_flagged_and_a_short_summary_is_a_note():
    text = plan_text().replace("comes after the encrypted store.", "comes after the encrypted store (S-01).")
    assert any("S-01" in t and "summary" in t for t in flagged(problems_of(text)))
    text = plan_text().replace("no meeting text. (covers AC3)", "no meeting text, per CON-004. (covers AC3)")
    assert any("CON-004" in t for t in flagged(problems_of(text)))
    short = plan_text().replace(
        "This is part of the first working path through the agent, the tracer, and it comes after the encrypted store.", "")
    notes = [t for t, flag in problems_of(short) if not flag]
    assert len(notes) == 1 and "3 sentences" in notes[0]


def test_lines_before_any_heading_and_a_heading_with_nothing_under_it_are_flagged():
    text = mini().replace("Moving:\n", "").replace("Stopping:\n- It stops. (covers AC2)", "Stopping:")
    found = flagged(ticketcopy.problems(breakdown.read(text)["stories"][0]))
    assert any("before the first heading" in t for t in found)
    assert any("'Stopping', with no lines under it" in t for t in found)


def test_a_summary_without_grouped_criteria_and_the_reverse_are_each_named():
    no_block = mini().split("Ticket criteria")[0] + "\n| Task | Size | Component |\n|---|---|---|\n| Build it | S | Core |\n\nBlocked by: none\n"
    found = ticketcopy.problems(breakdown.read(no_block)["stories"][0])
    assert any("no 'Ticket criteria' block" in t for t, flag in found if flag)
    no_summary = mini().replace("Summary: It goes. It stops.\n", "")
    found = ticketcopy.problems(breakdown.read(no_summary)["stories"][0])
    assert any("no 'Summary:' line" in t for t, flag in found if flag)


import shutil  # noqa: E402

from vela import cli, ticketrefs  # noqa: E402
from vela.edge import teamdocs  # noqa: E402


def heron():
    return cli.load_vault(VAULT)


def questions():
    return teamdocs.design_questions(VAULT, plan_text())


def test_the_design_questions_are_read_from_the_design_the_plan_names():
    found = questions()
    assert found["OQ-005"]["title"] == "Is the person told when Consent and identity is down, or their sign-in has expired?"
    assert found["OQ-005"]["what_would_unblock"].startswith("The solution lead says whether silence on a Consent outage")


def test_a_plan_whose_design_cannot_be_read_gives_none_not_an_empty_answer(tmp_path):
    root = tmp_path / "v"
    shutil.copytree(VAULT, root)
    (root / "docs" / "tech-design" / "desktop-agent.md").unlink()
    assert teamdocs.design_questions(root, plan_text()) is None


def test_each_contract_is_written_out_from_the_vault():
    refs = ticketrefs.relies_on(heron(), stories()["S-02"], "APP-desktop-agent")
    consent = next(r for r in refs if r["id"] == "CON-003")
    assert consent == {
        "kind": "contract", "id": "CON-003", "name": "Consent check",
        "description": "The Desktop agent asks Consent and identity whether a person has agreed, before it reads anything, and gets back what it may read.",
        "sends": "the person's sign-in",
        "gets": "whether they have agreed, and which sources the agent may read (calendar entries, transcripts)",
        "crosses": "", "provides": False, "provider": "Consent and identity", "state": "not decided yet", "open": 2}
    assert next(r for r in refs if r["id"] == "CON-004")["open"] == 3
    assert [r["id"] for r in refs] == ["CAP-005.FR1", "CON-003", "CON-004"]  # Traces to order


def test_a_requirement_the_grouped_criteria_cover_is_a_name_only_and_one_they_drop_is_written_out():
    req = next(r for r in ticketrefs.relies_on(heron(), stories()["S-02"], "APP-desktop-agent") if r["kind"] == "requirement")
    assert (req["name"], req["statement"]) == ("Agree to each source separately", None)
    dropped = plan_text().replace("(covers AC1, AC2)", "(covers AC2)")
    req = next(r for r in ticketrefs.relies_on(heron(), stories(dropped)["S-02"], "APP-desktop-agent") if r["kind"] == "requirement")
    assert req["statement"].startswith("When a person switches Heron on, they choose separately")


def test_each_open_question_the_story_waits_on_is_written_out_with_what_happens_meanwhile():
    found = ticketrefs.still_open(heron(), stories()["S-02"], questions())
    assert found == [{"id": "OQ-005", "found": True,
                      "question": "Is the person told when Consent and identity is down, or their sign-in has expired?",
                      "until": "the agent shows nothing and logs",
                      "waits_label": "What would answer it",
                      "waits": questions()["OQ-005"]["what_would_unblock"]}]
    assert ticketrefs.open_problems(heron(), stories()["S-02"], questions()) == []


def test_a_vault_unknown_names_its_question_and_owner_and_a_missing_meanwhile_is_flagged():
    text = plan_text().replace("Blocked by: S-01 (store).", "Blocked by: S-01 (store). Who builds the record waits on UNK-068.")
    found = ticketrefs.still_open(heron(), stories(text)["S-02"], questions())
    unknown = next(q for q in found if q["id"] == "UNK-068")
    assert (unknown["question"], unknown["until"], unknown["waits_label"], unknown["waits"]) == (
        "Which team builds Consent and identity?", None, "Waiting on", "the product owner")
    said = ticketrefs.open_problems(heron(), stories(text)["S-02"], questions())
    assert any("Who builds Consent and identity (UNK-068)" in t and "until then" in t and flag for t, flag in said)


def test_without_the_design_each_design_question_is_flagged():
    said = ticketrefs.open_problems(heron(), stories()["S-02"], None)
    assert said == [("waits on OQ-005, but the plan's design couldn't be read, so its ticket can't say what the question is", True)]
