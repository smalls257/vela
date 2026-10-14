"""What the where skill says, pinned in one place (overhaul plan Task 3).

Every test that pins this text lives here, so the rewrite that changes it edits this file and no other skill's.
Each section is headed by the file it came from and that file's reason.
"""
from conftest import REPO

PLUGIN = REPO / "plugin"


def text(rel):
    return (PLUGIN / rel).read_text(encoding="utf-8")


# --- From tests/test_reader_skills.py: Reader mode in the skill text: no git in a read copy, owner-only skills
# refuse, a reader's decisions are pending, and every skill finds the installed vela by the one order START.md states.


def test_the_where_skill_needs_no_vela_to_start():
    skill = text("skills/where/SKILL.md")
    assert "CLAUDE_PLUGIN_ROOT = " in skill and "CLAUDE_SKILL_DIR = " in skill and ".claude/skills/vela/scripts/vela" in skill


def test_where_reports_whether_injection_ran():
    """Wave 1, step 0: the user's /vela:where in Cowork answers whether `!` injection runs there. The skill must say
    which happened, and still produce the values when the host left the line unrun."""
    skill = text("skills/where/SKILL.md")
    assert "`injection: yes`" in skill and "`injection: no`" in skill
    assert "run the same `echo ...` line yourself" in skill
    assert "end by asking the user to send this whole output" in skill
