"""American spelling, and the vaults written before it.

The toolkit now writes American English. A vault made earlier still says "licences" and opens its cost concern with the
old template line, and a script may still read the old "catalogue" JSON key. Renaming only the new side would not crash;
the checks would just stop noticing, so each old form is fed in here and must still be read. W372 is the other half: it
says, in plain words, when a page's own prose is spelled the British way."""
import json
import shutil

import pytest

from conftest import REPO, check, edit, findings, run

from vela import catalog, cli, readload, spelling

OLD_COST_LINE = "Running cost, licences and shared budgets such as mainframe processing."
NEW_COST_LINE = "Running cost, licenses and shared budgets such as mainframe processing."


def opens_with(vault, line):
    page = vault / "01-goals.md"
    text = page.read_text(encoding="utf-8")
    title = next(row for row in text.split("\n") if row.startswith("# "))
    page.write_text(text.replace(title, f"{title}\n\n{line}", 1), encoding="utf-8")


def codes_on(out, path):
    return [code for code, where in findings(out) if where == path]


# ------------------------------------------------------------------------------ W368 knows the retired British line

def test_the_shipped_template_lines_hold_the_new_cost_line_and_the_retired_one():
    lines = cli.load_template_lines()
    assert NEW_COST_LINE in lines and OLD_COST_LINE in lines
    assert OLD_COST_LINE not in cli.TEMPLATE_LINES.read_text(encoding="utf-8"), "the current list is American"


@pytest.mark.parametrize("line", [OLD_COST_LINE, NEW_COST_LINE])
def test_an_opening_left_from_either_template_still_reads_as_template_text(mini, line):
    opens_with(mini, line)
    _, out = check(mini)
    assert "W368" in codes_on(out, "01-goals.md"), out


def test_a_missing_retired_line_file_is_a_tool_failure(tmp_path, monkeypatch):
    monkeypatch.setattr(cli, "TEMPLATE_LINES_RETIRED", tmp_path / "nope.txt")
    with pytest.raises(cli.ToolError):
        cli.load_template_lines()


# ------------------------------------------------------------------------------ the JSON key, both spellings

@pytest.mark.parametrize("flag", ["--json", "--stats"])
def test_questions_json_carries_catalog_and_the_old_catalogue_key(mini, flag):
    argv = ["questions", "--vault", str(mini), "--json"] + (["--stats"] if flag == "--stats" else [])
    code, out = run(*argv)
    assert code == 0, out
    answer = json.loads(out)
    assert answer["catalog"] == answer["catalogue"] == cli.load_catalog().version


def test_version_keys_name_one_version_twice():
    assert catalog.version_keys(3) == {"catalog": 3, "catalogue": 3}


# ------------------------------------------------------------------------------ W809 still hears "licences"

def test_british_licences_still_raise_the_untyped_subject_warning(tmp_path):
    ub = tmp_path / "unified-booking"
    shutil.copytree(REPO / "examples" / "unified-booking", ub)
    ledger = ub / "11-unknowns-and-risks.md"
    edit(ledger, next(row for row in ledger.read_text(encoding="utf-8").split("\n")
                      if row.startswith("| Q-REG-02@INI-002 |")) + "\n", "")
    cost = ub / "08-concerns" / "concern-cost.md"
    text = cost.read_text(encoding="utf-8")
    cost.write_text(text.replace("licenses", "licences"), encoding="utf-8")
    assert "licences" in cost.read_text(encoding="utf-8")
    run("render", "--vault", str(ub))
    _, out = run("check", "--vault", str(ub), "--today", "2026-11-20")
    assert "W809" in codes_on(out, "08-concerns/concern-cost.md"), out
    assert "'licences' may be an untyped subject" in out


# ------------------------------------------------------------------------------ W372, a British spelling in prose

def test_a_british_spelling_warns_once_per_page_naming_each_word_and_its_american_form(mini):
    opens_with(mini, "The till prints in colour. Colour costs extra, and the centre pays for the colour toner.")
    _, out = check(mini)
    assert codes_on(out, "01-goals.md").count("W372") == 1, out
    line = next(row for row in out.splitlines() if " W372 " in row)
    assert "This page spells 2 words the British way: colour, centre." in line
    assert "Write the American spelling: color, center." in line


def test_american_spelling_is_quiet(mini):
    opens_with(mini, "The till prints in color, and the center pays for the toner.")
    _, out = check(mini)
    assert "W372" not in codes_on(out, "01-goals.md"), out


@pytest.mark.parametrize("text", [
    "> The supplier wrote: the colour toner is late.",  # a quote keeps its source's words
    "The till runs `colour_mode` on boot.",  # code
    "The supplier is on https://example.org/colour-toner today.",  # a URL
    "The Ministry of Defence buys the same till.",  # a name keeps its spelling
    "The supplier rang APP-call-centre about it.",  # an ID names a file
])
def test_quotes_code_urls_names_and_ids_keep_their_spelling(mini, text):
    opens_with(mini, text)
    _, out = check(mini)
    assert "W372" not in codes_on(out, "01-goals.md"), out


def test_history_keeps_the_words_it_was_written_in():
    from vela.parse import parse_page
    text = "---\nid: goals\ntype: initiative-section\ntitle: T\n---\n\n# T\n\nThe till is red.\n\n## History\n\n- 2026-01-01: colour agreed.\n"
    page = parse_page("01-goals.md", text)
    assert readload.spelling_findings(page) == []


def test_the_bundled_list_is_the_map_the_toolkit_used_less_identifiers_and_towards():
    words = spelling.BRITISH_TO_AMERICAN
    assert words["licence"] == "license" and words["catalogue"] == "catalog" and words["practise"] == "practice"
    assert not {"darkslategrey", "callcentre", "harbourline", "towards", "analyses", "programmer"} & set(words)
    assert all(british != american for british, american in words.items())
