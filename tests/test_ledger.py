"""The question ledger: row grammar, evidence per state, wildcards and initiative rows, and
`planner questions`.

Each broken-copy test edits one row of the fixture ledger, renders, and expects exactly one
finding, so a rule that fires on the wrong thing shows up as an extra finding."""
import json
import shutil

import pytest

from conftest import REPO, check, edit, findings, run
from planner import cli, ledger, questions

FIXTURE = REPO / "examples" / "unified-booking"
LEDGER = "11-unknowns-and-risks.md"
TODAY = "2026-11-20"


@pytest.fixture
def ub(tmp_path):
    dest = tmp_path / "unified-booking"
    shutil.copytree(FIXTURE, dest)
    return dest


def broken(vault):
    code, out = run("render", "--vault", str(vault))
    assert code == 0, out
    return findings(check(vault, TODAY)[1])


def row_of(vault, copy):
    return next(r for r in questions.rows(cli.load_vault(vault)) if r.copy == copy)


def ask(vault, *extra):
    code, out = run("questions", "--vault", str(vault), "--json", *extra)
    return code, json.loads(out)


# ------------------------------------------------------------------ the fixture's ledger

def test_the_fixture_ledger_is_realistic_and_leaves_nothing_undisposed():
    vault = cli.load_vault(FIXTURE)
    states = {r.state for r in questions.rows(vault)}
    assert states == set(ledger.STATES), "the example shows every state"
    kinds = {r.kind for r in questions.rows(vault)}
    assert kinds == {"copy", "wildcard", "reviewer"}
    assert any(r.has("covers") for r in questions.rows(vault)), "the example shows an initiative row"
    assert not [d.copy.id for d in questions.dispositions(vault) if d.undisposed]
    vias = {d.copy.id: d.via for d in questions.dispositions(vault)}
    assert vias["Q-DAT-02@APP-booking"] == "Q-DAT-02@APP-*"
    assert vias["Q-DAT-02@APP-pricing"] == "", "an exception takes its own row"
    assert vias["Q-OPS-03@CAP-014"] == "Q-OPS-03@INI-002"


def test_the_fixture_is_clean_with_its_ledger():
    code, out = check(FIXTURE, TODAY)
    assert code == 0 and findings(out) == [], out


# ------------------------------------------------------------------ E801: row shape

@pytest.mark.parametrize("old, new, said", [
    ("| Q-REG-01@INI-002 | not-applicable |", "| Q-REG-01@INI-002 | n/a |", "state 'n/a' is not one of"),
    ("| Q-REG-01@INI-002 | not-applicable |", "| q-reg-01@ini-002 | not-applicable |", "is not a copy ID"),
    ("nothing is sold with another party | @hl-solution-lead | 2026-11-19 |",
     "nothing is sold with another party | hl-solution-lead | 2026-11-19 |", "By 'hl-solution-lead' is not a handle"),
    ("nothing is sold with another party | @hl-solution-lead | 2026-11-19 |",
     "nothing is sold with another party | @hl-solution-lead | 2026-02-30 |", "Date '2026-02-30' is not a real"),
    ("nothing is sold with another party | @hl-solution-lead | 2026-11-19 |",
     "nothing is sold with another party | @hl-solution-lead |", "it has 4 cells"),
    ("| Q-REG-01@INI-002 | not-applicable | reason:", "| Q-REG-01@INI-002 | not-applicable | why:", "Evidence key 'why'"),
    ("| Q-REG-01@INI-002 | not-applicable | reason: Booking", "| Q-REG-01@INI-002 | not-applicable | reason: \"Booking",
     "never closed"),
    ("| Q-REG-01@INI-002 | not-applicable | reason: Booking sells", "| Q-REG-01@INI-002 | not-applicable | quote: x; reason: Booking sells",
     "belongs on a reviewer question row"),
])
def test_a_malformed_row_is_e801(ub, old, new, said):
    edit(ub / LEDGER, old, new)
    assert broken(ub) == [("E801", LEDGER)]
    assert said in check(ub, TODAY)[1]


def test_two_rows_for_one_copy_is_e801(ub):
    row = "| Q-REG-01@INI-002 | not-applicable | reason: Booking sells single ferry crossings, and nothing is sold with another party | @hl-solution-lead | 2026-11-19 |\n"
    edit(ub / LEDGER, row, row + row)
    assert broken(ub) == [("E801", LEDGER)]
    assert "it is also a row at line" in check(ub, TODAY)[1]


def test_an_open_row_needs_no_by_or_date(ub):
    edit(ub / LEDGER, "| Q-REG-01@INI-002 | not-applicable | reason: Booking sells single ferry crossings, and nothing is sold "
         "with another party | @hl-solution-lead | 2026-11-19 |", "| Q-REG-01@INI-002 | open |  |  |  |")
    assert broken(ub) == []


# ------------------------------------------------------------------ E802: evidence per state

@pytest.mark.parametrize("old, new, said", [
    ("| asked | capture: [[2026-11-19-owed-questions#^c01]] |", "| asked | capture: by email |", "asked needs capture"),
    ("| answered | item: [[customer-identity-building-blocks#CON-005 Customer lookup\\|CON-005]]; source: SRC-07 |",
     "| answered | item: [[customer-identity-building-blocks#CON-005 Customer lookup\\|CON-005]] |", "answered needs source"),
    ("| answered | item: [[customer-identity-building-blocks#CON-005 Customer lookup\\|CON-005]]; source: SRC-07 |",
     "| answered | source: SRC-07 |", "answered needs item"),
    ("| answered | item: [[customer-identity-building-blocks#CON-005 Customer lookup\\|CON-005]]; source: SRC-07 |",
     "| answered | item: [[customer-identity-building-blocks#CON-005 Customer lookup\\|CON-005]]; source: SRC-99 |",
     "source SRC-99 is not a row in sources.md"),
    ("load-bearing: no; signpost: procurement's renewal notice each autumn", "load-bearing: maybe; signpost: x",
     "load-bearing: yes or no"),
    ("load-bearing: no; signpost: procurement's renewal notice each autumn", "load-bearing: no", "assumed needs signpost"),
    ("| Q-OPS-06@INI-002 | unknown | unknown: [[#UNK-006 Finance on Booking events\\|UNK-006]] |",
     "| Q-OPS-06@INI-002 | unknown | unknown: finance |", "unknown needs unknown"),
    ("| Q-OPS-06@INI-002 | unknown | unknown: [[#UNK-006 Finance on Booking events\\|UNK-006]] |",
     "| Q-OPS-06@INI-002 | unknown | unknown: UNK-099 |", "UNK-099 is not an unknown in this vault"),
    ("| Q-REG-01@INI-002 | not-applicable | reason: Booking sells single ferry crossings, and nothing is sold with another party |",
     "| Q-REG-01@INI-002 | not-applicable |  |", "not-applicable needs reason"),
    ('quote: "because points are earned at reservation" in [[04a-capability-delta]]',
     'quote: because points are earned at reservation', "a reviewer question needs quote"),
])
def test_a_state_without_its_evidence_is_e802(ub, old, new, said):
    edit(ub / LEDGER, old, new)
    assert broken(ub) == [("E802", LEDGER)]
    assert said in check(ub, TODAY)[1]


def test_a_semicolon_inside_a_quote_or_a_link_does_not_split_the_evidence():
    pairs, problems = ledger.split_evidence('source: "one; two"; item: [[a#b; c\\|d]]')
    assert problems == [] and pairs == (("source", '"one; two"'), ("item", "[[a#b; c\\|d]]"))


# ------------------------------------------------------------------ E803 and W804: what a row names

@pytest.mark.parametrize("old, new, code, said", [
    ("| Q-REG-01@INI-002 |", "| Q-REG-09@INI-002 |", "E803", "Q-REG-09, which is not in catalogue v1"),
    ("| Q-DAT-03@CON-002 |", "| Q-DAT-03@APP-booking |", "E803", "which is not a contract ID"),
    ("| Q-OPS-01@APP-* |", "| Q-OPS-01@CON-* |", "E803", "so it must start Q-OPS-01@APP-"),
    ("| R-FIN-01 |", "| R-XYZ-01 |", "E803", "names area XYZ"),
    ("| Q-DAT-03@CON-002 |", "| Q-DAT-03@CON-099 |", "W804", "is orphaned: CON-099 is no longer in the vault"),
    ("| Q-DAT-02@APP-pricing |", "| Q-DAT-02@APP-ferrymaster |", "W804", "no longer matches the trigger 'change in [new, changed]'"),
    ("| Q-OPS-03@INI-002 |", "| Q-OPS-03@CAP-012 |", "E803", "covers: belongs on an initiative row such as Q-OPS-03@INI-002"),
])
def test_a_row_that_names_nothing_owed(ub, old, new, code, said):
    edit(ub / LEDGER, old, new)
    got = [f for f in broken(ub) if f[0] in ("E803", "W804")]
    assert got == [(code, LEDGER)]
    assert said in check(ub, TODAY)[1]


def test_an_initiative_row_needs_covers_with_its_scope(ub):
    edit(ub / LEDGER, "; covers: capability |", "; covers: app |")
    assert broken(ub) == [("E803", LEDGER)]
    assert "so it needs covers: capability" in check(ub, TODAY)[1]


def test_removing_a_subject_orphans_its_rows_and_never_drops_them(ub):
    text = (ub / "03-context-and-scope.md").read_text(encoding="utf-8")
    start, end = text.index("### PTY-01 Tidepay"), text.index("### PTY-02 FERRYMASTER vendor")
    (ub / "03-context-and-scope.md").write_text(text[:start] + text[end:], encoding="utf-8")
    got = sorted(set(f for f in broken(ub) if f[0] == "W804"))
    out = check(ub, TODAY)[1]
    assert got == [("W804", LEDGER)]
    assert out.count("is orphaned: PTY-01 is no longer in the vault") == 3
    assert row_of(ub, "Q-PTN-02@PTY-01").state == "answered"


# ------------------------------------------------------------------ dispositions

def test_a_copy_with_no_row_is_undisposed_and_never_a_finding(ub):
    edit(ub / LEDGER, "| Q-OPS-02@CON-* | answered | item: [[booking-runtime#When a dependency is slow or down\\|Booking runtime]]; "
         "source: SRC-04 | @hl-booking-senior | 2026-11-19 |\n", "")
    assert broken(ub) == []
    code, answer = ask(ub, "--open")
    assert code == 0 and answer["undisposed"] == 7
    assert [c["id"] for c in answer["copies"]] == [f"Q-OPS-02@CON-00{n}" for n in range(1, 8)]
    assert all(c["state"] == "no row" and c["pending"] for c in answer["copies"])


def test_the_longest_wildcard_wins_and_an_own_row_beats_both(ub):
    edit(ub / LEDGER, "| Q-OPS-01@APP-booking |", "| Q-OPS-01@APP-book* |")
    vault = cli.load_vault(ub)
    via = {d.copy.id: d.via for d in questions.dispositions(vault)}
    assert via["Q-OPS-01@APP-booking"] == "Q-OPS-01@APP-book*" and via["Q-OPS-01@APP-kiosks"] == "Q-OPS-01@APP-*"


# ------------------------------------------------------------------ planner questions

def test_planner_questions_prints_the_coverage_line_and_one_line_per_copy():
    code, out = run("questions", "--vault", str(FIXTURE))
    lines = out.splitlines()
    assert code == 0
    assert lines[0] == "planner questions: 57 owed, 0 undisposed, against catalogue v1. 1 reviewer question, 1 open."
    assert "complete" not in out.lower()
    assert len(lines) == 59
    assert "Q-DAT-02@APP-booking | DAT | high | answered via Q-DAT-02@APP-* | APP-booking | settled | What customer data" in out
    assert lines[-1].startswith("R-FIN-01 | FIN | normal | open | reviewer | blocks nothing | Points are earned")


def test_planner_questions_filters_by_area_and_subject():
    code, answer = ask(FIXTURE, "--area", "PTN")
    assert code == 0 and {c["area"] for c in answer["copies"]} == {"PTN"} and answer["owed"] == 9
    assert answer["reviewer"] == []
    code, answer = ask(FIXTURE, "--subject", "SV-01")
    assert [c["id"] for c in answer["copies"]] == ["Q-DAT-04@SV-01", "Q-FIN-03@SV-01", "Q-FIN-04@SV-01", "Q-FIN-05@SV-01", "Q-FIN-06@SV-01"]
    assert answer["coverage"] == "5 owed, 0 undisposed, against catalogue v1"


def test_planner_questions_json_holds_every_field():
    _, answer = ask(FIXTURE)
    copy = next(c for c in answer["copies"] if c["id"] == "Q-PTN-02@PTY-02")
    assert copy == {"id": "Q-PTN-02@PTY-02", "entry": "Q-PTN-02", "area": "PTN", "severity": "high",
                    "question": copy["question"], "subject": "PTY-02", "subject_kind": "party", "state": "answered",
                    "row": copy["row"], "via": None, "pending": False, "blocks": ["ADR-0002", "CON-006"]}
    assert answer["reviewer"][0]["id"] == "R-FIN-01" and answer["reviewer"][0]["subject_kind"] == "reviewer"


def test_an_unknown_area_exits_2_and_an_unknown_subject_exits_1():
    code, out = run("questions", "--vault", str(FIXTURE), "--area", "fin")
    assert code == 2 and "Use one of: FIN, DAT, PTN, REG, OPS." in out
    code, out = run("questions", "--vault", str(FIXTURE), "--subject", "APP-nope")
    assert code == 1 and "APP-nope is not a subject in this vault" in out
    code, out = run("questions", "--vault", str(FIXTURE), "--subject", "APP-nope", "--json")
    assert json.loads(out) == {"subject": "APP-nope", "not_found": True}


def test_planner_questions_writes_nothing(ub):
    before = {p: p.read_bytes() for p in ub.rglob("*") if p.is_file()}
    run("questions", "--vault", str(ub))
    run("questions", "--vault", str(ub), "--json", "--open")
    assert {p: p.read_bytes() for p in ub.rglob("*") if p.is_file()} == before


def test_a_template_vault_owes_its_initiative_questions(tmp_path):
    vault = tmp_path / "vault"
    shutil.copytree(REPO / "template", vault)
    code, answer = ask(vault)
    assert code == 0
    assert answer["owed"] == answer["undisposed"] == 12
    assert {c["subject"] for c in answer["copies"]} == {"INI-001"}


def test_a_ledger_saved_with_crlf_line_endings_still_reads(ub):
    path = ub / LEDGER
    path.write_bytes(path.read_bytes().replace(b"\r\n", b"\n").replace(b"\n", b"\r\n"))
    code, answer = ask(ub)
    assert code == 0 and answer["undisposed"] == 0
    assert findings(check(ub, TODAY)[1]) == []
