"""What the shape skill says, pinned in one place (overhaul plan Task 3).

Every test that pins this text lives here, so the rewrite that changes it edits this file and no other skill's.
Each section is headed by the file it came from and that file's reason.
"""
import re
import shlex

from conftest import REPO, skill_text
from vela import cli

PLUGIN = REPO / "plugin"


def text(rel):
    return (PLUGIN / rel).read_text(encoding="utf-8")


def read(rel):
    return (PLUGIN / rel).read_text(encoding="utf-8")


# --- From tests/test_reviewers.py: The focused reviewers and the review checkpoints in the session skills.

# ------------------------------------------------------------------ the checkpoints replace the sweeps


def test_shape_runs_the_checkpoint_before_options_with_what_must_be_true():
    shape = text("skills/shape/SKILL.md")
    assert "references/REVIEW.md" in shape and '"before options"' in shape
    assert shape.index("run the review checkpoint") < shape.index("Show the options.")
    assert '"what must be true" set' in shape and "`assumed` ledger row" in shape
    assert "vela check --gate shape" in shape


def test_shape_shows_the_top_conditions_and_sends_the_rest_through_the_digest():
    shape = text("skills/shape/SKILL.md")
    assert "only the top few conditions" in shape and "coverage line" in shape
    assert "through the one digest (REVIEW section 5)" in shape
    assert "quotes the option's capture" in shape and "counterparties" in shape
    assert "the shape gate will warn" not in shape and "tell the lead only that close will list what is still assumed" in shape


# --- From tests/test_session_experience.py: What the skills make a lead go through (docs/research/2026-10-12-session-
# experience-review.md and the friction pass).

# --- S24: close starts on the lead's word, and still confirms before anything leaves the machine


def test_shape_stays_the_leads_to_start():
    assert "disable-model-invocation: true" in text("skills/shape/SKILL.md"), "shape must stay the lead's to start"


def test_shape_hands_the_lead_to_start_not_to_a_slash_command_they_must_type():
    body = text("skills/shape/SKILL.md")
    assert "Closing a session" in body, "shape must say how its session ends"
    assert "Do not run close yourself" not in body
    assert not re.search(r'[Tt]ell the user: "Run `/vela:close`', body)


# --- S26 and S43: the review digest is small, plain, once


def test_shape_leaves_the_digest_to_review():
    assert "high and blocking lines in full" not in text("skills/shape/SKILL.md")


# --- From tests/test_skill_commands.py: Skill text that names the v2 commands: vela next at start, the Options
# considered bullet Shape leaves and next reads, and the handoff manifest close writes.


def test_shape_writes_options_considered_as_one_bullet():
    assert "`**Options considered:**` bullet naming the picked option" in text("skills/shape/SKILL.md")


# --- From tests/test_skills.py: The plugin's skills: frontmatter, size, the files they point at, the plugin
# validator, and the rules each skill exists to hold.

# discover and shape (V1-11). There is no probe skill: unknowns are offered at start and in MODES.md.


def test_shape_offers_two_or_three_and_never_decides():
    shape = text("skills/shape/SKILL.md")
    assert "never one and never more than three" in shape
    assert "that's decided, grill to confirm" in shape
    assert "Shape never decides" in shape


def test_shape_fix_round():
    shape = text("skills/shape/SKILL.md")
    assert "`claude, from <name>`" in shape
    assert "After close, run `/vela:grill <name>`" in shape and '"/vela:grill Desktop agent"' in shape


# --- From tests/test_tracer_skills.py: The lead-side tracer guidance (S52, step 2): present in each skill, never a
# gate, the example in the plan's format, and no codes read to the lead.


def test_shape_carries_its_tracer_guidance():
    assert "which flow would prove it first" in read("skills/shape/SKILL.md")


def test_shape_leaves_the_tracer_definition_to_conventions():
    assert "thin path through every app" not in skill_text("shape")  # said once, in CONVENTIONS


def test_shape_never_makes_the_tracer_a_gate():
    for sentence in re.split(r"(?<=[.?!])\s+", read("skills/shape/SKILL.md")):
        if re.search(r"tracer", sentence, re.I):
            assert not re.search(r"\b(stop|stops|refuse|refuses|block|blocks|gate)\b", sentence, re.I), sentence


# --- Overhaul Task 22g: options are captured through `vela record add`; options, the checkpoint "before options" and
# what must be true stay the skill's.


SHAPE = read("skills/shape/SKILL.md")


def test_shape_names_only_commands_that_exist():
    parser = cli.build_parser()
    calls = re.findall(r"scripts/vela ([a-z][^`]*)`", SHAPE) + re.findall(r"`vela ([a-z][^`]*)`", SHAPE)
    assert len(calls) >= 2, calls
    for call in calls:
        argv = shlex.split(re.sub(r"<[^<>]*>", "X", call))
        _, extras = parser.parse_known_args(argv)
        assert not extras, (call, extras)


def test_shape_captures_its_options_through_the_numbering_command():
    assert "vela record add --origin claude --tag thought" in SHAPE
    assert not re.search(r"\^c(?:NN|\d)", SHAPE)


def test_shape_says_grill_lower_case_and_states_in_words():
    assert not re.search(r"\bGrill\b", SHAPE)
    assert "keep the chosen one as not decided yet until a grill decides it" in SHAPE.split("---", 2)[1]
    assert '"not decided yet"' in SHAPE


def test_shape_shows_an_option_by_name_with_a_pick_and_why():
    example = SHAPE.split("> **Unlock at the dock.**", 1)[1].split("\n", 1)[0]
    assert "My pick:" in example and "(partners)" in example
    assert not re.search(r"\b(?:APP|CON|F\d|R-)", example)
