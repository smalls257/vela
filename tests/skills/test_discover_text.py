"""What the discover skill says, pinned in one place (overhaul plan Task 3).

Every test that pins this text lives here, so the rewrite that changes it edits this file and no other skill's.
Each section is headed by the file it came from and that file's reason.
"""
import re
import shlex

from conftest import REPO
from vela import cli

PLUGIN = REPO / "plugin"


def text(rel):
    return (PLUGIN / rel).read_text(encoding="utf-8")


# --- From tests/test_reviewers.py: The focused reviewers and the review checkpoints in the session skills.

# ------------------------------------------------------------------ the checkpoints replace the sweeps


def test_discover_runs_the_checkpoint_after_the_read_back_and_the_implications_list_is_gone():
    discover = text("skills/discover/SKILL.md")
    assert "references/REVIEW.md" in discover and '"after the read-back"' in discover
    assert "What these sources imply" not in discover
    assert "vela add subject --subject-type PTY" in discover and "`--subject-type SV`" in discover
    assert "vela questions --subject <ID>" in discover


def test_discover_leaves_the_checks_every_area_makes_to_the_agent():
    body = text("skills/discover/SKILL.md")
    assert "Add to that focus" not in body and "who gains and who loses" not in body
    assert "service levels" not in body


def test_round_two_fixes_in_discover():
    disc = text("skills/discover/SKILL.md")
    assert "`vela questions --subject <ID>`" in disc
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


# --- Overhaul Task 22g: the mechanics moved into commands; the read-back and the judgment stay.


DISCOVER = text("skills/discover/SKILL.md")


def vela_calls(body):
    """Each `vela <cmd> ...` the skill writes in a code span, as argv with placeholders filled."""
    found = re.findall(r"`vela ([a-z][^`]*)`", body)
    return [shlex.split(re.sub(r"\^c(?:NN?|\d+)", "^c01", re.sub(r"<[^<>]*>", "X", call))) for call in found]


def test_discover_names_only_commands_that_exist():
    parser = cli.build_parser()
    calls = vela_calls(DISCOVER)
    assert len(calls) >= 8, calls
    for argv in calls:
        _, extras = parser.parse_known_args(argv)
        assert not extras, (argv, extras)


def test_the_token_rule_is_the_commands_refusal_not_a_sentence():
    assert "user:token@" not in DISCOVER  # `vela add source` strips it and says so
    assert "vela add source --title" in DISCOVER and "takes out any credential and says so" in DISCOVER


def test_state_from_kind_is_applys_refusal_and_resolutions_go_through_resolve():
    assert "`vela apply --schema marks`" in DISCOVER and "Apply won't write a fact from a plan" in DISCOVER
    assert "`resolve` decision file (`vela apply --schema resolve`)" in DISCOVER
    assert "vela record add --origin" in DISCOVER


def test_discover_keeps_a_read_back_said_by_name():
    four = DISCOVER.split("4. Show", 1)[1].split("\n5. ", 1)[0]
    assert "(the partner guide, what runs today)" in four and "Yes to these three?" in four
    assert not re.search(r"\b(?:SRC|UNK|APP|PTY|SV)-", four.split("> 1.", 1)[1])
    assert "Name sources by title when you talk" in DISCOVER


def test_discover_says_the_audit_wording():
    assert "Noted: the plan holds money or points on customers' behalf." in DISCOVER
    assert "Because of that, these questions now need answers:" in DISCOVER
    assert "noted, there is stored value" not in DISCOVER and "now owes" not in DISCOVER


def test_discover_stops_when_a_command_cant_say_it():
    assert "When a command can't express what the lead wants, say so and stop." in DISCOVER
