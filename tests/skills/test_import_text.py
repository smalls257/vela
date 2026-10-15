"""What the import skill says, pinned in one place (overhaul plan Task 3).

Every test that pins this text lives here, so the rewrite that changes it edits this file and no other skill's.
Each section is headed by the file it came from and that file's reason.
"""
from conftest import REPO

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
