"""What the import skill says, pinned in one place (overhaul plan Task 3).

Every test that pins this text lives here, so the rewrite that changes it edits this file and no other skill's.
Each section is headed by the file it came from and that file's reason.
"""
import re
import shlex

from conftest import REPO
from vela import cli

PLUGIN = REPO / "plugin"


def text(rel):
    return (PLUGIN / rel).read_text(encoding="utf-8")


EXPLORER_LINE = "The dashboard is up to date: dashboard.html — open it, or run /vela:explore to ask Claude from it"


# --- From tests/test_reader_skills.py: Reader mode in the skill text: no git in a read copy, owner-only skills
# refuse, a reader's decisions are pending, and every skill finds the installed vela by the one order START.md states.


def test_import_skips_git_for_a_reader():
    assert "in a reader copy, which has no git, write the batch and skip the commit" in text("skills/import/SKILL.md")


# --- From tests/test_session_experience.py: What the skills make a lead go through (docs/research/2026-10-12-session-
# experience-review.md and the friction pass).

# --- S36 to S47


def test_import_never_writes_decided():
    imported = text("skills/import/SKILL.md")
    assert "never `decided`" in imported and "or `decided` at all" in imported


# --- From tests/test_skills.py: The plugin's skills: frontmatter, size, the files they point at, the plugin
# validator, and the rules each skill exists to hold.

# tech-design-grill vault mode (V1-18): read the slice, link back by ID and commit, never copy vault text.


def test_import_says_where_the_explorer_is_and_never_stops_on_a_failed_build():
    imported = text("skills/import/SKILL.md")
    assert EXPLORER_LINE in imported and "a failed build never ends the import" in imported


# --- Overhaul Task 22g: sources through `vela add source`, clashes through `vela add unknown`; the map, the batches,
# the ledger and the checklist stay (no `vela checkpoint` exists yet, so the checklist is still the skill's).


IMPORT = text("skills/import/SKILL.md")


def test_import_names_only_commands_that_exist():
    parser = cli.build_parser()
    calls = [shlex.split(re.sub(r"<[^<>]*>", "X", c)) for c in re.findall(r"`vela ([a-z][^`]*)`", IMPORT)]
    assert len(calls) >= 6, calls
    for argv in calls:
        _, extras = parser.parse_known_args(argv)
        assert not extras, (argv, extras)


def test_import_registers_through_the_command_that_strips_tokens():
    assert "user:token@" not in IMPORT
    assert "vela add source --title" in IMPORT and "takes out any credential and says so" in IMPORT
    assert "`vela add unknown --name" in IMPORT


def test_import_leaves_case_tables_diagrams_and_slices_to_boundary_and_grill():
    assert ("Don't build case tables, strict diagrams or slices from imported material unless the source states them; "
            "leave those for boundary and grill, and let the warnings show.") in IMPORT


def test_imported_decisions_keep_todays_rule_while_the_guided_importer_is_parked():
    # Parked by the user (2026-10-14): no new rule for imported decisions vs the close gate.
    assert "A decision a source names is an `assumption` here, never `decided`" in IMPORT
    assert "grill to confirm" in IMPORT and "add an unknown asking the owner to confirm it" in IMPORT


def test_import_keeps_its_checklist_and_map_read_back_by_name():
    assert "## Done only when" in IMPORT and "`## Import ledger`" in IMPORT and "`## Import report`" in IMPORT
    example = IMPORT.split("> **Contracts.**", 1)[1].split("\n", 1)[0]
    assert "partner guide" in example and not re.search(r"\b(?:SRC|UNK|CON|APP)-", example)
    assert "Name sources by title when you talk" in IMPORT


def test_import_says_grill_in_lower_case_and_plan_to_the_lead():
    assert not re.search(r"\bGrill\b", IMPORT)
    assert "the vault is empty" not in IMPORT
