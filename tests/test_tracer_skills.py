"""The lead-side tracer guidance (S52, step 2): present in each skill, never a gate, the example in the plan's format, and no codes read to the lead.

    python3 -m pytest tests/test_tracer_skills.py
"""
import re

from conftest import REPO, skill_text

PLUGIN = REPO / "plugin"
LINT = [w.strip() for w in (PLUGIN / "references" / "lint-words.txt").read_text(encoding="utf-8").splitlines() if w.strip() and not w.startswith("#")]


def read(rel):
    return (PLUGIN / rel).read_text(encoding="utf-8")


def test_each_lead_side_skill_carries_its_tracer_guidance():
    assert "Draw the tracer candidate's flows first" in read("skills/boundary/SKILL.md")
    releases = read("skills/releases/SKILL.md")
    for part in ("the apps it crosses", "the new contracts it crosses", "Break a tie", "if two flows each cross three apps and three new contracts", "each requirement the tracer touches",
                 "Not in this slice", "kept it all", "**Flows:** none, <reason>", "no flow page yet", "The tracer is the slice page SLC-001"):
        assert part in releases, part
    assert "this app's piece of it" in skill_text("grill")
    assert "first epic is on the first thin path (the tracer" in read("skills/epics/SKILL.md")
    assert "which flow would prove it first" in read("skills/shape/SKILL.md")
    modes = read("references/MODES.md")
    assert "offer the tracer" in modes and "first epic is on release one's tracer" in modes
    assert "**Not in the tracer:**" in read("references/TECH-DESIGN-FROM-VAULT.md")


def test_the_tracer_is_explained_where_a_skill_first_says_it_and_is_the_slice_with_no_after():
    # The amendment of 2026-10-13: a slice is the unit of done and the tracer is slice one, so a sentence may say both.
    for name in ("boundary", "releases", "grill", "epics"):
        text = skill_text(name)  # the tracer is defined once, in CONVENTIONS; each skill names it the first thin path
        assert "first thin path" in text and ("Releases" in text or "Slices" in text), name
    assert "The tracer is the one slice with no After, usually SLC-001" in (REPO / "template" / "CONVENTIONS.md").read_text(encoding="utf-8")


def test_the_tracer_has_one_definition_and_boundary_hands_the_candidate_to_releases():
    conventions = (REPO / "template" / "CONVENTIONS.md").read_text(encoding="utf-8")
    assert conventions.count("a thin path through every app and contract it needs, built first and kept") == 1
    for name in ("boundary", "releases", "grill", "epics", "shape", "design"):
        assert "thin path through every app" not in skill_text(name), name  # said once, in CONVENTIONS
    boundary = skill_text("boundary")
    assert "so releases does not ask again" in boundary and "→ keep: [[<first flow page>#Steps|<the flow's name>]] (assumption)" in boundary
    releases = read("skills/releases/SKILL.md")
    assert "the first thin path the boundary session recorded" in releases and "open with it and ask whether it is still right" in releases


def test_no_skill_makes_the_tracer_a_gate():
    for name in ("boundary", "releases", "grill", "epics", "shape", "design", "breakdown", "tickets"):
        for sentence in re.split(r"(?<=[.?!])\s+", read(f"skills/{name}/SKILL.md")):
            if re.search(r"tracer", sentence, re.I):
                assert not re.search(r"\b(stop|stops|refuse|refuses|block|blocks|gate)\b", sentence, re.I), (name, sentence)


def test_the_releases_example_matches_the_plans_bullet_format():
    text = read("skills/releases/SKILL.md")
    block = text.split("```", 2)[1]
    assert block.index("**State:**") < block.index("**Slices:** SLC-001") < block.index("| Delivers")
    assert "`**Tracer:**`, `**Not in the tracer:**`" in text  # a vault still on the releases page keeps working
    assert '`vela conventions "Slices"` gives' in text


def test_the_conversation_asks_for_names_not_codes():
    section = read("skills/releases/SKILL.md").split("3. **The first thin path (the tracer).**", 1)[1].split("4. **The next slices.**", 1)[0]
    assert not re.search(r"\b(FLO|CAP|CON|APP)-\d", section)
    for word in LINT:
        assert not re.search(rf"\b{re.escape(word)}\b", section, re.I), word
