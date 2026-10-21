"""What the propose skill says, pinned in one place (overhaul plan Task 3).

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


def test_every_flag_propose_tells_claude_to_run_exists():
    flags = {flag for line in skill("propose").splitlines() if "vela" in line and ("propos" in line) for flag in re.findall(r"--[a-z][a-z-]*", line)}
    assert flags and flags <= option_strings(), flags - option_strings()


def test_propose_never_invents_a_reason_or_sends_anything():
    text = skill("propose")
    for rule in ("no reason given", "Never invent a reason", "Never send, email, upload or share the proposal", "never run `git` or `gh`",
                 "Never add that flag without their yes", "A skipped question, \"not sure\", or silence is fine"):
        assert rule in text, rule
    assert "vela role" in text and "you decide directly" in text and "--whys -" in text


# --- Overhaul Task 22h: relay the command, ask by the item's name.


def test_propose_names_only_commands_that_exist():
    import shlex
    from vela import cli
    parser = cli.build_parser()
    text = skill("propose")
    calls = re.findall(r"`vela ((?:propose|role)\b[^`]*)`", text)
    calls += [line.split("scripts/run-vela ", 1)[1].split(" <<", 1)[0].replace("[--zip]", "--zip")
              for line in text.splitlines() if "scripts/run-vela propose" in line]
    assert len(calls) >= 3, calls
    for call in calls:
        _, extras = parser.parse_known_args(shlex.split(re.sub(r"<[^>]*>", "X", call)))
        assert not extras, (call, extras)


def test_the_reader_is_asked_by_the_items_name_not_the_group_key():
    text = skill("propose")
    assert "by the item's name (the group key goes only into the command)" in text
    assert '"You changed the Record consent contract' in text
    assert "vault" not in text.split("## Proposing", 1)[0].split("# Propose", 1)[1]
    assert "When a command can't express what the user wants, say so and stop." in text
