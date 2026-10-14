"""`planner conventions "<section>"` prints one section of CONVENTIONS.md, and the check-codes table there is the one
`schema.CODES` holds (overhaul Task 30)."""
import json
import shutil

import pytest

from conftest import REPO, run
from planner import cli, conventions, schema

COPIES = ("template", "plugin/vault", "examples/unified-booking", "tests/stub-conventions")
TEMPLATE = REPO / "template"
TEXT = (TEMPLATE / "CONVENTIONS.md").read_text(encoding="utf-8")

# The sections the skills and references name. Each must be one exact heading, or the citation sends the model to
# a near-match list instead of the rule.
CITED = ("Overrides", "Pages", "Fact bullets", "Slices", "Releases", "Handoff", "Concern cells and waivers",
         "Questions and the ledger", "Pending approval", "Links out of the vault", "Flow steps", "Flow check",
         "Frontmatter", "IDs", "Fact tables", "Generated blocks", "Requirements and allocation", "Team design docs",
         "Sessions", "Areas and stages", "Voice examples")


def test_section_found_exactly():
    code, out = run("conventions", "fact bullets", "--vault", str(TEMPLATE))
    assert code == 0
    first, body = out.split("\n", 1)
    assert first.startswith("From the vault's CONVENTIONS.md")
    assert body.startswith("## Fact bullets\n")
    assert "\n## Overrides" not in body  # stops at the next heading of its level
    code, out = run("conventions", "## Overrides", "--vault", str(TEMPLATE), "--json")
    data = json.loads(out)
    assert code == 0 and data["section"] == "Overrides" and data["source"] == "vault" and data["words"] > 100


def test_near_match_lists_candidates_and_exits_1():
    code, out = run("conventions", "The ledger", "--vault", str(TEMPLATE))
    assert code == 1
    assert out.startswith('No section called "The ledger".')
    assert "- Questions and the ledger" in out
    near = [line for line in out.splitlines() if line.startswith("- ")]
    assert 1 <= len(near) <= 5
    code, out = run("conventions", "Overides", "--vault", str(TEMPLATE), "--json")
    assert code == 1 and "Overrides" in json.loads(out)["near"]


def test_not_found_never_prints_the_whole_file():
    code, out = run("conventions", "zzz nothing like it", "--vault", str(TEMPLATE))
    assert code == 1
    assert len(out.split()) < 60, out
    assert "## " not in out
    code, out = run("conventions", "--vault", str(TEMPLATE))  # no section named at all
    assert code == 1 and len(out.split()) < 30


def test_headings_inside_code_fences_are_not_sections():
    text = "# Doc\n\nIntro.\n\n## Real\n\nBody.\n\n```\n# Example title\n## Overrides\n```\n\nMore body.\n\n## Next\n\nEnd.\n"
    found = conventions.sections(text)
    assert [s.title for s in found] == ["Doc", "Real", "Next"]
    assert "## Overrides" in found[1].text and "More body." in found[1].text
    assert found[0].text == "# Doc\n\nIntro."  # the title holds only its opening, never the whole file
    # In the real file, the slice example's `## Overrides` is not a second Overrides section.
    titles = [s.title for s in conventions.sections(TEXT)]
    assert titles.count("Overrides") == 1 and "Not in this slice" not in titles


def test_every_section_the_skills_cite_resolves():
    found = conventions.sections(TEXT)
    for name in CITED:
        assert conventions.section(found, name) is not None, name
    code, out = run("conventions", "--list", "--vault", str(TEMPLATE))
    assert code == 0
    for name in CITED:
        assert any(line.strip().startswith(f"{name} (") for line in out.splitlines()), name


def test_generated_codes_table_equals_schema():
    for code, meaning in schema.CODES.items():
        assert f"| {code} | {meaning} |" in conventions.codes_table()
    for folder in COPIES:
        text = (REPO / folder / "CONVENTIONS.md").read_text(encoding="utf-8")
        assert conventions.codes_block() in text, f"{folder}: run python3 tools/conventions_codes.py"
        assert conventions.with_codes_table(text) == text, folder


def test_four_copies_identical():
    texts = {(REPO / folder / "CONVENTIONS.md").read_bytes() for folder in COPIES}
    assert len(texts) == 1


def test_a_file_without_the_block_is_refused_not_appended():
    with pytest.raises(conventions.NoCodesBlock):
        conventions.with_codes_table("# Conventions\n\nNo table here.\n")


def test_vault_without_conventions_reads_the_plugin_copy_and_says_so(tmp_path):
    code, out = run("conventions", "Overrides", "--vault", str(tmp_path))
    assert code == 0
    assert out.startswith("The vault has no CONVENTIONS.md, so this is the installed plugin's copy")
    assert str(cli.PLUGIN_CONVENTIONS) in out.split("\n", 1)[0]
    assert "\n## Overrides\n" in out


def test_render_and_check_leave_the_codes_block_alone(tmp_path):
    """CONVENTIONS.md is not a vault page, so `planner render` never rewrites its block nor `check` judges it."""
    vault = tmp_path / "vault"
    shutil.copytree(TEMPLATE, vault)
    before = (vault / "CONVENTIONS.md").read_bytes()
    code, out = run("render", "--vault", str(vault))
    assert code == 0, out
    assert (vault / "CONVENTIONS.md").read_bytes() == before and "CONVENTIONS" not in out
    code, out = run("check", "--vault", str(vault))
    assert code == 0 and "CONVENTIONS.md:" not in out
