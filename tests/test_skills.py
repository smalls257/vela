"""The plugin's skills: frontmatter, size, the files they point at, the plugin validator, and the
rules each skill exists to hold."""
import re
import shutil
import subprocess

import pytest
import yaml

from conftest import REPO

PLUGIN = REPO / "plugin"
SKILLS = sorted(p.parent for p in (PLUGIN / "skills").glob("*/SKILL.md"))
READ_ONLY = {"ask"}  # every other skill writes to the vault
# Files a reference may name that live outside references/: vault files, and files of the user's grill skills.
OTHER_FILES = {"CONVENTIONS.md", "CLAUDE.md", "SKILL.md", "CONTEXT.md", "NEG-AUDIT.md", "PREREQ-CHECK.md", "GRILL-LOOP.md",
               "REQUIREMENTS-FORMAT.md", "TECH-DESIGN-FORMAT.md"}
INSTALLED = re.compile(r"\.claude/skills/planner/([A-Za-z0-9_./-]+)")
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
    if skill.name in READ_ONLY:
        assert "disable-model-invocation" not in meta
        assert meta["disallowed-tools"] == "Write Edit NotebookEdit"
    else:
        assert meta.get("disable-model-invocation") is True, f"{skill.name} writes, so only the user may invoke it"


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
            assert (PLUGIN / rel).exists(), f"{path.name} names .claude/skills/planner/{rel}, which the plugin lacks"
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


# Session start, dump and close (V1-08). Each assertion pins a rule whose loss would be silent.

def test_start_stops_on_a_dirty_clone_and_says_when_main_is_old():
    start = text("references/START.md")
    assert "If any file is changed or untracked, stop and ask" in start
    assert "Never start from an old `main` without saying so." in start
    assert "add `-2`" in start
    assert "Never close a session for the user." in start
    assert "Review comments were not checked" in start or "review comments were not checked" in start
    assert "claude, from <name>" in start


def test_dump_writes_captures_only():
    dump = text("skills/dump/SKILL.md")
    assert "Never edit a page outside `sessions/` during a dump." in dump
    assert "pre-mortem" in dump
    assert "Do not run close yourself." in dump


def test_close_marks_honestly_and_never_claims_a_pr():
    close = text("skills/close/SKILL.md")
    assert "Never propose `fact`." in close
    assert "A `(claude)` line is parked unless the user picks it." in close
    assert "It is never parked." in close
    assert "Promoted on a nod" in close
    assert "May still say the old value" in close
    assert "passed as `org/team`" in close and "Drop the user's own handle." in close
    assert "Never say a PR exists unless `gh` printed its URL." in close
    assert "Do not open a PR for a branch that is not pushed." in close
