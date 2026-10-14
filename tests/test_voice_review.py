"""The voice review at close: a fresh-context agent flags paragraphs, the drafter rewrites
each once, and voicecheck keeps every fact the draft carried."""
import shutil
import subprocess

import pytest
import yaml

from conftest import REPO

PLUGIN = REPO / "plugin"
AGENT = PLUGIN / "agents" / "voice-reviewer.md"
CLOSE = PLUGIN / "skills" / "close" / "SKILL.md"


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


def test_the_agent_reads_both_folders_with_owner_examples_first():
    body = AGENT.read_text(encoding="utf-8")
    assert "`voice/local/<voice type>/`" in body and "`voice/examples/<voice type>/`" in body
    assert "Read local `owner` and `owner-edit` examples first" in body


def test_the_plugin_validator_accepts_the_agents_folder():
    if shutil.which("claude") is None:
        pytest.skip("the claude command is not installed here")
    result = subprocess.run(["claude", "plugin", "validate", str(PLUGIN)], capture_output=True, text=True, timeout=120)
    assert result.returncode == 0, result.stdout + result.stderr


# Fix round 2.

def run_git(repo, *args, stdin=None):
    return subprocess.run(["git", *args], cwd=repo, input=stdin, capture_output=True, text=True, check=True, timeout=60).stdout


def commit_page(repo, text, message):
    (repo / "page.md").write_text(text, encoding="utf-8")
    run_git(repo, "add", "page.md")
    run_git(repo, "-c", "user.name=t", "-c", "user.email=t@t", "-c", "commit.gpgsign=false", "commit", "-qm", message)
    return run_git(repo, "rev-parse", "HEAD").strip()


def owner_edit_commits(repo, baseline, headlines_and_bodies):
    """The skill's step 4 filter, as written: PR commits after the baseline, minus its own."""
    shas = run_git(repo, "log", "--format=%H", f"{baseline}..HEAD", "--", "page.md").split()
    kept = []
    for sha in shas:
        headline, body = headlines_and_bodies[sha]
        if headline.startswith(("draft: ", "Checkpoint ", "Close session ")):
            continue
        if "Co-Authored-By: Claude" in body or "Claude-Session:" in body:
            continue
        kept.append(sha)
    return kept


@pytest.fixture
def pr_repo(tmp_path):
    run_git(tmp_path, "init", "-q")
    return tmp_path


def test_close_and_checkpoint_commits_are_never_offered_as_owner_edits(pr_repo):
    meta = {}
    base = commit_page(pr_repo, "Draft one.\n", "draft: prose for APP-1")
    meta[base] = ("draft: prose for APP-1", "")
    for headline in ("Checkpoint APP-1", "Close session 2026-10-03-x"):
        sha = commit_page(pr_repo, f"Draft one.\n\nAdded by {headline}.\n", headline)
        meta[sha] = (headline, "")
    assert owner_edit_commits(pr_repo, base, meta) == []
    sha = commit_page(pr_repo, "Draft one, tuned.\n\nAdded by Close session 2026-10-03-x.\n", "Tune the wording")
    meta[sha] = ("Tune the wording", "")
    assert owner_edit_commits(pr_repo, base, meta) == [sha]
    skipped = commit_page(pr_repo, "Draft one, tuned again.\n\nAdded by Close session 2026-10-03-x.\n", "Reword")
    meta[skipped] = ("Reword", "Claude-Session: https://claude.ai/code/session_x")
    assert owner_edit_commits(pr_repo, base, meta) == [sha]


def test_a_commit_is_diffed_against_its_parent_so_other_commits_do_not_bleed_in(pr_repo):
    base = commit_page(pr_repo, "Alpha.\n\nBeta.\n", "draft: prose for APP-1")
    commit_page(pr_repo, "Alpha.\n\nBeta.\n\nGamma from section 3.\n", "Close session x")
    edit = commit_page(pr_repo, "Alpha, edited.\n\nBeta.\n\nGamma from section 3.\n", "Tune")
    per_commit = run_git(pr_repo, "diff", "-U0", f"{edit}^", edit, "--", "page.md")
    assert "+Alpha, edited." in per_commit and "Gamma" not in per_commit
    baseline_to_tip = run_git(pr_repo, "diff", "-U0", base, edit, "--", "page.md")
    assert "Gamma" in baseline_to_tip


# I1: Claude Code's Bash keeps no shell variable between calls, so harvest's temp file has a
# fixed path every later call can name, and each block must run on its own in a fresh shell.

HARVEST_FILE = ".vela/harvest/<pr>-<n>.txt"


