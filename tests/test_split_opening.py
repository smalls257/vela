"""S50: a page kept two openings that disagree. W371 warns for two or more prose paragraphs above the first `##`
heading that together run past the opening limit; ordinary short two-paragraph openings stay quiet."""
import shutil

from conftest import REPO, check, findings, skill_text

from vela import cli, readload, schema

PLUGIN = REPO / "plugin"
HEAD = """---
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
TAIL = """
## Traces to

<!-- generated:traces-to sha=00000000: do not edit, run vela render -->
<!-- /generated:traces-to -->
"""
EPIC = "13-epics/EPC-001-sell-at-the-till.md"


def words(count, start=0):
    return " ".join(f"item{n}" for n in range(start, start + count)) + "."


def write_epic(vault, opening, body="## Notes\n\nA short note about the till and the shop that the team keeps.\n"):
    (vault / "13-epics").mkdir(exist_ok=True)
    (vault / EPIC).write_text(HEAD + opening + "\n" + body + TAIL, encoding="utf-8")


def w371(vault):
    code, out = check(vault)
    assert code == 0, out  # a warning, never an error
    return [line for line in out.splitlines() if " W371 " in line]


def test_two_openings_that_restate_the_release_warn_at_the_second_one(mini):
    first = "The first release is assumed to be a laptop-only note that reads the calendar. " + words(80)
    second = "The first release is a note that reads the calendar and the Teams transcripts. " + words(80, 100)
    write_epic(mini, f"{first}\n\n{second}\n")
    lines = w371(mini)
    assert len(lines) == 1
    assert f"{EPIC}:17: W371" in lines[0] and "2 intro paragraphs before its first heading" in lines[0]
    assert "Keep one intro" in lines[0]


def test_what_a_page_does_and_what_it_does_not_own_is_an_ordinary_opening_and_stays_quiet(mini):
    write_epic(mini, f"{words(35)}\n\n{words(35, 100)}\n")
    assert w371(mini) == []
    write_epic(mini, f"{words(60)}\n\n{words(39, 100)}\n")  # 99 words: the unified-booking Booking page
    assert w371(mini) == []
    write_epic(mini, f"{words(75)}\n\n{words(75, 100)}\n")  # 150 words, the most one body paragraph may hold
    assert w371(mini) == []
    write_epic(mini, f"{words(75)}\n\n{words(76, 100)}\n")
    assert len(w371(mini)) == 1
    assert schema.PARAGRAPH_WORD_LIMIT == 150  # the rule borrows W365's limit and has no number of its own


def test_one_opening_never_warns_however_long_and_a_label_line_is_not_an_opening(mini):
    write_epic(mini, words(120) + "\n")  # W365's business, not W371's
    assert w371(mini) == []
    write_epic(mini, words(100) + "\n\n**Domain:** Sell\n\nToo short.\n")
    assert w371(mini) == []  # a label and a two-word line are not paragraphs of real words, so this is one opening


def test_a_list_between_the_paragraphs_does_not_make_them_one_opening(mini):
    write_epic(mini, f"{words(80)}\n\n- one thing\n- another\n\n{words(80, 100)}\n")
    assert len(w371(mini)) == 1


def test_paragraphs_under_a_heading_are_not_openings(mini):
    write_epic(mini, words(40) + "\n", body=f"## Notes\n\n{words(100, 100)}\n\n{words(100, 200)}\n")
    assert w371(mini) == []


def test_an_index_and_the_glossary_are_exempt(mini):
    terms = "\n\n".join(f"**Term{n}** means {words(20, n * 30)}" for n in range(6))
    (mini / "12-glossary.md").write_text(
        f"---\nid: glossary\ntype: initiative-section\ntitle: Glossary\nstate: inkling\nowner: \"@mini/shop-team\"\nauthored: authored\n---\n\n# Glossary\n\n{terms}\n",
        encoding="utf-8")
    assert w371(mini) == []
    page = cli.parse.parse_page("13-things.md", f"---\nid: things\ntype: index\ntitle: Things\nauthored: authored\n---\n\n# Things\n\n{words(100)}\n\n{words(100, 200)}\n")
    assert readload.split_opening_findings(page) == []


def test_the_heron_strategy_page_has_the_warning():
    vault = REPO / "tests" / "fixtures" / "team-skills" / "heron"
    code, out = check(vault)
    lines = [line for line in out.splitlines() if " W371 " in line]
    assert any(line.startswith("04-solution-strategy.md:17: W371 The page has 3 intro paragraphs") for line in lines), out


def test_the_template_and_the_example_stay_free_of_errors_and_the_template_stays_without_the_warning():
    code, out = check(REPO / "template")
    assert code == 0 and " W371 " not in out


def test_every_conventions_copy_explains_the_code():
    for folder in ("template", "plugin/vault", "examples/unified-booking", "tests/stub-conventions"):
        text = (REPO / folder / "CONVENTIONS.md").read_text(encoding="utf-8")
        assert "| W371 | two or more openings above the first heading, over 150 words together |" in text, folder
        assert "W371 fires on a page that keeps two or more separate openings" in text, folder


def test_close_replaces_the_opening_it_rewrites_instead_of_adding_one():
    text = skill_text("close")
    assert "A page has one opening: the one you rewrite replaces the old one, and you never write a new opening beside it." in text
    assert "draw W371; keep one and fold what the others add under a heading." in text
    assert "W363, W365, W368 and W371" in text
