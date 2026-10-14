"""What the discover skill says, pinned in one place (overhaul plan Task 3).

Every test that pins this text lives here, so the rewrite that changes it edits this file and no other skill's.
Each section is headed by the file it came from and that file's reason.
"""
import re

from conftest import REPO

PLUGIN = REPO / "plugin"


def text(rel):
    return (PLUGIN / rel).read_text(encoding="utf-8")


# --- From tests/test_reviewers.py: The focused reviewers and the review checkpoints in the session skills.

# ------------------------------------------------------------------ the checkpoints replace the sweeps


def test_discover_runs_the_checkpoint_after_the_read_back_and_the_implications_list_is_gone():
    discover = text("skills/discover/SKILL.md")
    assert "references/REVIEW.md" in discover and '"after the read-back"' in discover
    assert "What these sources imply" not in discover
    assert "### PTY-nn <name>" in discover and "### SV-nn <name>" in discover
    assert "vela questions --subject <ID>" in discover


def test_discover_leaves_the_checks_every_area_makes_to_the_agent():
    body = text("skills/discover/SKILL.md")
    assert "Add to that focus" not in body and "who gains and who loses" not in body
    assert "service levels" not in body


def test_round_two_fixes_in_discover():
    disc = text("skills/discover/SKILL.md")
    assert "python3 ${CLAUDE_PLUGIN_ROOT}/scripts/vela questions --subject <ID>" in disc
    assert "say aloud any pair of lines" in disc and "never two facts" in disc
    assert '"after the read-back" (the "Here\'s what I think exists" step' in disc


# --- From tests/test_session_experience.py: What the skills make a lead go through (docs/research/2026-10-12-session-
# experience-review.md and the friction pass).

# --- S24: close starts on the lead's word, and still confirms before anything leaves the machine


def test_discover_stays_the_leads_to_start():
    assert "disable-model-invocation: true" in text("skills/discover/SKILL.md"), "discover must stay the lead's to start"


def test_discover_hands_the_lead_to_start_not_to_a_slash_command_they_must_type():
    body = text("skills/discover/SKILL.md")
    assert "Closing a session" in body, "discover must say how its session ends"
    assert "Do not run close yourself" not in body
    assert not re.search(r'[Tt]ell the user: "Run `/vela:close`', body)


# --- S26 and S43: the review digest is small, plain, once


def test_discover_leaves_the_digest_to_review():
    assert "high and blocking lines in full" not in text("skills/discover/SKILL.md")


# --- S36 to S47


def test_discover_marks_its_own_captures():
    assert "→ keep: [[" in text("skills/discover/SKILL.md"), "discover no longer marks its own captures"


# --- From tests/test_skills.py: The plugin's skills: frontmatter, size, the files they point at, the plugin
# validator, and the rules each skill exists to hold.

# discover and shape (V1-11). There is no probe skill: unknowns are offered at start and in MODES.md.


def test_discover_cites_sources_and_never_promotes_a_plan_to_fact():
    discover = text("skills/discover/SKILL.md")
    assert "A line from an `intends` source is an `assumption`" in discover
    assert "Never copy document text into the vault." in discover
    assert "Claude's general knowledge is never a source." in discover
    assert "`Kind: repo`" in discover and "<url>@<sha>" in discover


def test_discover_fix_round_guesses_never_become_facts():
    d = text("skills/discover/SKILL.md")
    assert "Propose a `Kind` for each source" in d and "confirmed `Kind`" in d
    assert 'A line about the future ("will", "planned", "by Q4", "ready in") is an `assumption`, whatever its source\'s `Kind`.' in d
    assert "Label every line with its source" in d and "that source's `Kind`" in d and "what runs today or a plan" in d
    assert "the lines the lead said yes to" in d and "ask once more in different words" in d
    assert "`first-hand` is not a registered `Kind`" in d and "`Kind: exists`" in d
    assert "an owner handle and an ask-by date" in d
    assert "capture line and a `## Changes` row" in d


def test_discover_marks_its_fact_captures():
    assert "→ keep: [[<page>#<heading>|<ID>]] (fact)" in text("skills/discover/SKILL.md")


# --- From tests/test_vault_title.py: S49: the first session asks for the initiative's short name once, and vela check
# warns (W718) while the vault still carries the title the template ships.


def test_discover_asks_once_for_the_initiatives_short_name():
    text = (PLUGIN / "skills" / "discover" / "SKILL.md").read_text(encoding="utf-8")
    assert "asks once for the initiative's short name" in text
