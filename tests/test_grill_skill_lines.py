"""The grill skill's opening rules, kept short and pinned by name.

The Violation these lines prevent is a Paper Tiger session: 14 turns of reading, reviewers and "nothing ready, has X
happened?" that meet the grill's form and decide nothing. The rules that can live in code do (`check --gate decide
--all`, the agenda's yes order, the lead's display name); these are the ones only the model can follow.
"""
from conftest import REPO

SKILL = (REPO / "plugin" / "skills" / "grill" / "SKILL.md").read_text(encoding="utf-8")


def test_the_grill_opens_with_one_gate_call_and_a_ready_item_as_a_proposal():
    assert "vela check --gate decide --all --for-lead" in SKILL
    assert "I'd settle <item> as <answer>, because <reason>. Settle it?" in SKILL
    assert "Recaps and reading come after that, or only if needed." in SKILL
    assert "ask the question that would make the nearest item ready" in SKILL


def test_hold_is_recommended_only_when_the_gate_says_not_ready():
    assert "not \"hold\" or \"keep it open\", unless the gate says the item isn't ready" in SKILL


def test_the_review_checkpoint_waits_for_the_first_decision_or_a_pause():
    assert "after the first decision or a natural pause, never on turn 1" in SKILL


def test_a_yes_right_after_the_agenda_is_accepted_not_asked_again():
    assert "a yes right after the agenda is accepted in that turn, so never ask for it again" in SKILL


def test_an_answer_that_settles_a_not_ready_item_gets_the_override_offer_at_once():
    # E79: an early grill filed three clear yeses as notes and said the lead "chose not to override" without offering.
    assert "When an answer settles an item that isn't ready, offer to decide it anyway in that same turn" in SKILL
    assert "Never file a settling answer as a note without that offer." in SKILL
