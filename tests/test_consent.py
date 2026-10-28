"""The yes a decision takes is the lead's own word: nothing is read back first (a Silent Fallback is still ruled out by
refusing Claude's words and a bare "ok")."""
from vela import privaterecord
from vela.decisions import consent, record

RECORD_ID = "2026-10-27-grill-stock"


def opened(*captures):
    lines = ["---", f"id: {RECORD_ID}", "type: session", "date: 2026-10-27", "modes: [grill]", "status: open",
             "summary: In progress.", "---", "", "# 2026-10-27 Stock grill", "", "## Captures", "", *captures, ""]
    split = privaterecord.split_record("\n".join(lines) + "\n")
    return record.from_text(RECORD_ID, privaterecord.private_path(RECORD_ID), split.private)


def a_yes(ref, *captures):
    return consent.a_yes(ref, opened(*captures))


def test_a_yes_needs_no_read_back():
    assert a_yes("^c02", '- [answer] (@priya) "Settle it." ^c02') is None


def test_claudes_words_are_never_a_yes():
    refusal = a_yes("^c02", '- [answer] (claude) "Settle it." ^c02')
    assert refusal.rule == "consent-not-a-person"


def test_bare_ok_is_still_not_a_yes():
    refusal = a_yes("^c02", '- [answer] (@priya) "ok" ^c02')
    assert refusal.rule == "consent-bare-non-yes"
