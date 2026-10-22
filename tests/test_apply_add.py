"""The `add` apply kind and `vela add KIND` (overhaul Task 15): the CLI takes the ID and writes the skeleton in one
step, so the model never types the grammar and two branches never take one number. Each test is a rule a skill's prose
held before; a deleted rule fails here by name."""
import json
import shutil

import pytest

from conftest import MINI, run
from vela import cli, decisions, parse, schema
from vela.decisions import add, add_unknown, record as records, textedit
from vela.edge import apply as disk
import session_files

RECORD_ID = "2026-10-20-grill-stock"
RECORD = f"sessions/{RECORD_ID}.md"
TODAY = "2026-10-20"
CAPTURES = ['- [unknown] (@priya) "Who owns the till test rig?" ^c01',
            '- [thought] (@priya) "The shop must open on 2026-11-02." ^c02',
            '- [answer] (@priya) "Yes, as read." ^c03']


def make_vault(tmp_path, captures=CAPTURES, agenda=(), name="vault"):
    root = tmp_path / name
    shutil.copytree(MINI, root)
    lines = ["---", f"id: {RECORD_ID}", "type: session", "date: 2026-10-20", "modes: [grill]", "status: open",
             "summary: In progress.", "---", "", "# 2026-10-20 Stock grill", ""]
    if agenda:
        lines += ["## Agenda", "", *agenda, ""]
    lines += ["## Captures", "", *captures, ""]
    session_files.write_record(root, RECORD_ID, "\n".join(lines) + "\n")
    return root


def write(root, path, text):
    target = root / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(text, encoding="utf-8")


def opened(root):
    found, problem = records.open_record([("", RECORD, session_files.record_text(root, RECORD_ID))])
    assert problem is None, problem
    return found


def staged_view(root, branch_texts=()):
    staged = decisions.Staged(cli.load_vault(root), disk.reader(root))
    textedit.attach(staged, today=TODAY, branch_texts=list(branch_texts))
    return staged


def plan(root, kind, items, branch_texts=()):
    """(writes as {path: text}, refusals) for a one-file decision, against the vault on disk."""
    decision = decisions.Decision(kind, RECORD_ID, items, {})
    writes, refusals = decisions.plan(decision, staged_view(root, branch_texts), opened(root))
    return {w.path: w.text for w in writes}, refusals


def filed(root, kind, items, branch_texts=()):
    writes, refusals = plan(root, kind, items, branch_texts)
    assert not refusals, [r.plain + " / " + r.fix for r in refusals]
    return writes


UNKNOWNS = "11-unknowns-and-risks.md"


def test_add_unknown_takes_id_counting_branches(tmp_path):
    root = make_vault(tmp_path)
    writes = filed(root, "add", [{"type": "unknown", "name": "Till rig owner", "capture": "^c01", "owner": "@priya"}],
                   branch_texts=["### UNK-007 A question on another open branch"])
    page = writes[UNKNOWNS]
    assert "### UNK-008 Till rig owner" in page
    assert "- **Question:** Who owns the till test rig?" in page
    assert "- **Owner:** @priya" in page and "- **State:** open" in page
    assert "**Blocks:**" not in page.split("### UNK-008")[1]
    record = writes[RECORD]
    assert "| UNK-008 | - | open | [[2026-10-20-grill-stock#^c01]] |" in record
    assert '→ keep: [[11-unknowns-and-risks#UNK-008 Till rig owner|UNK-008]] (open) ^c01' in record


def test_ask_by_is_the_leads_date_or_absent(tmp_path):
    root = make_vault(tmp_path)
    no_date = filed(root, "add", [{"type": "unknown", "name": "Till rig owner", "capture": "^c01", "owner": "@priya"}])
    assert "Ask by" not in no_date[UNKNOWNS].split("### UNK-003")[1]  # nothing said: no line, and no date the tool chose
    said = filed(root, "add", [{"type": "unknown", "name": "Opening day", "capture": "^c02", "owner": "@priya"}])
    assert "Ask by" not in said[UNKNOWNS].split("### UNK-003")[1]  # a date inside the capture's words is not the lead giving one
    given = filed(root, "add", [{"type": "unknown", "name": "Opening day", "question": "When does it open?",
                                 "capture": "^c03", "owner": "@priya", "ask_by": "2026-10-30"}])
    assert "- **Ask by:** 2026-10-30" in given[UNKNOWNS]


def test_add_unknown_blocks_updates_agenda(tmp_path):
    root = make_vault(tmp_path, agenda=["- CON-002: GATE-3 confirmed yes, status open",
                                        "- CON-001: GATE-3 confirmed yes, status decided"])
    item = {"type": "unknown", "name": "Stock count lag", "question": "How old can the count be?",
            "owner": "@priya", "blocks": ["CON-002"]}
    writes = filed(root, "add", [item])
    assert "- **Blocks:** [[stock-building-blocks#CON-002 Stock level|CON-002]]" in writes[UNKNOWNS]
    assert "- CON-002: GATE-3 confirmed yes, status off-agenda: UNK-003" in writes[RECORD]
    assert "- CON-001: GATE-3 confirmed yes, status decided" in writes[RECORD]
    assert add_unknown.now_blocks(dict(item, id="UNK-003"), session_files.record_text(root, RECORD_ID)) == ["CON-002"]
    code, out = run("add", "unknown", "--vault", str(root), "--today", TODAY, "--name", "Stock count lag",
                    "--question", "How old can the count be?", "--owner", "@priya", "--blocks", "CON-002", "--json")
    data = json.loads(out)
    assert code == 0, out
    assert data["id"] == "UNK-003" and data["now_blocks"] == ["CON-002"], out
    code, said = run("add", "unknown", "--vault", str(root), "--today", TODAY, "--name", "Stock count source",
                     "--question", "Where does the count come from?", "--owner", "@priya", "--blocks", "CON-002",
                     "--for-lead")
    assert code == 0 and "Stock level" in said, said  # the agenda item it now blocks, by its name


def test_lead_words_with_pipes_and_newlines_escape_in_table_cells(tmp_path):
    words = 'Tills close at 22:00 | no **later** than [[01-goals|the goal]] says'
    root = make_vault(tmp_path, captures=[f'- [thought] (@priya) "{words}" ^c01'])
    write(root, "02-constraints.md", "---\nid: constraints\ntype: initiative-section\ntitle: Constraints\n"
                                     "state: inkling\nowner: \"@priya\"\nauthored: authored\n---\n\n# Constraints\n\n"
                                     "| ID | Constraint | Where it comes from | What it forces |\n|---|---|---|---|\n")
    writes = filed(root, "add", [{"type": "constraint", "capture": "^c01", "forces": "no late sale\nno refunds"}])
    row = next(line for line in writes["02-constraints.md"].split("\n") if line.startswith("| CST-"))
    cells = parse.split_row(row)
    assert len(cells) == 4, row
    assert textedit.unescape(cells[1]) == words  # the words themselves unchanged
    assert textedit.unescape(cells[3]) == "no late sale\nno refunds"
    assert "\n" not in row
    bullet = textedit.inline("one\ntwo **three**")
    assert "\n" not in bullet and textedit.unescape(bullet) == "one\ntwo **three**"
    assert parse.BULLET.match(f"- **Why:** {bullet}").group(2) == bullet


def test_source_token_stripped(tmp_path):
    root = make_vault(tmp_path)
    item = {"type": "source", "title": "Till firmware", "owner": "@till-team", "kind": "repo",
            "location": "https://sam:ghp_secret123@github.com/acme/till.git@0a1b2c3"}
    writes = filed(root, "add", [item])
    assert "ghp_secret123" not in writes["sources.md"] and "sam:" not in writes["sources.md"]
    assert "| SRC-002 | Till firmware | @till-team | 2026-10-20 | repo | https://github.com/acme/till.git@0a1b2c3 |" \
        in writes["sources.md"]
    assert add.notices(item) and "token" in add.notices(item)[0].lower()
    assert add.notices(dict(item, location="https://github.com/acme/till.git@0a1b2c3")) == []


def test_subject_refuses_missing_facts(tmp_path):
    root = make_vault(tmp_path)
    write(root, "03-context-and-scope.md", "---\nid: context-and-scope\ntype: initiative-section\ntitle: Context and "
                                           "scope\nstate: inkling\nowner: \"@priya\"\nauthored: mixed\n---\n\n"
                                           "# Context and scope\n\n## Outside parties\n")
    _, refusals = plan(root, "add", [{"type": "subject", "subject_type": "PTY", "name": "Card acquirer",
                                      "relationship": "supplier"}])
    assert [r.rule for r in refusals] == ["E808"]
    writes = filed(root, "add", [{"type": "subject", "subject_type": "PTY", "name": "Card acquirer",
                                  "relationship": "supplier", "agreements": "none known", "capture": "^c03"}])
    page = writes["03-context-and-scope.md"]
    assert "### PTY-01 Card acquirer\n\n- **Relationship:** supplier\n- **Agreements:** none known" in page
    assert "(subject) ^c03" in writes[RECORD]


EPIC = """---
id: EPC-004
type: epic
title: Sell at the till
state: draft
owner: "@till-team"
authored: mixed
apps: [APP-till]
delivers: [CAP-001]
---

# EPC-004 Sell at the till

The till sells.

Still open: nothing.

**Owning team:** @till-team

## Done when

### A sale is recorded

The till records a sale.

- Trace: CAP-001.FR1, CON-001  ·  AC1

### ~~A refund is recorded~~

Struck, but it keeps its number.

- Trace: CON-001  ·  AC4

## History
"""


def test_epic_two_owning_teams_refused(tmp_path):
    root = make_vault(tmp_path)
    _, refusals = plan(root, "add", [{"type": "epic", "title": "Run the till", "team": ["@till-team", "@shop-team"],
                                      "apps": ["APP-till"]}])
    assert [r.rule for r in refusals] == ["epic-one-team"]
    assert "one team" in refusals[0].plain
    writes = filed(root, "add", [{"type": "epic", "title": "Run the till", "team": ["@till-team"],
                                  "apps": ["APP-till"]}])
    path = next(p for p in writes if p.startswith("13-epics/EPC-001-"))
    assert "**Owning team:** @till-team" in writes[path] and "apps: [APP-till]" in writes[path]


def test_epic_ac_numbered_after_highest(tmp_path):
    root = make_vault(tmp_path)
    write(root, "13-epics/EPC-004-sell-at-the-till.md", EPIC)
    writes = filed(root, "add", [{"type": "epic", "id": "EPC-004", "criterion": "A receipt is printed",
                                  "says": "The till prints a receipt with one VAT line.",
                                  "trace": ["CAP-001.FR2", "CON-001"], "concerns": ["testing"]}])
    page = writes["13-epics/EPC-004-sell-at-the-till.md"]
    assert "### A receipt is printed\n\nThe till prints a receipt with one VAT line.\n\n" \
           "- Trace: CAP-001.FR2, CON-001  ·  AC5  ·  [testing]\n" in page
    assert page.index("AC5") < page.index("## History")


def test_app_stub_carries_its_state_in_a_field(tmp_path):
    root = make_vault(tmp_path)
    writes = filed(root, "add", [{"type": "app-stub", "slug": "desk", "name": "Desk", "change": "new",
                                  "owner": "@desk-team", "capture": "^c03"}])
    page = writes["05-building-blocks/desk-building-blocks.md"]
    meta, _, problem = parse.split_frontmatter(page)
    assert problem is None and meta["id"] == "APP-desk" and meta["state"] == "inkling" and meta["change"] == "new"
    assert meta["stub"] == "boundary" and "Its boundary sheet" not in page
    assert "08-concerns/concern-testing.md" not in writes  # an app with no row is unexamined; no page says so
    assert "| APP-desk | - | inkling | [[2026-10-20-grill-stock#^c03]] |" in writes[RECORD]


def test_add_cut_writes_options_considered(tmp_path):
    root = make_vault(tmp_path)
    write(root, "05-building-blocks/05-building-blocks.md", "---\nid: building-blocks\ntype: index\ntitle: Building "
                                                             "blocks\nauthored: mixed\n---\n\n# Building blocks\n\n"
                                                             "One page per app.\n")
    writes = filed(root, "add", [{"type": "cut", "name": "Desk beside the till", "capture": "^c03",
                                  "apps": ["Desk=new", "Till=changed"],
                                  "rejected": ["One till app: the desk team ships on its own schedule"]}])
    page = writes["05-building-blocks/05-building-blocks.md"]
    assert "## Desk beside the till\n\n- Desk: new\n- Till: changed\n" in page
    assert "- **Options considered:** Desk beside the till (picked); One till app: rejected, the desk team ships on " \
           "its own schedule" in page
    assert "→ keep: [[05-building-blocks#Desk beside the till|cut]] (assumption) ^c03" in writes[RECORD]


def test_fr_numbered_after_the_highest(tmp_path):
    root = make_vault(tmp_path)
    write(root, "capabilities/CAP-001-sell.md", "---\nid: CAP-001\ntype: capability\ntitle: Sell\nstate: assumption\n"
                                                "owner: \"@priya\"\nauthored: authored\norigin: proposed\nchange: new\n"
                                                "---\n\n# CAP-001 Sell\n\n## Functional requirements\n\n"
                                                "### CAP-001.FR3 Take a card\n\nCards.\n\n- **State:** assumption\n")
    writes = filed(root, "add", [{"type": "fr", "capability": "CAP-001", "name": "Print a receipt",
                                  "need": "A shopper leaves with a receipt.", "capture": "^c03",
                                  "criteria": ["The receipt shows one VAT line."]}])
    page = writes["capabilities/CAP-001-sell.md"]
    assert "### CAP-001.FR4 Print a receipt\n\nA shopper leaves with a receipt.\n\n- **State:** assumption\n" \
           "- **Source:** [[2026-10-20-grill-stock#^c03]]\n\n- The receipt shows one VAT line.\n" in page


def test_unknown_field_for_a_type_refused(tmp_path):
    root = make_vault(tmp_path)
    _, refusals = plan(root, "add", [{"type": "source", "title": "x", "owner": "@a", "kind": "exists",
                                      "location": "local only", "blocks": ["CON-001"]}])
    assert [r.rule for r in refusals] == ["decision-unknown-field"]


def test_add_cli_equals_one_item_apply(tmp_path):
    by_add = make_vault(tmp_path, name="by-add")
    by_apply = make_vault(tmp_path, name="by-apply")
    for root in (by_add, by_apply):
        write(root, "02-constraints.md", "---\nid: constraints\ntype: initiative-section\ntitle: Constraints\n"
                                         "state: inkling\nowner: \"@priya\"\nauthored: authored\n---\n\n# Constraints"
                                         "\n\n| ID | Constraint | Where it comes from | What it forces |\n"
                                         "|---|---|---|---|\n")
    code, out = run("add", "constraint", "--vault", str(by_add), "--today", TODAY, "--capture", "^c02",
                    "--forces", "the till work lands before November")
    assert code == 0, out
    path = by_apply / ".vela" / "decisions" / RECORD_ID / "01-add.json"
    path.parent.mkdir(parents=True)
    path.write_text(json.dumps({"version": 1, "kind": "add", "session": RECORD_ID, "items": [
        {"type": "constraint", "capture": "^c02", "forces": "the till work lands before November"}]}),
        encoding="utf-8")
    code, out = run("apply", str(path), "--vault", str(by_apply))
    assert code == 0, out

    def pages(root):
        return {p.relative_to(root).as_posix(): p.read_text(encoding="utf-8")
                for p in root.rglob("*.md") if ".vela" not in p.parts}
    assert pages(by_add) == pages(by_apply)
    assert "| CST-001 |" in (by_add / "02-constraints.md").read_text(encoding="utf-8")
    drafted = list((by_add / ".vela" / "decisions" / RECORD_ID).glob("*-add.json"))
    assert len(drafted) == 1 and "applied" in json.loads(drafted[0].read_text(encoding="utf-8"))


def test_add_cli_refusal_writes_nothing(tmp_path):
    root = make_vault(tmp_path)
    before = (root / UNKNOWNS).read_text(encoding="utf-8")
    code, out = run("add", "unknown", "--vault", str(root), "--today", TODAY, "--name", "Bad: name",
                    "--question", "q?", "--owner", "@priya", "--json")
    assert code == 1, out
    assert json.loads(out)["refusals"][0]["rule"] == "add-heading"
    assert (root / UNKNOWNS).read_text(encoding="utf-8") == before


@pytest.mark.parametrize("kind", sorted(add.TYPES))
def test_every_type_has_an_example_its_own_validate_accepts_in_shape(kind):
    module = add.TYPES[kind]
    assert set(module.EXAMPLE) <= set(module.FIELDS) | {"type"}, kind
    assert set(module.REQUIRED) <= set(module.FIELDS), kind
    assert module.__doc__ and "Violation" in (add.__doc__ or ""), kind


# --- add unknown: no second copy of an open question (full3 P14: UNK-070 and UNK-073 asked "will the January 18 slot
# hold" twice, filed by two sessions with no check).
def test_a_near_identical_open_question_is_refused_naming_the_existing_one(tmp_path):
    root = make_vault(tmp_path)
    item = {"type": "unknown", "name": "Test till", "question": "Is there a test till that we can use?",
            "owner": "@priya"}
    _, refusals = plan(root, "add", [item])
    assert [r.rule for r in refusals] == ["add-duplicate-question"]
    assert "Till test rig" in refusals[0].plain and "UNK-001" in refusals[0].fix
    assert "different_because" in refusals[0].override


def test_a_different_question_or_a_resolved_twin_is_filed(tmp_path):
    root = make_vault(tmp_path)
    other = {"type": "unknown", "name": "Float size", "question": "How much cash float does each till start with?",
             "owner": "@priya"}
    assert filed(root, "add", [other])
    resolved_twin = {"type": "unknown", "name": "VAT line", "question": "Does the receipt need a VAT line?",
                     "owner": "@priya"}
    assert filed(root, "add", [resolved_twin])  # UNK-002 is resolved, so it is not an open question to add to


def test_the_override_files_it_and_writes_why(tmp_path):
    root = make_vault(tmp_path)
    item = {"type": "unknown", "name": "Test till", "question": "Is there a test till we can use?",
            "owner": "@priya", "different_because": "this one is about the pilot store, not head office"}
    page = filed(root, "add", [item])[UNKNOWNS]
    assert "- **Not the same as an open question because:** this one is about the pilot store, not head office" in page


def test_same_question_threshold():
    same = add_unknown.same_question
    assert same("Will the January 18 slot hold?", "Will the January 18 slot still hold for the pilot?")
    assert not same("Who owns the till test rig?", "Who pays for the till licence?")
    assert not same("Hold?", "Hold?")  # too short to call a copy


def test_add_unknown_cli_refuses_a_copy_then_files_with_the_reason(tmp_path):
    root = make_vault(tmp_path)
    args = ["add", "unknown", "--vault", str(root), "--today", TODAY, "--name", "Test till",
            "--question", "Is there a test till we can use?", "--owner", "@priya"]
    code, _ = run(*args)
    assert code != 0
    code, _ = run(*args, "--different-because", "pilot store only")
    assert code == 0


def test_the_override_bullet_does_not_trip_the_vault_check(tmp_path):
    root = make_vault(tmp_path)
    before = run("check", "--vault", str(root))[1]
    run("add", "unknown", "--vault", str(root), "--today", TODAY, "--name", "Test till",
        "--question", "Is there a test till we can use?", "--owner", "@priya", "--different-because", "pilot only")
    after = run("check", "--vault", str(root))[1]
    assert "Not the same" not in after
    assert after.count("error") <= before.count("error")
