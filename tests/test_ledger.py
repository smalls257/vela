"""The question ledger: row grammar, evidence per state, wildcards and initiative rows, and
`planner questions`.

Each broken-copy test edits one row of the fixture ledger, renders, and expects exactly one
finding, so a rule that fires on the wrong thing shows up as an extra finding."""
import json
import shutil

import pytest

from conftest import REPO, check, edit, findings, run
from vela import cli, ledger, questions

FIXTURE = REPO / "examples" / "unified-booking"
LEDGER = "11-unknowns-and-risks.md"
TODAY = "2026-11-20"


@pytest.fixture
def ub(tmp_path):
    dest = tmp_path / "unified-booking"
    shutil.copytree(FIXTURE, dest)
    return dest


def broken(vault, allow=()):
    """Every finding as (code, path), less the codes in `allow`. A test that breaks the whole ledger
    allows W809 and says so with `untyped_warns`."""
    code, out = run("render", "--vault", str(vault))
    assert code == 0, out
    return [f for f in findings(check(vault, TODAY)[1]) if f[0] not in allow]


def untyped_warns(vault):
    """A ledger that disposes of nothing leaves Q-REG-02 unanswered, so the cost page's licenses warn."""
    assert ("W809", "08-concerns/concern-cost.md") in findings(check(vault, TODAY)[1])


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
    assert vias["Q-DAT-02@APP-website"] == "Q-DAT-02@APP-*"
    assert vias["Q-DAT-02@APP-pricing"] == "", "an exception takes its own row"
    assert vias["Q-OPS-03@CAP-012"] == "Q-OPS-03@INI-002"
    assert vias["Q-OPS-03@CAP-014"] == "", "an own row beats an initiative row that covers"


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
    ("| answered | item: [[customer-identity-building-blocks#CON-005 Customer lookup\\|CON-005]]; source: SRC-07; answer: Booking becomes a new user of customer data, through the Customer lookup contract CON-005 |",
     "| answered | item: [[customer-identity-building-blocks#CON-005 Customer lookup\\|CON-005]]; answer: Booking becomes a new user of customer data, through the Customer lookup contract CON-005 |", "answered needs source"),
    ("| answered | item: [[customer-identity-building-blocks#CON-005 Customer lookup\\|CON-005]]; source: SRC-07; answer: Booking becomes a new user of customer data, through the Customer lookup contract CON-005 |",
     "| answered | item: [[customer-identity-building-blocks#CON-005 Customer lookup\\|CON-005]]; source: SRC-07 |", "answered needs answer"),
    ("| answered | item: [[customer-identity-building-blocks#CON-005 Customer lookup\\|CON-005]]; source: SRC-07; answer: Booking becomes a new user of customer data, through the Customer lookup contract CON-005 |",
     "| answered | item: [[customer-identity-building-blocks#CON-005 Customer lookup\\|CON-005]]; source: SRC-07; answer: Booking becomes a new user of customer data, through the Customer lookup contract CON-005; reason: x |", "reason: does not belong on a row that is answered"),
    ("| answered | item: [[customer-identity-building-blocks#CON-005 Customer lookup\\|CON-005]]; source: SRC-07; answer: Booking becomes a new user of customer data, through the Customer lookup contract CON-005 |",
     '| answered | item: [[customer-identity-building-blocks#CON-005 Customer lookup\\|CON-005]]; source: "Customers pay in cash." in [[concern-data]] SRC-07; answer: Booking becomes a new user of customer data, through the Customer lookup contract CON-005 |',
     "source must be exactly one SRC-nn, or exactly one quote"),
    ("| answered | item: [[customer-identity-building-blocks#CON-005 Customer lookup\\|CON-005]]; source: SRC-07; answer: Booking becomes a new user of customer data, through the Customer lookup contract CON-005 |",
     '| answered | item: [[customer-identity-building-blocks#CON-005 Customer lookup\\|CON-005]]; source: "SRC-07 says customers pay in cash" in [[concern-data]]; answer: Booking becomes a new user of customer data, through the Customer lookup contract CON-005 |',
     "is not in the written text of [[concern-data]]"),
    ("| answered | item: [[customer-identity-building-blocks#CON-005 Customer lookup\\|CON-005]]; source: SRC-07; answer: Booking becomes a new user of customer data, through the Customer lookup contract CON-005 |",
     "| answered | item: [[customer-identity-building-blocks#CON-005 Customer lookup\\|CON-005]]; source: I made this up, see SRC-07; answer: Booking becomes a new user of customer data, through the Customer lookup contract CON-005 |",
     "source must be exactly one SRC-nn, or exactly one quote"),
    ("| answered | item: [[customer-identity-building-blocks#CON-005 Customer lookup\\|CON-005]]; source: SRC-07; answer: Booking becomes a new user of customer data, through the Customer lookup contract CON-005 |",
     "| answered | source: SRC-07; answer: Booking becomes a new user of customer data, through the Customer lookup contract CON-005 |", "answered needs item"),
    ("| answered | item: [[customer-identity-building-blocks#CON-005 Customer lookup\\|CON-005]]; source: SRC-07; answer: Booking becomes a new user of customer data, through the Customer lookup contract CON-005 |",
     "| answered | item: [[customer-identity-building-blocks#CON-005 Customer lookup\\|CON-005]]; source: SRC-99; answer: Booking becomes a new user of customer data, through the Customer lookup contract CON-005 |",
     "source SRC-99 is not a row in sources.md"),
    ("load-bearing: no; signpost: procurement's renewal notice each autumn", "load-bearing: maybe; signpost: x",
     "load-bearing: yes or no"),
    ("load-bearing: no; signpost: procurement's renewal notice each autumn", "load-bearing: no", "assumed needs signpost"),
    ("| Q-OPS-06@INI-002 | unknown | unknown: [[#UNK-006 Finance on Booking events\\|UNK-006]] |",
     "| Q-OPS-06@INI-002 | unknown | unknown: finance |", "unknown needs unknown"),
    ("| Q-OPS-06@INI-002 | unknown | unknown: [[#UNK-006 Finance on Booking events\\|UNK-006]] |",
     "| Q-OPS-06@INI-002 | unknown | unknown: UNK-099 |", "UNK-099 is not an unknown in this vault"),
    ("| Q-OPS-06@INI-002 | unknown | unknown: [[#UNK-006 Finance on Booking events\\|UNK-006]] |",
     "| Q-OPS-06@INI-002 | unknown | unknown: [[#UNK-007 Booking on-call\\|UNK-007]] |", "UNK-007 is resolved; record the answer"),
    ("| Q-REG-01@INI-002 | not-applicable | reason: Booking sells single ferry crossings, and nothing is sold with another party |",
     "| Q-REG-01@INI-002 | not-applicable |  |", "not-applicable needs reason"),
    ('quote: "because points are earned at reservation" in [[04a-capability-delta]]',
     'quote: because points are earned at reservation', 'quote must be "<the words>" in [[<page>]]'),
])
def test_a_state_without_its_evidence_is_e802(ub, old, new, said):
    edit(ub / LEDGER, old, new)
    assert broken(ub) == [("E802", LEDGER)]
    assert said in check(ub, TODAY)[1]


GOOD_QUOTE = ('source: "The only personal data is the customer ID." in [[concern-data]]')
ROW_QUOTE = ('source: "Notifications resolves contact details at send time from Customer identity." in [[concern-data]]')


@pytest.mark.parametrize("quote, said", [
    ('source: "notifications RESOLVES contact   details at send time from *Customer identity*" in [[concern-data\\|Data]]', None),
    ('source: "Finance should read Booking events instead of FERRYMASTER?" in [[11-unknowns-and-risks]]',
     'is not in the written text of [[11-unknowns-and-risks]]'),
    ('source: "Should the finance reconciliation job read Booking events instead of FERRYMASTER?" in [[11-unknowns-and-risks]]', None),
    ('source: "Catalog v1 owes these questions. Each row says where one stands." in [[11-unknowns-and-risks]]', 'is not in the written text of [[11-unknowns-and-risks]]'),
    ('source: "customer identity." in [[concern-data]]', "fewer than 4 words"),
    ('source: "gives 8 weeks\u2019 notice of changes" in [[concern-ownership]]', None),
    ('source: "The only personal data is the customer ID."', 'source must be exactly one SRC-nn, or exactly one quote'),
    ('source: "Customers pay in cash today." in [[concern-data]]', 'is not in the written text of [[concern-data]]'),
    ('source: "CAP-013 Reserve a crossing (replace)" in [[04a-capability-delta]]', 'is not in the written text of [[04a-capability-delta]]'),
])
def test_a_quoted_source_must_name_its_page_and_be_on_it(ub, quote, said):
    edit(ub / LEDGER, ROW_QUOTE, quote)
    if said is None:
        assert broken(ub) == []
        return
    assert broken(ub) == [("E802", LEDGER)]
    assert said in check(ub, TODAY)[1]


def test_a_quote_on_a_page_that_is_not_in_the_vault_is_refused():
    vault = cli.load_vault(FIXTURE)
    said = questions.quote_problem(vault, '"The only personal data is the customer ID." in [[concern-nope]]', "source")
    assert said == "source cites [[concern-nope]], which is not a page in this vault"


def test_only_hand_written_body_text_can_be_quoted():
    vault = cli.load_vault(FIXTURE)
    text = questions.normal_text(questions.quotable_text(vault.page("04a-capability-delta")))
    assert "every capability this initiative changes" in text
    assert "reserve a crossing (replace)" not in text, "a generated block is not hand-written"
    assert "initiative: ini-002" not in text, "frontmatter is not body text"
    ledger_text = questions.normal_text(questions.quotable_text(vault.page("11-unknowns-and-risks")))
    assert "should the finance reconciliation job" in ledger_text and "q-fin-02@ini-002" not in ledger_text


def test_every_quote_in_the_fixture_ledger_is_on_its_page():
    vault = cli.load_vault(FIXTURE)
    quoted = [(r, key, r.get(key)) for r in questions.rows(vault) for key in ("source", "quote")
              if r.get(key).startswith('"')]
    assert len(quoted) >= 10, "the fixture shows quoted evidence"
    assert [(r.copy, key) for r, key, value in quoted if questions.quote_problem(vault, value, key)] == []


def test_a_semicolon_inside_a_quote_or_a_link_does_not_split_the_evidence():
    pairs, problems = ledger.split_evidence('source: "one; two"; item: [[a#b; c\\|d]]')
    assert problems == [] and pairs == (("source", '"one; two"'), ("item", "[[a#b; c\\|d]]"))


# ------------------------------------------------------------------ E803 and W804: what a row names

@pytest.mark.parametrize("old, new, code, said", [
    ("| Q-REG-01@INI-002 |", "| Q-REG-09@INI-002 |", "E803", "Q-REG-09, which is not in catalog v1"),
    ("| Q-DAT-03@CON-002 |", "| Q-DAT-03@APP-booking |", "E803", "which is not a contract ID"),
    ("| Q-DAT-02@APP-* |", "| Q-DAT-02@CON-* |", "E803", "so it must start Q-DAT-02@APP-"),
    ("| R-FIN-01 | open | question:", "| R-XYZ-01 | open | question:", "E803", "names area XYZ"),
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
    assert row_of(ub, "Q-PTN-02@PTY-01").state == "assumed"


# ------------------------------------------------------------------ dispositions

def drop_row(vault, prefix):
    path = vault / LEDGER
    kept = [l for l in path.read_text(encoding="utf-8").split("\n") if not l.startswith(prefix)]
    path.write_text("\n".join(kept), encoding="utf-8")


def test_a_copy_with_no_row_is_undisposed_and_never_a_finding(ub):
    drop_row(ub, "| Q-DAT-02@APP-* |")
    assert broken(ub) == []
    code, answer = ask(ub, "--open")
    assert code == 0 and answer["undisposed"] == 3
    assert [c["id"] for c in answer["copies"]] == ["Q-DAT-02@APP-call-center", "Q-DAT-02@APP-kiosks", "Q-DAT-02@APP-website",
                                                   "Q-FIN-02@INI-002"]  # the fixture's asked copy, still pending
    assert [c["state"] for c in answer["copies"]] == ["no row"] * 3 + ["asked"] and all(c["pending"] for c in answer["copies"])


def test_a_row_with_an_error_disposes_of_nothing(ub):
    edit(ub / LEDGER, "; answer: Finance owns the points, through INI-004 Loyalty Revamp |", " |")
    assert broken(ub) == [("E802", LEDGER)]
    code, answer = ask(ub)
    copy = next(c for c in answer["copies"] if c["id"] == "Q-FIN-03@SV-01")
    assert copy["valid"] is False and copy["state"] == "answered" and copy["pending"]
    assert answer["undisposed"] == 1 and answer["coverage"].startswith("57 owed, 1 undisposed")
    assert [c["id"] for c in ask(ub, "--open")[1]["copies"]] == ["Q-FIN-02@INI-002", "Q-FIN-03@SV-01"]
    _, out = run("questions", "--vault", str(ub))
    assert "Q-FIN-03@SV-01 | FIN | high | unreadable row (answered) | SV-01 | not linked to an item yet |" in out


def test_a_broken_exception_is_not_quietly_replaced_by_its_wildcard(ub):
    edit(ub / LEDGER, "reason: Pricing holds fare rules only, per the Data concern, so it holds no customer data", "reason:")
    vault = cli.load_vault(ub)
    d = next(d for d in questions.dispositions(vault) if d.copy.id == "Q-DAT-02@APP-pricing")
    assert d.row.copy == "Q-DAT-02@APP-pricing" and not d.valid and d.undisposed


def test_the_longest_wildcard_wins_and_an_own_row_beats_both(ub):
    edit(ub / LEDGER, "| Q-DAT-02@APP-booking |", "| Q-DAT-02@APP-book* |")
    vault = cli.load_vault(ub)
    via = {d.copy.id: d.via for d in questions.dispositions(vault)}
    assert via["Q-DAT-02@APP-booking"] == "Q-DAT-02@APP-book*" and via["Q-DAT-02@APP-kiosks"] == "Q-DAT-02@APP-*"


# ------------------------------------------------------------------ planner questions

def test_planner_questions_prints_the_coverage_line_and_one_line_per_copy():
    code, out = run("questions", "--vault", str(FIXTURE))
    lines = out.splitlines()
    assert code == 0
    assert lines[0] == ("planner questions: 57 standard questions apply, 0 not dealt with yet, 1 asked but not answered, "
                        "1 open reviewer question (question catalog v1). 1 reviewer question, 1 open.")
    assert "complete" not in out.lower()
    assert len(lines) == 59
    assert "Q-DAT-02@APP-website | DAT | high | answered by assumption through Q-DAT-02@APP-* | APP-website | dealt with | What customer data" in out
    assert lines[-1].startswith("R-FIN-01 | FIN | normal | open | reviewer | not linked to an item yet | Points are earned")


def test_planner_questions_filters_by_area_and_subject():
    code, answer = ask(FIXTURE, "--area", "PTN")
    assert code == 0 and {c["area"] for c in answer["copies"]} == {"PTN"} and answer["owed"] == 9
    assert answer["reviewer"] == []
    code, answer = ask(FIXTURE, "--subject", "SV-01")
    assert [c["id"] for c in answer["copies"]] == ["Q-DAT-04@SV-01", "Q-FIN-03@SV-01", "Q-FIN-04@SV-01", "Q-FIN-05@SV-01", "Q-FIN-06@SV-01"]
    assert answer["coverage"] == "5 owed, 0 undisposed, against catalog v1"


def test_planner_questions_json_holds_every_field():
    _, answer = ask(FIXTURE)
    copy = next(c for c in answer["copies"] if c["id"] == "Q-PTN-02@PTY-02")
    assert copy == {"id": "Q-PTN-02@PTY-02", "entry": "Q-PTN-02", "area": "PTN", "severity": "high",
                    "question": copy["question"], "subject": "PTY-02", "subject_kind": "party",
                    "subject_page": "03-context-and-scope.md", "state": "assumed", "valid": True,
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


# ------------------------------------------------------------------ the ledger's own shape

@pytest.mark.parametrize("header", [
    "| Copy | Status | Evidence | By | Date |",
    "| Cpy | State | Evidence | By | Date |",
    "| Copy ID | State | Evidence | By | Date |",
    "| **Copy** | State | Evidence | By | Date |",
    "| copy | State | Evidence | By | Date |",
    "| Copy | Evidence | State | By | Date |",
    "| Copy | State | Evidence | By |",
    "| Copy | State | Evidence | By | Date | Notes |",
])
def test_a_ledger_header_that_is_not_exact_is_e801_and_never_hides_the_ledger(ub, header):
    edit(ub / LEDGER, "| Copy | State | Evidence | By | Date |\n|---|---|---|---|---|", header + "\n|---|---|---|---|---|")
    assert broken(ub, allow=("W809", "W366")) == [("E801", LEDGER)]
    untyped_warns(ub)
    assert "is headed" in check(ub, TODAY)[1] and "not exactly" in check(ub, TODAY)[1]


def test_a_ledger_table_must_sit_directly_under_the_ledger_heading(ub):
    edit(ub / LEDGER, "| Copy | State | Evidence | By | Date |\n", "## Notes\n\n| Copy | State | Evidence | By | Date |\n")
    assert broken(ub, allow=("W809", "W366")) == [("E801", LEDGER)]
    untyped_warns(ub)
    assert "must sit under ## Question ledger" in check(ub, TODAY)[1]


def test_a_second_ledger_heading_is_e801(ub):
    path = ub / LEDGER
    path.write_text(path.read_text(encoding="utf-8") + "\n## Question ledger\n", encoding="utf-8")
    assert broken(ub) == [("E801", LEDGER)]
    assert "appears twice" in check(ub, TODAY)[1]


def test_a_fully_shadowed_wildcard_is_w804(ub):
    path = ub / LEDGER
    text = path.read_text(encoding="utf-8")
    wild = next(l for l in text.split("\n") if l.startswith("| Q-DAT-02@APP-* |"))
    own = "\n".join(wild.replace("Q-DAT-02@APP-*", f"Q-DAT-02@{app}", 1) for app in ("APP-website", "APP-call-center", "APP-kiosks"))
    path.write_text(text.replace(wild, wild + "\n" + own), encoding="utf-8")
    assert [f for f in broken(ub) if f[0] == "W804"] == [("W804", LEDGER)]
    assert "Q-DAT-02@APP-* is shadowed" in check(ub, TODAY)[1]


def test_a_wildcard_on_an_initiative_entry_is_w804(ub):
    edit(ub / LEDGER, "| Q-PTN-01@INI-002 |", "| Q-PTN-01@INI-* |")
    assert [f for f in broken(ub) if f[0] == "W804"] == [("W804", LEDGER)]
    assert "is a wildcard on an initiative entry" in check(ub, TODAY)[1]


def test_a_row_dated_after_today_is_w812(ub):
    edit(ub / LEDGER, "| @hl-solution-lead | 2026-11-19 |\n| Q-FIN-03@SV-01", "| @hl-solution-lead | 2026-12-01 |\n| Q-FIN-03@SV-01")
    assert broken(ub) == [("W812", LEDGER)]


def test_a_reviewer_quote_is_checked_against_its_page_too(ub):
    edit(ub / LEDGER, 'quote: "because points are earned at reservation" in [[04a-capability-delta]]',
         'quote: "because points are earned at booking" in [[04a-capability-delta]]')
    assert broken(ub) == [("E802", LEDGER)]
    assert 'quote "because points are earned at booking" is not in the written text' in check(ub, TODAY)[1]


def test_rows_of_a_misplaced_table_are_read_but_dispose_of_nothing(ub):
    edit(ub / LEDGER, "| Copy | State | Evidence | By | Date |\n", "## Notes\n\n| Copy | State | Evidence | By | Date |\n")
    assert broken(ub, allow=("W809", "W366")) == [("E801", LEDGER)]
    untyped_warns(ub)
    code, answer = ask(ub)
    assert code == 0 and answer["undisposed"] == 57 and not any(c["valid"] for c in answer["copies"] if c["row"])
    assert answer["reviewer_open"] == 1


def test_rows_under_a_second_ledger_heading_dispose_of_nothing(ub):
    path = ub / LEDGER
    text = path.read_text(encoding="utf-8")
    start = text.index("| Copy | State | Evidence")
    path.write_text(text[:start].rstrip("\n") + "\n\n## Question ledger\n\n" + text[start:], encoding="utf-8")
    found = sorted(set(f[0] for f in broken(ub, allow=("W809",))))
    assert found == ["E801"]
    untyped_warns(ub)
    assert "appears twice" in check(ub, TODAY)[1] and "must sit under" in check(ub, TODAY)[1]
    assert ask(ub)[1]["undisposed"] == 57


def test_a_glossary_table_headed_copy_on_another_page_is_not_a_ledger(ub):
    path = ub / "12-glossary.md"
    path.write_text(path.read_text(encoding="utf-8") + "\n| Copy ID | Meaning |\n|---|---|\n| Q-X | a glossary row |\n", encoding="utf-8")
    assert broken(ub) == []


def test_an_unknown_named_twice_in_one_row_is_reported_once(ub):
    edit(ub / LEDGER, "| Q-OPS-06@INI-002 | unknown | unknown: [[#UNK-006 Finance on Booking events\\|UNK-006]] |",
         "| Q-OPS-06@INI-002 | unknown | unknown: UNK-007 and UNK-007 again |")
    assert broken(ub) == [("E802", LEDGER)]
    assert check(ub, TODAY)[1].count("UNK-007 is resolved; record the answer") == 1
