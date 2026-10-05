"""The last fix wave: the root README describes v2, and close, START, CONVENTIONS and the
plugin manifest say what the code and the workflow actually do."""
import json
import re
import shutil
import subprocess

import pytest

from conftest import REPO
from planner import voicecheck

PLUGIN = REPO / "plugin"


def read(*parts):
    return REPO.joinpath(*parts).read_text(encoding="utf-8")


def close_section(start, end):
    return read("plugin", "skills", "close", "SKILL.md").split(start, 1)[1].split(end, 1)[0]


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
    help_text = subprocess.run(["python3", str(PLUGIN / "bin" / "planner"), "--help"], capture_output=True, text=True).stdout
    commands = re.search(r"\{([a-z,]+)\}", help_text).group(1).split(",")
    for command in commands:
        assert f"`{command}`" in row, command
    assert "voice-reviewer" in row


# M1: a stale session branch merges main before render

def test_close_merges_a_moved_main_before_render():
    step = close_section("## 6. Render and check", "## 7.")
    assert "git merge-base --is-ancestor origin/main HEAD" in step
    assert "git merge --no-edit origin/main" in step
    assert step.index("git merge --no-edit origin/main") < step.index("planner render`, then")
    assert "take either side and re-render" in step
    assert "Any other conflict: stop and show it" in step
    assert "long-lived PR" in read("README.md") and "merge `origin/main`" in read("README.md")


# M2: a probe suggestion is START's ask-or-research offer

def test_start_says_what_a_probe_suggestion_means():
    start = read("plugin", "references", "START.md").split("## 4.", 1)[1].split("## 5.", 1)[0]
    assert "When `planner next` suggests `probe`, it means the ask-or-research offer above. There is no Probe skill." in start


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
    review = close_section("### Voice review", "### Harvest")
    assert "List only the prose paragraphs this section drafted" in review


# M5: house-voice's no-examples line has a place in the PR body

def test_close_pr_body_carries_the_no_examples_line():
    assert "No examples for <type>: drafted without examples" in read("plugin", "skills", "house-voice", "SKILL.md")
    body = close_section("## 8. Open the PR", "- **Minutes.**")
    assert '- **House voice:** each "No examples for <type>: drafted without examples" line house-voice gave' in body


# M6: the plugin manifest

def test_manifest_is_version_0_2_0_and_describes_v2():
    data = json.loads(read("plugin", ".claude-plugin", "plugin.json"))
    assert data["version"] == "0.2.0"
    for word in ("session skills", "house voice", "handoff", "challenge", "health"):
        assert word in data["description"], word


@pytest.mark.skipif(shutil.which("claude") is None, reason="claude CLI not installed")
def test_the_bumped_manifest_validates():
    result = subprocess.run(["claude", "plugin", "validate", str(PLUGIN)], capture_output=True, text=True, timeout=120)
    assert result.returncode == 0, result.stdout + result.stderr
