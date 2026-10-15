"""The decision-file core (overhaul Task 4), pure: the kind registry, the file's shape, and the consent checks of plan
4.3. Each consent check is a Sensor on what the record says, not proof the lead said it; these tests pin that a
missing or malformed yes is refused with the sentence the lead would hear."""
import sys
import types

import pytest

from vela import decisions, say
from vela.decisions import consent, record, schema

RECORD_ID = "2026-10-20-grill-stock"


def record_text(*captures):
    lines = ["---", f"id: {RECORD_ID}", "type: session", "date: 2026-10-20", "modes: [grill]", "status: open",
             "summary: In progress.", "---", "", "# 2026-10-20 Stock grill", "", "## Captures", "", *captures, ""]
    return "\n".join(lines) + "\n"


def opened(*captures):
    found, problem = record.open_record([("", f"sessions/{RECORD_ID}.md", record_text(*captures))])
    assert problem is None, problem
    return found


READBACK = "- [readback] (claude) I read back: stock level is decided as the count left ^c30"


def test_bare_ok_is_not_a_yes():
    rec = opened(READBACK, '- [answer] (@priya) "ok" ^c31')
    refusal = consent.a_yes("^c31", rec, readback="^c30")
    assert refusal is not None and refusal.plain == "You said 'ok'. Is that a yes to the wording as I read it?"
    assert consent.not_bare_non_yes(rec.capture("^c31")) is not None


def test_claude_origin_is_not_a_yes():
    rec = opened(READBACK, "- [answer] (claude) yes, decide it ^c31")
    refusal = consent.a_yes("^c31", rec, readback="^c30")
    assert refusal.plain == "That line was mine, not yours. Does the wording I read back sound right to you?"


def test_claude_from_summary_is_not_a_yes():
    rec = opened(READBACK, "- [answer] (claude, from @priya) Priya is happy with it ^c31")
    assert consent.from_a_person(rec.capture("^c31")).plain == "That line was mine, not yours. Does the wording I read back sound right to you?"


def test_yes_before_readback_is_refused():
    rec = opened('- [answer] (@priya) "Yes, decide it." ^c29', READBACK)
    refusal = consent.a_yes("^c29", rec, readback="^c30")
    assert refusal.plain == "Your yes came before I read the final wording back, so I'll read it again."
    assert consent.after_readback(rec.capture("^c29"), rec.capture("^c30")) is not None


def test_a_yes_after_its_readback_passes():
    rec = opened(READBACK, '- [answer] (@priya) "Yes, as read." ^c31')
    assert consent.a_yes("^c31", rec, readback="^c30") is None


def test_missing_capture_is_refused():
    rec = opened(READBACK)
    assert consent.a_yes("^c44", rec, readback="^c30").plain == \
        "I don't have your answer written down yet, so I haven't filed it."
    assert consent.exists("not a capture", rec) is not None


def test_group_readback_over_seven_refused():
    assert consent.group_small_enough(7) is None
    refusal = consent.group_small_enough(8)
    assert refusal.plain == "That was too much for one yes. I'll read it back in smaller groups."
    items = [{"readback": "^c30"}] * 8 + [{"readback": "^c40"}]
    assert consent.group_sizes(items) == {"^c30": 8, "^c40": 1}


def test_why_must_be_the_leads_words():
    rec = opened("- [why] (claude) because it is simpler ^c32", '- [why] (@priya) "Stores already count it." ^c33')
    assert consent.why_in_their_words("^c32", rec).plain == "Why this one, in your words?"
    assert consent.why_in_their_words("^c33", rec) is None


def test_push_yes_must_follow_the_send_notice():
    rec = opened('- [answer] (@priya) "Yes, send it." ^c12', '- [answer] (@priya) "Yes, send it." ^c15')
    assert consent.after_send_notice(rec.capture("^c12"), notice_count=14).plain == \
        "Before I send anything, I need to tell you what goes and to whom."
    assert consent.after_send_notice(rec.capture("^c15"), notice_count=14) is None


def test_capture_text_changed_since_draft_refused():
    rec = opened(READBACK, '- [answer] (@priya) "Yes, as read." ^c31')
    sealed = schema.seal({"yes": "^c31"}, rec, ["^c31"])
    assert consent.unchanged_since_draft(rec.capture("^c31"), sealed["seen"]["^c31"]) is None
    edited = opened(READBACK, '- [answer] (@priya) "Yes, but only for stores." ^c31')
    refusal = consent.unchanged_since_draft(edited.capture("^c31"), sealed["seen"]["^c31"])
    assert refusal is not None and "the answer changed since i wrote this down" in refusal.plain.lower()


def test_refusal_has_plain_fix_and_override():
    rec = opened(READBACK, '- [answer] (@priya) "ok" ^c31', "- [why] (claude) simpler ^c32")
    refusals = [consent.exists("^c99", rec), consent.from_a_person(rec.capture("^c30")),
                consent.not_bare_non_yes(rec.capture("^c31")),
                consent.after_readback(rec.capture("^c30"), rec.capture("^c31")), consent.group_small_enough(9),
                consent.why_in_their_words("^c32", rec), consent.after_send_notice(rec.capture("^c31"), 40),
                consent.unchanged_since_draft(rec.capture("^c31"), "0" * 64)]
    for refusal in refusals:
        assert isinstance(refusal, say.Refusal)
        shaped = refusal.as_json()
        assert shaped["refused"] is True and shaped["rule"] and shaped["plain"] and shaped["fix"] and shaped["override"]
        assert say.leak_in(refusal.plain) is None, refusal.plain


def test_bare_non_yes_words_come_from_closegate():
    """One list of bare non-yes words in the codebase: consent reads closegate's, it never keeps its own."""
    from vela import closegate
    assert not hasattr(consent, "BARE_NON_YES") or consent.BARE_NON_YES is closegate.BARE_NON_YES


def test_unknown_kind_refused_plainly():
    module, refusal = decisions.kind_module("allocate")  # in KINDS, no module built (the kind was dropped)
    assert module is None and refusal.plain == "I can't file that kind of decision yet."
    module, refusal = decisions.kind_module("frobnicate")
    assert module is None and "kind of decision" in refusal.plain and refusal.fix and refusal.override


def test_kind_module_with_a_broken_import_is_a_bug_not_not_yet(monkeypatch):
    def boom(name):
        raise ModuleNotFoundError("No module named 'yaml'", name="yaml")
    monkeypatch.setattr(decisions.importlib, "import_module", boom)
    with pytest.raises(ModuleNotFoundError):
        decisions.kind_module("allocate")


def test_kinds_and_module_names():
    assert schema.KINDS == ("marks", "add", "ledger", "decide", "agenda", "override", "defer", "resolve", "allocate",
                            "release", "handoff", "challenge")
    assert schema.module_name("ledger") == "ledger_rows" and schema.module_name("decide") == "decide"


def test_file_shape_is_checked_before_any_kind_runs():
    _, refusals = decisions.load('{"version": 2, "kind": "decide", "session": "x", "items": []}')
    assert refusals and "newer" in refusals[0].plain
    _, refusals = decisions.load("{not json")
    assert refusals and refusals[0].rule == "decision-file-json"
    _, refusals = decisions.load('{"version": 1, "kind": "decide", "session": "x", "items": {}}')
    assert refusals


def test_unfilled_judgment_field_and_unknown_field_refused(monkeypatch):
    kind = types.ModuleType("vela.decisions.note")
    kind.SCHEMA = schema.KindSchema(fields={"page": "the page", "yes": "the lead's yes"}, judgment=("yes",),
                                    required=("page", "yes"), example={"page": "x.md", "yes": "^c31"})
    monkeypatch.setitem(sys.modules, "vela.decisions.note", kind)
    monkeypatch.setattr(schema, "KINDS", schema.KINDS + ("note",))
    refusals = decisions.shape_refusals(kind.SCHEMA, {"page": "x.md", "yes": None, "yse": "^c31"}, 0)
    rules = {r.rule for r in refusals}
    assert rules == {"decision-unfilled", "decision-unknown-field"}


def test_draft_item_leaves_judgment_null_with_a_hint():
    kind_schema = schema.KindSchema(fields={"page": "the page", "yes": "the capture holding the lead's yes"},
                                    judgment=("yes",), required=("page", "yes"), example={})
    item = schema.draft_item(kind_schema, {"page": "x.md"})
    assert item == {"page": "x.md", "yes": None, "hints": {"yes": "the capture holding the lead's yes"}}


def test_draft_path_numbers_in_sequence():
    assert schema.draft_path("2026-10-20-x", ["01-marks.json", "02-decide.json"], "ledger") == \
        ".vela/decisions/2026-10-20-x/03-ledger.json"
