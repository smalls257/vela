"""What the allocate skill says, pinned in one place (overhaul plan Task 3).

Every test that pins this text lives here, so the rewrite that changes it edits this file and no other skill's.
Each section is headed by the file it came from and that file's reason.
"""
import re

from conftest import REPO, assert_offered_then_asked


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


# --- From tests/test_session_experience.py: What the skills make a lead go through (the constraints the skills put on a lead's session).

# --- S24: close starts on the lead's word, and still confirms before anything leaves the machine


def test_allocate_stays_the_leads_to_start():
    assert_offered_then_asked("allocate")


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


# ---- overhaul plan Task 22f: the conversation voice first, the sheet in the lead's words, contracts through add contract

SKILL = (REPO / "plugin" / "skills" / "allocate" / "SKILL.md").read_text(encoding="utf-8")


def test_allocate_loads_the_voice_before_its_first_question():
    line = next(p for p in SKILL.split("\n\n") if "references/CONVERSATION-VOICE.md`" in p and "voice/VOICE.md" in p)
    assert line.index("voice/VOICE.md") < line.index("references/CONVERSATION-VOICE.md`")
    # allocate writes no page prose (table cells and contract bullets are never voiced), so no house-voice clause
    at = SKILL.index(line)
    assert at < SKILL.index("vela render") and at < SKILL.index("show the allocation as a grid")


def test_allocate_names_only_commands_that_exist():
    import shlex
    from vela import cli
    parser = cli.build_parser()
    calls = re.findall(r"`vela ([a-z][^`]*)`", SKILL)
    assert any(c.startswith("add contract") for c in calls) and any(c.startswith("add unknown") for c in calls)
    for call in calls:
        argv = shlex.split(re.sub(r"<[^>]*>", "X", call).replace("^cNN", "^c01"))
        _, extras = parser.parse_known_args(argv)
        assert not extras, (call, extras)


def test_the_sheet_labels_are_said_in_the_leads_words():
    for label in ("**What each app does:**", "**What passes between apps, and the contract that carries it:**",
                  "**A handover no contract covers yet:**", "**What nobody does yet:**"):
        assert label in SKILL, label
    for old in ("Each app's share:", "What crosses:", "A missing contract:", "What is left:"):
        assert old not in SKILL, old


def test_a_missing_contract_goes_through_add_contract_and_is_told_plainly():
    assert "vela add contract --provider" in SKILL
    assert "with every required bullet, `**State:** assumption` and `**Change:** new`" not in SKILL  # add contract's now
    assert "This is a new contract between apps that nobody planned when the apps were split. It still needs deciding like the others." in SKILL
    assert "boundary did not draw" not in SKILL


def test_allocate_keeps_what_no_command_owns_yet():
    # "40 words or fewer" stays: the `allocate` apply kind (Task 15b) was dropped, so no command refuses a long cell.
    assert "40 words or fewer" in SKILL
    # The missing `allocation` block stays by hand: `render --add-missing-blocks` was never built.
    assert "add an `## Allocation` section with the empty block markers" in SKILL


def test_allocate_says_rows_and_apps_by_name_and_grill_lower_case():
    assert "say the requirement and the app by name" in SKILL
    assert "/vela:grill APP-<slug>" not in SKILL and '"/vela:grill Desktop agent"' in SKILL
    assert not re.search(r"\bGrill\b", SKILL)
