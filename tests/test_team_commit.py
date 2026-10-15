"""`vela team commit` (Task 24's companion): a team session's commit goes through vela by exact path, so design and
breakdown never stage by hand once the hook denies it."""
import json
import shutil

import pytest

from conftest import REPO, run
from test_close_stage import change, committed, git

TEMPLATE = REPO / "template"


@pytest.fixture
def repo(tmp_path):
    root = tmp_path / "vault"
    shutil.copytree(TEMPLATE, root)
    git(root, "init", "-q", "-b", "main")
    git(root, "config", "user.name", "Team Lead")
    git(root, "config", "user.email", "team@example.com")
    git(root, "add", "-A")
    git(root, "commit", "-q", "-m", "Start")
    git(root, "switch", "-q", "-c", "design/heron")
    return root


def commit(root, *extra):
    return run("team", "commit", "--vault", str(root), *extra)


def test_the_teams_files_are_committed_by_path_and_the_plan_is_left_out(repo):
    (repo / ".gitignore").unlink()  # even with the ignore file lost, the inbox can't ride a design commit
    git(repo, "commit", "-q", "-am", "drop ignore")
    change(repo, "docs/tech-design/heron.md", "# Heron design\n")
    change(repo, "CONTEXT.md", "Heron words\n")
    change(repo, "01-goals.md")
    change(repo, ".inbox/call.md")
    code, out = commit(repo, "--about", "the walking skeleton", "--json")
    assert code == 1, out  # something was left out, and it says what
    data = json.loads(out)
    assert committed(repo) == ["CONTEXT.md", "docs/tech-design/heron.md"]
    assert git(repo, "log", "-1", "--format=%s").strip() == "design: the walking skeleton"
    assert [n["rule"] for n in data["never"]] == ["inbox"]
    assert [left["path"] for left in data["left"]] == ["01-goals.md"]


def test_main_is_refused_and_nothing_is_committed(repo):
    git(repo, "switch", "-q", "main")
    change(repo, "docs/plan/heron-breakdown.md", "# Plan\n")
    head = git(repo, "rev-parse", "HEAD")
    code, out = commit(repo, "--about", "story one", "--for-lead")
    assert code == 1 and "main" in out and "review" in out
    assert git(repo, "rev-parse", "HEAD") == head


def test_nothing_of_the_teams_changed_is_said_plainly(repo):
    change(repo, "01-goals.md")
    code, out = commit(repo, "--about", "x", "--for-lead")
    assert code == 1 and "nothing to save" in out
