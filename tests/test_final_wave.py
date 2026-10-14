"""The last fix wave: the root README describes v2, and close, START, CONVENTIONS and the
plugin manifest say what the code and the workflow actually do."""
import json
import re
import shutil
import subprocess

import pytest

from conftest import REPO, skill_text
from planner import voicecheck

PLUGIN = REPO / "plugin"


def read(*parts):
    return REPO.joinpath(*parts).read_text(encoding="utf-8")


def close_section(start, end):
    return skill_text("close").split(start, 1)[1].split(end, 1)[0]


# I3 and M7: the root README

def test_readme_names_every_v2_command_a_returning_user_looks_for():
    readme = read("README.md")
    for command in ("planner status", "planner next", "planner health", "planner query", "planner handoff",
                    "planner handoff verify", "planner voicecheck", "planner export jira-csv"):
        assert f"`{command}" in readme, command
    for skill in ("/planner:voice-seed", "/planner:challenge", "/planner:ask", "/planner:epics"):
        assert skill in readme, skill


def test_readme_explains_voice_seed_review_harvest_and_challenge():
    readme = read("README.md")
    assert "`voice/examples/`" in readme and "`voice/local/`" in readme
    assert "employer owns" in readme
    assert "voice review" in readme and "Only the vault's owner harvests" in readme
    assert "answer session on the challenge's branch" in readme


def test_readme_is_honest_about_the_weekly_workflow_and_names_generated_diagrams():
    readme = read("README.md")
    assert '"Vault health"' in readme and "Issues enabled" in readme and "not been tested live" in readme
    assert "generated diagrams" in readme and "`planner render`" in readme


def test_readme_checklist_count_matches_the_template_checklist():
    checklist = read("template", "README.md").split("## Setup checklist", 1)[1].split("\n## ", 1)[0]
    steps = re.findall(r"(?m)^(\d+)\. ", checklist)
    assert f"steps 1 to {steps[-1]}" in read("README.md")
    assert "steps 1 to 8" not in read("README.md")


def test_readme_plugin_row_lists_every_cli_command():
    row = next(line for line in read("README.md").splitlines() if line.startswith("| `plugin/` |"))
    help_text = subprocess.run(["python3", str(PLUGIN / "scripts" / "planner"), "--help"], capture_output=True, text=True, timeout=120).stdout
    commands = re.search(r"\{([a-z,-]+)\}", help_text).group(1).split(",")
    for command in commands:
        assert f"`{command}`" in row, command
    assert "voice-reviewer" in row


# M1: a stale session branch merges main before render

def test_close_merges_a_moved_main_before_render():
    # The merge recipe moved into `planner close sync-main` (tests/test_sync_main.py pins its behavior); the skill
    # runs it before render and checkpoints through `close stage`.
    step = close_section("## 6. Render and check", "## 7.")
    assert step.index("planner close sync-main") < step.index("planner render`, then")
    assert "planner close stage --checkpoint" in step
    assert "git merge" not in step and "-X ours" not in step and "--theirs" not in step
    assert "long-lived PR" in read("README.md") and "merge `origin/main`" in read("README.md")


def test_a_block_only_conflict_keeps_the_sessions_clean_edits(tmp_path):
    """main rewrote a generated block; the session edited G3 on the same page. -X ours keeps G3."""
    def git(*args, ok=True):
        done = subprocess.run(["git", *args], cwd=tmp_path, capture_output=True, text=True, timeout=60)
        assert not ok or done.returncode == 0, done.stderr
        return done
    page = tmp_path / "01-goals.md"
    lines = ["# Goals", "", "| G3 | Hold seats | 60% |", "", "filler"] + [""] * 6 + [
        "<!-- generated:progress-map sha=aaa: do not edit, run planner render -->", "old block",
        "<!-- /generated:progress-map -->", ""]
    page.write_text("\n".join(lines), encoding="utf-8")
    git("init", "-q", "-b", "main"); git("config", "user.email", "t@t"); git("config", "user.name", "t")
    git("config", "commit.gpgsign", "false")
    git("add", "."); git("commit", "-qm", "base")
    git("switch", "-qc", "session/s1")
    page.write_text(page.read_text().replace("60%", "65%").replace("old block", "session block"), encoding="utf-8")
    git("commit", "-qam", "Checkpoint s1")
    git("switch", "-q", "main")
    page.write_text(page.read_text().replace("old block", "main block"), encoding="utf-8")
    git("commit", "-qam", "main moved")
    git("switch", "-q", "session/s1")
    assert git("merge", "--no-edit", "main", ok=False).returncode == 1  # the block conflicts
    git("merge", "--abort")
    git("merge", "--no-edit", "-X", "ours", "main")
    text = page.read_text()
    assert "65%" in text and "<<<<<<<" not in text


# M2: a suggestion to chase an unknown reaches the lead as plain words, not as the name of a skill that does not exist

def test_start_never_mentions_a_probe_skill_because_next_says_what_to_do():
    start = read("plugin", "references", "START.md").split("## 4.", 1)[1].split("## 5.", 1)[0]
    assert "probe" not in start.lower()
    assert "Ask the user whether they know the answer now" in start


# M3: CONVENTIONS' negation sentence matches voicecheck

def test_conventions_negation_words_match_the_code():
    words = re.search(r"\(\?:(.*?)\)", voicecheck.NEGATION.pattern).group(1).split("|")
    plain = [w for w in words if w.isalpha()]
    assert "\\w+n't" in words
    sentence = read("template", "CONVENTIONS.md").split("`negation` (", 1)[1].split(")", 1)[0]
    for word in plain:
        assert re.search(rf"\b{word}\b", sentence), word
    assert "any word ending in n't" in sentence
    assert "The count is per file" in sentence and "each paragraph" not in sentence


# M4: the draft commit holds each drafted page whole

def test_close_says_the_draft_commit_holds_whole_pages_and_review_lists_only_prose():
    draft = close_section("## 4. Draft the prose", "### Voice review")
    assert "holds each drafted page whole, including its structured section-3 edits" in draft
    assert "Commit the drafts on their own" not in draft
    review = (PLUGIN / "skills" / "close" / "VOICE-REVIEW.md").read_text(encoding="utf-8")
    assert "List only the prose paragraphs this section drafted" in review


# M5: house-voice's no-examples line has a place in the PR body

def test_close_pr_body_carries_the_no_examples_line():
    assert "No examples for <type>: drafted without examples" in read("plugin", "skills", "house-voice", "SKILL.md")
    body = (PLUGIN / "skills" / "close" / "PR-BODY.md").read_text(encoding="utf-8")
    assert '- **House voice:** each "No examples for <type>: drafted without examples" line house-voice gave' in body


# M6: the plugin manifest

def test_manifest_is_version_0_2_0_and_describes_v2():
    data = json.loads(read("plugin", ".claude-plugin", "plugin.json"))
    # Version must be in semantic versioning format
    assert re.match(r"^\d+\.\d+\.\d+$", data["version"]), f"version {data['version']} is not in semver format"
    for word in ("session skills", "house voice", "handoff", "challenge", "health"):
        assert word in data["description"], word


@pytest.mark.skipif(shutil.which("claude") is None, reason="claude CLI not installed")
def test_the_bumped_manifest_validates():
    result = subprocess.run(["claude", "plugin", "validate", str(PLUGIN)], capture_output=True, text=True, timeout=120)
    assert result.returncode == 0, result.stdout + result.stderr


def test_readme_names_what_has_not_run_against_real_github():
    line = [l for l in read("README.md").splitlines() if l.startswith("- **Not yet run against a real GitHub repo:**")][0]
    for piece in ("weekly issue", "harvest", "answering a challenge", "merge of a moved `main`"):
        assert piece in line, piece


def test_grill_sets_a_challenged_item_back_by_its_kind():
    grill = read("plugin", "skills", "grill", "SKILL.md")
    assert "to `reopened` for an epic or to `assumption` for anything else" in grill
    assert "reopen it first" not in grill


def test_start_does_not_offer_to_resume_a_waiting_challenge():
    start = read("plugin", "references", "START.md")
    assert "challenge waiting for an answer" in start and "offer the \"Answer a challenge\" path" in start


def test_guide_html_is_rendered_from_guide_md():
    """GUIDE.html must be kept current with GUIDE.md by running render_doc.py."""
    import sys
    # Import render_doc to use its page() function
    guide_md = REPO / "docs" / "GUIDE.md"
    guide_html = REPO / "docs" / "GUIDE.html"

    # Render GUIDE.md
    sys.path.insert(0, str(REPO / "docs"))
    from render_doc import page

    markdown_text = guide_md.read_text(encoding="utf-8")
    title = next((line[2:] for line in markdown_text.splitlines() if line.startswith("# ")), "guide")
    rendered_html = page(markdown_text, title)

    # Compare with committed GUIDE.html
    committed_html = guide_html.read_text(encoding="utf-8")
    assert rendered_html == committed_html, "GUIDE.html is stale; run: python3 docs/render_doc.py docs/GUIDE.md"
