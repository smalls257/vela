"""What the proposals skill says, pinned in one place (overhaul plan Task 3).

Every test that pins this text lives here, so the rewrite that changes it edits this file and no other skill's.
Each section is headed by the file it came from and that file's reason.
"""
import re

from conftest import REPO


def skill(name):
    return (REPO / "plugin" / "skills" / name / "SKILL.md").read_text(encoding="utf-8")


def option_strings():
    from vela import cli
    parser = cli.build_parser()
    commands = parser._subparsers._group_actions[0].choices
    found = set()
    for sub in [commands["propose"], *commands["proposals"]._subparsers._group_actions[0].choices.values()]:
        found |= {o for action in sub._actions for o in action.option_strings}
    return found


# --- From tests/test_proposals.py: vela propose and vela proposals: a reader's changes become a patch an owner can
# apply, and the owner's answer comes back.

# ------------------------------------------------------------------ the two skills


def test_every_flag_proposals_tells_claude_to_run_exists():
    flags = {flag for line in skill("proposals").splitlines() if "vela" in line and ("propos" in line) for flag in re.findall(r"--[a-z][a-z-]*", line)}
    assert flags and flags <= option_strings(), flags - option_strings()


def test_review_leaves_every_decision_to_the_owner_and_never_pushes():
    text = skill("proposals")
    for rule in ("pending decisions first", "The owner always decides", "Never write the owner's reason for them", "**Never push, and never open a PR yourself.**",
                 "Never block it, never hide it", "E316", "git worktree remove", "vela proposals accept", "vela proposals reject", "vela proposals answer"):
        assert rule in text, rule
