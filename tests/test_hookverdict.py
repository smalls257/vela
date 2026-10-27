"""edit_verdict: what a hand edit to a vault page may not change (a state, a generated block, the open-question note).
bash_verdict: only a private path is stopped; a push, a PR and plain staging of plan pages get no opinion."""
import pytest

from vela import hookverdict
from vela.hookverdict import DENY, bash_verdict

PAGE = """### CON-001 Booking API

- **State:** decided

## History

#### CON-001

- **Decision:** [[2026-10-20-grill]]
"""
NOTED = PAGE + "- **Decided with open:** UNK-009\n"


def test_a_hand_typed_decided_with_open_bullet_is_denied():
    verdict = hookverdict.edit_verdict(PAGE, NOTED)
    assert verdict is not None and verdict.decision == hookverdict.DENY
    assert "Only `vela decide` writes" in verdict.reason


def test_a_hand_changed_decided_with_open_bullet_is_denied():
    changed = NOTED.replace("UNK-009", "UNK-010")
    assert hookverdict.edit_verdict(NOTED, changed).decision == hookverdict.DENY


def test_taking_the_note_away_or_leaving_it_alone_is_allowed():
    assert hookverdict.edit_verdict(NOTED, PAGE) is None
    assert hookverdict.edit_verdict(NOTED, NOTED + "- **Why:** because\n") is None


def test_a_hand_moved_state_is_still_denied():
    assert hookverdict.edit_verdict(PAGE, PAGE.replace("decided", "assumption")).decision == hookverdict.DENY


@pytest.mark.parametrize("command", ["git add 05-building-blocks/stock-building-blocks.md", "git add -A",
                                     "git commit -am x", "git push -u origin session/x", "gh pr create --fill",
                                     "gh pr comment 4 --body ok", "git add .", "git commit -m x",
                                     "git add sessions/2026-10-20-x.md voice/house/a.md"])
def test_routine_git_and_gh_get_no_opinion(command):
    assert bash_verdict(command) is None


@pytest.mark.parametrize("command", ["git add sessions/private/2026-10-20-x.md", "git add .inbox/call.md",
                                     "git add voice/local/a.md", "git add -f sessions/private/x.md",
                                     "git add --force .vela/session.json", "git add -f 02-constraints.md",
                                     "git add -Af", "git add 02-constraints.md .inbox/x.md"])
def test_a_private_path_or_a_forced_stage_is_denied(command):
    found = bash_verdict(command)
    assert found is not None and found.decision == DENY


def test_a_deny_names_the_private_path_and_the_way_out():
    found = bash_verdict("git add .inbox/call.md")
    assert found.forbidden == [".inbox/call.md"] and "vela close stage" in found.reason


def test_a_commit_whose_index_holds_a_private_path_is_denied():
    held = ["/p/sessions/private/x.md"]
    assert bash_verdict("git commit -m x", cwd="/p", plan_roots=["/p"], staged=held).decision == DENY
    assert bash_verdict("git commit -m x", cwd="/p", plan_roots=["/p"], staged=["/p/02-constraints.md"]) is None


def test_a_commit_whose_index_could_not_be_read_is_denied():
    assert bash_verdict("git commit -m x", cwd="/p", plan_roots=["/p"], staged=None).decision == DENY


def test_a_private_path_outside_every_plan_is_the_owners_own():
    assert bash_verdict("git add notes/.inbox/x.md", cwd="/r", plan_roots=["/r/projects/heron"]) is None
    inside = bash_verdict("git add projects/heron/.inbox/x.md", cwd="/r", plan_roots=["/r/projects/heron"])
    assert inside is not None and inside.decision == DENY


def test_broad_staging_is_safe_because_the_template_ignores_every_never_rule_path():
    """`git add -A` gets no opinion only while .gitignore keeps every forbidden prefix out of it."""
    import subprocess
    import tempfile
    import pathlib
    from vela import guard
    template = pathlib.Path(__file__).resolve().parents[1] / "plugin" / "template" / ".gitignore"
    paths = [".inbox/call.md", "sessions/private/2026-10-20-x.md", "voice/local/a.md", "voice/corpus/a.md",
             ".vela/session.json"]
    with tempfile.TemporaryDirectory() as folder:
        subprocess.run(["git", "init", "-q", folder], check=True)
        pathlib.Path(folder, ".gitignore").write_text(template.read_text(encoding="utf-8"), encoding="utf-8")
        for path in paths:
            assert guard.never_rule(path) is not None
            done = subprocess.run(["git", "-C", folder, "check-ignore", "-q", path])
            assert done.returncode == 0, f"{path} is not ignored by the template"
