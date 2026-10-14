"""The pure part of `close gate` (overhaul Task 10a): a change into or out of decided needs the lead's quoted yes."""
from planner import closegate, model, parse

RECORD = "2026-10-20-grill-consent"


def record(captures, rows):
    lines = ["---", "date: 2026-10-20", "modes: [grill]", "status: open", "---", "", "## Captures", ""]
    lines += captures + ["", "## Changes", "", "| ID | From | To | Source |", "|---|---|---|---|"] + rows
    return "\n".join(lines) + "\n"


def vault(state="decided", override=""):
    page = parse.parse_page("05-building-blocks/booking-building-blocks.md", "\n".join([
        "---", "id: APP-booking", "type: app-building-blocks", "title: Booking", "state: assumption", "---", "",
        "# Booking", "", "### CON-003 Consent records", "", "- **State:** " + state, override, ""]))
    return model.build([page], {})


def judged(captures, rows, state="decided", override=""):
    v = vault(state, override)
    changes = closegate.consent_changes({"CON-003": "assumption", "APP-booking": "assumption"}, closegate.states(v), v)
    return closegate.judge(changes, record(captures, rows), RECORD, v)


def test_hand_set_decided_with_no_changes_row_refused():
    problems, consent = judged([], [])
    assert len(problems) == 1 and not consent
    assert "Consent records was made decided with nothing on record" in problems[0].plain
    assert "CON-003" not in problems[0].plain and "CON-003" in problems[0].detail


def test_changes_row_citing_claude_capture_refused():
    problems, _ = judged(["- [thought] (claude) Decide consent now ^c01"],
                         [f"| CON-003 | assumption | decided | [[{RECORD}#^c01]] |"])
    assert "on my suggestion" in problems[0].plain


def test_claude_from_summary_is_not_a_quote():
    problems, _ = judged(["- [thought] (claude, from @lead) the lead agreed ^c01"],
                         [f"| CON-003 | assumption | decided | [[{RECORD}#^c01]] |"])
    assert problems and "own yes" in problems[0].plain


def test_bare_ok_is_not_a_yes():
    for words in ('"ok"', "Okay.", "sure", '"next"'):
        problems, _ = judged([f"- [thought] (@lead) {words} ^c01"], [f"| CON-003 | assumption | decided | [[{RECORD}#^c01]] |"])
        assert problems and "isn't a yes" in problems[0].plain, words


def test_a_quoted_yes_passes_and_lands_in_the_consent_block():
    problems, consent = judged(['- [thought] (@lead) "Yes, decide it as read." says yes to consent records ^c04'],
                               [f"| CON-003 | assumption | decided | [[{RECORD}#^c04]] |"])
    assert not problems
    block = closegate.consent_block(consent)
    assert block[0] == "**Consent**"
    assert f'- Consent records (CON-003), assumption to decided: "Yes, decide it as read." [[{RECORD}#^c04]]' in block


def test_override_bullet_lets_it_through_and_is_listed():
    bullet = f"- **Override:** {closegate.QUOTED_YES_RULE} by @lead on 2026-10-20: the owner said yes on the phone"
    problems, consent = judged([], [], override=bullet)
    assert not problems
    assert consent and "by override" in consent[0].change and "on the phone" in consent[0].words


def test_reader_copy_checks_every_changes_row():
    rows = closegate.change_rows(record(["- [thought] (claude) do it ^c01"],
                                        [f"| CON-003 | assumption | decided | [[{RECORD}#^c01]] |",
                                         f"| UNK-001 | - | open | [[{RECORD}#^c01]] |"]))
    changes = closegate.reader_changes(rows, {"CON-003": "decided", "UNK-001": "open"})
    assert [c.item for c in changes] == ["CON-003"]


def test_other_state_moves_are_not_judged():
    v = vault(state="assumption")
    assert closegate.consent_changes({"CON-003": "inkling"}, closegate.states(v), v) == []
