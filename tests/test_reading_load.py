"""Pages a person can hold in mind: plain names in prose, IDs on a Trace line, and the five reading-load warnings.

People hold about four to seven things at once, so a criterion that ends "(CON-001, FLO-001). From CAP-001.FR2." fails
its reader before it fails any check. W360 to W364 say so, as warnings only, and say how to write it in plain words."""
import json
import re
import shutil

import pytest
from conftest import REPO, check, findings, run

from planner import cli, parse, query, readability, reading, viewer
from planner.explorer.pages_data import page_reader
from planner.explorer.record import Keys, chips_html, inline_html

HERON = REPO / "tests" / "sim" / "snapshots" / "heron-desk" / "after-full-1"
REWRITTEN = REPO / "tests" / "fixtures" / "readable" / "EPC-001-calendar.md"
EPIC_PATH = "13-epics/EPC-001-calendar.md"
CODES = ("W360", "W361", "W362", "W363", "W364")

EPIC_HEAD = """---
id: EPC-001
type: epic
title: Sell at the till
initiative: INI-900
state: draft
owner: "@mini/shop-team"
authored: mixed
apps: [APP-shop]
delivers: [CON-001]
---

# Sell at the till

"""
EPIC_TAIL = """
## Traces to

<!-- generated:traces-to sha=00000000: do not edit, run planner render -->
<!-- /generated:traces-to -->
"""
SUMMARY = "The till sends each basket to the shop and gets a receipt back. Still open: how long a sale may wait.\n"
EPIC = "13-epics/EPC-001-sell-at-the-till.md"


def write_epic(vault, criteria, summary=SUMMARY):
    (vault / "13-epics").mkdir(exist_ok=True)
    numbered = "\n".join(f"{n}. {text}" for n, text in enumerate(criteria, 1))
    (vault / EPIC).write_text(f"{EPIC_HEAD}{summary}\n## Epic acceptance criteria\n\n{numbered}\n{EPIC_TAIL}", encoding="utf-8")
    run("render", "--vault", str(vault))


def reading_codes(vault):
    code, out = check(vault)
    assert code == 0, out  # warnings only, never errors
    return [c for c, _ in findings(out) if c in CODES]


def message(vault, wanted):
    _, out = check(vault)
    return next(line for line in out.splitlines() if f" {wanted} " in line)


# ---------------------------------------------------------------- W360 and W361

def test_a_sentence_with_three_ids_warns_and_says_how_to_move_them(mini):
    write_epic(mini, ["A basket sent on CON-001 Sale API and CON-002 Stock level is waiting on UNK-001 Till test rig."])
    assert reading_codes(mini).count("W360") == 1
    line = message(mini, "W360")
    assert "3 IDs" in line and "- Trace:" in line


def test_two_ids_in_a_sentence_do_not_trip_the_crowded_sentence_warning(mini):
    write_epic(mini, ["A basket sent on CON-001 Sale API returns a receipt, and CON-002 Stock level is read."])
    assert "W360" not in reading_codes(mini)


def test_a_bare_id_warns_and_the_fix_names_the_thing(mini):
    write_epic(mini, ["A basket sent on CON-001 returns a receipt with the till's sale number."])
    assert reading_codes(mini) == ["W361"]
    assert "Sale API" in message(mini, "W361")


def test_an_id_followed_by_its_name_does_not_warn(mini):
    write_epic(mini, ["A basket sent on CON-001 Sale API returns a receipt with the till's sale number."])
    assert reading_codes(mini) == []


def test_an_id_inside_a_link_a_code_span_a_trace_line_or_history_does_not_warn(mini):
    write_epic(mini, ["A basket sent over [[shop-building-blocks#CON-001 Sale API|the sale call]] returns a receipt, as `CON-001` says.\n"
                      "   - Trace: CON-001, G1"])
    path = mini / EPIC
    path.write_text(path.read_text(encoding="utf-8") + "\n## History\n\n- The cut was argued over CON-001, CON-002 and G1.\n", encoding="utf-8")
    assert reading_codes(mini) == []


def test_an_id_in_a_table_or_a_heading_is_the_machines_and_does_not_warn(mini):
    write_epic(mini, ["A basket returns a receipt."])
    path = mini / EPIC
    path.write_text(path.read_text(encoding="utf-8") + "\n### The sale call\n\n| Contract | Note |\n|---|---|\n| CON-001 | CON-002 |\n",
                    encoding="utf-8")
    assert reading_codes(mini) == []


# ---------------------------------------------------------------- W362

def bullet_page(count, split_at=None):
    items = [f"- Thing number {n} the person reads" for n in range(1, count + 1)]
    if split_at:
        items.insert(split_at, "\n### The second group\n")
    return "\n".join(items)


def test_a_list_of_ten_under_one_heading_warns_and_subheadings_end_it(mini):
    path = mini / "01-goals.md"
    original = path.read_text(encoding="utf-8")
    path.write_text(original + "\n## Things to read\n\n" + bullet_page(10) + "\n", encoding="utf-8")
    assert reading_codes(mini) == ["W362"]
    assert "subheadings" in message(mini, "W362")
    path.write_text(original + "\n## Things to read\n\n" + bullet_page(10, split_at=5) + "\n", encoding="utf-8")
    assert reading_codes(mini) == []


def test_nine_items_is_not_over_the_limit_and_fact_bullets_do_not_count(mini):
    path = mini / "01-goals.md"
    path.write_text(path.read_text(encoding="utf-8") + "\n## Things to read\n\n" + bullet_page(9)
                    + "\n- **Owner:** @mini-lead\n- **State:** open\n", encoding="utf-8")
    assert reading_codes(mini) == []


# ---------------------------------------------------------------- W363

WALL = ("The till reads the basket and the shop answers with a receipt that the person keeps. " * 4 + "\n\n") * 14


def test_a_long_page_with_no_summary_warns_and_a_summary_ends_it(mini):
    path = mini / "01-goals.md"
    original = path.read_text(encoding="utf-8")
    title = re.search(r"^# .*\n", original, re.M).group(0)
    stripped = original.replace(title, title + "\n## Notes\n\n" + WALL, 1)
    path.write_text(stripped, encoding="utf-8")
    assert reading_codes(mini).count("W363") == 1
    summarised = stripped.replace(title, title + "\nThis page lists what the till reads and what the person keeps. Still open: the receipt format.\n", 1)
    path.write_text(summarised, encoding="utf-8")
    assert "W363" not in reading_codes(mini)


def test_a_short_page_needs_no_summary(mini):
    assert "W363" not in reading_codes(mini)


# ---------------------------------------------------------------- W364

def test_an_epic_with_ten_criteria_warns_once_and_nine_pass(mini):
    write_epic(mini, [f"The till shows result number {n} to the person." for n in range(1, 11)])
    codes = reading_codes(mini)
    assert codes == ["W364"]
    assert "Split" in message(mini, "W364")
    write_epic(mini, [f"The till shows result number {n} to the person." for n in range(1, 10)])
    assert reading_codes(mini) == []


def test_criteria_under_subheadings_still_count_as_the_epics_criteria(mini):
    (mini / "13-epics").mkdir(exist_ok=True)
    groups = ["### First\n\n" + "\n".join(f"{n}. The till shows result {n}." for n in range(1, 6)),
              "### Second\n\n" + "\n".join(f"{n}. The till shows result {n}." for n in range(6, 11))]
    (mini / EPIC).write_text(f"{EPIC_HEAD}{SUMMARY}\n## Epic acceptance criteria\n\n" + "\n\n".join(groups) + EPIC_TAIL, encoding="utf-8")
    run("render", "--vault", str(mini))
    assert reading_codes(mini) == ["W364"]


# ---------------------------------------------------------------- the heron epic

def vault_with(tmp_path, epic):
    vault = tmp_path / "heron"
    shutil.copytree(HERON, vault)
    if epic is not None:
        shutil.copy(epic, vault / EPIC_PATH)
    return vault


def on_epic(out):
    return [c for c, p in findings(out) if p == EPIC_PATH and c in CODES]


def test_the_heron_epic_as_the_session_wrote_it_trips_the_warnings_and_the_rewrite_does_not(tmp_path):
    before = vault_with(tmp_path / "a", None)
    code, out = check(before, "2026-10-12")
    assert code == 0 and set(on_epic(out)) == {"W361"}
    assert len(on_epic(out)) >= 7  # every criterion
    assert any(c == "W360" for c, _ in findings(out))  # and the other epics hold sentences of three or more
    after = vault_with(tmp_path / "b", REWRITTEN)
    code, out = check(after, "2026-10-12")
    assert code == 0 and on_epic(out) == [], out


def test_the_rewrite_keeps_the_traceability_it_had(tmp_path):
    after = vault_with(tmp_path, REWRITTEN)
    code, out = check(after, "2026-10-12")
    assert code == 0
    assert not [c for c, _ in findings(out) if c.startswith("E") or c in ("W501", "W502", "W503", "W504", "W505")], out


# ---------------------------------------------------------------- the Trace line

@pytest.mark.parametrize("line,expected", [
    ("   - Trace: CAP-001.FR1, CON-001, FLO-001", ["CAP-001.FR1", "CON-001", "FLO-001"]),
    ("- Trace: CON-001 FLO-001", ["CON-001", "FLO-001"]),
    ("  * **Trace:** UNK-021", ["UNK-021"]),
    ("- Trace:", []),
    ("- Tracer: CON-001", []),
    ("1. Trace: CON-001", []),
])
def test_trace_ids_reads_the_line_in_every_spelling(line, expected):
    assert readability.trace_ids(line) == expected


def test_style_knows_trace_is_not_prose_and_close_must_not_delete_it(tmp_path):
    vault = vault_with(tmp_path, REWRITTEN)
    code, out = run("style", EPIC_PATH, "--vault", str(vault))
    assert "Trace" not in out and "fact bullet" not in out, out
    text = "# Calendar\n\nA sentence that opens the page with enough words to count.\n\n1. A criterion.\n   - **Trace:** CON-001\n"
    assert reading.style_problems(text, "epic", parse.KNOWN_LABELS.values()) == []


def test_style_flags_an_id_in_a_list_item_and_points_at_the_trace_line():
    text = "# T\n\nA sentence that opens the page with enough words to count.\n\n## Criteria\n\n1. A basket on CON-001 returns a receipt.\n"
    why = [w for _, w in reading.style_problems(text, "epic")]
    assert any("'- Trace:'" in w for w in why), why


def test_query_refs_labels_a_trace_mention(mini):
    write_epic(mini, ["A basket returns a receipt.\n   - Trace: CON-001"])
    result = query.refs(cli.load_vault(mini), "CON-001")
    assert sorted(r["via"] for r in result["refs"] if r["page"] == EPIC) == ["delivers", "link", "trace"]  # the link is the generated traces-to table


def test_old_vaults_that_write_from_cap_in_prose_still_check(tmp_path):
    code, out = check(vault_with(tmp_path, None), "2026-10-12")
    assert code == 0 and "From CAP" in (tmp_path / "heron" / EPIC_PATH).read_text(encoding="utf-8")


# ---------------------------------------------------------------- how the pages read

def test_name_ids_shows_the_name_once_and_leaves_code_and_links_alone():
    class Names:
        def lookup(self, item_id):
            return readability.Entry(item_id, "Sale API", None, "") if item_id == "CON-001" else None

        def name(self, item_id):
            return "Sale API" if item_id == "CON-001" else ""

    shown = readability.name_ids("Send on CON-001 Sale API, not `CON-001` or [[x|CON-001]]; CON-009 stays; (CON-001).", Names(),
                                 lambda e: f"<{e.name}>")
    assert shown == "Send on <Sale API>, not `CON-001` or [[x|CON-001]]; CON-009 stays; (<Sale API>)."


def explore_data(root):
    code, said = run("explore", str(root), "--today", "2026-10-12")
    assert code == 0, said
    text = (root / "dashboard.html").read_text(encoding="utf-8")
    return json.loads(re.search(r'<script type="application/json" id="data">(.*?)</script>', text, re.S).group(1))


def test_the_explorer_shows_a_bare_id_as_its_name_with_the_id_in_the_tooltip(tmp_path):
    vault = vault_with(tmp_path, None)
    data = explore_data(vault)
    html = data["epicCriteria"]["EPC-001"][0]["html"]
    assert 'class="ref idname"' in html and 'title="CON-001"' in html and ">Calendar entries<" in html
    assert re.search(r'>Calendar entries<span class="idsuf"> CON-001</span></a>', html)
    assert not re.search(r"(?<![\"\w>-])CON-001(?![\w\"-])", re.sub(r'<span class="idsuf">.*?</span>', "", html).replace('title="CON-001"', ""))


def test_the_explorer_shows_a_trace_line_as_one_folded_row_of_name_chips(tmp_path):
    vault = vault_with(tmp_path, REWRITTEN)
    data = explore_data(vault)
    criteria = data["epicCriteria"]["EPC-001"]
    assert len(criteria) == 7
    row = criteria[0]["trace"]
    assert row.startswith('<details class="r-trace"><summary>Traces to (3)</summary>') and " open" not in row.split(">")[0]
    assert [m for m in re.findall(r'class="ref chip" data-ref="([^"]+)"', row)] == ["CAP-001.FR1", "CON-001", "FLO-001"]
    assert ">Calendar entries<" in row and ">CON-001<" not in row
    page = data["reader"]["EPC-001"]["html"]
    assert page.count('<details class="r-trace">') == 7 and "Trace:" not in page


def test_a_trace_line_names_nothing_it_cannot_open():
    vault = cli.load_vault(HERON)
    keys = Keys(vault)
    assert chips_html(["CON-001", "NOPE-404"], keys).count("class=\"ref chip\"") == 1
    assert chips_html(["NOPE-404"], keys) == ""


def test_inline_html_leaves_an_unknown_id_and_a_code_span_as_written():
    vault = cli.load_vault(HERON)
    keys = Keys(vault)
    page = vault.page("EPC-001-calendar")
    shown = inline_html("See NOPE-404 and `CON-001`.", keys, page)
    assert "NOPE-404" in shown and "<code>CON-001</code>" in shown and "idname" not in shown


def test_the_offline_viewer_names_ids_and_folds_each_trace_row(tmp_path):
    vault_dir = vault_with(tmp_path, REWRITTEN)
    vault = cli.load_vault(vault_dir)
    names = readability.NameIndex(vault)
    page = vault.page("EPC-001-calendar")
    body = viewer.page_data(page, names)["body"]
    assert body.count("<summary>Traces to (3)</summary>") == 6 and "<summary>Traces to (4)</summary>" in body
    assert "[[heron-building-blocks#CON-001 Calendar entries|Calendar entries]]" in body and "Trace:" not in body
    old = viewer.page_data(vault.page("EPC-002-chosen-folder"), names)["body"]
    assert '<span title="CON-002">' in old and "(CON-002" not in old.split("## Traces to")[0]
    assert viewer.page_data(page)["body"].count("Trace:") == 7  # no names given: the page is shown as written


def test_a_trace_line_stays_beside_its_criterion_not_in_details():
    text = "### A group\n\n1. First criterion.\n   - Trace: CON-001\n2. Second criterion.\n   - Trace: CON-002\n"
    shown = reading.arrange(text)
    assert "Details" not in shown and shown.count("Trace:") == 2


def test_an_also_open_section_folds_like_the_ledger():
    text = "# Unknowns\n\nThree matter now.\n\n## Also open (2)\n\n- One of the rest.\n- Another of the rest.\n\n## Next\n\nText.\n"
    shown = reading.arrange(text)
    assert "<details><summary>Also open (2)</summary>" in shown and shown.index("</details>") < shown.index("## Next")


def test_the_explorer_reader_folds_also_open(tmp_path):
    vault_dir = vault_with(tmp_path, None)
    page = vault_dir / "11-unknowns-and-risks.md"
    page.write_text(page.read_text(encoding="utf-8") + "\n## Also open (2)\n\n- One of the rest.\n- Another of the rest.\n", encoding="utf-8")
    vault = cli.load_vault(vault_dir)
    html = page_reader(vault.page("11-unknowns-and-risks"), Keys(vault))["html"]
    assert '<details class="r-fold"><summary>Also open (2)</summary>' in html


# ---------------------------------------------------------------- the rule is written where sessions read it

def text_of(*parts):
    return (REPO.joinpath(*parts)).read_text(encoding="utf-8")


def test_conventions_and_the_skills_state_the_trace_line_and_the_reading_load():
    conventions = text_of("template", "CONVENTIONS.md")
    for phrase in ("`- Trace: CAP-001.FR1, CON-001, FLO-001`", "Cowan 2001; Miller 1956", "`## Also open (n)`", "W364 warns past nine"):
        assert phrase in conventions, phrase
    assert "Plain names and a page a person can hold" in text_of("plugin", "references", "START.md")
    assert "or a `- Trace:` line, to quiet it" in text_of("plugin", "skills", "close", "SKILL.md")
    assert "split" in text_of("plugin", "skills", "epics", "SKILL.md") and "Trace" in text_of("plugin", "skills", "requirements", "SKILL.md")
    for copy in ("plugin/vault/CONVENTIONS.md", "examples/unified-booking/CONVENTIONS.md", "tests/stub-conventions/CONVENTIONS.md"):
        assert text_of(*copy.split("/")) == conventions, copy
