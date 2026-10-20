"""`vela marks plan` (overhaul Task 14): close section 2's default marks as one table in `vela.markrules`, and the
command that drafts the `marks` (and `ledger`) decision files from it.

One test per rule, table-driven, so a rule deleted from the table fails a named case. The rule's reason lives in the
table row itself (plan 3.1, S8), and `test_every_rule_carries_its_reason` holds that.
"""
import json
import os
import shutil
import stat

import pytest

from conftest import MINI, run
from vela import decisions, markrules, say
from vela.decisions import record as records, schema

TODAY = "2026-10-14"
RECORD_ID = "2026-10-14-desk-close"
LEAD = "@sam"


def ctx(**over):
    base = dict(record_id=RECORD_ID, modes=("dump",), today=TODAY, lead=LEAD,
                open_items=frozenset(), ledger_copies=frozenset())
    base.update(over)
    return markrules.Context(**base)


def record_text(captures, modes="[dump]", reviews=""):
    lines = ["---", f"id: {RECORD_ID}", "type: session", f"date: {TODAY}", f"modes: {modes}", "status: open",
             "summary: In progress.", "---", "", f"# {TODAY} Desk close", "", "## Captures", "", *captures, ""]
    text = "\n".join(lines) + "\n"
    if reviews:
        text += "\n## Reviews\n\n" + reviews + "\n"
    return text + "\n## Changes\n\n| ID | From | To | Source |\n|---|---|---|---|\n"


def planned(captures, **over):
    return markrules.plan(record_text(captures), ctx(**over))


def only_item(plan):
    assert len(plan.items) == 1, plan.items
    return plan.items[0]


# One row per close section 2 rule: (case, capture line, context overrides, expected fields of the drafted item).
RULES = [
    ("wild-park", '- [wild] (@sam) "What if the desk ran itself?" ^c01', {},
     {"rule": "wild-park", "mark": "park", "needs_lead": False}),
    ("claude-park", "- [idea] (claude) A digest at 7:30 could carry the prep notes too. ^c01", {},
     {"rule": "claude-park", "mark": "park", "needs_lead": False}),
    ("claude-from-park", "- [thought] (claude, from CIO) The CIO's brief expects install in two minutes. ^c01", {},
     {"rule": "claude-park", "mark": "park"}),
    ("pty-subject", "- [thought] (claude, from product owner) Zoom is a partner. type at close: PTY ^c01", {},
     {"rule": "typed-subject", "mark": "keep", "to": "subject", "state": "subject", "subject_type": "PTY"}),
    ("sv-subject", '- [thought] (@sam) "Points are held for each customer." type at close: SV ^c01', {},
     {"rule": "typed-subject", "mark": "keep", "to": "subject", "state": "subject", "subject_type": "SV"}),
    ("copy-ledger", '- [thought] (@sam) Q-FIN-03@SV-01: "not applicable, no money moves" ^c01', {},
     {"rule": "copy-ledger", "mark": "keep", "to": "ledger", "id": ["Q-FIN-03@SV-01"], "state": "not-applicable"}),
    ("copy-ledger-waits", '- [thought] (@sam) waits on UNK-020: Q-PTN-03@PTY-02, Q-PTN-06@PTY-02 ^c01', {},
     {"rule": "copy-ledger", "mark": "keep", "to": "ledger", "id": ["Q-PTN-03@PTY-02", "Q-PTN-06@PTY-02"],
      "state": "unknown", "unknown": "UNK-020"}),
    ("claude-unknown-needs-lead", "- [unknown] (claude) Does the call tool keep a record per call? ^c01", {},
     {"rule": "claude-unknown", "mark": None, "needs_lead": True}),
    ("lifted-needs-lead", '- [thought] (CISO) "No meeting text leaves a laptop until the review passes." ^c01', {},
     {"rule": "lifted-line", "mark": None, "needs_lead": True}),
    ("shape-assumption", '- [thought] (@sam) "We picked option B, the folder." ^c01', {"modes": ("shape",)},
     {"rule": "shape-pick", "mark": "keep", "to": "assumption", "state": "assumption"}),
    ("person-idea-inkling", '- [idea] (@sam) "A morning digest might help." ^c01', {},
     {"rule": "person-inkling", "mark": "keep", "to": "inkling", "state": "inkling"}),
    ("person-unknown", '- [unknown] (@sam) "Who signs off the pack?" ^c01', {},
     {"rule": "person-unknown", "mark": "keep", "to": "unknown", "state": "open", "owner": LEAD}),
    ("deferral-unknown", '- [thought] (@sam) "The retention period is left for a grill." ^c01', {},
     {"rule": "deferral-unknown", "mark": "keep", "to": "unknown", "state": "open", "owner": LEAD}),
]


@pytest.mark.parametrize("case,line,over,expected", RULES, ids=[r[0] for r in RULES])
def test_each_default_rule(case, line, over, expected):
    item = only_item(planned([line], **over))
    for field, value in expected.items():
        assert item.get(field) == value, (field, item)


def test_shape_pick_is_never_an_inkling():
    item = only_item(planned(['- [idea] (@sam) "Go with option A." ^c01'], modes=("shape",)))
    assert item["to"] == "assumption" and item["state"] != "inkling"


def test_shape_pick_in_an_epics_session_is_left_to_the_epic_pages():
    """An epics session already wrote the epic pages, so a picked cut is no new assumption."""
    item = only_item(planned(['- [idea] (@sam) "Go with option A." ^c01'], modes=("shape", "epics")))
    assert item["rule"] != "shape-pick"


def test_never_fact():
    """No default proposes `fact`: a capture is a fact only when the lead names its source and it has a row."""
    lines = ['- [thought] (claude, from CISO) The CISO says it is a fact that no text leaves the laptop. ^c01',
             '- [thought] (@sam) "It is a fact: SRC-02 says so." ^c02',
             '- [idea] (@sam) "The 18 January slot is fixed." ^c03',
             "- [thought] (claude) Fact: the tenant has 4,200 users. ^c04"]
    plan = planned(lines)
    assert plan.items and all(i.get("state") != "fact" for i in plan.items)
    assert all(lo["recommend"].get("state") != "fact" for lo in plan.leftovers)


def test_claude_unknown_offers_keep_or_drop_never_park():
    plan = planned(["- [unknown] (claude) Does the call tool keep a record per call? ^c01"])
    left = plan.leftovers[0]
    assert left["capture"] == "^c01" and set(left["choices"]) == {"keep", "drop"}
    assert left["recommend"]["to"] == "unknown"


def test_lifted_line_from_the_lead_is_copied_and_listed():
    item = only_item(planned(['- [thought] (@sam) "The desk opens at eight." ^c01']))
    assert not item["needs_lead"] and item["lifted"] is True


def test_claude_deferral_needs_the_lead():
    """Claude never decides an unknown alone, and a deferral becomes one."""
    item = only_item(planned(["- [thought] (claude) The retention period is left for a grill. ^c01"]))
    assert item["needs_lead"] and item["rule"] == "claude-unknown"


def test_mode_written_marks_left_alone():
    lines = ['- [decision] (@sam) "Yes." → keep: [[heron#CON-002 Chosen folder|CON-002]] (decided) ^c01',
             "- [thought] (claude, from CISO) Text stays on the laptop. → keep: [[02-constraints#Constraints|CST-3]] "
             "(fact) ^c02",
             "- [wild] (@sam) What if it ran itself? ^c03"]
    plan = planned(lines)
    assert [i["capture"] for i in plan.items] == ["^c03"]
    alone = {a["capture"]: a for a in plan.left_alone}
    assert set(alone) == {"^c01", "^c02"}
    assert alone["^c02"]["promoted_on_a_nod"] and not alone["^c01"]["promoted_on_a_nod"]


def test_no_default_picks_an_ask_by_date():
    """A date nobody chose is not the owner's plan. The lead gives one, or agrees the model's proposal, and `add
    unknown` files it with their capture; a default that wrote one (the nearest hard date, two weeks on) is gone."""
    lines = ['- [unknown] (@sam) "Who signs off the pack? Ask by 2026-10-20." ^c01',
             '- [thought] (@sam) "The retention period is left for a grill." ^c02']
    for item in planned(lines).items:
        assert "ask_by" not in item, item


def test_never_asks_for_bookkeeping():
    """Handle and owner are computed; no leftover is about bookkeeping, and no date is made up."""
    lines = ['- [unknown] (@sam) "Who signs off the pack?" ^c01', '- [worry] (@sam) "The council may say no." ^c02',
             '- [thought] (@sam) "The retention period is left for a grill." ^c03']
    plan = planned(lines)
    assert not plan.leftovers
    for item in plan.items:
        assert item["owner"] == LEAD and "ask_by" not in item, item
    assert not any(word in json.dumps(plan.leftovers) for word in ("handle", "minutes", "sources"))


def test_owner_falls_back_to_the_capture_handle_when_no_handle_is_kept():
    item = only_item(planned(['- [unknown] (@sam) "Who signs off the pack?" ^c01'], lead=""))
    assert item["owner"] == "@sam"


def test_leftovers_ranked_by_what_they_block():
    lines = ["- [unknown] (claude) Is the folder ever empty? ^c01",
             "- [unknown] (claude) Does CON-002 cover past entries, and does EPC-001 wait on it? ^c02",
             "- [unknown] (claude) Does CON-002 need a second folder? ^c03"]
    plan = planned(lines, open_items=frozenset({"CON-002", "EPC-001"}))
    assert [lo["capture"] for lo in plan.leftovers] == ["^c02", "^c03", "^c01"]
    assert plan.leftovers[0]["blocks"] == ["CON-002", "EPC-001"]


def test_review_row_not_taken_gets_a_ledger_row_citing_its_checkpoint():
    reviews = ("### 1. Before options, 2026-10-14\n\n- **Coverage:** FIN found 2\n- **Dropped:** none\n\n"
               "| Finding | Area | Severity | Copy | Question | Quote |\n|---|---|---|---|---|---|\n"
               "| F1.1 | FIN | normal | new | Who pays for the laptop model? | \"It costs a model\" in [[x]] |\n"
               "| F1.2 | FIN | high | new | Who carries the hosting risk? | \"hosted\" in [[x]] |\n"
               "| F1.3 | DAT | normal | Q-DAT-05@INI-001 | What was the data collected for? | \"the digest\" |\n")
    text = record_text(['- [thought] (@sam) waits on UNK-012: F1.2 ^c01'], reviews=reviews)
    plan = markrules.plan(text, ctx())
    by_finding = {row["finding"]: row for row in plan.ledger}
    assert set(by_finding) == {"F1.1", "F1.2"}, plan.ledger  # an owed copy not taken stays undisposed
    untaken = by_finding["F1.1"]
    assert untaken["state"] == "open" and untaken["capture"] is None
    assert untaken["cite"] == f"[[{RECORD_ID}#1. Before options, 2026-10-14]]"
    assert untaken["question"] == "Who pays for the laptop model?" and untaken["area"] == "FIN"
    taken = by_finding["F1.2"]
    assert taken["state"] == "unknown" and taken["unknown"] == "UNK-012" and taken["capture"] == "^c01"


def test_a_copy_already_in_the_ledger_gets_no_second_row():
    plan = planned(['- [thought] (@sam) Q-FIN-01@INI-001: yes, points are held. type at close: SV ^c01'],
                   ledger_copies=frozenset({"Q-FIN-01@INI-001"}))
    assert not plan.ledger
    plan = planned(['- [thought] (@sam) Q-FIN-01@INI-001: yes, points are held. type at close: SV ^c01'])
    assert [(r["copy"], r["state"]) for r in plan.ledger] == [("Q-FIN-01@INI-001", "answered")]


def test_every_rule_carries_its_reason():
    assert markrules.RULES
    for rule in markrules.RULES:
        assert len(rule.reason.split()) >= 6, rule.name


def test_mark_parser_reads_the_grammar_and_refuses_the_rest():
    keep = markrules.parse_mark("keep: [[11-unknowns-and-risks#Question ledger|R-DAT-10]] (unknown); "
                                "[[11-unknowns-and-risks#Question ledger|R-DAT-11]] (unknown)")
    assert keep.kind == "keep" and [t.id for t in keep.targets] == ["R-DAT-10", "R-DAT-11"]
    assert markrules.parse_mark("park").kind == "park"
    assert markrules.parse_mark("drop: repeats c03").reason == "repeats c03"
    for bad in ("keep it", "drop:", "keep: [[p#h|X]]", "parked"):
        assert markrules.parse_mark(bad) is None, bad


# The command, against a real folder.

def vault_with_record(tmp_path, captures, modes="[dump]"):
    root = tmp_path / "vault"
    shutil.copytree(MINI, root)
    (root / "sessions" / f"{RECORD_ID}.md").write_text(record_text(captures, modes), encoding="utf-8")
    (root / ".vela").mkdir(exist_ok=True)
    (root / ".vela" / "handle").write_text("sam\n", encoding="utf-8")
    return root


def marks_plan(root, *flags):
    return run("marks", "plan", "--vault", str(root), "--today", TODAY, *flags)


def drafts(root):
    return sorted((root / ".vela" / "decisions" / RECORD_ID).glob("*.json"))


def test_draft_matches_task4_file_shape(tmp_path):
    root = vault_with_record(tmp_path, ['- [wild] (@sam) "What if it ran itself?" ^c01',
                                        "- [unknown] (claude) Is the folder ever empty? ^c02"])
    code, out = marks_plan(root, "--json")
    assert code == say.DONE, out  # the draft is written, so the exit says so; the leftovers are in needs_lead
    path = root / ".vela" / "decisions" / RECORD_ID / "01-marks.json"
    assert drafts(root) == [path]
    assert json.loads(out)["wrote"] == [f".vela/decisions/{RECORD_ID}/01-marks.json"]
    decision, problems = decisions.load(path.read_text(encoding="utf-8"))
    assert not problems and decision.kind == "marks" and decision.session == RECORD_ID
    record = records.from_text(RECORD_ID, f"sessions/{RECORD_ID}.md",
                               (root / "sessions" / f"{RECORD_ID}.md").read_text(encoding="utf-8"))
    for item in decision.items:
        assert set(item["seen"]) == {item["capture"]}
        assert item["seen"][item["capture"]] == schema.quote_hash(record.capture(item["capture"]))
    leftover = next(i for i in decision.items if i["needs_lead"])
    assert leftover["mark"] is None and leftover["lead_answer"] is None
    assert set(leftover["hints"]) >= {"mark", "lead_answer"}
    data = json.loads(out)
    assert [n["capture"] for n in data["needs_lead"]] == ["^c02"]
    assert data["drafts"] == [f".vela/decisions/{RECORD_ID}/01-marks.json"]


def test_nothing_left_for_the_lead_exits_0_and_rerun_replaces_an_unapplied_draft(tmp_path):
    root = vault_with_record(tmp_path, ['- [wild] (@sam) "What if it ran itself?" ^c01'])
    assert marks_plan(root)[0] == 0
    assert marks_plan(root)[0] == 0
    assert [p.name for p in drafts(root)] == ["01-marks.json"]


def test_for_lead_says_the_counts_and_the_leftovers_plainly(tmp_path):
    root = vault_with_record(tmp_path, ['- [wild] (@sam) "What if it ran itself?" ^c01',
                                        "- [unknown] (claude) Does UNK-001 still hold the test rig? ^c02"])
    code, out = marks_plan(root, "--for-lead")
    assert code == 0, out
    assert say.leak_in(out) is None and "Till test rig" in out, out
    assert out.startswith("One of today's notes needs your call:"), out  # the answer first
    assert "one is set aside for later" in out and "I'd keep it as an open question" in out, out


@pytest.fixture
def failing_git(tmp_path, monkeypatch):
    """A `git` on PATH that records any call and fails, so a test sees git was never run."""
    shim = tmp_path / "shim"
    shim.mkdir()
    marker = tmp_path / "git-was-called"
    script = shim / "git"
    script.write_text(f"#!/bin/sh\necho called >> {marker}\nexit 97\n", encoding="utf-8")
    script.chmod(script.stat().st_mode | stat.S_IEXEC)
    monkeypatch.setenv("PATH", f"{shim}{os.pathsep}{os.environ['PATH']}")
    return marker


def test_reader_copy_writes_the_draft_without_git(tmp_path, failing_git):
    root = vault_with_record(tmp_path, ['- [wild] (@sam) "What if it ran itself?" ^c01'])
    (root / ".vela" / "workspace.json").write_text('{"author": "Sam"}', encoding="utf-8")
    code, out = marks_plan(root, "--for-lead")
    assert code == 0, out
    assert drafts(root) and not failing_git.exists()
    assert "your copy" in out.lower()


def test_no_open_session_is_refused(tmp_path):
    root = tmp_path / "vault"
    shutil.copytree(MINI, root)
    code, out = marks_plan(root)
    assert code == 1 and "No session is open" in out
