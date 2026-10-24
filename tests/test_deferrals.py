"""A matter left for a Grill is an open question with an owner and a date, never a sentence that nothing will read again."""
import pytest

from conftest import check, edit, findings
import session_files

SHOP = "05-building-blocks/shop-building-blocks.md"
UNK = "11-unknowns-and-risks.md"
OPEN = "[[11-unknowns-and-risks#UNK-001 Till test rig|the till test rig]]"
RESOLVED = "[[11-unknowns-and-risks#UNK-002 Receipt format|the receipt format]]"


def codes(out):
    return [code for code, _ in findings(out)]


def say(mini, sentence):
    edit(mini / SHOP, "# Shop\n", f"# Shop\n\n{sentence}\n")


@pytest.mark.parametrize("sentence", [
    "How long a receipt is kept is left for a Grill.",
    "The refund limit is left for the Grill.",
    "Parked for a later Grill: who may void a sale.",
    "A Grill will decide the till's float.",
    "The rounding rule is to be decided later.",
    "This is settled in the next Grill.",
    "We'll settle it later.",
])
def test_prose_that_leaves_a_matter_for_a_grill_warns(mini, sentence):
    say(mini, sentence)
    _, out = check(mini)
    assert codes(out) == ["W389"]


def test_a_linked_open_question_carries_the_deferral(mini):
    say(mini, f"How long a receipt is kept is left for a Grill, and {OPEN} asks it.")
    _, out = check(mini)
    assert codes(out) == []


def test_a_question_in_the_same_paragraph_counts_even_on_another_line(mini):
    say(mini, f"How long a receipt is kept is left for a Grill.\nThe question is {OPEN}.")
    _, out = check(mini)
    assert codes(out) == []


def test_a_resolved_question_carries_nothing(mini):
    say(mini, f"How long a receipt is kept is left for a Grill; see {RESOLVED}.")
    _, out = check(mini)
    assert codes(out) == ["W389"]


def test_ordinary_prose_about_a_grill_is_left_alone(mini):
    say(mini, "A Grill decided the till's float on January 10.")
    _, out = check(mini)
    assert codes(out) == []


def test_a_session_record_may_say_it(mini):
    record_id = next((mini / "sessions").glob("*.md")).stem
    session_files.write_record(mini, record_id, session_files.record_text(mini, record_id) + "\nThe float was left for a Grill.\n")
    _, out = check(mini)
    assert "W389" not in codes(out)
