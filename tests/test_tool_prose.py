"""Tool-written prose: state lives in frontmatter fields, the tool invents no dates, generated blocks say so.

The Violation each test pins: Forensic Coding plus Silent Fallback (code that recovers state from a sentence loses it
without a signal when a model rewrites the sentence), a value nobody chose (an Ask by the tool computed), and a
generated block that reads as the owner's words (Leaky Narrative at the reader). Anchor: state sits in a field."""
import re

from conftest import check, edit, findings, run
from test_apply_add import RECORD, UNKNOWNS, filed, make_vault, plan
from vela import cli, render, rules, schema

TESTING = "08-concerns/concern-testing.md"
STOCK = "05-building-blocks/stock-building-blocks.md"
STUB_APP = ("---\nid: APP-links\ntype: app-building-blocks\ntitle: Links\nstate: inkling\nchange: new\n"
            "stage: boundaries\n{extra}owner: \"@lead\"\nauthored: authored\n---\n# Links\n\n{body}\n")


def problems(out):
    """What the check found, leaving out the stale-block and age warnings a test's edit or clock moves."""
    return [f for f in findings(out) if f[0] not in ("W402", "W711", "W716")]


def stub_vault(tmp_path, extra, body):
    (tmp_path / ".vela.yaml").write_text("initiative: INI-001\ntitle: New\n", encoding="utf-8")
    (tmp_path / "05-building-blocks").mkdir()
    (tmp_path / "05-building-blocks" / "links-building-blocks.md").write_text(
        STUB_APP.format(extra=extra, body=body), encoding="utf-8")
    return tmp_path


# --- 1. state in fields ---------------------------------------------------------------------------------------------

def test_a_stub_is_found_by_its_field_whatever_the_page_says(tmp_path):
    vault = stub_vault(tmp_path, "stub: boundary\n", "Links is new, and we haven't read its parts back yet.")
    code, out = run("next", "--vault", str(vault), "--today", "2026-01-15")
    assert code == 0 and "read back the boundary of Links" in out, out


def test_the_old_sentence_without_the_field_is_not_a_stub(tmp_path):
    vault = stub_vault(tmp_path, "", "Its boundary sheet is still to be read back.")
    code, out = run("next", "--vault", str(vault), "--today", "2026-01-15")
    assert "read back the boundary" not in out, out


def test_the_stub_writer_sets_the_field_and_adds_no_tool_sentence(tmp_path):
    root = make_vault(tmp_path)
    writes = filed(root, "add", [{"type": "app-stub", "slug": "desk", "name": "Desk", "change": "new",
                                  "owner": "@desk-team", "capture": "^c03"}])
    page = writes["05-building-blocks/desk-building-blocks.md"]
    assert "\nstub: boundary\n" in page
    assert page.split("---\n", 2)[2].strip() == "# Desk"
    assert not hasattr(schema, "BOUNDARY_STUB_LINE")
    assert TESTING not in writes, "no concern page is touched"


def test_a_stub_field_must_say_boundary(mini):
    edit(mini / STOCK, "authored: authored\n", "authored: authored\nstub: yes\n")
    _, out = check(mini)
    assert ("E105", STOCK) in problems(out)


def test_an_app_with_no_row_on_a_concern_page_is_unexamined_and_nothing_says_so(mini):
    edit(mini / TESTING, "| [[stock-building-blocks\\|Stock]] | unchanged | Existing tests hold |\n", "")
    _, out = check(mini)
    assert problems(out) == [], out
    vault = cli.load_vault(mini)
    assert "Not looked at yet" not in (mini / TESTING).read_text(encoding="utf-8")
    cell = [line for line in render.concern_matrix(vault, vault.page("01-goals")).split("\n") if "Stock" in line]
    assert cell and "not reviewed yet" in cell[0], cell


def test_no_code_reads_a_not_looked_at_yet_sentence():
    assert not hasattr(rules, "NOT_LOOKED_LINE") and not hasattr(rules, "not_looked_at")


def test_the_unknown_writer_leaves_blocks_out_when_it_blocks_nothing(tmp_path):
    root = make_vault(tmp_path)
    writes = filed(root, "add", [{"type": "unknown", "name": "Till rig owner", "capture": "^c01", "owner": "@priya"}])
    assert "**Blocks:**" not in writes[UNKNOWNS].split("### UNK-003")[1]


def test_an_open_unknown_with_no_blocks_line_blocks_nothing_and_checks_clean(mini):
    assert "UNK-001" in (mini / "11-unknowns-and-risks.md").read_text(encoding="utf-8")
    _, out = check(mini)
    assert problems(out) == [], out


def test_the_word_nothing_is_no_longer_a_blocks_value(mini):
    edit(mini / "11-unknowns-and-risks.md", "- **Opened:** 2026-01-10\n", "- **Opened:** 2026-01-10\n- **Blocks:** the till rollout\n")
    _, out = check(mini)
    assert ("E302", "11-unknowns-and-risks.md") in problems(out)


def test_the_handoff_pr_is_its_own_field(mini):
    edit(mini / STOCK, "authored: authored\n", 'authored: authored\nhanded_off: "Stock senior, 2026-01-12"\n'
                                                "handed_off_pr: pending\n")
    _, out = check(mini)
    assert ("W325", STOCK) in problems(out) and not [f for f in problems(out) if f[0].startswith("E")], out
    edit(mini / STOCK, "handed_off_pr: pending\n", "handed_off_pr: 41\n")
    _, out = check(mini)
    assert problems(out) == [], out


def test_a_pr_sentence_inside_handed_off_is_no_longer_read(mini):
    edit(mini / STOCK, "authored: authored\n", 'authored: authored\nhanded_off: "Stock senior, 2026-01-12, PR #4"\n')
    _, out = check(mini)
    assert ("E105", STOCK) in problems(out)


def test_a_pr_number_with_no_handoff_is_refused(mini):
    edit(mini / STOCK, "authored: authored\n", "authored: authored\nhanded_off_pr: 4\n")
    _, out = check(mini)
    assert ("E105", STOCK) in problems(out)


# --- 2. no tool-chosen Ask by ---------------------------------------------------------------------------------------

def test_an_unknown_with_no_date_has_no_ask_by_line_and_no_default(tmp_path):
    root = make_vault(tmp_path)
    writes = filed(root, "add", [{"type": "unknown", "name": "Till rig owner", "capture": "^c01", "owner": "@priya"}])
    block = writes[UNKNOWNS].split("### UNK-003")[1]
    assert "Ask by" not in block and "2026-11-0" not in block


def test_a_date_said_inside_a_capture_is_not_picked_up_for_the_lead(tmp_path):
    root = make_vault(tmp_path)
    writes = filed(root, "add", [{"type": "unknown", "name": "Opening day", "capture": "^c02", "owner": "@priya"}])
    assert "Ask by" not in writes[UNKNOWNS].split("### UNK-003")[1]


def test_a_date_with_no_capture_behind_it_is_refused(tmp_path):
    root = make_vault(tmp_path)
    _, refusals = plan(root, "add", [{"type": "unknown", "name": "Opening day", "question": "When does it open?",
                                      "owner": "@priya", "ask_by": "2026-10-30"}])
    assert [r.rule for r in refusals] == ["add-ask-by-capture"], refusals


def test_a_date_the_lead_gave_is_filed_citing_their_capture(tmp_path):
    root = make_vault(tmp_path)
    writes = filed(root, "add", [{"type": "unknown", "name": "Opening day", "capture": "^c03", "owner": "@priya",
                                  "question": "When does it open?", "ask_by": "2026-10-30"}])
    assert "- **Ask by:** 2026-10-30" in writes[UNKNOWNS]
    assert "[[2026-10-20-grill-stock#^c03]]" in writes[RECORD]


def test_nothing_in_markrules_computes_a_date():
    from vela import markrules
    assert not hasattr(markrules, "ask_by") and not hasattr(markrules, "NEW_UNKNOWN_DAYS")


def test_an_open_unknown_with_no_ask_by_is_not_an_error_and_is_not_overdue(mini):
    edit(mini / "11-unknowns-and-risks.md", "- **Ask by:** 2026-02-01\n", "")
    _, out = check(mini, "2027-01-01")
    assert problems(out) == [], out


# --- 3. generated blocks say so -------------------------------------------------------------------------------------

def test_every_generated_block_opens_with_the_caption(mini):
    vault = cli.load_vault(mini)
    page = vault.page("01-goals")
    for name in render.GENERATORS:
        assert render.block_content(vault, page, name).startswith(schema.GENERATED_CAPTION + "\n"), name
    assert set(render.GENERATORS) == set(schema.BLOCKS)


def test_the_rendered_page_carries_the_caption_under_the_marker(mini):
    code, _ = run("render", "--vault", str(mini))
    assert code == 0
    text = "\n".join(p.read_text(encoding="utf-8") for p in mini.rglob("*.md"))
    blocks = re.findall(r"<!-- generated:(\S+) sha=\w+: [^>]*-->\n([^\n]*)\n", text)
    assert blocks and all(first == schema.GENERATED_CAPTION for _, first in blocks), blocks


def test_a_block_that_lost_its_caption_is_out_of_date(mini):
    _, out = check(mini)
    assert findings(out) == []
    page = mini / "11-unknowns-and-risks.md"
    page.write_text(page.read_text(encoding="utf-8").replace(schema.GENERATED_CAPTION + "\n", ""), encoding="utf-8")
    _, out = check(mini)
    assert findings(out), "a block that lost its caption is out of date until vela render runs"
