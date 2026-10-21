"""The October 14 voice audit rows C92 covers (audit row C92): what the lead hears from epics, reviewers, voice,
where --probe, check --fix, terms and prose replace. Each test holds a line's shape, not just its words: the answer
before the list, a count in words, the model's own slips kept from the lead, one name for a reader's copy.
"""
import shutil
import types

from conftest import REPO, run
from vela import say
from vela.commands import check, prose, reviewers, voice, voice_settle
from vela.edge import hostprobe
from vela import prosereplace

HERON_DESK = REPO / "tests" / "sim" / "snapshots" / "heron-desk" / "after-full-1"


def test_epics_lint_answers_with_a_count_then_one_line_per_epic(tmp_path):
    """Row 181: 46 flat lines with no head line, every criterion twice. Now the count comes first, each epic is one
    line, and the default output still lists every finding for the model."""
    vault = tmp_path / "vault"
    shutil.copytree(HERON_DESK, vault, ignore=shutil.ignore_patterns(".vela"))
    code, out = run("epics", "lint", "--vault", str(vault), "--for-lead", "--more")
    lines = out.splitlines()
    assert code == 1, out
    assert lines[0].startswith(("Twenty", "23 criteria across four epics need a fix.")), out
    assert lines[1].startswith("Calendar: ") and " criteria " in lines[1], out
    assert lines[-1] == "Start with Calendar?", out
    assert len(lines) <= 7 and all(say.leak_in(line) is None for line in lines), out
    code, default = run("epics", "lint", "--vault", str(vault))
    assert default.count(".AC") >= 23  # every finding, with its ID, for the model


def test_epics_frontier_says_the_team_and_the_tracer_in_words(tmp_path):
    """Rows 183-185: no @handle, no "Still to cover: nothing", the tracer by its kept name, no "are none"."""
    code, out = run("epics", "frontier", "--team", "@agent-lead", "--vault", str(HERON_DESK), "--for-lead")
    assert "The agent lead's team has four epics with 23 criteria so far. Nothing is left to cover." in out, out
    assert "the tracer (the first slice built end to end)" in out and "thin path" not in out
    code, out = run("epics", "frontier", "--team", "@nobody", "--vault", str(HERON_DESK), "--for-lead")
    assert code == 1 and out.startswith("I don't know that team. The teams here are the agent lead's team"), out
    assert "@" not in out


def test_reviewers_skip_line_says_what_was_skipped_without_ledger_words():
    prep = types.SimpleNamespace(packets=[1, 2, 3], skipped=[types.SimpleNamespace(label="Cost")])
    (line,) = reviewers.lead_lines(prep)
    assert line.plain.endswith("I skipped cost: nothing there changed or is waiting on an answer. Want it checked "
                               "anyway?")
    assert "owed" not in line.plain


def test_voice_retire_line_says_why_in_words_with_the_date_in_words():
    example = types.SimpleNamespace(path="voice/examples/x.md", source="owner-edit", added="2026-10-01")
    plain = voice.retire_line(example, "cap").plain
    assert plain == "Saving this pushes out your oldest example, from October 1, 2026, because I keep five at most."
    assert "retire" not in voice.retire_line(example, "seed").plain


def test_voice_harvest_and_save_failures_say_no_tool_words():
    import re
    for words in (voice.HARVEST_OWNER_ONLY, voice.NO_GITHUB, voice.UNCHECKED_PR):
        assert say.leak_in(words) is None and not re.search(r"\b(?:harvest|clone|gh|git)\b", words.lower()), words


def test_voice_settle_restored_reason_reads_as_a_sentence():
    """Row 206: "because the rewrite a sentence named as redundant wasn't removed as named"."""
    ok, _, plain = voice_settle.verdict("A cat sat. The dog ran.", "A cat sat.", ["Nothing like this."])
    assert not ok and f"because the rewrite {plain}." == "because the rewrite didn't take out the sentence it was meant to."


def test_where_with_no_git_says_the_stance_once_and_nothing_under_it():
    """Rows 213 and 216: the stance said git couldn't be used while the row under it said git runs."""
    row, said = hostprobe.stance({"python": "3.12.1", "git": "no", "git_repo": False})
    assert row == "no-git" and said.startswith("This folder isn't set up with git, so sessions are recorded")
    row, said = hostprobe.stance({"python": "3.8.10", "git": "yes", "git_repo": True})
    assert row == "no-git" and "Python is too old" in said
    assert hostprobe.stance({"reader": True})[1].startswith(say.YOUR_COPY)


def test_check_fix_refusal_and_change_line_speak_the_leads_words():
    args = types.SimpleNamespace(fix="W390", gate=None, item=None, app=None)
    (refusal,) = check.fix_refusal(args).refusals
    assert "lags its rows" not in refusal.plain and refusal.waiver_words() == ""
    change = types.SimpleNamespace(path="01-goals.md", line=7, before="assumption", after="decided", why="x",
                                   page="goals")
    resolver = types.SimpleNamespace(page_title=lambda _: "Goals", name=lambda _: "Goals")
    plain = check.changed_line(change, resolver).plain
    assert plain == "Goals is now marked decided, to match what's on it. It said not decided yet before."


def test_terms_names_the_words_without_calling_them_kept():
    code, out = run("terms", "x")
    assert code == 2 and out.strip() == "vela terms: 'x' isn't one of Vela's own words. Those are grill, slice and tracer."


def test_a_line_that_holds_no_paragraph_is_the_models_slip():
    """Row 224: a line number and "frontmatter" reached the lead for a line the model picked."""
    miss = prosereplace.Miss("no paragraph", "Line 2 is in the page's frontmatter, not its prose.")
    result = prose.refused(miss)
    assert result.refusals[0].audience == say.MODEL
    assert say.render(result, "for-lead") == say.MY_SIDE
    generated = prose.refused(prosereplace.Miss("generated block", "Line 9 is in a block vela writes."))
    assert say.render(generated, "for-lead") == "That's not a paragraph anyone wrote, so there's nothing to keep."


def test_a_readers_copy_has_one_name_in_what_the_lead_hears():
    """Row 215: "read copy", "reader copy", "reading copy" and "published copy" across seven commands."""
    import re
    lib = REPO / "plugin" / "lib" / "vela"
    old = re.compile(r"plain=\"This is a (?:read|reader|reading|published) copy|\"This is a (?:read|reading) copy, ")
    hits = [f"{p.relative_to(lib)}" for p in lib.rglob("*.py") if old.search(p.read_text(encoding="utf-8"))]
    assert hits == [], hits
