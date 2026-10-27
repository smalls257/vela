"""What the open skill says, pinned in one place (overhaul plan Task 3).

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


def test_the_open_skill_runs_vela_open_and_never_git_init():
    skill = text("skills/open/SKILL.md")
    assert "scripts/run-vela open" in skill and "Never run `git init`" in skill and "never writes to the folder" in skill.lower()
    assert "--into vela-workspaces/" in skill


# --- From tests/test_skills.py: The plugin's skills: frontmatter, size, the files they point at, the plugin
# validator, and the rules each skill exists to hold.

# tech-design-grill vault mode (V1-18): read the slice, link back by ID and commit, never copy vault text.


def test_open_says_where_the_explorer_is():
    assert EXPLORER_LINE in text("skills/open/SKILL.md")


# --- Overhaul Task 22h: relay the command; the reader hears what a .mine.md file is.


def test_open_names_only_commands_that_exist():
    import re
    import shlex
    from vela import cli
    parser = cli.build_parser()
    calls = re.findall(r"scripts/run-vela (open [^`]*)`", text("skills/open/SKILL.md"))
    assert calls, calls
    for call in calls:
        _, extras = parser.parse_known_args(shlex.split(re.sub(r"<[^>]*>", "X", call)))
        assert not extras, (call, extras)


def test_a_reopen_says_where_the_readers_version_went_in_plain_words():
    skill = text("skills/open/SKILL.md")
    assert '"Your version is kept next to it in a file ending .mine.md"' in skill
    assert "`<page>.mine.md`" not in skill and "every skill runs as a reader" not in skill
    assert "the planning sessions (`/vela:dump`, `/vela:shape` and so on)" in skill
    assert "Never delete or empty a folder to make room." in skill


def test_open_takes_a_github_link_and_never_an_older_copy():
    skill = text("skills/open/SKILL.md")
    assert "GitHub link" in skill and "never offer an older copy" in skill
    assert "get the newer plan" in skill and "full vela plugin" in skill


def test_open_opens_the_dashboard_instead_of_offering():
    body = text("skills/open/SKILL.md")
    assert "Open `dashboard.html` in the workspace (`open` or `xdg-open`)" in body and "Offer to open" not in body
