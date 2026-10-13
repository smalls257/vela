"""Two readers of one format must agree, and a failure must be seen (Silent Fallback). One test per ledger ID of the
platform review's core group; each failed before its fix."""
import csv
import io
import shutil

import pytest

from conftest import REPO, check, edit, findings, run
from planner import breakdown, completeness, links, parse, releases, render
from planner.cli import load_vault

SHOP = "05-building-blocks/shop-building-blocks.md"
UNKNOWNS = "11-unknowns-and-risks.md"
GOALS = "01-goals.md"
UB = REPO / "examples" / "unified-booking"
TODAY = "2026-11-20"


def codes(out, path=None):
    return sorted(c for c, p in findings(out) if path is None or p == path)


# --------------------------------------------------------------------------- C5

@pytest.mark.parametrize("old, new", [
    ("### UNK-001 Till test rig", "### UNK-12 Till test rig"),
    ("### UNK-001 Till test rig", "### UNK-001: Till test rig"),
    ("### UNK-001 Till test rig", "### unk-001 Till test rig"),
])
def test_c5_a_malformed_item_heading_is_an_error_not_plain_text(mini, old, new):
    edit(mini / UNKNOWNS, old, new)
    code, out = check(mini)
    assert "E810" in codes(out, UNKNOWNS), out
    assert code == 1


def test_c5_a_contract_heading_with_a_colon_is_caught(mini):
    edit(mini / SHOP, "### CON-001 Sale API", "### CON-001: Sale API")
    _, out = check(mini)
    assert "E810" in codes(out, SHOP), out


# --------------------------------------------------------------------------- C6

def test_c6_a_second_frontmatter_key_is_refused(mini):
    edit(mini / SHOP, "state: decided\n", "state: decided\nstate: inkling\n")
    _, out = check(mini)
    assert "E102" in codes(out, SHOP) and "second 'state:'" in out


def test_c6_a_repeated_fact_bullet_names_the_ignored_line(mini):
    edit(mini / SHOP, "- **Consumers:** [[till-building-blocks|Till]]",
         "- **State:** assumption\n- **Consumers:** [[till-building-blocks|Till]]")
    _, out = check(mini)
    assert "E209" in codes(out, SHOP), out
    assert "is ignored" in out


# --------------------------------------------------------------------------- C7

def test_c7_w329_keeps_its_line_after_a_unicode_line_separator(mini):
    row = "| G2 | Sell [[till-building-blocks|Till]] things | Some | decided |\n"
    edit(mini / GOALS, "# Mini shop\n", "# Mini shop  pasted\n")
    edit(mini / GOALS, "| G1 | Sell from one till | One till sells every product | decided |\n",
         "| G1 | Sell from one till | One till sells every product | decided |\n" + row)
    _, out = check(mini)
    want = next(n for n, ln in enumerate((mini / GOALS).read_text(encoding="utf-8").split("\n"), 1) if ln.startswith("| G2 |"))
    assert f"{GOALS}:{want}: W329" in out, out


@pytest.mark.parametrize("separator", ["\x0b", "\x0c", "\x1c", "\x85", " ", " "])
def test_c7_lines_of_splits_on_newline_alone(separator):
    assert parse.lines_of(f"a{separator}b\r\nc") == [f"a{separator}b", "c"]


# --------------------------------------------------------------------------- C11

def test_c11_a_fence_with_an_info_string_does_not_close_the_outer_fence():
    text = "---\nid: x\n---\n```md\n```python\ncode\n```\n\n- **Owner:** @a\n"
    page = parse.parse_page("x.md", text)
    assert [b.label for b in page.bullets] == ["Owner"]
    assert not page.errors


def test_c11_inline_code_at_line_start_is_not_a_fence():
    page = parse.parse_page("x.md", "---\nid: x\n---\n```a``` inline\n\n- **Owner:** @a\n")
    assert [b.label for b in page.bullets] == ["Owner"] and not page.errors


def test_c11_reading_and_parse_share_one_closing_rule():
    from planner import reading
    assert reading.closes_fence is parse.closes_fence
    assert not parse.closes_fence("```python", "```")
    assert parse.closes_fence("  ````  ", "```")
    assert not parse.closes_fence("~~~", "```")


# --------------------------------------------------------------------------- C12

PLAN = REPO / "tests" / "fixtures" / "breakdown" / "desk-agent-breakdown.md"


@pytest.mark.parametrize("prefix, crlf", [("", True), ("﻿", False), ("﻿", True)])
def test_c12_a_breakdown_with_crlf_or_a_bom_reads_as_the_lf_file_does(prefix, crlf):
    text = PLAN.read_text(encoding="utf-8")
    text = text.replace("\r\n", "\n")
    plain = breakdown.read(text)
    variant = prefix + (text.replace("\n", "\r\n") if crlf else text)
    got = breakdown.read(variant)
    assert got["meta"] == plain["meta"] and got["meta"].get("status")
    assert got["problems"] == plain["problems"]


def test_c12_a_missing_frontmatter_says_so_not_status_is_none():
    plan = breakdown.read("# Plan\n\n### S-01 One\n")
    assert any("no frontmatter was read" in p for p in plan["problems"]), plan["problems"]
    assert not any("is None" in p for p in plan["problems"])


def test_c12_an_escaped_pipe_stays_in_its_cell():
    assert breakdown.cells("| Task a \\| b | M | Comp |") == ["Task a | b", "M", "Comp"]


# --------------------------------------------------------------------------- C30

def test_c30_a_cell_that_starts_like_a_formula_is_written_as_text():
    rows = [{"Issue Id": "S-01", "Summary": "=HYPERLINK(\"http://x\")", "Description": "+cmd", "Issue Type": "Story",
             "Parent": "", "Story Points": 5, "labels": [], "Blocked by": "@x"}]
    got = list(csv.reader(io.StringIO(breakdown.csv_text(rows))))[1]
    assert got[1].startswith("'=") and got[2].startswith("'+") and got[5] == "5"


# --------------------------------------------------------------------------- C17, C19, C23, C27

def ub_copy(tmp_path):
    dest = tmp_path / "ub"
    shutil.copytree(UB, dest)
    return dest


def test_c17_a_page_level_override_clears_a_decided_allocation_row(tmp_path):
    from test_releases import ROW, APP, FR, CAP
    vault = ub_copy(tmp_path)
    (vault / CAP).write_text((vault / CAP).read_text(encoding="utf-8").rstrip("\n") + "\n" + FR, encoding="utf-8")
    app = vault / APP
    app.write_text(app.read_text(encoding="utf-8").rstrip("\n") + "\n" + ROW.replace("| assumption |\n", "| decided |\n"),
                   encoding="utf-8")
    edit(app, "- **Decision:** [[2026-09-09-booking-containers]]\n", "Booking holds seats.\n")
    before = run("check", "--vault", str(vault), "--today", TODAY)[1]
    row_line = [ln for ln in before.splitlines() if ln.startswith(APP) and " E303 " in ln and "@APP-booking" in ln]
    assert row_line, before
    edit(app, "Booking holds seats.\n", "- **Override:** grill by @hl-solution-lead on 2026-11-20: the lead accepted the share without a Grill\n")
    after = run("check", "--vault", str(vault), "--today", TODAY)[1]
    assert not [ln for ln in after.splitlines() if ln.startswith(APP) and " E303 " in ln and "@APP-booking" in ln], after
    assert [ln for ln in after.splitlines() if ln.startswith(APP) and " W303 " in ln and "@APP-booking" in ln], after


def test_c19_a_retired_app_exists_today(tmp_path):
    vault = ub_copy(tmp_path)
    edit(vault / "05-building-blocks" / "pricing-building-blocks.md", "change: changed", "change: retired")
    assert releases.snapshots(load_vault(vault))[0]["apps"]["APP-pricing"] == "exists"


def test_c23_a_prose_section_on_the_releases_page_is_not_a_release(tmp_path):
    from test_releases import vault_with, release, LINK
    vault = vault_with(tmp_path, release("Release one", [f"{LINK} | all | "]) + "## Open questions\n\nWho signs off?\n")
    assert [r.name for r in releases.releases(load_vault(vault))] == ["Release one"]
    out = run("check", "--vault", str(vault), "--today", TODAY)[1]
    assert "E342" not in out and "E344" not in out, out


def test_c27_a_release_set_to_decided_needs_a_grill(tmp_path):
    from test_releases import vault_with, release, LINK
    vault = vault_with(tmp_path, release("Release one", [f"{LINK} | all | "], state="decided"))
    out = run("check", "--vault", str(vault), "--today", TODAY)[1]
    assert [ln for ln in out.splitlines() if "04b-releases.md" in ln and " E303 " in ln and "Release one" in ln], out


# --------------------------------------------------------------------------- C18

def test_c18_a_share_with_nothing_to_count_stays_out_of_the_mean():
    empty, half = completeness.Share("a", 0, 0), completeness.Share("b", 1, 2)
    assert empty.ratio is None and half.ratio == 0.5


def test_c18_an_untouched_template_is_not_43_percent(tmp_path):
    vault = tmp_path / "t"
    shutil.copytree(REPO / "template", vault)
    (vault / ".planner.yaml").write_text("initiative: INI-001\ntitle: New\n", encoding="utf-8")
    percent, _ = completeness.measure(load_vault(vault))
    assert percent < 20


# --------------------------------------------------------------------------- C24

def test_c24_a_title_with_a_pipe_is_escaped_in_every_generated_link():
    assert render.link("till", "Till | Tills") == "[[till\\|Till \\| Tills]]"
    assert render.link("till", render.cell("Till | Tills")) == "[[till\\|Till \\| Tills]]"


def test_c24_render_leaves_the_vault_valid_when_a_title_holds_a_pipe(mini):
    edit(mini / SHOP, "title: Shop\n", "title: Shop | Tills\n")
    assert run("render", "--vault", str(mini))[0] == 0
    code, out = check(mini)
    assert "W329" not in out and "E4" not in out, out
    assert "Shop \\| Tills" in (mini / GOALS).read_text(encoding="utf-8")


# --------------------------------------------------------------------------- C25

def test_c25_a_url_with_balanced_parentheses_keeps_its_end():
    class Item:
        id = "CON-001"
        facts = {"Links": type("B", (), {"value": "[Spec](https://en.wikipedia.org/wiki/Foo_(bar)), [Docs](https://d.example/x)"})()}
    found, problems = links.of_item(Item)
    assert [l.url for l in found] == ["https://en.wikipedia.org/wiki/Foo_(bar)", "https://d.example/x"], problems


# --------------------------------------------------------------------------- C20, C31

def test_c20_an_empty_frontmatter_block_is_reported(mini):
    (mini / SHOP).write_text("---\n---\n\n# Shop\n", encoding="utf-8")
    _, out = check(mini)
    assert "E101" in codes(out, SHOP), out


def test_c31_a_null_id_and_owner_give_one_clear_finding(mini):
    edit(mini / SHOP, "id: APP-shop\n", "id:\n")
    edit(mini / SHOP, 'owner: "@mini/shop-team"\n', "owner:\n")
    _, out = check(mini)
    mine = [ln for ln in out.splitlines() if ln.startswith(SHOP)]
    assert not any("'None'" in ln for ln in mine), mine
    assert any("E103" in ln and "'id'" in ln for ln in mine), mine


# --------------------------------------------------------------------------- C22, T12

def test_c22_a_second_row_for_one_goal_id_is_reported(mini):
    edit(mini / GOALS, "| G1 | Sell from one till | One till sells every product | decided |\n",
         "| G1 | Sell from one till | One till sells every product | decided |\n| G1 | Another | x | inkling |\n")
    _, out = check(mini)
    assert "E210" in codes(out, GOALS), out


def test_t12_two_rows_for_one_app_on_a_concern_page_are_reported(mini):
    edit(mini / "08-concerns/concern-testing.md", "| [[stock-building-blocks\\|Stock]] | unchanged | Existing tests hold |\n",
         "| [[stock-building-blocks\\|Stock]] | unchanged | Existing tests hold |\n| [[stock-building-blocks\\|Stock]] | addressed | again |\n")
    _, out = check(mini)
    assert "E210" in codes(out, "08-concerns/concern-testing.md"), out


# --------------------------------------------------------------------------- C32

def test_c32_every_finding_code_the_library_writes_is_listed_in_codes():
    import re
    from planner import schema
    used = set()
    for path in (REPO / "plugin" / "lib" / "planner").rglob("*.py"):
        used.update(re.findall(r'"([EW]\d{3})"', path.read_text(encoding="utf-8")))
    assert sorted(used - set(schema.CODES)) == []


@pytest.mark.parametrize("prefix, expected", [("ADR", "ADR-0001"), ("R", "R-01"), ("PTY", "PTY-01"), ("UNK", "UNK-001")])
def test_c32_next_id_hands_out_an_id_its_own_check_accepts(prefix, expected):
    from planner import ids, schema
    got = ids.next_id(prefix, [])
    assert got == expected
    pattern = {"ADR": schema.PAGE_ID_RE["decision"], "R": schema.ITEM_ID_RE, "PTY": schema.ITEM_ID_RE}.get(prefix)
    assert pattern is None or pattern.match(got)
