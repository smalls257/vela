"""The never-staged rules and the allow-list (overhaul Task 9): pure path verdicts, and the pre-commit hook that asks
them. No test here checks a spelling of `git add`: the allow-list decides by path, so there is no spelling to miss."""
import json
import os
import shutil
import subprocess

from conftest import REPO, run
from vela import guard

HOOK = REPO / "template" / ".githooks" / "pre-commit"
LAUNCHER = REPO / "plugin" / "scripts" / "planner"


def test_guard_path_verdicts(tmp_path):
    never = {".inbox/call.md": "inbox", "notes/.inbox/call.md": "inbox", ".Inbox/Call.md": "inbox",
             "voice/local/mine.md": "voice-local", "voice/corpus/essay.txt": "voice-corpus",
             "Voice/Corpus/essay.txt": "voice-corpus", ".planner/session.json": "tool-state",
             "./.planner/workspace.json": "tool-state", "a/../.inbox/x.md": "inbox"}
    allowed = (".planner/explorer-pins.json", "voice/examples/decision/one.md", "01-goals.md", "sources.md",
               ".planner.yaml", "inbox/not-hidden.md", "voice/localish.md", "README.md")
    for path, key in never.items():
        code, out = run("guard", "path", path, "--vault", str(tmp_path), "--json")
        assert code == 1, (path, out)
        assert json.loads(out)["rule"] == key, path
    for path in allowed:
        code, out = run("guard", "path", path, "--vault", str(tmp_path))
        assert code == 0, (path, out)
    code, out = run("guard", "path", str(tmp_path / ".inbox" / "x.md"), "--vault", str(tmp_path), "--for-lead")
    assert code == 1 and out.strip() == "The meeting notes in the inbox stay on this machine; I've left them out."


def test_the_plan_sorts_each_path_once_and_never_rules_win():
    changed = ["01-goals.md", "sessions/s1.md", "sessions/s0.md", ".inbox/a.md", "handoffs/APP-x.md",
               "dashboard.html", "scratch.txt", ".planner/explorer-pins.json", "voice/examples/x/y.md"]
    plan = guard.plan(changed, {"01-goals.md", "sessions/s1.md", "sessions/s0.md", ".inbox/a.md"}, "s1")
    assert plan.stage == ("01-goals.md", "sessions/s1.md", ".planner/explorer-pins.json", "voice/examples/x/y.md")
    assert [p for p, _ in plan.never] == [".inbox/a.md"]
    assert dict(plan.left) == {"sessions/s0.md": guard.OTHER_SESSION, "handoffs/APP-x.md": guard.HANDOFF,
                               "dashboard.html": guard.DASHBOARD, "scratch.txt": guard.OTHER}


def git(root, *args, env=None):
    return subprocess.run(["git", "-C", str(root), *args], capture_output=True, text=True, timeout=60,
                          env={**os.environ, **(env or {})})


def test_pre_commit_rejects_inbox(tmp_path):
    repo = tmp_path / "vault"
    (repo / ".githooks").mkdir(parents=True)
    shutil.copy(HOOK, repo / ".githooks" / "pre-commit")
    os.chmod(repo / ".githooks" / "pre-commit", 0o755)
    git(repo, "init", "-q")
    for key, value in (("user.name", "Test Lead"), ("user.email", "lead@example.com"), ("core.hooksPath", ".githooks")):
        git(repo, "config", key, value)
    env = {"PLANNER": str(LAUNCHER)}
    (repo / "01-goals.md").write_text("goals\n", encoding="utf-8")
    git(repo, "add", "--", "01-goals.md")
    first = git(repo, "commit", "-q", "-m", "goals", env=env)
    assert first.returncode == 0, first.stdout + first.stderr

    (repo / ".inbox").mkdir()
    (repo / ".inbox" / "call notes.md").write_text("company material\n", encoding="utf-8")
    git(repo, "add", "-f", "--", ".inbox/call notes.md")
    refused = git(repo, "commit", "-q", "-m", "oops", env=env)
    said = refused.stdout + refused.stderr
    assert refused.returncode != 0, said
    assert "The meeting notes in the inbox stay on this machine" in said and ".inbox/call notes.md" in said
    assert git(repo, "rev-list", "--count", "HEAD").stdout.strip() == "1"

    missing = git(repo, "commit", "-q", "-m", "oops", env={"PLANNER": str(tmp_path / "nowhere")})
    assert missing.returncode != 0 and "were not checked" in missing.stderr, "a hook that cannot run must not pass"
