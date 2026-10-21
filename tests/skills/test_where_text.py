"""What the where skill says, pinned in one place (overhaul plan Task 3).

Every test that pins this text lives here, so the rewrite that changes it edits this file and no other skill's.
Each section is headed by the file it came from and that file's reason.
"""
import re

from conftest import REPO

PLUGIN = REPO / "plugin"


def text(rel):
    return (PLUGIN / rel).read_text(encoding="utf-8")


def bang_lines(skill):
    return [line for line in skill.splitlines() if line.startswith("!`")]


# --- From tests/test_reader_skills.py: Reader mode in the skill text: no git in a read copy, owner-only skills
# refuse, a reader's decisions are pending, and every skill finds the installed vela by the one order START.md states.


def test_the_where_skill_needs_no_vela_to_start():
    skill = text("skills/where/SKILL.md")
    assert "CLAUDE_PLUGIN_ROOT = " in skill and "CLAUDE_SKILL_DIR = " in skill and ".claude/skills/vela/scripts/vela" in skill


def test_where_reports_whether_injection_ran():
    """Wave 1, step 0: the user's /vela:where in Cowork answers whether `!` injection runs there. The skill must say
    which happened, and still produce the values when the host left the line unrun."""
    skill = text("skills/where/SKILL.md")
    assert "`injection: yes`" in skill and "`injection: no`" in skill
    assert "run the same `echo ...` line yourself" in skill
    assert "Ask the user to send this whole output" in skill


# --- Overhaul plan Task 7-skill: the probe runs as a normal step, because Cowork doesn't run `!` lines (P19).


def test_where_runs_the_probe_as_a_normal_step():
    skill = text("skills/where/SKILL.md")
    assert "Run it as a normal step" in skill
    call = "where --probe --json --plugin-root \"${CLAUDE_PLUGIN_ROOT}\" --skill-dir \"${CLAUDE_SKILL_DIR}\" --injection"
    assert call in skill
    assert not any("--probe" in line for line in bang_lines(skill)), "the probe must not depend on injection"
    # Cowork leaves both variables empty: the plugins-folder fallback, newest first, finds the CLI under synced/.
    assert "ls -t" in skill and "/synced/*/vela/scripts/vela" in skill and "/cache/*/vela/*/scripts/vela" in skill


def test_where_keeps_one_injection_line():
    lines = bang_lines(text("skills/where/SKILL.md"))
    assert len(lines) == 1
    # Rule deletion: the probe reports what the hand-written path loop and tool checks did.
    assert "for p in" not in lines[0] and "scripts/vela" not in lines[0] and "python3 --version" not in lines[0]


def test_where_offers_the_full_table_rather_than_leading_with_it():
    """Conversation rule 7 (voice audit row 213): the answer first, about four things, the rest offered."""
    skill = text("skills/where/SKILL.md")
    answer, offer = skill.index("Answer first"), skill.index('"Want the full table to send to the plugin\'s maintainer?"')
    assert answer < offer
    assert "one table row per `rows` entry" in skill[offer:] and "`yes`, `no` or `couldn't tell`" in skill[offer:]
    assert "When all is well, that's the whole answer" in skill and "about four things at most" in skill
    # Raw git and gh words never reach the lead.
    assert "never repeat a row's `detail`" in skill
    # Rule deletion: the probe checks git, gh and the network itself.
    for gone in ("git --version", "gh --version", "curl -sI", "find /"):
        assert gone not in skill


def test_where_allowed_tools_stay_narrow():
    front = text("skills/where/SKILL.md").split("---")[1]
    tools = re.search(r"^allowed-tools: (.*)$", front, re.M).group(1)
    assert "Bash(sh *scripts/run-vela *)" in tools
    for gone in ("curl", "find", "git", "gh", "test"):
        assert f"Bash({gone}" not in tools


def test_where_description_is_short_and_plain():
    front = text("skills/where/SKILL.md").split("---")[1]
    description = re.search(r"^description: (.*)$", front, re.M).group(1)
    assert len(description) <= 250 and "<" not in description and ">" not in description


def test_where_says_the_stance():
    skill = text("skills/where/SKILL.md")
    assert "Answer first, in your words, from the `stance` sentence" in skill


def test_where_loads_the_voice_before_it_talks():
    skill = text("skills/where/SKILL.md")
    load = next(line for line in skill.splitlines() if "voice/VOICE.md" in line)
    assert "references/CONVERSATION-VOICE.md" in load
    assert load.index("voice/VOICE.md") < load.index("CONVERSATION-VOICE")
    first_question = skill.index('"Want the full table')
    assert skill.index(load) < skill.index("Answer first") < first_question


# --- Overhaul plan Task 23: plan 7.3's stances, each tied to the probe rows that select it.


def test_where_names_the_stances():
    skill = text("skills/where/SKILL.md")
    stances = {
        "git, network and gh yes": "every session runs here, close included",
        "git yes, network or gh not": "`/vela:close` in Claude Code sends them",
        "a git repo where git doesn't run": "read, ask, find, explore and draft here",
        "no git": "sessions are recorded in Claude Code; drafts reach the vault as a proposal",
    }
    for row, said in stances.items():
        assert f"- {row}: " in skill and said in skill
        line = next(line for line in skill.splitlines() if line.startswith(f"- {row}: "))
        assert said in line, f"the stance for {row!r} must sit on its own row's line"


def test_where_no_longer_probes_a_flag_nothing_sets():
    """No skill carries disable-model-invocation, so there is no host behavior left to try by hand."""
    skill = text("skills/where/SKILL.md")
    assert "disable-model-invocation" not in skill and "frontmatter flags" not in skill and "/vela:dump" not in skill
