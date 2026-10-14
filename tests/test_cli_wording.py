"""CLI wording: names before IDs, plain states, and the kept words (slice, tracer, grill) defined once on first use."""
from conftest import REPO, run

from vela import cli, handoffwarn

EXAMPLE = REPO / "examples" / "unified-booking"


def test_named_puts_the_name_first_and_keeps_the_id_as_a_tag():
    vault = cli.load_vault(EXAMPLE)
    contract = vault.contracts[0]
    assert vault.named(contract.id) == f"{contract.name} ({contract.id})"
    app = vault.apps[0]
    assert vault.named(app.id) == f"{app.meta['title']} ({app.id})"
    assert vault.named("CON-999") == "CON-999"  # nothing names it, so the ID stays the subject rather than a blank


def test_assumption_reads_not_decided_yet_never_still_assumption():
    assert handoffwarn.state_phrase("assumption") == "is not decided yet"
    assert handoffwarn.state_phrase("draft") == "is still a draft"
    assert handoffwarn.state_phrase("decided") == "is decided"


def test_each_kept_word_used_is_defined_once_in_first_use_order():
    notes = cli.term_notes(["Decide it in a grill.", "The tracer is SLC-001; the grill again.", "Two slices."])
    assert [n.split('"')[1] for n in notes] == ["grill", "tracer", "slice"]
    assert all(n.startswith('What "') for n in notes)
    assert cli.term_notes(["Nothing to define here."]) == []


def test_routine_output_does_not_repeat_definitions_but_terms_gives_them():
    _, out = run("next", "--vault", str(REPO / "tests" / "fixtures" / "team-skills" / "heron"), "--today", "2026-10-12")
    assert " grill " in out.splitlines()[0]
    assert not [line for line in out.splitlines() if line.startswith("What \"")]
    code, out = run("terms")
    assert code == 0 and [line.split('"')[1] for line in out.splitlines()] == ["grill", "slice", "tracer"]
    code, out = run("terms", "slices")
    assert code == 0 and out.startswith('What "slice" means:')
    code, out = run("terms", "lamp")
    assert code == 2 and "no definition" in out


def test_check_says_the_date_it_judged_by_in_words():
    _, out = run("check", "--vault", str(EXAMPLE), "--today", "2026-11-20")
    assert "judged as of 2026-11-20 (the date you gave)" in out.splitlines()[0] and "--today" not in out.splitlines()[0]
