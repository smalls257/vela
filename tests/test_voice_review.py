"""The voice review at close: a fresh-context agent flags paragraphs, the drafter rewrites
each once, and voicecheck keeps every fact the draft carried."""
import re
import shutil
import subprocess
import textwrap

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
    assert "Then commit the rewrites that passed with the message `draft: voice rewrite for <id>`" in close
    assert "run `git restore -- <page>`" in close and "keeps its earlier draft whole" in close
    assert "Run it for no other file." in close
    assert "Never commit a rewrite voicecheck could not check." in close
    assert "**Voice review:** each paragraph the reviewer flagged" in close


def test_close_covers_the_empty_broken_and_meddling_reviewer():
    close = close_text()
    assert "you must not change any file, and you must report any file you changed" in close
    assert "If the output differs from step 1, the reviewer changed a file: stop and show the user." in close
    assert "returned anything but the table, treat the review as not run" in close
    assert "If it flagged no paragraph, skip steps 4 and 5 of this part" in close
    for kind in ("wikilink", "code span", "date", "ID", "number (with its units or currency)", "table cell",
                 "version", "frontmatter line", "negation"):
        assert kind in close


def test_the_agent_reads_both_folders_with_owner_examples_first():
    body = AGENT.read_text(encoding="utf-8")
    assert "`voice/local/<voice type>/`" in body and "`voice/examples/<voice type>/`" in body
    assert "Read local `owner` and `owner-edit` examples first" in body


def recipe_commands():
    """The fenced voicecheck block in close's text, with the planner path pointed at this repo."""
    found = re.search(r"^ *```\n( *tmp=\$\(mktemp\)\n.*?)^ *```", close_text(), re.S | re.M)
    block = textwrap.dedent(found.group(1))
    assert ".claude/skills/planner/bin/planner" in block
    return block.replace(".claude/skills/planner/bin/planner", str(PLUGIN / "bin" / "planner"))


def git_in(repo, *args):
    cmd = ["git", "-c", "user.name=T", "-c", "user.email=t@example.invalid", *args]
    return subprocess.run(cmd, cwd=repo, check=True, capture_output=True, text=True).stdout


def close_voicecheck(repo, page):
    """Run close's block for one page, then close's exit-0 and exit-1 branches."""
    script = recipe_commands().replace("<page>", page)
    code = subprocess.run(["bash", "-c", script], cwd=repo, capture_output=True, text=True).returncode
    if code == 0:
        git_in(repo, "add", page)
        git_in(repo, "commit", "-qm", "draft: voice rewrite for s")
    elif code == 1:
        git_in(repo, "restore", "--", page)
    return code


DRAFT = "Booking holds a seat for 10 minutes while the customer pays on Tidepay's page.\n"


def draft_repo(tmp_path):
    git_in(tmp_path, "init", "-q")
    (tmp_path / "page.md").write_text(DRAFT, encoding="utf-8")
    (tmp_path / "record.md").write_text("Changes\n", encoding="utf-8")
    git_in(tmp_path, "add", "page.md", "record.md")
    git_in(tmp_path, "commit", "-qm", "draft: prose for s")
    (tmp_path / "record.md").write_text("Changes\n| row | added by step 3 |\n", encoding="utf-8")


@pytest.mark.skipif(shutil.which("git") is None, reason="git is not installed")
def test_a_rewrite_that_lost_a_number_is_restored_and_other_work_survives(tmp_path):
    draft_repo(tmp_path)
    (tmp_path / "page.md").write_text("Booking keeps the seat for ten minutes while the customer pays.\n", encoding="utf-8")
    assert close_voicecheck(tmp_path, "page.md") == 1
    assert (tmp_path / "page.md").read_text(encoding="utf-8") == DRAFT
    assert "added by step 3" in (tmp_path / "record.md").read_text(encoding="utf-8")


@pytest.mark.skipif(shutil.which("git") is None, reason="git is not installed")
def test_a_clean_rewrite_is_committed_and_other_work_stays_uncommitted(tmp_path):
    draft_repo(tmp_path)
    rewrite = "Booking holds the seat for 10 minutes while the customer pays on Tidepay's page.\n"
    (tmp_path / "page.md").write_text(rewrite, encoding="utf-8")
    assert close_voicecheck(tmp_path, "page.md") == 0
    assert git_in(tmp_path, "log", "-1", "--format=%s").strip() == "draft: voice rewrite for s"
    assert git_in(tmp_path, "status", "--porcelain").strip() == "M record.md"


def test_the_plugin_validator_accepts_the_agents_folder():
    if shutil.which("claude") is None:
        pytest.skip("the claude command is not installed here")
    result = subprocess.run(["claude", "plugin", "validate", str(PLUGIN)], capture_output=True, text=True, timeout=120)
    assert result.returncode == 0, result.stdout + result.stderr
