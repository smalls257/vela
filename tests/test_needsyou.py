"""vela.needsyou: what needs a person, most urgent first. Pure, so every rule is tested with plain dicts.

    python3 -m pytest -q tests/test_needsyou.py

The Violation these guard against is a Leaky Narrative on the page: when a question is late, how long an app counts as
"just handed", which grills are ready and what comes first are decided here, not rediscovered in script. The page,
the "N for you" badge and the sidebar then cannot disagree, because all three keep lines from this one list.
"""
import ast
import pathlib

import pytest
from vela import needsyou

TODAY = "2026-10-21"


def ask(ident, key="@agent-lead", date="2026-11-02", state="open", owner="@sim-lead", name="Agent lead"):
    return {"id": ident, "state": state, "askBy": date, "ownerRaw": owner, "ask": {"key": key, "name": name}}


def grill(ident, group, owner=("@agent-lead",)):
    return {"id": ident, "key": ident, "group": group, "owner": list(owner)}


def keys(found):
    return [(line["kind"], line["key"]) for line in found["lines"]]


def test_a_question_is_late_before_today_soon_within_a_week_and_later_after():
    assert needsyou.question_standing("2026-10-20", TODAY) == ("late", -1)
    assert needsyou.question_standing("2026-10-21", TODAY) == ("soon", 0)
    assert needsyou.question_standing("2026-10-28", TODAY) == ("soon", 7)
    assert needsyou.question_standing("2026-10-29", TODAY) == ("later", 8)


def test_a_question_without_a_real_date_has_none_and_is_never_called_late():
    assert needsyou.question_standing("", TODAY) == ("none", None)
    assert needsyou.question_standing("2026-13-45", TODAY) == ("none", None)
    assert needsyou.question_standing("when the CIO answers", TODAY) == ("none", None)
    assert needsyou.question_standing("2026-10-20", "not a date") == ("none", None)


def test_only_open_questions_are_lines_and_each_names_who_was_asked():
    found = needsyou.extract([ask("UNK-001"), ask("UNK-002", state="resolved"), ask("UNK-003", key="the CIO", name="the CIO")], [], [], [], TODAY)
    assert keys(found) == [("question", "UNK-001"), ("question", "UNK-003")]
    assert found["lines"][0]["for"] == ["@agent-lead"]
    assert found["lines"][1]["for"] == [] and found["lines"][1]["words"] == "the CIO"  # a role, not a person: the page matches the words


def test_lines_come_most_urgent_first_and_a_page_only_filters_them():
    asks = [ask("UNK-later", date="2026-12-01"), ask("UNK-late", date="2026-10-10"), ask("UNK-soon", date="2026-10-25"), ask("UNK-none", date=""),
            ask("UNK-later2", date="2026-11-15"), ask("UNK-late2", date="2026-10-01")]
    proposals = [{"key": "EPC-001", "by": "@reader", "date": "2026-10-20", "owners": ["@agent-lead"]}]
    handed = [{"key": "APP-desktop-agent", "handed_off": "@agent-lead, 2026-10-19"}]
    found = needsyou.extract(asks, [grill("CON-001", "ready")], proposals, handed, TODAY)
    assert keys(found) == [("question", "UNK-late2"), ("question", "UNK-late"), ("question", "UNK-soon"), ("proposal", "EPC-001"), ("handed", "APP-desktop-agent"),
                           ("grill", "CON-001"), ("question", "UNK-later2"), ("question", "UNK-later"), ("question", "UNK-none")]
    tiers = [line["tier"] for line in found["lines"]]
    assert tiers == sorted(tiers)


def test_a_grill_is_a_line_only_when_it_is_ready_or_already_said_yes_to():
    rows = [grill("A", "ready"), grill("B", "said-yes"), grill("C", "one-away"), grill("D", "ready", owner=())]
    found = needsyou.extract([], rows, [], [], TODAY)
    assert keys(found) == [("grill", "A"), ("grill", "B")]  # one thing away is not yet theirs to run; a grill nobody owns is nobody's line
    assert [line["standing"] for line in found["lines"]] == ["ready", "said-yes"]


def test_a_proposal_goes_to_the_owners_and_one_with_no_owner_is_nobodys():
    found = needsyou.extract([], [], [{"key": "CON-001", "by": "@reader", "date": "", "owners": ["@Agent-Lead", "@sim-lead"]},
                                       {"key": "CON-002", "by": "@reader", "date": "2026-10-01", "owners": [""]}], [], TODAY)
    assert keys(found) == [("proposal", "CON-001")]
    assert found["lines"][0]["for"] == ["@agent-lead", "@sim-lead"]  # lower-cased, so a handle matches however the page spells it


def test_proposals_are_oldest_first_and_undated_ones_last():
    proposals = [{"key": "C", "by": "@r", "date": "", "owners": ["@a"]}, {"key": "B", "by": "@r", "date": "2026-10-20", "owners": ["@a"]},
                 {"key": "A", "by": "@r", "date": "2026-10-02", "owners": ["@a"]}]
    assert keys(needsyou.extract([], [], proposals, [], TODAY)) == [("proposal", "A"), ("proposal", "B"), ("proposal", "C")]


@pytest.mark.parametrize("text, want", [("@agent-lead, 2026-10-19", ("@agent-lead", "2026-10-19")), ("Booking senior, 2026-10-19", ("Booking senior", "2026-10-19")),
                                        ("@agent-lead", None), ("@agent-lead, 2026-13-45", None), (", 2026-10-19", None), ("", None)])
def test_a_handoff_field_is_read_when_it_names_someone_and_has_a_real_date(text, want):
    assert needsyou.parse_handed_off(text) == want


def test_a_handoff_written_as_a_name_travels_as_a_name_for_the_page_to_match():
    found = needsyou.extract([], [], [], [{"key": "APP-booking", "handed_off": "Booking senior, 2026-10-19"}, {"key": "APP-x", "handed_off": "@Agent-Lead, 2026-10-19"}], TODAY)
    by_key = {line["key"]: line for line in found["lines"]}
    named, handle = by_key["APP-booking"], by_key["APP-x"]
    assert named["for"] == [] and named["named"] == "booking senior"
    assert handle["for"] == ["@agent-lead"] and handle["named"] == ""


def test_an_app_is_just_handed_for_two_weeks_and_never_before_its_date():
    handed = [{"key": "NEW", "handed_off": "@a, 2026-10-19"}, {"key": "EDGE", "handed_off": "@a, 2026-10-07"}, {"key": "OLD", "handed_off": "@a, 2026-10-06"},
              {"key": "FUTURE", "handed_off": "@a, 2026-10-22"}, {"key": "MALFORMED", "handed_off": "everyone, soon"}]
    found = needsyou.extract([], [], [], handed, TODAY)
    assert keys(found) == [("handed", "NEW"), ("handed", "EDGE")]  # newest first; 14 days is still new, 15 is not
    assert needsyou.HANDED_DAYS == 14


def test_the_dates_on_a_persons_side_are_the_questions_they_own_that_someone_else_must_answer():
    asks = [ask("UNK-1", key="@identity-lead", date="2026-11-02", owner="@agent-lead (asking @identity-lead)", name="Identity lead"),
            ask("UNK-2", key="@x", date="2026-10-01", owner="@agent-lead"), ask("UNK-3", key="@x", date="", owner="@agent-lead"),
            ask("UNK-4", key="@x", date="2026-10-30", owner="@agent-lead", state="resolved"), ask("UNK-5", key="@x", date="2026-10-25", owner="@agent-lead")]
    dates = needsyou.extract(asks, [], [], [], TODAY)["dates"]
    assert [(d["key"], d["date"]) for d in dates] == [("UNK-5", "2026-10-25"), ("UNK-1", "2026-11-02")]  # open, dated today or later, earliest first
    assert dates[1]["for"] == ["@agent-lead"] and dates[1]["askedName"] == "Identity lead"  # the owner is the first handle, not the one asked in the parenthesis


def test_nothing_in_means_nothing_out():
    assert needsyou.extract([], [], [], [], TODAY) == {"lines": [], "dates": []}


def test_the_module_reads_no_clock_and_touches_no_files():
    tree = ast.parse(pathlib.Path(needsyou.__file__).read_text(encoding="utf-8"))
    imported = {n.names[0].name.split(".")[0] for n in ast.walk(tree) if isinstance(n, ast.Import)} | {n.module.split(".")[0] for n in ast.walk(tree) if isinstance(n, ast.ImportFrom)}
    assert imported <= {"datetime", "re", "vela"}, imported
    assert "today()" not in pathlib.Path(needsyou.__file__).read_text(encoding="utf-8")
