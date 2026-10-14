"""What the allocate skill says, pinned in one place (overhaul plan Task 3).

Every test that pins this text lives here, so the rewrite that changes it edits this file and no other skill's.
Each section is headed by the file it came from and that file's reason.
"""
import re

from conftest import REPO


def words(count, start=0):
    """Distinct words, so a long paragraph is not also a repeated phrase."""
    return " ".join(f"item{n}" for n in range(start, start + count)) + ". "


LINT = REPO / "plugin" / "references" / "lint-words.txt"


PLUGIN = REPO / "plugin"


def text(rel):
    return (PLUGIN / rel).read_text(encoding="utf-8")


# --- From tests/test_readload.py: The second five reading-load warnings (design session 16): a paragraph, a table
# cell, a stock phrase, a template opening and an abbreviation that costs the reader more than a careful writer would.

# ------------------------------------------------------------------------------------------------ the lint word list (16-D2)


def test_allocate_never_names_a_listed_word():
    """Naming a word in a prompt raises its odds, so the list lives in the lint and the reviewer, and the drafter never
    sees it."""
    from vela import reading
    words = reading.lint_words(LINT.read_text(encoding="utf-8"))
    relative = "skills/allocate/SKILL.md"
    text = (REPO / "plugin" / relative).read_text(encoding="utf-8")
    for word in words:
        assert not reading.lint_pattern(word).search(text.replace("lint-words.txt", "")), f"{relative} names '{word}'"


# --- From tests/test_session_experience.py: What the skills make a lead go through (docs/research/2026-10-12-session-
# experience-review.md and the friction pass).

# --- S24: close starts on the lead's word, and still confirms before anything leaves the machine


def test_allocate_stays_the_leads_to_start():
    assert "disable-model-invocation: true" in text("skills/allocate/SKILL.md"), "allocate must stay the lead's to start"


def test_allocate_hands_the_lead_to_start_not_to_a_slash_command_they_must_type():
    body = text("skills/allocate/SKILL.md")
    assert "Closing a session" in body, "allocate must say how its session ends"
    assert "Do not run close yourself" not in body
    assert not re.search(r'[Tt]ell the user: "Run `/vela:close`', body)


# --- S26 and S43: the review digest is small, plain, once


def test_allocate_leaves_the_digest_to_review():
    assert "high and blocking lines in full" not in text("skills/allocate/SKILL.md")


# --- S36 to S47


def test_allocate_marks_its_own_captures():
    assert "→ keep: [[" in text("skills/allocate/SKILL.md"), "allocate no longer marks its own captures"
