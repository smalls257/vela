"""SETTLE.md: one settle check every mode reaches through START; it keeps the read-back and never names a size."""
import re

from conftest import REPO

REFS = REPO / "plugin" / "references"
SETTLE = (REFS / "SETTLE.md").read_text(encoding="utf-8")
START = (REFS / "START.md").read_text(encoding="utf-8")
MODES = (REFS / "MODES.md").read_text(encoding="utf-8")


def test_start_points_every_mode_to_settle():
    assert "references/SETTLE.md" in START and "a grill `(decided)`" not in START


def test_settle_files_on_the_leads_word():
    for kept in ("--yes ^cM", "--later --yes ^cM", "--gate decide --item <ID> --for-lead"):
        assert kept in SETTLE, kept
    for gone in ("Still yes?", "--readback", "Why this one, in your words?"):
        assert gone not in SETTLE, gone


def test_someone_elses_item_is_settled_by_the_leads_yes_with_no_flag_or_reason():
    assert "The lead's yes settles it" in SETTLE
    assert "--on-behalf" not in SETTLE and "owner's yes is checked" not in SETTLE


def test_a_one_option_answer_goes_through_options_none():
    assert "pass the answer as `--options-none ^cN`" in SETTLE


def test_a_plain_yes_to_a_pick_gets_one_offer():
    assert "Want to settle that now, or keep it as not decided yet?" in SETTLE and "don't offer it again" in SETTLE


def test_a_hesitant_lead_is_offered_a_grill_once():
    assert "Sounds like this one's worth testing. Want a grill on it, now or later?" in SETTLE


def test_settle_names_no_size_and_types_no_stage():
    assert not re.search(r"\b(?:small|medium|large) plan\b|\bband\b|\bstage:", SETTLE, re.I)


def test_settle_stays_short():
    assert len(SETTLE.split()) <= 450


def test_no_mode_lists_writing_decided_as_a_must_not_except_epics_own_rule():
    rows = [line for line in MODES.splitlines() if line.startswith("| ") and "`decided`" in line]
    assert [r.split("|")[1].strip() for r in rows] == ["Epics (`epics`)"]
