"""The requirements session carries over requirements-grill's habit of fixing each term once: two words for one thing
get one question, the answer is used from then on, and the glossary owns it."""
import re

from conftest import REPO

SKILL = REPO / "plugin" / "skills" / "requirements" / "SKILL.md"


def section(text, heading):
    start = text.index(heading)
    end = text.index("\n## ", start + 1)
    return text[start:end]


def test_two_words_for_one_thing_are_asked_about_once_and_the_answer_is_used_from_then_on():
    step = section(SKILL.read_text(encoding="utf-8"), "## 2. One capability at a time")
    habit = step.split("**Fix each term once.**", 1)[1].split("\n", 1)[0]
    assert "uses two words for one thing" in habit
    assert "ask once which is the vault's word" in habit
    assert "from then on in every requirement and criterion" in habit
    assert "`12-glossary.md`" in habit


def test_the_habit_is_short_and_sits_before_anything_is_written():
    text = SKILL.read_text(encoding="utf-8")
    habit = text.split("**Fix each term once.**", 1)[1].split("\n", 1)[0]
    assert len(re.findall(r"[.!?](?:\s|$)", habit)) <= 2
    assert text.index("**Fix each term once.**") < text.index("## 3. Write the confirmed requirements")
