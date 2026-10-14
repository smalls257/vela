"""Close's text after the overhaul's Task 22a-1: sections 1, 6 and 7 run commands instead of git recipes. Each rule the
commands took over is gone from the skill (one rule, one home), and its reason lives in the command's docstring."""
import re
import shlex

from conftest import REPO, skill_text
from vela import cli
from vela.commands import close_gate, close_stage, close_sync
from vela import guard, mergeplan

CLOSE = skill_text("close")


def test_moved_recipes_are_gone_from_close():
    for recipe in ("merge-base --is-ancestor", "-X ours", "git branch -r --list", "git branch --list 'session/*'",
                   "git add -A", "git merge --abort", "git grep -l '^status: open'"):
        assert recipe not in CLOSE, recipe


def test_close_names_only_commands_that_exist():
    parser = cli.build_parser()
    calls = re.findall(r"`planner ((?:close|session|guard|conventions|check-slice) [^`]*)`", CLOSE)
    assert len(calls) >= 6, calls
    for call in calls:
        argv = shlex.split(re.sub(r"<[^>]*>", "X", call))
        args, extras = parser.parse_known_args(argv)
        assert not extras, (call, extras)


def test_the_moved_rules_keep_their_reasons_in_code():
    assert "theirs" in mergeplan.__doc__ and "theirs" in close_sync.__doc__  # one wrong side loses the owner's edits
    assert "git add -A" in close_stage.__doc__ and "allow-list" in close_stage.__doc__
    assert ".inbox/" in guard.__doc__
    assert "Edit tool" in close_gate.__doc__


def test_close_gate_runs_before_the_close_commit_and_its_consent_block_goes_in_the_pr():
    seven = CLOSE.split("## 7. Finish the record", 1)[1].split("## 8.", 1)[0]
    assert seven.index("planner close gate --for-lead") < seven.index("planner close stage --close")
    assert seven.index("planner check-slice --changed") < seven.index("planner close stage --close")
    eight = CLOSE.split("## 8. Open the PR", 1)[1].split("## What you tell", 1)[0]
    assert "planner close gate --consent-block" in eight


def test_a_command_that_cant_do_it_is_a_stop_not_a_recipe():
    assert "never fall back to doing its steps by hand" in CLOSE


def test_close_says_grill_in_lower_case():
    own = (REPO / "plugin" / "skills" / "close" / "SKILL.md").read_text(encoding="utf-8")
    assert not re.search(r"\bGrill\b", own)
    assert (REPO / "plugin" / "lib" / "vela" / "terms.py").is_file()
