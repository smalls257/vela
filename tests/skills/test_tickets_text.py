"""What the tickets skill says, pinned in one place (overhaul plan Task 3).

Every test that pins this text lives here, so the rewrite that changes it edits this file and no other skill's.
Each section is headed by the file it came from and that file's reason.
"""
import re

import yaml
from conftest import REPO
from test_skill_commands_exist import calls, is_a_mention, parse_error
from vela import cli

PLUGIN = REPO / "plugin"


TICKETS = PLUGIN / "skills" / "tickets"


def text(path):
    return path.read_text(encoding="utf-8")


LINT = [w.strip() for w in (PLUGIN / "references" / "lint-words.txt").read_text(encoding="utf-8").splitlines() if w.strip() and not w.startswith("#")]


def skill_text_breakdown_tickets_skills(folder):
    return "\n".join(text(p) for p in sorted(folder.glob("*.md")))


def read(rel):
    return (PLUGIN / rel).read_text(encoding="utf-8")


# --- From tests/test_breakdown_tickets_skills.py: The text of /vela:breakdown and /vela:tickets: each kept item and
# each built-in rule is there, nothing points at a file that is not, and the plan format's own example is something
# the reader reads clean.


def test_tickets_reads_the_voices_through_start_and_the_conversation_voice_file():
    body = text(TICKETS / "SKILL.md")
    assert "references/CONVERSATION-VOICE.md" in body and "voice/VOICE.md" in body and "references/START.md" in body


def test_the_tickets_skill_checks_asks_creates_nothing_without_a_yes_and_stops():
    body = text(TICKETS / "SKILL.md")
    for phrase in ("vela tickets check", "Markdown ticket list", "CSV for Jira import", "Do you already have Jira connected to Claude, or a Jira command-line tool?",
                   "never guess a project key", "Nothing is created in any outside system without an explicit yes",
                   "Write no script to create tickets", "stop with one short summary", "9 stories, 42 tasks, 3 flagged"):
        assert phrase in body, phrase
    assert "tools/breakdown_to_tickets.py" not in body  # not shipped in the plugin zip; the CLI carries the converter


def test_tickets_names_no_missing_plugin_file_and_no_word_the_lint_list_holds():
    folder = TICKETS
    body = skill_text_breakdown_tickets_skills(folder)
    for rel in re.findall(r"\$\{CLAUDE_PLUGIN_ROOT\}/([A-Za-z0-9_./-]+)", body):
        rel = rel.rstrip(".")
        assert (PLUGIN / rel).exists(), f"{folder.name} names {rel}"
    for word in LINT:
        assert not re.search(rf"\b{re.escape(word)}", body, re.I), f"{folder.name} uses {word!r}"
    assert "~/.claude" not in body and "skill 1" not in body.lower() and "to-issues" not in body


# --- From tests/test_tracer_skills.py: The lead-side tracer guidance (S52, step 2): present in each skill, never a
# gate, the example in the plan's format, and no codes read to the lead.


def test_tickets_never_makes_the_tracer_a_gate():
    for sentence in re.split(r"(?<=[.?!])\s+", read("skills/tickets/SKILL.md")):
        if re.search(r"tracer", sentence, re.I):
            assert not re.search(r"\b(stop|stops|refuse|refuses|block|blocks|gate)\b", sentence, re.I), sentence


# --- Task 22k: the overhaul rewrite.

VOICE_LINE = re.compile(r"^.*`voice/VOICE\.md`.*references/CONVERSATION-VOICE\.md.*$", re.M)


def test_tickets_loads_the_voice_before_its_first_question():
    body = text(TICKETS / "SKILL.md").split("---\n", 2)[2]
    line = VOICE_LINE.search(body).group(0)
    assert line.startswith("Before your first question")
    assert body.index(line) < body.index("## 3. Ask which output") and body.index(line) < body.index('?"')


def test_tickets_says_the_check_in_words_and_no_raw_failure():
    body = text(TICKETS / "SKILL.md")
    assert "It looks for:" not in body  # the list of checks is the command's, not the skill's
    assert "say in one plain sentence that you couldn't check the plan" in body
    assert "MCP server" not in body


def test_tickets_description_is_short_and_has_no_angle_brackets():
    description = yaml.safe_load(text(TICKETS / "SKILL.md").split("---\n", 2)[1])["description"]
    assert len(description) <= 250 and "<" not in description and ">" not in description


def test_tickets_names_only_commands_that_exist():
    parser = cli.build_parser()
    found = list(calls(TICKETS / "SKILL.md"))
    assert len(found) >= 3, found
    for line, written, argv in found:
        assert is_a_mention(parser, argv) or parse_error(parser, argv) is None, (line, written)
