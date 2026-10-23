"""E315 and the close gate's receipt check: a Decision or Dissent line is in the receipt form, and the lead's own words
sit behind a lead receipt. `vela check` judges the form only (it doesn't know who the lead is); the gate knows the lead."""
from vela import closegate, closestate, model, parse, receipts, rules

RECORD = "2026-10-22-booking-api"
OLD = "2026-01-10-shop-api"
PASSED = closestate.Verdict(False, "Main was already in this branch; nothing to bring in.", "up-to-date")
LEAD = ("priya", frozenset({"Priya Rao"}))


def session_stub(record_id, date):
    return parse.parse_page(f"sessions/{record_id}.md", "\n".join([
        "---", f"id: {record_id}", "type: session", f"title: {record_id}", f"date: {date}", "modes: [grill]",
        "status: closed", "---", ""]))


def booking(*bullets, state="decided"):
    return parse.parse_page("05-building-blocks/booking-building-blocks.md", "\n".join([
        "---", "id: APP-booking", "type: app-building-blocks", "title: Booking", "state: assumption", "---", "",
        "# Booking", "", "### CON-003 Consent records", "", f"- **State:** {state}", *bullets, ""]))


def vault_with(*bullets, split="2026-10-22", state="decided"):
    config = {"records_split": split} if split else {}
    pages = [booking(*bullets, state=state), session_stub(RECORD, "2026-10-22"), session_stub(OLD, "2026-01-10")]
    return model.build(pages, config)


def codes_with(*bullets, split="2026-10-22"):
    return [f.code for f in receipts.receipt_rules(vault_with(*bullets, split=split), "2026-10-22")]


def test_e315_on_a_malformed_receipt_and_not_on_an_exempt_one():
    assert "E315" in codes_with(f"- **Decision:** [[{RECORD}]] seven")
    assert "E315" not in codes_with(f"- **Decision:** [[{OLD}]] seven")
    assert "E315" not in codes_with(f"- **Decision:** [[{OLD}]]")


def test_with_no_records_split_nothing_is_exempt():
    assert "E315" in codes_with(f"- **Decision:** [[{OLD}]]", split=None)


def test_a_receipt_with_a_ref_and_a_who_is_clean():
    assert not codes_with(f'- **Decision:** [[{RECORD}]] c07, @priya: "Yes, one booking API."',
                          f"- **Decision:** [[{RECORD}]] c09, @cto-ana")


def test_a_bare_link_needs_an_override_for_the_quoted_yes_rule():
    bare = f"- **Decision:** [[{RECORD}]]"
    override = f"- **Override:** {closegate.QUOTED_YES_RULE} by @priya on 2026-10-22: the owner said yes by phone"
    assert "E315" in codes_with(bare)
    assert "E315" not in codes_with(bare, override)
    other = "- **Override:** E318 by @priya on 2026-10-22: the vendor tests it"
    assert "E315" in codes_with(bare, other)


def test_a_dissent_must_parse():
    assert "E315" in codes_with(f"- **Decision:** [[{RECORD}]] c07, @priya", "- **Dissent:** raj thinks it is slow")
    assert not codes_with(f"- **Decision:** [[{RECORD}]] c07, @priya", "- **Dissent:** @raj, 2026-10-22")


def test_a_yaml_date_for_records_split_still_compares():
    import datetime
    assert "E315" not in codes_with(f"- **Decision:** [[{OLD}]]", split=datetime.date(2026, 10, 22))


def test_each_line_is_judged_once():
    found = [f for f in receipts.receipt_rules(vault_with(f"- **Decision:** [[{RECORD}]] seven"), "2026-10-22")
             if f.code == "E315"]
    assert len(found) == 1


def test_e315_is_one_of_the_rules_check_runs():
    found = rules.check(vault_with(f"- **Decision:** [[{RECORD}]] seven"), "2026-10-22")
    assert "E315" in [f.code for f in found]


# ---- the gate

def private_text(*captures):
    lines = ["---", "date: 2026-10-22", "modes: [grill]", "status: open", "---", "", "## Captures", "", *captures, "",
             "## Changes", "", "| ID | From | To | Source |", "|---|---|---|---|"]
    return "\n".join(lines) + "\n"


YES = '- [answer] (@priya) "Yes, one booking API." → park ^c07'
ANA = '- [answer] (@cto-ana) "Yes, one booking API." → park ^c09'
ANA_QUOTE = '- [quote-yes] (@cto-ana) "Yes, quote me." → park ^c10'
RAJ = '- [worry] (@raj) "This is too slow." → park ^c11'


def gate(*bullets, captures=(YES,), lead=LEAD, before_bullets=(), part=1):
    now = vault_with(*bullets)
    before = vault_with(*before_bullets, state="assumption")
    return closegate.receipt_problems(now, before, RECORD, part, private_text(*captures), lead)


def kinds(found):
    return {p.kind for p in found}


def test_the_gate_wants_the_leads_words_on_their_own_receipt():
    found = gate(f"- **Decision:** [[{RECORD}]] c07, @priya")
    assert kinds(found) == {closegate.RECEIPT}
    assert found[0].plain == "The decision on Consent records has none of your words on record yet."
    assert "CON-003" not in found[0].plain and "CON-003" in found[0].detail


def test_the_leads_handle_may_arrive_without_an_at_sign_or_as_a_display_name():
    assert gate(f"- **Decision:** [[{RECORD}]] c07, @priya", lead=("@priya", frozenset()))
    assert gate(f"- **Decision:** [[{RECORD}]] c07, @priya", lead=("PRIYA", frozenset()))


def test_the_leads_words_clear_it():
    assert not gate(f'- **Decision:** [[{RECORD}]] c07, @priya: "Yes, one booking API."')


def test_someone_elses_words_need_their_own_quote_yes():
    line = f'- **Decision:** [[{RECORD}]] c09, @cto-ana: "Yes, one booking API."'
    found = gate(line, captures=(ANA,))
    assert [p.plain for p in found] == ["Consent records's decision quotes someone who hasn't said yes to being quoted."]
    assert not gate(line, captures=(ANA, ANA_QUOTE))


def test_someone_elses_receipt_without_words_is_fine():
    assert not gate(f"- **Decision:** [[{RECORD}]] c09, @cto-ana", captures=(ANA,))


def test_unquoted_dissent_words_get_the_same_wording():
    line = f'- **Dissent:** @raj, 2026-10-22: "This is too slow." (see [[{RECORD}]])'
    found = gate(line, captures=(RAJ,))
    assert kinds(found) == {closegate.RECEIPT} and "hasn't said yes to being quoted" in found[0].plain
    own = '- [quote-yes] (@raj) "Yes, quote me." → park ^c12'
    assert not gate(line, captures=(RAJ, own))


def test_receipts_that_were_already_there_or_cite_another_part_are_not_this_sessions():
    line = f"- **Decision:** [[{RECORD}]] c07, @priya"
    assert not gate(line, before_bullets=(line,))
    assert not gate(f"- **Decision:** [[{RECORD}]] 2.c07, @priya")
    assert not gate(f"- **Decision:** [[{OLD}]] c07, @priya")


def test_ready_carries_the_receipt_problem():
    seen = closegate.Seen(today="2026-10-22", sync=PASSED, hooks_ran=True, lead=LEAD,
                          before=vault_with(state="assumption"))
    row = f"| CON-003 | assumption | decided | [[{RECORD}#^c07]] |"
    marked = '- [answer] (@priya) "Yes, one booking API." → keep: [[booking-building-blocks#CON-003 Consent records|CON-003]] (decided) ^c07'
    text = private_text(marked) + row + "\n"
    now = vault_with(f"- **Decision:** [[{RECORD}]] c07, @priya")
    result = closegate.ready(now, text, RECORD, seen)
    assert closegate.RECEIPT in kinds(result.problems)
    assert closegate.KINDS.index(closegate.RECEIPT) == closegate.KINDS.index(closegate.CONSENT) + 1


# ---- marks that point nowhere

def marked_text(target):
    return private_text(f'- [answer] (@priya) "Yes." → keep: {target} (decided) ^c07')


def mark_problems(target):
    return closegate.mark_target_problems(vault_with(), marked_text(target))


def test_a_mark_whose_page_or_heading_is_missing_blocks_the_close():
    assert not mark_problems("[[booking-building-blocks#CON-003 Consent records|CON-003]]")
    missing_page = mark_problems("[[nowhere#CON-003 Consent records|CON-003]]")
    missing_heading = mark_problems("[[booking-building-blocks#CON-099 Gone|CON-099]]")
    assert missing_page and missing_heading
    assert {p.kind for p in missing_page + missing_heading} == {closegate.CHECK}
    assert "CON-099" not in missing_heading[0].plain and "CON-099" in missing_heading[0].detail


def test_a_record_still_committed_whole_predates_receipts():
    whole = parse.parse_page(f"sessions/{OLD}.md", "\n".join([
        "---", f"id: {OLD}", "type: session", f"title: {OLD}", "date: 2026-10-06", "modes: [grill]", "status: closed",
        "---", "", "## Captures", "", '- [answer] (@priya) "Yes." ^c01', ""]))
    vault = model.build([booking(f"- **Decision:** [[{OLD}]]"), whole], {})
    assert not list(receipts.receipt_rules(vault, "2026-10-22"))


def test_a_dissent_with_words_must_say_which_session_they_came_from():
    decision = f"- **Decision:** [[{RECORD}]] c07, @priya"
    assert "E315" in codes_with(decision, '- **Dissent:** @raj, 2026-10-22: "This is too slow."')
    assert not codes_with(decision, f'- **Dissent:** @raj, 2026-10-22: "This is too slow." (see [[{RECORD}]])')


def test_once_records_split_is_set_a_whole_record_dated_after_it_is_not_exempt():
    def whole(date):
        return parse.parse_page(f"sessions/{OLD}.md", "\n".join([
            "---", f"id: {OLD}", "type: session", f"title: {OLD}", f"date: {date}", "modes: [grill]", "status: closed",
            "---", "", "## Captures", "", '- [answer] (@priya) "Yes." ^c01', ""]))

    def found(date):
        vault = model.build([booking(f"- **Decision:** [[{OLD}]]"), whole(date)], {"records_split": "2026-10-22"})
        return [f.code for f in receipts.receipt_rules(vault, "2026-10-22")]
    assert found("2026-10-21") == [] and found("2026-10-22") == ["E315"]


def test_a_mark_on_a_missing_page_and_on_a_missing_heading_read_differently():
    page = mark_problems("[[nowhere#CON-003 Consent records|CON-003]]")[0].plain
    heading = mark_problems("[[booking-building-blocks#CON-099 Gone|CON-099]]")[0].plain
    assert "can't find that page" in page and "under a heading that isn't there" in heading


def test_dissent_words_pass_without_a_session_only_when_every_link_is_a_source():
    sources = parse.parse_page("sources.md", "---\nid: sources\ntype: sources\ntitle: Sources\n---\n\n# Sources\n")
    decision = f"- **Decision:** [[{RECORD}]] c07, @priya"

    def codes(link):
        line = f'- **Dissent:** @raj, 2026-10-22: "This is too slow." ([[{link}]])'
        vault = model.build([booking(decision, line), sources, session_stub(RECORD, "2026-10-22")],
                            {"records_split": "2026-10-22"})
        return [f.code for f in receipts.receipt_rules(vault, "2026-10-22")]
    assert codes("sources#SRC-012|the one-pager") == []
    assert codes("booking-building-blocks") == ["E315"]
    assert codes("nowhere") == ["E315"]
