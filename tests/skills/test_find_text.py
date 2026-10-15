"""What the find skill says, pinned in one place (overhaul plan Task 3, Task 22k).

Every test that pins this text lives here, so the rewrite that changes it edits this file and no other skill's.
"""
import re

import yaml
from conftest import REPO
from test_skill_commands_exist import calls, is_a_mention, parse_error
from vela import cli

FIND = REPO / "plugin" / "skills" / "find" / "SKILL.md"


# The voice load line: the owner's VOICE.md, then the plugin's conversation voice, in that order on one line.
VOICE_LINE = re.compile(r"^.*`voice/VOICE\.md`.*references/CONVERSATION-VOICE\.md.*$", re.M)


def body():
    return FIND.read_text(encoding="utf-8").split("---\n", 2)[2]


def meta():
    return yaml.safe_load(FIND.read_text(encoding="utf-8").split("---\n", 2)[1])


def test_find_loads_the_voice_before_it_says_anything():
    text = body()
    line = VOICE_LINE.search(text).group(0)  # VOICE.md first, then the conversation voice
    assert text.index(line) < text.index("## Steps")


def test_find_answers_by_name_not_by_path():
    text = body()
    assert 'Best place: <title> (<page title> page, "<heading>")' in text
    assert '`Best place: Record consent (Consent and identity page, "Record consent")`' in text
    assert "Journeys that use it:" in text and "Flows that cross it" not in text
    assert "<path>" not in text and "Never print IDs or file paths." in text


def test_find_stays_fast_and_points_at_ask():
    text = body()
    assert "Stop after three searches in all." in text
    assert "For a careful answer with every source checked: /vela:ask <question>." in text


def test_find_description_is_short_and_has_no_angle_brackets():
    description = meta()["description"]
    assert len(description) <= 250 and "<" not in description and ">" not in description


def test_find_names_only_commands_that_exist():
    parser = cli.build_parser()
    found = list(calls(FIND))
    assert found
    for line, written, argv in found:
        assert is_a_mention(parser, argv) or parse_error(parser, argv) is None, (line, written)
