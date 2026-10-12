"""planner next-id: a number an open session branch already holds is never handed out again (UNK-026 twice, heron run)."""
import subprocess

import pytest

from conftest import check, edit, findings, run
from planner import ids

UNKNOWNS = "11-unknowns-and-risks.md"


def test_next_id_is_one_above_the_highest_and_never_fills_a_gap():
    assert ids.next_id("UNK", ["UNK-001 UNK-002", "see UNK-005"]) == "UNK-006"
    assert ids.next_id("UNK", []) == "UNK-001"


def test_next_id_ignores_longer_prefixes_and_keeps_the_widest_width():
    assert ids.next_id("CON", ["ACON-009 CON-002"]) == "CON-003"
    assert ids.next_id("CON", ["CON-0010"]) == "CON-0011"


def test_next_id_refuses_what_is_not_a_prefix():
    with pytest.raises(ValueError):
        ids.next_id("unk", [])


def test_the_command_counts_the_vault(mini):
    code, out = run("next-id", "UNK", "--vault", str(mini))
    assert (code, out.strip()) == (0, "UNK-003")


def test_the_command_refuses_a_bad_prefix_with_exit_2(mini):
    code, out = run("next-id", "unk", "--vault", str(mini))
    assert code == 2 and "not an ID prefix" in out


def _git(repo, *args):
    subprocess.run(["git", "-C", str(repo), "-c", "user.name=t", "-c", "user.email=t@example.com", *args],
                   check=True, capture_output=True, timeout=60)


def test_the_command_counts_a_number_held_only_on_an_open_session_branch(mini):
    _git(mini, "init", "-q", "-b", "main")
    _git(mini, "add", "-A")
    _git(mini, "commit", "-q", "-m", "vault")
    _git(mini, "switch", "-q", "-c", "session/2026-01-15-other")
    with open(mini / UNKNOWNS, "a", encoding="utf-8") as page:
        page.write("\n### UNK-004 Held on a branch\n")
    _git(mini, "commit", "-qam", "branch unknown")
    _git(mini, "switch", "-q", "main")
    assert run("next-id", "UNK", "--vault", str(mini)) == (0, "UNK-005\n")


def test_check_errors_when_two_unknowns_share_an_id(mini):
    edit(mini / UNKNOWNS, "### UNK-002 Receipt format", "### UNK-001 Receipt format")
    _, out = check(mini)
    assert any(code == "E208" for code, _ in findings(out))


def test_skills_number_new_ids_with_the_command_not_by_eye():
    from conftest import REPO
    for path in ("references/MODES.md", "skills/close/SKILL.md", "skills/challenge/SKILL.md"):
        assert "planner next-id UNK" in (REPO / "plugin" / path).read_text(encoding="utf-8"), path
