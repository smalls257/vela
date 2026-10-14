"""Reader mode in the skill text: no git in a read copy, owner-only skills refuse, a reader's decisions are pending,
and every skill finds the installed planner by the one order START.md states."""
import re

import pytest
import yaml
from conftest import REPO, run, skill_text
from sharing import make_vault

PLUGIN = REPO / "plugin"
SKILLS = sorted((PLUGIN / "skills").glob("*/SKILL.md"))
VENDORED_PROGRAM = "python3 .claude/skills/planner/scripts/planner"


def text(rel):
    return (PLUGIN / rel).read_text(encoding="utf-8")


def meta(path):
    return yaml.safe_load(path.read_text(encoding="utf-8").split("---\n", 2)[1])


@pytest.mark.parametrize("path", SKILLS, ids=lambda p: p.parent.name)
def test_no_skill_hard_codes_the_vendored_program(path):
    assert VENDORED_PROGRAM not in path.read_text(encoding="utf-8")


@pytest.mark.parametrize("path", SKILLS, ids=lambda p: p.parent.name)
def test_every_planner_permission_is_the_one_loose_pattern(path):
    allowed = meta(path).get("allowed-tools", "")
    assert re.findall(r"Bash\(python3 [^)]*planner[^)]*\)", allowed) in ([], ["Bash(python3 *scripts/planner *)"]), path


def test_the_resolution_order_is_stated_once_in_start():
    start = text("references/START.md")
    assert start.count("## Where the planner runs from") == 1
    order = start.split("## Where the planner runs from")[1].split("## ")[0]
    positions = [order.index(m) for m in ("1. `${CLAUDE_SKILL_DIR}/../../scripts/planner`", "2. `${CLAUDE_PLUGIN_ROOT}/scripts/planner`",
                                          "3. `.claude/skills/planner/scripts/planner`", "planner_path")]
    assert positions == sorted(positions)
    assert "I cannot find the planner program. Run `/planner:where` and send me what it prints." in order


def test_start_skips_git_for_a_reader_and_still_writes_the_record():
    start = text("references/START.md")
    assert "This is a read copy, so I will not use git" in start
    assert "Session records are still written" in start
    for step in ("## 1.", "## 2.", "## 3.", "## 5."):
        assert "**Reader copy:**" in start.split(step)[1].split("\n## ")[0], step
    assert "- **Pending approval:** @<their handle>, <today>" in start


def test_close_has_a_reader_section_that_commits_and_pushes_nothing():
    close = skill_text("close")
    pointer = close.split("## Reader copy: no git, no PR")[1].split("## 1. Find the session")[0]
    assert "skills/close/READER.md" in pointer and "Never say a PR exists" in pointer
    section = text("skills/close/READER.md")  # read only when `planner role` says reader
    assert "Nothing is committed, pushed or sent" in section and "Never say a PR exists" in section
    assert "Pending approval" in section and "Never write a handoff manifest" in section
    assert "grep -l '^status: open' sessions/*.md" in section


def test_owner_only_skills_refuse_in_a_reader_copy_naming_the_owner():
    assert "That is the owner's call" in text("skills/challenge/SKILL.md") and "published.json" in text("skills/challenge/SKILL.md")
    assert "owner's call" in text("skills/grill/SKILL.md") and "published.json" in text("skills/grill/SKILL.md")


def test_import_and_voice_seed_skip_git_for_a_reader():
    assert "in a reader copy, which has no git, write the batch and skip the commit" in text("skills/import/SKILL.md")
    assert "only the local-only place is open" in text("skills/voice-seed/SKILL.md")


def test_grill_marks_a_readers_decisions_pending():
    assert "- **Pending approval:** @<handle>, <today>" in text("skills/grill/SKILL.md")


def test_the_open_skill_runs_planner_open_and_never_git_init():
    skill = text("skills/open/SKILL.md")
    assert "scripts/planner open" in skill and "Never run `git init`" in skill and "never writes to the folder" in skill.lower()
    assert "--into planner-workspaces/" in skill


def test_the_where_skill_needs_no_planner_to_start():
    skill = text("skills/where/SKILL.md")
    assert "CLAUDE_PLUGIN_ROOT = " in skill and "CLAUDE_SKILL_DIR = " in skill and ".claude/skills/planner/scripts/planner" in skill


@pytest.fixture
def reader_copy(tmp_path):
    vault = make_vault(tmp_path)
    assert run("publish", "--vault", str(vault), "--out", str(tmp_path / "copy"), "--today", "2026-10-11")[0] == 0
    assert run("open", str(tmp_path / "copy"), "--into", str(tmp_path / "ws"), "--author", "Sam Okoye", "--today", "2026-10-12")[0] == 0
    return tmp_path / "ws"


def test_a_reader_cannot_hand_off_or_upgrade_and_is_told_whose_call_it_is(reader_copy):
    for argv in (["handoff", "APP-till"], ["upgrade"]):
        code, out = run(*argv, "--vault", str(reader_copy))
        assert code == 2 and "Priya Nair's call" in out, (argv, out)


def test_a_reader_may_still_verify_a_handoff_read_only(reader_copy):
    code, out = run("handoff", "verify", "APP-till", "--vault", str(reader_copy))
    assert "owner's job" not in out


def test_where_reports_whether_injection_ran():
    """Wave 1, step 0: the user's /planner:where in Cowork answers whether `!` injection runs there. The skill must say
    which happened, and still produce the values when the host left the line unrun."""
    skill = text("skills/where/SKILL.md")
    assert "`injection: yes`" in skill and "`injection: no`" in skill
    assert "run the same `echo ...` line yourself" in skill
    assert "end by asking the user to send this whole output" in skill
