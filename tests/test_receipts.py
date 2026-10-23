"""The grammar of a receipt (`- **Decision:**`) and a Dissent, and the one way a handle is written.

The Violation this guards is a Distributed Monolith in the line grammar: the split, the decide writer and the check
each re-spelled `[[id]] c07, @maria: "..."`, so one changed spelling would split them. They all go through here."""
from vela import privaterecord, receipts

REF = privaterecord.Ref


def test_handle_ref_adds_the_at_once():
    assert receipts.handle_ref("maria") == "@maria"
    assert receipts.handle_ref("@maria") == "@maria"
    assert receipts.handle_ref(" @org/team ") == "@org/team"
    assert receipts.handle_ref("") == ""


def test_decision_with_words_round_trips():
    value = receipts.decision_value("2026-10-22-x", REF(2, 7), "@maria", "Yes.")
    assert value == '[[2026-10-22-x]] 2.c07, @maria: "Yes."'
    assert receipts.parse_decision(value) == receipts.Receipt("2026-10-22-x", REF(2, 7), "@maria", None, "Yes.")


def test_decision_in_part_one_has_the_short_ref_and_a_bare_handle_gets_its_at():
    value = receipts.decision_value("2026-10-22-x", REF(1, 9), "cto-ana")
    assert value == "[[2026-10-22-x]] c09, @cto-ana"
    assert receipts.parse_decision(value) == receipts.Receipt("2026-10-22-x", REF(1, 9), "@cto-ana", None, None)


def test_decision_names_the_source_that_states_it():
    value = receipts.decision_value("2026-10-22-x", REF(1, 9), "@maria", "Agreed.", stated_in="SRC-04")
    assert value == '[[2026-10-22-x]] c09, @maria, as SRC-04 states: "Agreed."'
    assert receipts.parse_decision(value).stated_in == "SRC-04"


def test_an_override_receipt_is_the_bare_link():
    assert receipts.decision_value("2026-10-22-x", None) == "[[2026-10-22-x]]"
    assert receipts.parse_decision("[[2026-10-22-x]]") == receipts.Receipt("2026-10-22-x", None, "", None, None)


def test_decision_words_stay_one_line_and_keep_inner_quotes():
    value = receipts.decision_value("2026-10-22-x", REF(1, 1), "@maria", 'She said "go"\nand **meant** it')
    assert "\n" not in value and "**" not in value.replace("\\*\\*", "")
    assert receipts.parse_decision(value).words.startswith('She said "go"')


def test_a_line_that_is_not_a_receipt_parses_to_none():
    assert receipts.parse_decision("see the plan") is None


def test_dissent_round_trips_with_and_without_words():
    assert receipts.dissent_value("raj", "2026-10-22") == "@raj, 2026-10-22"
    assert receipts.parse_dissent("@raj, 2026-10-22") == receipts.Dissent("@raj", "2026-10-22", None, "")
    value = receipts.dissent_value("@raj", "2026-10-22", "Too slow.", see="2026-10-22-x")
    assert value == '@raj, 2026-10-22: "Too slow." (see [[2026-10-22-x]])'
    assert receipts.parse_dissent(value) == receipts.Dissent("@raj", "2026-10-22", "Too slow.", "2026-10-22-x")


def test_dissent_written_before_the_quotes_still_parses():
    assert receipts.parse_dissent("@raj, 2026-01-10: too slow") == receipts.Dissent("@raj", "2026-01-10", "too slow", "")


def test_a_dissent_with_no_date_parses_to_none():
    assert receipts.parse_dissent("raj thinks it is slow") is None
