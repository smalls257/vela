"""The voice review at close: a fresh-context agent flags paragraphs, the drafter rewrites
each once, and voicecheck keeps every fact the draft carried."""
import shutil
import subprocess

import pytest
import yaml

from conftest import REPO, run

PLUGIN = REPO / "plugin"
AGENT = PLUGIN / "agents" / "voice-reviewer.md"
CLOSE = PLUGIN / "skills" / "close" / "SKILL.md"


def close_text():
    return CLOSE.read_text(encoding="utf-8")


def test_the_agent_is_named_described_and_may_only_read():
    text = AGENT.read_text(encoding="utf-8")
    assert text.startswith("---\n")
    meta = yaml.safe_load(text.split("---\n", 2)[1])
    assert meta["name"] == "voice-reviewer"
    assert isinstance(meta["description"], str) and len(meta["description"]) >= 40
    assert {t.strip() for t in meta["tools"].split(",")} == {"Read", "Grep", "Glob"}
    assert len(text.splitlines()) < 500


def test_the_agent_reads_active_examples_and_never_rewrites():
    body = AGENT.read_text(encoding="utf-8")
    assert "whose frontmatter says `state: active`, in file-name order. Skip `state: retired`." in body
    assert "Never read `voice/corpus/`." in body
    assert "not reviewed: fewer than two active <type> examples" in body
    assert "| # | Page | Verdict | What differs | Example |" in body
    assert "Never rewrite a paragraph or offer replacement text." in body
    assert "Never create, edit or delete a file." in body
    assert "Never flag a paragraph for its facts, IDs, numbers, dates or links." in body


def test_close_dispatches_a_fresh_reviewer_and_never_reviews_itself():
    close = close_text()
    assert "Dispatch the `planner:voice-reviewer` subagent with the Agent tool" in close
    assert "everything in `.claude/skills/planner/agents/voice-reviewer.md` after the frontmatter" in close
    assert "Never review the drafts yourself in this conversation." in close
    assert '"**Voice review:** not run: <the reason>"' in close


def test_close_rewrites_once_and_keeps_the_draft_when_a_fact_moves():
    close = close_text()
    assert "Rewrite each paragraph the reviewer flags once" in close
    assert "Do not send the rewrite back for review." in close
    assert "python3 .claude/skills/planner/bin/planner voicecheck --range HEAD" in close
    assert "commit the rewrites with the message `draft: voice rewrite for <id>`" in close
    assert "run `git restore -- <page>`" in close and "keeps its earlier draft whole" in close
    assert "Never commit a rewrite voicecheck could not check." in close
    assert "**Voice review:** each paragraph the reviewer flagged" in close


@pytest.mark.skipif(shutil.which("git") is None, reason="git is not installed")
def test_the_close_recipe_discards_a_rewrite_that_lost_a_number(tmp_path):
    """The exact commands close runs: commit the draft, rewrite, voicecheck, restore on exit 1."""
    git = ["git", "-c", "user.name=T", "-c", "user.email=t@example.invalid"]
    draft = "Booking holds a seat for 10 minutes while the customer pays on Tidepay's page.\n"
    subprocess.run(git + ["init", "-q"], cwd=tmp_path, check=True)
    (tmp_path / "page.md").write_text(draft, encoding="utf-8")
    subprocess.run(git + ["add", "page.md"], cwd=tmp_path, check=True)
    subprocess.run(git + ["commit", "-qm", "draft: prose for s"], cwd=tmp_path, check=True)
    (tmp_path / "page.md").write_text("Booking keeps the seat for ten minutes while the customer pays.\n", encoding="utf-8")
    code, out = run("voicecheck", "--range", "HEAD", "--vault", str(tmp_path))
    assert code == 1 and "page.md: missing: 10 minutes (number), before line 1" in out
    subprocess.run(["git", "restore", "--", "page.md"], cwd=tmp_path, check=True)
    assert (tmp_path / "page.md").read_text(encoding="utf-8") == draft


def test_the_plugin_validator_accepts_the_agents_folder():
    if shutil.which("claude") is None:
        pytest.skip("the claude command is not installed here")
    result = subprocess.run(["claude", "plugin", "validate", str(PLUGIN)], capture_output=True, text=True, timeout=120)
    assert result.returncode == 0, result.stdout + result.stderr
