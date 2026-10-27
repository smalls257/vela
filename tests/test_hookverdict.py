"""edit_verdict: what a hand edit to a vault page may not change (a state, a generated block, the open-question note)."""
from vela import hookverdict

PAGE = """### CON-001 Booking API

- **State:** decided

## History

#### CON-001

- **Decision:** [[2026-10-20-grill]]
"""
NOTED = PAGE + "- **Decided with open:** UNK-009\n"


def test_a_hand_typed_decided_with_open_bullet_is_denied():
    verdict = hookverdict.edit_verdict(PAGE, NOTED)
    assert verdict is not None and verdict.decision == hookverdict.DENY
    assert "Only `vela decide` writes" in verdict.reason


def test_a_hand_changed_decided_with_open_bullet_is_denied():
    changed = NOTED.replace("UNK-009", "UNK-010")
    assert hookverdict.edit_verdict(NOTED, changed).decision == hookverdict.DENY


def test_taking_the_note_away_or_leaving_it_alone_is_allowed():
    assert hookverdict.edit_verdict(NOTED, PAGE) is None
    assert hookverdict.edit_verdict(NOTED, NOTED + "- **Why:** because\n") is None


def test_a_hand_moved_state_is_still_denied():
    assert hookverdict.edit_verdict(PAGE, PAGE.replace("decided", "assumption")).decision == hookverdict.DENY
