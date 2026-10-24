"""The `marks` apply kind (overhaul Task 15): close's "Find the session and mark the captures": "write the marks" as code. A mark goes into its capture
line before the block ID, a leftover is filed only on the lead's own answer, and a fact never comes from a plan."""
import json

from test_apply_add import RECORD, RECORD_ID, TODAY, filed, make_vault, opened, plan, write
from vela import closegate, markrules
from vela.decisions import marks

SOURCES = ("---\nid: sources\ntype: sources\ntitle: Sources\nauthored: authored\n---\n\n# Sources\n\n"
           "| ID | Title | Owner | Date | Kind | Location |\n|---|---|---|---|---|---|\n"
           "| SRC-01 | Stock read API documentation | @stock-team | 2026-01-02 | exists | local only |\n"
           "| SRC-02 | Till roadmap deck | @till-team | 2026-09-01 | intends | local only |\n")


def line_of(text, ref):
    return next(line for line in text.split("\n") if line.rstrip().endswith(ref))


def test_marks_written_before_block_id(tmp_path):
    root = make_vault(tmp_path, captures=['- [thought] (@priya) "Is there a rig?" ^c05',
                                          "- [wild] (@priya) What if the till ran on a phone ^c06",
                                          "- [thought] (claude) A second till could help ^c07"])
    writes = filed(root, "marks", [
        {"capture": "^c05", "mark": "keep", "to": "unknown", "id": "UNK-001", "state": "open"},
        {"capture": "^c06", "mark": "park"},
        {"capture": "^c07", "mark": "drop", "drop_reason": "repeats the till goal"}])
    record = writes[RECORD]
    assert line_of(record, "^c05") == ('- [thought] (@priya) "Is there a rig?" → keep: '
                                       '[[11-unknowns-and-risks#UNK-001 Till test rig|UNK-001]] (open) ^c05')
    assert line_of(record, "^c06").endswith("on a phone → park ^c06")
    assert line_of(record, "^c07").endswith("could help → drop: repeats the till goal ^c07")
    for ref in ("^c05", "^c06", "^c07"):
        found = closegate.CAPTURE_RE.match(line_of(record, ref))
        assert found and markrules.parse_mark(found["mark"]) is not None, ref


def test_a_capture_already_marked_is_refused(tmp_path):
    root = make_vault(tmp_path, captures=["- [wild] (@priya) A phone till → park ^c06"])
    _, refusals = plan(root, "marks", [{"capture": "^c06", "mark": "drop", "drop_reason": "no"}])
    assert [r.rule for r in refusals] == ["marks-already-marked"]


def test_marks_plan_draft_is_accepted_as_drafted(tmp_path):
    """Task 14's `marks plan` writes the items; this kind must take every field it writes, not refuse them as typos."""
    captures = ['- [unknown] (claude) Does the till need a VAT line? ^c01',
                "- [wild] (@priya) A phone till ^c02",
                '- [answer] (@priya) "Keep it, ask finance." ^c03']
    root = make_vault(tmp_path, captures=captures)
    record = opened(root)
    ctx = markrules.Context(record_id=RECORD_ID, modes=("grill",), today=TODAY, lead="@priya")
    drafted = markrules.draft_files(markrules.plan(record.text, ctx), RECORD_ID, record)["marks"]["items"]
    leftover = next(i for i in drafted if i["capture"] == "^c01")
    assert leftover["needs_lead"] and leftover["mark"] is None
    _, refusals = plan(root, "marks", drafted)
    assert {r.rule for r in refusals} == {"decision-unfilled"}  # only the lead's answer is missing, no field refused
    leftover.update(mark="keep", to="unknown", state="open", lead_answer="^c03", name="VAT line on receipts",
                    owner="@priya")
    for item in drafted:
        if item["mark"] is None:  # the answer line itself, which no default covers: the model marks it
            item["mark"] = "park"
    writes = filed(root, "marks", drafted)
    assert "### UNK-003 VAT line on receipts" in writes["11-unknowns-and-risks.md"]
    assert line_of(writes[RECORD], "^c01").endswith(
        "→ keep: [[11-unknowns-and-risks#UNK-003 VAT line on receipts|UNK-003]] (open) ^c01")
    assert line_of(writes[RECORD], "^c02").endswith("→ park ^c02")


def test_leftover_on_claudes_word_refused(tmp_path):
    root = make_vault(tmp_path, captures=["- [unknown] (claude) Does the till need a VAT line? ^c01",
                                          "- [answer] (claude) I'd drop it ^c02"])
    _, refusals = plan(root, "marks", [{"capture": "^c01", "mark": "drop", "drop_reason": "covered", "needs_lead": True,
                                        "lead_answer": "^c02"}])
    assert [r.rule for r in refusals] == ["consent-not-a-person"]
    _, refusals = plan(root, "marks", [{"capture": "^c01", "mark": "drop", "drop_reason": "covered", "needs_lead": True,
                                        "lead_answer": None}])
    assert [r.rule for r in refusals] == ["marks-needs-lead"]


def test_fact_from_intends_source_refused(tmp_path):
    root = make_vault(tmp_path, captures=['- [thought] (@priya) "The till API is ready in Q4." ^c01',
                                          '- [answer] (@priya) "The deck says yes, one VAT line." ^c02'])
    write(root, "sources.md", SOURCES)
    _, refusals = plan(root, "marks", [{"capture": "^c01", "mark": "keep", "to": "contract", "id": "CON-002",
                                        "state": "fact", "source": "SRC-02"}])
    assert [r.rule for r in refusals] == ["fact-from-intends"]
    assert "plan" in refusals[0].plain
    writes = filed(root, "marks", [{"capture": "^c01", "mark": "keep", "to": "contract", "id": "CON-002",
                                    "state": "fact", "source": "SRC-01"}])
    assert "(fact) ^c01" in writes[RECORD]
    _, refusals = plan(root, "resolve", [{"id": "UNK-001", "answer": "^c02", "source": "SRC-02"}])
    assert [r.rule for r in refusals] == ["fact-from-intends"]
    assert marks.SCHEMA.required == ("capture", "mark")


def test_marks_schema_takes_every_field_marks_plan_writes():
    written = {"capture", "rule", "reason", "mark", "to", "id", "state", "needs_lead", "lifted", "owner", "ask_by",
               "blocks", "subject_type", "unknown", "recommend", "lead_answer", "page", "options_considered",
               "deferral"}
    assert written <= set(marks.SCHEMA.fields)
    assert json.dumps(marks.SCHEMA.example)


def test_a_keep_with_no_id_or_page_is_refused_to_the_model_not_the_lead(tmp_path):
    from vela import say
    root = make_vault(tmp_path, captures=['- [idea] (@priya) "A badge for regulars." ^c05'])
    _, refusals = plan(root, "marks", [{"capture": "^c05", "mark": "keep", "to": "inkling", "state": "inkling",
                                        "id": None, "page": None}])
    unfilled = [r for r in refusals if r.rule == "decision-unfilled"]
    assert unfilled and all(r.audience == say.MODEL for r in unfilled)
