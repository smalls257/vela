"""The `ledger` apply kind (overhaul Task 17): close/LEDGER.md's question-ledger rows as code. One row per copy, an `R-`
number past every open branch, evidence by state, and a `## Changes` row for each. Each test is a rule the skill's
prose held before; a deleted rule fails here by name."""
import json

from conftest import run
from test_apply_add import RECORD, RECORD_ID, TODAY, filed, make_vault, opened, plan, write
from vela import ledger, markrules
from vela.decisions import ledger_rows

UNKNOWNS = "11-unknowns-and-risks.md"
SHOP = "05-building-blocks/shop-building-blocks.md"
REVIEWS = ("### 1. Before options, 2026-10-14\n\n- **Coverage:** FIN found 2\n- **Dropped:** none\n\n"
           "| Finding | Area | Severity | Copy | Question | Quote |\n|---|---|---|---|---|---|\n"
           "| F1.1 | FIN, DAT | high | new | Who pays for the test till? | \"Shop sells products to the till\" in "
           "[[shop-building-blocks]] |\n"
           "| F1.2 | OPS | normal | new | Who restarts the till? | \"Shop sells products to the till\" in "
           "[[shop-building-blocks]] |\n")


def ledger_lines(text):
    """{copy: [row line]} of the page's ledger table, every written row parsed with the check's own parser."""
    found = {}
    for line in text.split("\n"):
        if line.startswith("| ") and not line.startswith(("| Copy ", "|---")):
            from vela import parse
            cells = [c.strip() for c in parse.split_row(line)]
            if len(cells) == 5 and ledger.parse_copy(cells[0])[0]:
                row = ledger.parse_row(UNKNOWNS, 0, cells)
                assert not row.problems, (line, row.problems)
                found.setdefault(cells[0], []).append(line)
    return found


def drafted(root, ledger_copies=()):
    record = opened(root)
    ctx = markrules.Context(record_id=RECORD_ID, modes=("dump",), today=TODAY, lead="@priya",
                            ledger_copies=frozenset(ledger_copies))
    return markrules.draft_files(markrules.plan(record.text, ctx), RECORD_ID, record)["ledger"]["items"]


def test_waits_on_group_one_row_per_id(tmp_path):
    root = make_vault(tmp_path, captures=[
        "- [thought] (@priya) waits on UNK-001: Q-DAT-03@INI-900, Q-OPS-02@INI-900, Q-FIN-01@INI-900 ^c01"])
    items = drafted(root, ledger_copies={"Q-FIN-01@INI-900"})
    assert [i["copy"] for i in items] == ["Q-DAT-03@INI-900", "Q-OPS-02@INI-900", "Q-FIN-01@INI-900"]
    writes = filed(root, "ledger", items)
    rows = ledger_lines(writes[UNKNOWNS])
    for copy in ("Q-DAT-03@INI-900", "Q-OPS-02@INI-900", "Q-FIN-01@INI-900"):
        assert len(rows[copy]) == 1, rows  # the row already there is changed in place, never a second
        assert f"| {copy} | unknown | unknown: [[11-unknowns-and-risks#UNK-001 Till test rig\\|UNK-001]] | @priya | " \
               f"{TODAY} |" == rows[copy][0]
    record = writes[RECORD]
    assert f"| Q-DAT-03@INI-900 | - | unknown | [[{RECORD_ID}#^c01]] |" in record
    assert f"| Q-FIN-01@INI-900 | not-applicable | unknown | [[{RECORD_ID}#^c01]] |" in record
    assert "reason: the shop holds no value" not in writes[UNKNOWNS]  # the old state's evidence goes with it


def test_unknown_must_be_open_with_an_owner(tmp_path):
    root = make_vault(tmp_path, captures=["- [thought] (@priya) waits on UNK-002: Q-DAT-03@INI-900 ^c01"])
    _, refusals = plan(root, "ledger", drafted(root))
    assert [r.rule for r in refusals] == ["ledger-unknown"]


def test_r_id_numbers_past_other_branches(tmp_path):
    root = make_vault(tmp_path, captures=["- [thought] (@priya) A note ^c01"])
    item = {"copy": None, "area": "FIN, DAT", "state": "open", "question": "Who pays for the test till?",
            "quote": "\"Shop sells products to the till\" in [[shop-building-blocks]]", "severity": "high",
            "cite": f"[[{RECORD_ID}#1. Before options, 2026-10-14]]"}
    writes = filed(root, "ledger", [item, dict(item, question="Who pays for the second till?")],
                   branch_texts=["| R-FIN-03 | open | question: on another session branch |  |  |"])
    rows = ledger_lines(writes[UNKNOWNS])
    assert {"R-FIN-04", "R-FIN-05"} <= set(rows), rows  # the first area's code, past the branch, one row each
    assert not any(c.startswith("R-DAT") for c in rows)
    # what `edge/idgit.branch_texts` gives: ID-shaped tokens, one per line, where R-FIN-07 reads as FIN-07
    writes = filed(root, "ledger", [item], branch_texts=["UNK-001\nFIN-07\n"])
    assert "R-FIN-08" in ledger_lines(writes[UNKNOWNS])


def test_answered_needs_item_and_source(tmp_path):
    root = make_vault(tmp_path, captures=['- [answer] (@priya) Q-DAT-03@INI-900: "Only the sale total is kept." ^c01'])
    base = {"copy": "Q-DAT-03@INI-900", "state": "answered", "capture": "^c01"}
    _, refusals = plan(root, "ledger", [dict(base, source="SRC-01")])
    assert [r.rule for r in refusals] == ["ledger-answered-item"]
    _, refusals = plan(root, "ledger", [dict(base, item="CON-001")])
    assert [r.rule for r in refusals] == ["ledger-answered-source"]
    _, refusals = plan(root, "ledger", [dict(base, item="CON-001", source="SRC-09")])
    assert [r.rule for r in refusals] == ["ledger-source-unregistered"]  # never an invented source
    writes = filed(root, "ledger", [dict(base, item="CON-001", source="SRC-01")])
    assert ledger_lines(writes[UNKNOWNS])["Q-DAT-03@INI-900"] == [
        "| Q-DAT-03@INI-900 | answered | item: [[shop-building-blocks#CON-001 Sale API\\|CON-001]]; "
        f"answer: Only the sale total is kept.; source: SRC-01 | @priya | {TODAY} |"]


def test_page_quote_from_this_close_refused(tmp_path):
    root = make_vault(tmp_path, captures=[
        '- [answer] (@priya) Q-DAT-03@INI-900: "The shop keeps only the sale total." ^c01'])
    shop = (root / SHOP).read_text(encoding="utf-8")
    written = shop.replace("Shop sells products to the till.\n",
                           "Shop sells products to the till. The shop keeps only the sale total.\n")
    write(root, SHOP, written)  # this close copied the lead's words onto the page
    base = {"copy": "Q-DAT-03@INI-900", "state": "answered", "capture": "^c01", "item": "CON-001"}
    _, refusals = plan(root, "ledger", [dict(base, source='"The shop keeps only the sale total" in '
                                                          '[[shop-building-blocks]]')])
    assert [r.rule for r in refusals] == ["ledger-quote-this-close"]
    _, refusals = plan(root, "ledger", [dict(base, source='"Nobody wrote these words anywhere" in '
                                                          '[[shop-building-blocks]]')])
    assert [r.rule for r in refusals] == ["ledger-quote-not-on-page"]
    filed(root, "ledger", [dict(base, source='"Shop sells products to the till" in [[shop-building-blocks]]')])
    # under a decided item the words stand, whoever wrote them
    write(root, SHOP, shop.replace("- **Change policy:** versioned.\n",
                                   "- **Change policy:** versioned.\n- **Notes:** The shop keeps only the sale total.\n"))
    filed(root, "ledger", [dict(base, source='"The shop keeps only the sale total" in [[shop-building-blocks]]')])


def test_review_row_not_taken_gets_a_ledger_row(tmp_path):
    root = make_vault(tmp_path, captures=["- [thought] (@priya) waits on UNK-001: F1.2 ^c01"])
    text = (root / RECORD).read_text(encoding="utf-8")
    write(root, RECORD, text + "\n## Reviews\n\n" + REVIEWS)
    items = drafted(root)
    assert {i["finding"] for i in items} == {"F1.1", "F1.2"}
    writes = filed(root, "ledger", items)  # a marks-plan draft applies as drafted
    rows = ledger_lines(writes[UNKNOWNS])
    assert rows["R-FIN-01"] == ['| R-FIN-01 | open | question: Who pays for the test till?; quote: "Shop sells '
                                'products to the till" in [[shop-building-blocks]]; severity: high | | |']
    assert rows["R-OPS-01"][0].startswith("| R-OPS-01 | unknown | unknown: [[11-unknowns-and-risks#UNK-001")
    assert "question: Who restarts the till?" in rows["R-OPS-01"][0]
    record = writes[RECORD]
    assert f"| R-FIN-01 | - | open | [[{RECORD_ID}#1. Before options, 2026-10-14]] |" in record
    assert f"| R-OPS-01 | - | unknown | [[{RECORD_ID}#^c01]] |" in record


def test_ledger_section_made_after_risks(tmp_path):
    root = make_vault(tmp_path, captures=["- [thought] (@priya) Q-DAT-03@INI-900: does not apply, no data kept ^c01"])
    page = (root / UNKNOWNS).read_text(encoding="utf-8")
    write(root, UNKNOWNS, page[:page.index("## Question ledger")])
    writes = filed(root, "ledger", [{"copy": "Q-DAT-03@INI-900", "state": "not-applicable", "capture": "^c01"}])
    new = writes[UNKNOWNS]
    assert new.index("## Risks") < new.index("## Question ledger")
    assert "<!-- generated:undisposed-questions sha=00000000: do not edit, run vela render -->" in new
    assert "| Copy | State | Evidence | By | Date |" in new
    assert "reason: does not apply, no data kept" in ledger_lines(new)["Q-DAT-03@INI-900"][0]


def test_not_applicable_that_defers_refused(tmp_path):
    root = make_vault(tmp_path, captures=["- [thought] (@priya) Q-DAT-03@INI-900: not for now ^c01"])
    _, refusals = plan(root, "ledger", [{"copy": "Q-DAT-03@INI-900", "state": "not-applicable", "capture": "^c01"}])
    assert [r.rule for r in refusals] == ["ledger-not-applicable-defers"]


def test_assumed_needs_load_bearing_and_signpost(tmp_path):
    root = make_vault(tmp_path, captures=["- [thought] (@priya) Q-DAT-03@INI-900: we think only totals are kept ^c01",
                                          '- [answer] (@priya) "A refund that needs the basket would show it." ^c02'])
    base = {"copy": "Q-DAT-03@INI-900", "state": "assumed", "capture": "^c01"}
    _, refusals = plan(root, "ledger", [base])
    assert {r.rule for r in refusals} == {"ledger-assumed"}
    writes = filed(root, "ledger", [dict(base, load_bearing="yes", signpost="^c02")])
    assert ("belief: we think only totals are kept; load-bearing: yes; signpost: A refund that needs the basket "
            "would show it.") in ledger_lines(writes[UNKNOWNS])["Q-DAT-03@INI-900"][0]


def test_schema_takes_every_field_marks_plan_writes():
    written = {"copy", "finding", "area", "state", "unknown", "capture", "existing", "cite", "question", "quote",
               "severity", "item"}
    assert written <= set(ledger_rows.SCHEMA.fields)
    assert json.dumps(ledger_rows.SCHEMA.example)


def test_apply_ledger_through_the_cli(tmp_path):
    root = make_vault(tmp_path, captures=["- [thought] (@priya) Q-DAT-03@INI-900: does not apply, no data kept ^c01"])
    path = root / ".vela" / "decisions" / RECORD_ID / "01-ledger.json"
    write(root, str(path.relative_to(root)), json.dumps({"version": 1, "kind": "ledger", "session": RECORD_ID, "items": [
        {"copy": "Q-DAT-03@INI-900", "state": "not-applicable", "capture": "^c01"}]}))
    code, out = run("apply", str(path), "--vault", str(root), "--today", TODAY, "--json")
    assert code == 0, out
    assert "| Q-DAT-03@INI-900 | not-applicable |" in (root / UNKNOWNS).read_text(encoding="utf-8")
