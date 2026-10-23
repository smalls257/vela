"""The plugin's skills: frontmatter, size, the files they point at, the plugin validator, and the
rules each skill exists to hold."""
import re
import shutil
import subprocess

import pytest
import yaml

from conftest import REPO, run

PLUGIN = REPO / "plugin"
SKILLS = sorted(p.parent for p in (PLUGIN / "skills").glob("*/SKILL.md"))
READ_ONLY = {"ask", "find"}  # every other skill writes to the vault
# Only ask and find are read-only. Every skill is open to the model: none carries disable-model-invocation. A writing skill
# is offered in the person's words and started on a yes (START.md, "Offering a session").
NO_OFFER_LINE = {"ask", "find", "close"}  # read-only, or started on the lead's word and confirmed in the skill
# Files a reference may name that live outside references/: vault files, and files of the user's grill skills.
OTHER_FILES = {"CONVENTIONS.md", "CLAUDE.md", "SKILL.md", "CONTEXT.md", "NEG-AUDIT.md", "PREREQ-CHECK.md", "GRILL-LOOP.md",
               "REQUIREMENTS-FORMAT.md", "TECH-DESIGN-FORMAT.md", "REVIEW-CHECKPOINT.md"}
INSTALLED = re.compile(r"(?:\.claude/skills/vela|\$\{CLAUDE_PLUGIN_ROOT\})/([A-Za-z0-9_./-]+)")
SIBLING = re.compile(r"`([A-Z][A-Z0-9-]*\.md)`")


def frontmatter(path):
    text = path.read_text(encoding="utf-8")
    assert text.startswith("---\n"), f"{path} has no frontmatter"
    return yaml.safe_load(text.split("---\n", 2)[1])


def text(rel):
    return (PLUGIN / rel).read_text(encoding="utf-8")


def ids(paths):
    return [p.name for p in paths]


@pytest.mark.parametrize("skill", SKILLS, ids=ids(SKILLS))
def test_frontmatter(skill):
    meta = frontmatter(skill / "SKILL.md")
    assert meta["name"] == skill.name
    assert isinstance(meta.get("description"), str) and len(meta["description"]) >= 40
    assert "disable-model-invocation" not in meta
    if skill.name in READ_ONLY:
        assert meta["disallowed-tools"] == "Write Edit NotebookEdit"
    if skill.name not in NO_OFFER_LINE:
        assert "Offer it when" in meta["description"] and "only on a yes" in meta["description"], skill.name


def test_start_carries_the_shared_offer_rule():
    # The October 23 trim moved the rule: START's "Offering a session" section is gone and CONVERSATION-VOICE, which every
    # session reads, holds it once.
    assert "## Offering a session" not in text("references/START.md")


def test_conversation_voice_carries_the_offer_line():
    voice = text("references/CONVERSATION-VOICE.md")
    assert "Offer a session, never start one unasked" in voice
    for phrase in ("say which one in plain words and why", "ask once", "start it only on a yes",
                   "A no or silence means answer the question as asked"):
        assert phrase in voice, phrase


@pytest.mark.parametrize("skill", SKILLS, ids=ids(SKILLS))
def test_under_500_lines(skill):
    assert len((skill / "SKILL.md").read_text(encoding="utf-8").splitlines()) < 500


DOCS = SKILLS + [PLUGIN / "references"]


@pytest.mark.parametrize("folder", DOCS, ids=ids(DOCS))
def test_every_file_a_skill_or_reference_names_exists(folder):
    files = [folder / "SKILL.md"] if (folder / "SKILL.md").exists() else sorted(folder.glob("*.md"))
    for path in files:
        body = path.read_text(encoding="utf-8")
        for rel in INSTALLED.findall(body):
            rel = rel.rstrip(".")
            assert (PLUGIN / rel).exists(), f"{path.name} names .claude/skills/vela/{rel}, which the plugin lacks"
        if folder.name == "references":
            for name in SIBLING.findall(body):
                assert name in OTHER_FILES or (folder / name).exists(), f"{path.name} names {name}, which is not in references/"


def test_references_hold_no_skill_frontmatter():
    for path in (PLUGIN / "references").glob("*.md"):
        assert not path.read_text(encoding="utf-8").startswith("---"), f"{path.name} is a reference, not a skill"


def test_claude_plugin_validate():
    if shutil.which("claude") is None:
        pytest.skip("the claude command is not installed here")
    result = subprocess.run(["claude", "plugin", "validate", str(PLUGIN)], capture_output=True, text=True, timeout=120)
    assert result.returncode == 0, result.stdout + result.stderr


def test_no_skill_offers_to_draft_an_ask():
    for path in (PLUGIN / "skills").glob("*/SKILL.md"):
        body = path.read_text(encoding="utf-8")
        for phrase in ("draft a short ask", "an ask instead", "offer an ask", "an ask to the"):
            assert phrase not in body, (path, phrase)


def test_the_area_reviewer_quotes_a_changed_page():
    assert "it quotes a `Changed:` page" in text("agents/area-reviewer.md")


def test_the_static_build_close_runs_writes_the_page_and_names_it_on_its_last_line(tmp_path):
    vault = tmp_path / "v"
    shutil.copytree(REPO / "tests/sim/snapshots/trading-coach/after-80b", vault)
    code, said = run("explore", str(vault), "--today", "2026-10-10")
    assert code == 0, said
    assert (vault / "dashboard.html").is_file()
    assert said.strip().splitlines()[-1].startswith("vela explore: wrote ") and "serving" not in said


def test_a_build_that_fails_exits_2_says_why_and_leaves_no_new_page(tmp_path):
    code, said = run("explore", str(tmp_path / "not-a-vault"))
    assert code == 2 and said.strip(), said
    assert not (tmp_path / "not-a-vault" / "dashboard.html").exists()
