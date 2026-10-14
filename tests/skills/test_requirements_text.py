"""What the requirements skill says, pinned in one place (overhaul plan Task 3).

Every test that pins this text lives here, so the rewrite that changes it edits this file and no other skill's.
Each section is headed by the file it came from and that file's reason.
"""
import re

from conftest import REPO


def text_of(*parts):
    return (REPO.joinpath(*parts)).read_text(encoding="utf-8")


SKILL = REPO / "plugin" / "skills" / "requirements" / "SKILL.md"


def section(text, heading):
    start = text.index(heading)
    end = text.index("\n## ", start + 1)
    return text[start:end]


PLUGIN = REPO / "plugin"


def text(rel):
    return (PLUGIN / rel).read_text(encoding="utf-8")


# --- From tests/test_reading_load.py: Pages a person can hold in mind: plain names in prose, IDs on a Trace line, and
# the five reading-load warnings.

# ---------------------------------------------------------------- the rule is written where sessions read it


def test_requirements_names_the_trace_line():
    assert "Trace" in text_of("plugin", "skills", "requirements", "SKILL.md")


# --- From tests/test_requirements_terms.py: The requirements session carries over requirements-grill's habit of
# fixing each term once: two words for one thing get one question, the answer is used from then on, and the glossary
# owns it.


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


# --- From tests/test_session_experience.py: What the skills make a lead go through (docs/research/2026-10-12-session-
# experience-review.md and the friction pass).

# --- S24: close starts on the lead's word, and still confirms before anything leaves the machine


def test_requirements_stays_the_leads_to_start():
    assert "disable-model-invocation: true" in text("skills/requirements/SKILL.md"), "requirements must stay the lead's to start"


def test_requirements_hands_the_lead_to_start_not_to_a_slash_command_they_must_type():
    body = text("skills/requirements/SKILL.md")
    assert "Closing a session" in body, "requirements must say how its session ends"
    assert "Do not run close yourself" not in body
    assert not re.search(r'[Tt]ell the user: "Run `/vela:close`', body)


# --- S26 and S43: the review digest is small, plain, once


def test_requirements_leaves_the_digest_to_review():
    assert "high and blocking lines in full" not in text("skills/requirements/SKILL.md")


# --- S36 to S47


def test_a_dropped_requirement_is_never_struck_through():
    requirements = text("skills/requirements/SKILL.md")
    assert "stays, struck through" not in requirements and "never strike its heading through" in requirements


def test_requirements_marks_its_own_captures():
    assert "→ keep: [[" in text("skills/requirements/SKILL.md"), "requirements no longer marks its own captures"
