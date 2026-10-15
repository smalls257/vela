"""The pure part of `close gate` (overhaul Task 10a): a change into or out of decided needs the lead's quoted yes."""
from vela import closegate, closestate, model, parse, say

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
    assert "You haven't said yes to deciding Consent records yet." == problems[0].plain
    assert "CON-003" not in problems[0].plain and "CON-003" in problems[0].detail


def test_changes_row_citing_claude_capture_refused():
    problems, _ = judged(["- [thought] (claude) Decide consent now ^c01"],
                         [f"| CON-003 | assumption | decided | [[{RECORD}#^c01]] |"])
    assert "was my suggestion, not your yes" in problems[0].plain


def test_claude_from_summary_is_not_a_quote():
    problems, _ = judged(["- [thought] (claude, from @lead) the lead agreed ^c01"],
                         [f"| CON-003 | assumption | decided | [[{RECORD}#^c01]] |"])
    assert problems and "not your yes" in problems[0].plain


def test_bare_ok_is_not_a_yes():
    for words in ('"ok"', "Okay.", "sure", '"next"'):
        problems, _ = judged([f"- [thought] (@lead) {words} ^c01"], [f"| CON-003 | assumption | decided | [[{RECORD}#^c01]] |"])
        assert problems and "Was that a yes" in problems[0].plain, words


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


# Task 10: the rest of the list. `ready` is pure: everything git or the disk says arrives in a `Seen`.

PASSED = closestate.Verdict(False, "Main was already in this branch; nothing to bring in.", "up-to-date")
LEDGER_PAGE = "\n".join([
    "---", "id: unknowns-and-risks", "type: unknowns-and-risks", "title: Unknowns and risks", "---", "",
    "# Unknowns and risks", "", "## Question ledger", "", "| Copy | State | Evidence | By | Date |", "|---|---|---|---|---|",
    "{rows}", ""])
ROW = "| Q-DAT-01@APP-booking | not-applicable | reason: no personal data | @lead | 2026-10-01 |"
OVERRIDE = "- **Override:** E318 by @lead on 2026-10-01: the vendor tests it"
MARKED = f'- [thought] (@lead) "Yes, decide it as read." → keep: [[booking-building-blocks#CON-003 Consent records|CON-003]] (decided) ^c04'
YES_ROW = f"| CON-003 | assumption | decided | [[{RECORD}#^c04]] |"


def vault_of(rows=ROW, override_line="", state="decided"):
    booking = parse.parse_page("05-building-blocks/booking-building-blocks.md", "\n".join([
        "---", "id: APP-booking", "type: app-building-blocks", "title: Booking", "state: assumption", "---", "",
        "# Booking", "", "### CON-003 Consent records", "", "- **State:** " + state, override_line, ""]))
    unknowns = parse.parse_page("11-unknowns-and-risks.md", LEDGER_PAGE.format(rows=rows))
    return model.build([booking, unknowns], {})


def seen(**kw):
    kw.setdefault("today", "2026-10-20")
    kw.setdefault("sync", PASSED)
    kw.setdefault("before", vault_of(state="assumption"))
    kw.setdefault("hooks_ran", True)
    return closegate.Seen(**kw)


def readied(captures=(MARKED,), rows=(YES_ROW,), now=None, **kw):
    return closegate.ready(now or vault_of(), record(list(captures), list(rows)), RECORD, seen(**kw))


def plains(found):
    return [p.plain for p in found]


def test_clean_session_passes():
    result = readied()
    assert result.ready, plains(result.problems)
    assert [c.item for c in result.consent] == ["CON-003"]


def test_unmarked_capture_blocks():
    unmarked = '- [thought] (@lead) "Yes, decide it as read." ^c04'
    result = readied(captures=(unmarked, "- [idea] (claude) a second note ^c05"))
    assert not result.ready
    problem = next(p for p in result.problems if p.kind == closegate.UNMARKED)
    assert problem.plain.startswith("Two things you said aren't sorted yet")
    assert "^c04" in problem.detail and "^c05" in problem.detail and problem.clear


def test_ledger_row_removed_since_branch_point_blocks():
    result = readied(now=vault_of(rows=""))
    assert not result.ready
    problem = next(p for p in result.problems if "ledger" in p.detail)
    assert "Q-DAT-01@APP-booking" in problem.detail  # the command's resolver says the copy as its question
    assert "put" in problem.clear.lower()


def test_override_removed_since_branch_point_blocks():
    result = readied(before=vault_of(override_line=OVERRIDE, state="assumption"))
    assert not result.ready
    problem = next(p for p in result.problems if "override" in p.detail)
    assert "Consent records" in problem.plain and "vendor tests it" in problem.plain


def test_a_removal_the_lead_agreed_to_is_let_through():
    said = '- [thought] (@lead) "Drop that override, the vendor no longer tests it." → park ^c06'
    result = readied(captures=(MARKED, said), rows=(YES_ROW, f"| CON-003 | override | removed | [[{RECORD}#^c06]] |"),
                     before=vault_of(override_line=OVERRIDE, state="assumption"))
    assert result.ready, plains(result.problems)


def test_a_removal_on_claudes_word_still_blocks():
    said = "- [thought] (claude) the override looks stale → park ^c06"
    result = readied(captures=(MARKED, said), rows=(YES_ROW, f"| CON-003 | override | removed | [[{RECORD}#^c06]] |"),
                     before=vault_of(override_line=OVERRIDE, state="assumption"))
    assert not result.ready


def test_render_stale_blocks():
    result = readied(stale=("05-building-blocks/booking-building-blocks.md",))
    assert not result.ready and any("generated" in p for p in plains(result.problems))
    assert all(p.audience == say.MODEL for p in result.problems if p.kind == closegate.RENDER)  # Claude's own step


def test_tree_not_clean_blocks():
    result = readied(stray=("notes.txt",))
    assert not result.ready
    problem = next(p for p in result.problems if "notes.txt" in p.plain)
    assert problem.clear


def test_an_error_with_no_recorded_choice_blocks():
    """Check's errors arrive already filtered by the overrides (rules.check applies them), so one that is still here
    has no recorded choice behind it."""
    error = model.Finding("05-building-blocks/booking-building-blocks.md", 11, "E318",
                          "CON-003 is decided but says nothing about who tests it.", "Add a Tested by line.")
    result = readied(errors=(error,))
    assert not result.ready
    problem = next(p for p in result.problems if p.plain.startswith("On Booking:"))
    assert "E318" in problem.detail and "E318" not in problem.plain and "override" in problem.clear


def test_flowcheck_line_per_affected_slice():
    lines = (("SLC-001 Book a room: passes. Checked because Consent records changed → Booking → SLC-001 Book a room.",
              "The flow check of Book a room: passes."),
             ("SLC-002 Pay: fails, 1 open finding (dead end).", "The flow check of Pay: fails, 1 open finding."))
    result = readied(flow=lines)
    assert result.ready  # a read-back for the lead, not a gate
    flow = [n for n in result.notes if n.detail.startswith("SLC-")]
    assert [(n.detail, n.plain) for n in flow] == list(lines)


def test_hooks_marker_missing_is_said_plainly():
    result = readied(hooks_ran=False)
    assert result.ready
    assert any("Hooks did not run in this session" in n.plain for n in result.notes)
    assert not any("Hooks" in n.plain for n in readied().notes)


def test_a_conflict_is_said_as_not_brought_in_never_as_a_merge_still_open():
    """sync-main aborts a merge that stops, so the true state is that main's changes aren't in yet."""
    verdict = closestate.verdict(closestate.record(closestate.CONFLICT, "session/x"))
    assert verdict.blocks and "still open" not in verdict.plain and "haven't brought" in verdict.plain
    assert verdict.audience == say.LEAD  # only the lead can choose between the two versions
    assert closestate.verdict(None).audience == say.MODEL  # sync-main not run yet is Claude's own step


def test_sync_not_run_blocks():
    result = readied(sync=closestate.verdict(None))
    assert not result.ready and "Main hasn't been brought into this branch yet." in plains(result.problems)


def test_reader_copy_checks_without_git():
    """A reader copy has no branch point: `before` is None, and the record's Changes rows are judged as written."""
    unmarked = '- [thought] (@lead) "Yes, decide it as read." ^c04'
    result = readied(captures=(unmarked,), before=None, reader=True)
    assert not result.ready and any("isn't sorted yet" in p for p in plains(result.problems))
    assert readied(before=None, reader=True).ready
