"""What the neg-audit reference says, pinned in one place (overhaul plan Task 3).

Every test that pins this text lives here, so the rewrite that changes it edits this file and no other skill's.
Each section is headed by the file it came from and that file's reason.
"""
from conftest import REPO

PLUGIN = REPO / "plugin"


def text(path):
    return path.read_text(encoding="utf-8")


# --- From tests/test_breakdown_tickets_skills.py: The text of /vela:breakdown and /vela:tickets: each kept item and
# each built-in rule is there, nothing points at a file that is not, and the plan format's own example is something
# the reader reads clean.


def test_the_self_audit_is_the_users_text_with_only_its_header_changed():
    mine = text(PLUGIN / "references" / "NEG-AUDIT.md")
    original = text(REPO / "integrations" / "tech-design-grill" / "skill" / "NEG-AUDIT.md")
    assert mine == original.replace("## Violation Guide (from `~/.claude/CLAUDE.md`)", "## Violation Guide (the failure modes below)")
    assert mine != original and "~/.claude" not in mine
