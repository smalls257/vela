"""`vela prose replace` (overhaul Task 21d): the old paragraph is copied byte for byte under `## Replaced prose` in
the open session record, because a model asked to copy a paragraph word for word tidies it. A plain folder in
tmp_path: the command runs no git, so none is needed."""
import json

from conftest import run
import session_files

MARKER = "<!-- generated:unknowns sha=00000000: do not edit, run vela render -->"

PAGE = "\n".join([
    "---",
    "id: APP-till",
    "type: app",
    "title: Till",
    "---",
    "",
    "# Till",
    "",
    "The till sells **everything** the shop stocks, through [[CON-001|the sale API]].  ",
    "It opens at nine.\t",
    "",
    "## Unknowns",
    "",
    MARKER,
    "- [[UNK-001]] who owns the till",
    "<!-- /generated:unknowns -->",
    "",
    "Second paragraph, plain.",
    "",
])

RECORD_ID = "2026-10-14-till-grill"
RECORD = "\n".join([
    "---",
    "id: 2026-10-14-till-grill",
    "type: session",
    "date: 2026-10-14",
    "modes: [grill]",
    "status: open",
    "summary: In progress.",
    "---",
    "",
    "# 2026-10-14 Grill: till",
    "",
    "## Captures",
    "",
    "- [thought] (@lead) The till opens at ten. ^c01",
    "",
])

FIRST = ("The till sells **everything** the shop stocks, through [[CON-001|the sale API]].  \n"
         "It opens at nine.\t\n")


def make(tmp_path, record=RECORD):
    (tmp_path / "05-building-blocks").mkdir()
    (tmp_path / "05-building-blocks" / "till.md").write_bytes(PAGE.encode("utf-8"))
    session_files.write_record(tmp_path, RECORD_ID, record)


def replace(tmp_path, line, *extra):
    return run("prose", "replace", "--vault", str(tmp_path), "--page", "05-building-blocks/till.md",
               "--line", str(line), "--today", "2026-10-14", *extra)


def test_replace_copies_verbatim(tmp_path):
    make(tmp_path)
    code, output = replace(tmp_path, 10)
    assert code == 0, output
    text = session_files.record_text(tmp_path, RECORD_ID)
    assert text.startswith(RECORD)
    added = text[len(RECORD):]
    assert added == ("\n## Replaced prose\n\nFrom 05-building-blocks/till.md, 2026-10-14:\n\n" + FIRST)
    assert FIRST in session_files.record_text(tmp_path, RECORD_ID)  # bytes equal: `**`, the wikilink, both trailing spaces
    assert (tmp_path / "05-building-blocks" / "till.md").read_bytes() == PAGE.encode("utf-8")  # the page is untouched


def test_no_paragraph_at_line_exits_1(tmp_path):
    make(tmp_path)
    for line in (8, 7, 2, 99):  # blank, a heading, the frontmatter, past the end
        code, output = replace(tmp_path, line)
        assert code == 1, (line, output)
    assert session_files.record_text(tmp_path, RECORD_ID) == RECORD


def test_line_inside_generated_block_refused(tmp_path):
    make(tmp_path)
    for line in (14, 15, 16):
        code, output = replace(tmp_path, line, "--json")
        assert code == 1, output
        assert json.loads(output)["refusals"][0]["rule"] == "generated block"
    assert session_files.record_text(tmp_path, RECORD_ID) == RECORD


def test_second_replace_appends(tmp_path):
    earlier = "From 01-goals.md, 2026-10-13:\n\nThe old goal.\n"
    make(tmp_path, RECORD + "\n## Replaced prose\n\n" + earlier + "\n## Changes\n\nNone yet.\n")
    assert replace(tmp_path, 9)[0] == 0
    assert replace(tmp_path, 18)[0] == 0
    text = session_files.record_text(tmp_path, RECORD_ID)
    assert text.startswith(RECORD + "\n## Replaced prose\n\n" + earlier)  # what was there stays byte for byte
    order = [text.index(earlier), text.index(FIRST), text.index("Second paragraph, plain.\n"), text.index("## Changes")]
    assert order == sorted(order)  # each new entry goes at the end of the section, before the next heading
    assert text.endswith("Second paragraph, plain.\n\n## Changes\n\nNone yet.\n")


def test_heading_created_once(tmp_path):
    make(tmp_path)
    assert replace(tmp_path, 9)[0] == 0
    assert replace(tmp_path, 18)[0] == 0
    assert session_files.record_text(tmp_path, RECORD_ID).count("## Replaced prose") == 1


def test_no_open_record_exits_1_and_several_exit_3(tmp_path):
    make(tmp_path, RECORD.replace("status: open", "status: closed"))
    code, output = replace(tmp_path, 9)
    assert code == 1 and "No session is open" in output
    session_files.write_record(tmp_path, RECORD_ID, RECORD)
    session_files.write_record(tmp_path, "2026-10-14-other", RECORD.replace("till-grill", "other"))
    code, output = replace(tmp_path, 9, "--json")
    assert code == 3, output
    assert [c["id"] for c in json.loads(output)["needs_lead"]] == ["2026-10-14-other", "2026-10-14-till-grill"]
    assert session_files.record_text(tmp_path, RECORD_ID) == RECORD
    code, output = replace(tmp_path, 9, "--record", "2026-10-14-till-grill")
    assert code == 0, output


def test_for_lead_says_no_ids(tmp_path):
    make(tmp_path)
    code, output = replace(tmp_path, 9, "--for-lead")
    assert code == 0, output
    assert "APP-" not in output and "UNK-" not in output


def test_page_outside_vault_exits_2(tmp_path):
    make(tmp_path)
    code, output = run("prose", "replace", "--vault", str(tmp_path), "--page", "../nowhere.md", "--line", "1")
    assert code == 2, output
