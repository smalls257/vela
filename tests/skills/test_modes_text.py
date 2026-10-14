"""What the modes reference says, pinned in one place (overhaul plan Task 3).

Every test that pins this text lives here, so the rewrite that changes it edits this file and no other skill's.
Each section is headed by the file it came from and that file's reason.
"""
import re

from conftest import REPO


def read(*parts):
    return REPO.joinpath(*parts).read_text(encoding="utf-8")


PLUGIN = REPO / "plugin"


def section(text, heading):
    """The body of a `## heading` section, up to the next `## `."""
    match = re.search(rf"^## {re.escape(heading)}\n(.*?)(?=^## |\Z)", text, re.M | re.S)
    return match.group(1) if match else ""


def read_override(*parts):
    return (PLUGIN.joinpath(*parts)).read_text(encoding="utf-8")


def text(rel):
    return (PLUGIN / rel).read_text(encoding="utf-8")


def read_tracer_skills(rel):
    return (PLUGIN / rel).read_text(encoding="utf-8")


# --- From tests/test_answer.py: Answering a challenge: START opens an answer session on the challenge's own branch, a
# Grill (or the lead setting the item back) works there, and close pushes to that branch and comments on the open
# challenge PR instead of opening a new one.


def test_modes_lists_the_answer_session():
    assert "| Answer (`answer`)" in read("plugin", "references", "MODES.md")
    assert "| `answer` |" in read("plugin", "references", "MODES.md")


# --- From tests/test_challenge.py: /vela:challenge: a senior's challenge after handoff becomes an open unknown they
# own, which blocks the item, and a Dissent line on it.


def test_modes_lists_the_challenge_session():
    assert "| Challenge (`challenge`)" in (PLUGIN / "references" / "MODES.md").read_text(encoding="utf-8")


# --- From tests/test_design_skill.py: /vela:design (P13, S48, S52): the plugin's design skill, the summary-first doc
# it writes, and the Heron fixture.

# --- design as a known mode ---------------------------------------------------------------------------------------


def test_modes_names_the_design_session():
    modes = (PLUGIN / "references" / "MODES.md").read_text(encoding="utf-8")
    team = section(modes, "Team-side sessions")
    assert "`/vela:design --app APP-x`" in team and "`docs/tech-design/<slug>.md`" in team


# --- From tests/test_final_fixes.py: Fixes from the final whole-branch review: each test names the failure it keeps
# out.

# 1, M6, M9, M5, M4, 7, M2, M3, README: the words the skills and template must carry


def test_modes_says_epics_runs_render_too():
    modes = read("plugin/references/MODES.md")
    assert "Close runs `vela render` for those." not in modes and "so does `epics`" in modes


# --- From tests/test_next_id.py: vela next-id: a number an open session branch already holds is never handed out
# again (UNK-026 twice, heron run).


def test_modes_numbers_new_unknowns_with_the_command_not_by_eye():
    from conftest import REPO
    assert "vela next-id UNK" in (REPO / "plugin" / "references/MODES.md").read_text(encoding="utf-8")


# --- From tests/test_override.py: The user can override any rule, and an override is never invisible.

# ------------------------------------------------------------- skill text


def test_modes_says_the_user_may_override_any_rule():
    assert "The user may override any of them" in read_override("references", "MODES.md")


# --- From tests/test_reviewers.py: The focused reviewers and the review checkpoints in the session skills.

# ------------------------------------------------------------------ the checkpoints replace the sweeps


def test_modes_has_no_question_cap_and_no_sweep():
    modes = text("references/MODES.md")
    assert "at most two questions" not in modes and "concern sweep" not in modes
    assert "## Owed questions" in modes and "No question is dropped and none is owed a quota" in modes
    assert modes.count("question ledger rows") == 5  # dump, discover, shape, boundary and grill write them at close


# ------------------------------------------------------------------ a close, run by its rules, on real records
# The helpers below apply close's rules to session records as a session leaves them, unmarked. What
# the lead says at close (facts, states, beliefs) is the only other input. Each row, mark, subject and
# unknown is derived from those, never written by hand, so the test fails if the rules produce rows
# that check refuses.


def test_modes_asks_once_what_the_lead_might_not_know_they_need():
    modes = text("references/MODES.md")
    assert "**Ask what they might not know they need.**" in modes
    assert "In Discover, Shape and Grill" in modes and "who has to agree or be consulted" in modes


# --- From tests/test_session_experience.py: What the skills make a lead go through (docs/research/2026-10-12-session-
# experience-review.md and the friction pass).

# --- S26 and S43: the review digest is small, plain, once


def test_modes_puts_no_cap_on_the_digest():
    assert "no cap" not in text("references/MODES.md").lower()


# --- From tests/test_skill_commands.py: Skill text that names the v2 commands: vela next at start, the Options
# considered bullet Shape leaves and next reads, and the handoff manifest close writes.


def test_modes_says_where_to_start():
    modes = text("references/MODES.md")
    assert "## Where to start" in modes
    assert "`vela next` names the one app and mode" in modes and "`vela status` shows every app's stage" in modes


def test_modes_writes_assumptions_with_options_considered():
    assert "`assumption` items with `**Options considered:**`" in text("references/MODES.md")


# --- From tests/test_skills.py: The plugin's skills: frontmatter, size, the files they point at, the plugin
# validator, and the rules each skill exists to hold.

# discover and shape (V1-11). There is no probe skill: unknowns are offered at start and in MODES.md.


def test_there_is_no_probe_skill():
    assert not (PLUGIN / "skills" / "probe").exists()
    assert "probe" not in text("references/MODES.md").lower()


# epics (V1-17): the check finds the frontier, only the lead's confirmation decides, the gate closes.


def test_modes_knows_epics():
    assert "| Epics (`epics`)" in text("references/MODES.md") and "| `epics` | `draft` epic pages" in text("references/MODES.md")


# tech-design-grill vault mode (V1-18): read the slice, link back by ID and commit, never copy vault text.


def test_modes_lists_the_boundary_session():
    modes = text("references/MODES.md")
    assert "| Boundary (`boundary`) |" in modes and "| `boundary` |" in modes


def test_modes_asks_the_lead_first_never_drafts_an_ask_and_ends_a_blocked_session():
    modes = text("references/MODES.md")
    assert "**Ask the lead first.**" in modes and "**A blocked session ends.**" in modes
    assert "Claude never drafts an email, a message, a chase or an ask for anyone to send, and never offers to." in modes
    assert "Never fill a blocked session with other work." in modes


# --- From tests/test_tracer_skills.py: The lead-side tracer guidance (S52, step 2): present in each skill, never a
# gate, the example in the plan's format, and no codes read to the lead.


def test_modes_carries_its_tracer_guidance():
    modes = read_tracer_skills("references/MODES.md")
    assert "offer the tracer" in modes and "first epic is on release one's tracer" in modes
