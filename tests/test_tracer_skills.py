"""The lead-side tracer guidance (S52, step 2): present in each skill, never a gate, the example in the plan's format, and no codes read to the lead.

    python3 -m pytest tests/test_tracer_skills.py
"""
import re

from conftest import REPO

PLUGIN = REPO / "plugin"
LINT = [w.strip() for w in (PLUGIN / "references" / "lint-words.txt").read_text(encoding="utf-8").splitlines() if w.strip() and not w.startswith("#")]


def read(rel):
    return (PLUGIN / rel).read_text(encoding="utf-8")


def test_each_lead_side_skill_carries_its_tracer_guidance():
    assert "Draw the tracer candidate's flows first" in read("skills/boundary/SKILL.md")
    releases = read("skills/releases/SKILL.md")
    for part in ("the apps it crosses", "the new contracts it crosses", "Break a tie", "Heron", "for each requirement the tracer touches",
                 "Not in the tracer", "kept it all", "**Tracer:** none, <reason>", "no flow page yet"):
        assert part in releases, part
    assert "this app's piece of it" in read("skills/grill/SKILL.md")
    assert "first epic is on the tracer" in read("skills/epics/SKILL.md")
    assert "which flow would prove it first" in read("skills/shape/SKILL.md")
    modes = read("references/MODES.md")
    assert "offer the tracer" in modes and "first epic is on release one's tracer" in modes
    assert "**Not in the tracer:**" in read("references/TECH-DESIGN-FROM-VAULT.md")


def test_the_tracer_is_explained_where_a_skill_first_says_it_and_is_never_a_slice():
    for name in ("boundary", "releases", "grill", "epics", "shape"):
        text = read(f"skills/{name}/SKILL.md")
        if name != "shape":
            assert re.search(r"thin path through every app", text), name
        for sentence in re.split(r"(?<=[.?!])\s+", text):
            if re.search(r"tracer", sentence, re.I):
                assert not re.search(r"\bslices?\b", sentence, re.I), (name, sentence)


def test_no_skill_makes_the_tracer_a_gate():
    for name in ("boundary", "releases", "grill", "epics", "shape", "design", "breakdown", "tickets"):
        for sentence in re.split(r"(?<=[.?!])\s+", read(f"skills/{name}/SKILL.md")):
            if re.search(r"tracer", sentence, re.I):
                assert not re.search(r"\b(stop|stops|refuse|refuses|block|blocks|gate)\b", sentence, re.I), (name, sentence)


def test_the_releases_example_matches_the_plans_bullet_format():
    text = read("skills/releases/SKILL.md")
    assert re.search(r"^- \*\*Tracer:\*\* \[\[FLO-001-[^|\]]+\|FLO-001\]\], \[\[FLO-002-[^|\]]+\|FLO-002\]\], [a-z]", text, re.M)
    assert re.search(r"^- \*\*Not in the tracer:\*\* .+ \(CAP-\d+\.FR\d+\): .+", text, re.M)
    block = text.split("```", 2)[1]
    assert block.index("**State:**") < block.index("**Tracer:**") < block.index("**Not in the tracer:**") < block.index("| Delivers")


def test_the_conversation_asks_for_names_not_codes():
    section = read("skills/releases/SKILL.md").split("3. **The tracer.**", 1)[1].split("4. **What comes next.**", 1)[0]
    assert not re.search(r"\b(FLO|CAP|CON|APP)-\d", section)
    for word in LINT:
        assert not re.search(rf"\b{re.escape(word)}\b", section, re.I), word
