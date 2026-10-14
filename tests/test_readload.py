"""The second five reading-load warnings (design session 16): a paragraph, a table cell, a stock phrase, a template opening
and an abbreviation that costs the reader more than a careful writer would. Warnings only, each with a plain fix line."""
import pathlib

import pytest
from conftest import REPO, check, findings

from vela import cli, readload, schema

CODES = ("W365", "W366", "W367", "W368", "W369")
HEAD = """---
id: EPC-{n}
type: epic
title: Epic number {n}
initiative: INI-900
state: draft
owner: "@mini/shop-team"
authored: mixed
apps: [APP-shop]
delivers: [CON-001]
---

# Epic number {n}

"""
TAIL = """
## Traces to

<!-- generated:traces-to sha=00000000: do not edit, run vela render -->
<!-- /generated:traces-to -->
"""


def words(count, start=0):
    """Distinct words, so a long paragraph is not also a repeated phrase."""
    return " ".join(f"item{n}" for n in range(start, start + count)) + ". "




def opening(number):
    """A summary no other page shares, so one page's opening is never the repeated phrase under test."""
    return f"Page {number} is about topic{number}x while area{number}y waits.\n"


def write_page(vault, number, body, summary=None):
    folder = vault / "13-epics"
    folder.mkdir(exist_ok=True)
    path = folder / f"EPC-{number:03d}-epic-{number}.md"
    path.write_text(HEAD.format(n=f"{number:03d}") + (summary or opening(number)) + "\n" + body + TAIL, encoding="utf-8")
    return path


def codes(vault):
    code, out = check(vault)
    assert code == 0, out
    return [c for c, _ in findings(out) if c in CODES]


def line_for(vault, wanted):
    _, out = check(vault)
    return next(line for line in out.splitlines() if f" {wanted} " in line)


# ------------------------------------------------------------------------------------------------ W365

def test_a_paragraph_over_150_words_warns_and_says_where_to_split(mini):
    write_page(mini, 1, "## Notes\n\n" + words(151) + "\n")
    assert codes(mini) == ["W365"]
    line = line_for(mini, "W365")
    assert "words" in line and "Split at the second topic" in line


def test_a_paragraph_of_exactly_150_words_passes(mini):
    write_page(mini, 1, "## Notes\n\n" + words(150) + "\n")
    assert codes(mini) == []


def test_four_links_in_a_paragraph_warn_and_three_pass(mini):
    links = " ".join(f"[[shop-building-blocks|shop {n}]]" for n in range(1, 5))
    write_page(mini, 1, f"## Notes\n\nThe till reads {links}.\n")
    assert codes(mini) == ["W365"]
    assert "4 links" in line_for(mini, "W365")
    write_page(mini, 1, "## Notes\n\nThe till reads " + " ".join(f"[[shop-building-blocks|shop {n}]]" for n in range(1, 4)) + ".\n")
    assert codes(mini) == []


def test_the_opening_is_held_to_a_tighter_limit_than_a_body_paragraph(mini):
    long_opening = words(120) + "\n"  # under 150, over the opening's 90
    write_page(mini, 1, "## Notes\n\nA short note about the till and the shop that is read by the person.\n", summary=long_opening)
    assert codes(mini) == ["W365"]
    assert "The opening" in line_for(mini, "W365")
    write_page(mini, 1, "## Notes\n\n" + words(120, 500) + "\n")
    assert codes(mini) == []


def test_lists_tables_trace_lines_and_history_are_not_paragraphs(mini):
    items = "\n".join(f"- {words(160, 1000 * n)}" for n in range(2))
    body = f"## Notes\n\n{items}\n\n## History\n\n{words(160, 5000)}\n"
    write_page(mini, 1, body)
    assert codes(mini) == []


# ------------------------------------------------------------------------------------------------ W366

def table(cell):
    return f"## Notes\n\n| Part | Share |\n|---|---|\n| The till | {cell} |\n"


def test_a_cell_over_40_words_warns_and_40_pass(mini):
    write_page(mini, 1, table(words(41)))
    assert codes(mini) == ["W366"]
    assert "Split it into rows of one point each" in line_for(mini, "W366")
    write_page(mini, 1, table(words(40)))
    assert codes(mini) == []


def test_a_cell_inside_a_generated_block_or_history_is_not_the_writers(mini):
    write_page(mini, 1, "## History\n\n| Part | Share |\n|---|---|\n| The till | " + words(60) + " |\n")
    assert codes(mini) == []


# ------------------------------------------------------------------------------------------------ W367

STAMP = "Whether the shop accepts a basket is still open as a question."


def six_pages(vault, sentence=STAMP, pages=6):
    for n in range(1, pages + 1):
        write_page(vault, n, f"## Notes\n\nThe till number {n} reads topic{n}z. {sentence}\n")


def test_a_clause_on_six_pages_is_reported_once_with_the_pages(mini):
    six_pages(mini)
    assert codes(mini) == ["W367"]
    _, out = check(mini)
    stamped = [line for line in out.splitlines() if " W367 " in line]
    assert len(stamped) == 1 and "is still open as" in stamped[0] and "6 pages" in stamped[0]
    assert "EPC-001-epic-1" in stamped[0] and "EPC-006-epic-6" in stamped[0]
    assert "Say the state once" in stamped[0]


def test_five_pages_with_the_clause_once_each_pass(mini):
    six_pages(mini, pages=5)
    assert codes(mini) == []


def test_eleven_uses_on_one_page_report(mini):
    write_page(mini, 1, "## Notes\n\n" + "\n\n".join(f"Part {n} of the work is still open as a question." for n in range(11)) + "\n")
    assert codes(mini) == ["W367"]


def test_a_phrase_that_is_a_name_is_not_a_stamp(mini):
    six_pages(mini, sentence="Gift voucher and refund.")
    assert codes(mini) == ["W367"]  # no page is called that, so it reads as stamped
    for n in range(1, 7):
        page = mini / "13-epics" / f"EPC-{n:03d}-epic-{n}.md"
        page.write_text(page.read_text(encoding="utf-8").replace("title: Epic number", "title: Gift voucher and refund number"), encoding="utf-8")
    assert codes(mini) == []  # a page is called that: repeating it is how a page refers to a thing


def test_history_tables_and_fact_bullets_do_not_count_toward_a_phrase(mini):
    for n in range(1, 7):
        write_page(mini, n, f"## Notes\n\nThe till number {n} reads topic{n}z.\n\n- **Note:** {STAMP}\n\n"
                            f"| A | B |\n|---|---|\n| {STAMP} | x |\n\n## History\n\n{STAMP}\n")
    assert codes(mini) == []


# ------------------------------------------------------------------------------------------------ W368

TEMPLATE_LINE = "Every capability this initiative changes. Each capability page holds what provides it today and after."


def test_an_opening_that_is_a_template_line_warns_and_a_written_one_does_not(mini):
    page = mini / "01-goals.md"
    text = page.read_text(encoding="utf-8")
    title = next(line for line in text.split("\n") if line.startswith("# "))
    page.write_text(text.replace(title, f"{title}\n\n{TEMPLATE_LINE}", 1), encoding="utf-8")
    assert "W368" in codes(mini)
    assert "Replace it with what is actually true for this project now" in line_for(mini, "W368")
    page.write_text(text.replace(title, f"{title}\n\nThe till costs about nine pounds a day to run, and nobody has agreed who pays.", 1), encoding="utf-8")
    assert "W368" not in codes(mini)


def template_corpus():
    root = REPO / "template"
    return readload.template_corpus((path.relative_to(root).parts, path.read_text(encoding="utf-8"))
                                    for path in sorted(root.rglob("*.md")))


def test_the_shipped_template_lines_are_the_template_pages():
    shipped = [line for line in cli.TEMPLATE_LINES.read_text(encoding="utf-8").split("\n") if line]
    assert shipped == template_corpus(), (
        "plugin/catalog/template-lines.txt is out of date; rewrite it from test_readload.template_corpus()")


def test_a_missing_template_line_file_is_a_tool_failure_not_an_empty_list(tmp_path):
    with pytest.raises(cli.ToolError):
        cli.load_template_lines(tmp_path / "nope.txt")


# ------------------------------------------------------------------------------------------------ W369

def test_an_abbreviation_not_spelled_out_warns_once_per_page(mini):
    write_page(mini, 1, "## Notes\n\nThe CISO reads the pack, and the CISO signs it.\n")
    assert codes(mini) == ["W369"]
    line = line_for(mini, "W369")
    assert "CISO" in line and "Write out what CISO stands for" in line


@pytest.mark.parametrize("text", [
    "The Chief Information Security Officer (CISO) reads the pack, and the CISO signs it.",
    "The CISO (Chief Information Security Officer) reads the pack.",
    "The CISO reads the pack. The Chief Information Security Officer (CISO) signs it.",
    "The till is an IT matter, and the PC in the shop runs it.",
])
def test_an_abbreviation_spelled_out_or_understood_does_not_warn(mini, text):
    write_page(mini, 1, f"## Notes\n\n{text}\n")
    assert codes(mini) == []


def test_ids_links_and_code_are_not_abbreviations(mini):
    write_page(mini, 1, "## Notes\n\nThe till calls CON-001 through [[shop-building-blocks|the shop page]] and `SQL` runs inside.\n")
    assert codes(mini) == []


def test_limits_live_in_one_place():
    assert (schema.PARAGRAPH_WORD_LIMIT, schema.PARAGRAPH_LINK_LIMIT, schema.CELL_WORD_LIMIT) == (150, 3, 40)
    assert schema.OPENING_WORD_LIMIT < schema.PARAGRAPH_WORD_LIMIT


# ------------------------------------------------------------------------------------------------ the Heron unknowns page

SNAPSHOTS = REPO / "tests" / "sim" / "snapshots" / "heron-desk"


@pytest.mark.parametrize("snapshot", ["after-design-2", "after-full-1"])
def test_the_heron_unknowns_opening_that_lists_every_question_trips_the_opening_limit(snapshot):
    """The opening runs a chain of every open question inline. A list page's opening counts and points; it never
    enumerates the list, and W365's opening limit is what notices when it does."""
    _, out = check(SNAPSHOTS / snapshot, today="2026-10-12")
    opening = [line for line in out.splitlines() if line.startswith("11-unknowns-and-risks.md:") and " W365 " in line]
    assert len(opening) == 1 and "The opening runs" in opening[0]


def test_an_opening_that_counts_and_points_passes(mini):
    summary = ("Twenty-eight questions are open. Three hold up the first release, and the most urgent is who owns Heron, "
               "due 23 October. The table below lists the rest, each with who is asked and when.\n")
    write_page(mini, 1, "## Notes\n\nThe till reads one thing.\n", summary=summary)
    assert codes(mini) == []


# ------------------------------------------------------------------------------------------------ the lint word list (16-D2)

LINT = REPO / "plugin" / "references" / "lint-words.txt"
PROSE_WITH_WORDS = ("# Till\n\nThe till is robust and it leverages the shop. It is a robust design.\n")


def test_style_lists_each_lint_word_once_with_its_count():
    from vela import reading
    words = reading.lint_words(LINT.read_text(encoding="utf-8"))
    problems = [why for _, why in reading.style_problems(PROSE_WITH_WORDS, "epic", (), words)]
    assert [p for p in problems if "'robust'" in p] == ["'robust' is on the list of words to avoid and appears 2 times on this page; say what the thing does in plain words"]
    assert any("'leverage'" in p and "once" in p for p in problems)


def test_lint_words_match_endings_and_phrases_and_nothing_inside_a_longer_word():
    from vela import reading
    assert reading.lint_pattern("leverage").search("It is leveraging the shop")
    assert reading.lint_pattern("ensure").search("Ensures a receipt")
    assert reading.lint_pattern("going forward").search("Going  forward we")
    assert not reading.lint_pattern("ensure").search("insurer")
    assert not reading.lint_pattern("robust").search("robustness")


def test_the_cli_reads_the_one_word_list(tmp_path, mini):
    page = mini / "01-goals.md"
    text = page.read_text(encoding="utf-8")
    title = next(line for line in text.split("\n") if line.startswith("# "))
    page.write_text(text.replace(title, f"{title}\n\nThe till is a seamless way to pay for things at the shop.", 1), encoding="utf-8")
    from conftest import run
    code, out = run("style", "--vault", str(mini), "01-goals")
    assert code == 1 and "'seamless' is on the list of words to avoid" in out


def test_a_missing_word_list_is_a_tool_failure_not_an_empty_list(tmp_path):
    with pytest.raises(cli.ToolError):
        cli.load_lint_words(tmp_path / "nope.txt")


def test_the_drafting_instructions_never_name_a_listed_word():
    """Naming a word in a prompt raises its odds, so the list lives in the lint and the reviewer, and the drafter never
    sees it: not in house-voice, not in close, not in epics."""
    from vela import reading
    words = reading.lint_words(LINT.read_text(encoding="utf-8"))
    for relative in ("skills/house-voice/SKILL.md", "skills/close/SKILL.md", "skills/epics/SKILL.md", "skills/allocate/SKILL.md"):
        text = (REPO / "plugin" / relative).read_text(encoding="utf-8")
        for word in words:
            assert not reading.lint_pattern(word).search(text.replace("lint-words.txt", "")), f"{relative} names '{word}'"


def test_the_reviewer_reads_the_list_from_the_same_file():
    text = (REPO / "plugin" / "agents" / "voice-reviewer.md").read_text(encoding="utf-8")
    assert "references/lint-words.txt" in text
    from vela import reading
    for word in reading.lint_words(LINT.read_text(encoding="utf-8")):
        assert f'"{word}"' not in text
