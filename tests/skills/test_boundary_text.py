"""What the boundary skill says, pinned in one place (overhaul plan Task 3).

Every test that pins this text lives here, so the rewrite that changes it edits this file and no other skill's.
Each section is headed by the file it came from and that file's reason.
"""
import re

from conftest import REPO, skill_text

PLUGIN = REPO / "plugin"


def text(rel):
    return (PLUGIN / rel).read_text(encoding="utf-8")


def read(rel):
    return (PLUGIN / rel).read_text(encoding="utf-8")


# --- From tests/test_cases.py: A contract's case table: the parser reads it, `vela check` warns when it is missing or
# cannot be trusted.


def test_boundary_writes_the_case_table_and_asks_one_question_per_open_case():
    from conftest import skill_text
    assert "case table" in skill_text("boundary") and "one question per open case" in skill_text("boundary")


# --- From tests/test_session_experience.py: What the skills make a lead go through (docs/research/2026-10-12-session-
# experience-review.md and the friction pass).

# --- S24: close starts on the lead's word, and still confirms before anything leaves the machine


def test_boundary_stays_the_leads_to_start():
    assert "disable-model-invocation: true" in text("skills/boundary/SKILL.md"), "boundary must stay the lead's to start"


def test_boundary_hands_the_lead_to_start_not_to_a_slash_command_they_must_type():
    body = text("skills/boundary/SKILL.md")
    assert "Closing a session" in body, "boundary must say how its session ends"
    assert "Do not run close yourself" not in body
    assert not re.search(r'[Tt]ell the user: "Run `/vela:close`', body)


# --- S26 and S43: the review digest is small, plain, once


def test_boundary_leaves_the_digest_to_review():
    assert "high and blocking lines in full" not in text("skills/boundary/SKILL.md")


# --- S36 to S47


def test_boundary_tests_cuts_against_requirements():
    assert "functional requirements" in text("skills/boundary/SKILL.md").split("## 2.")[0]
    assert "Test each cut against the functional requirements" in text("skills/boundary/SKILL.md")


def test_boundary_marks_its_own_captures():
    assert "→ keep: [[" in text("skills/boundary/SKILL.md"), "boundary no longer marks its own captures"


# --- From tests/test_skills.py: The plugin's skills: frontmatter, size, the files they point at, the plugin
# validator, and the rules each skill exists to hold.

# tech-design-grill vault mode (V1-18): read the slice, link back by ID and commit, never copy vault text.


def test_boundary_turns_a_decided_direction_into_apps_and_decides_nothing():
    b = text("skills/boundary/SKILL.md")
    assert "Offer 2 or 3 ways to cut the direction into apps, never one and never more than three" in b
    assert "write a line only after the yes `START.md` defines" in b and "a yes to a group counts for the lines in it" in b
    assert "read the sheet back in two groups" in b.lower()
    assert "Every page this session writes is an `assumption`, never `decided`" in b and "never `addressed`" in b
    assert "→ keep: [[<page>#<heading>|<ID>]] (assumption)" in b
    assert 'the checkpoint "after the pages are written"' in b and "questions --subject <ID>" in b
    assert "/vela:grill <APP-id>" in b


def test_boundary_asks_which_capability_each_flow_serves_and_leaves_it_out_without_capabilities():
    boundary = skill_text("boundary")
    assert "`capabilities`" in boundary and "which capability the journey serves" in boundary
    assert "leave the field out and do not invent one" in boundary


# --- From tests/test_tracer_skills.py: The lead-side tracer guidance (S52, step 2): present in each skill, never a
# gate, the example in the plan's format, and no codes read to the lead.


def test_boundary_carries_its_tracer_guidance():
    assert "Draw the tracer candidate's flows first" in read("skills/boundary/SKILL.md")


def test_boundary_explains_the_tracer_as_the_first_thin_path():
    # The amendment of 2026-10-13: a slice is the unit of done and the tracer is slice one, so a sentence may say both.
    text = skill_text("boundary")  # the tracer is defined once, in CONVENTIONS; each skill names it the first thin path
    assert "first thin path" in text and ("Releases" in text or "Slices" in text)


def test_boundary_leaves_the_tracer_definition_to_conventions():
    assert "thin path through every app" not in skill_text("boundary")  # said once, in CONVENTIONS


def test_boundary_hands_the_tracer_candidate_to_releases():
    boundary = skill_text("boundary")
    assert "so releases does not ask again" in boundary and "→ keep: [[<first flow page>#Steps|<the flow's name>]] (assumption)" in boundary


def test_boundary_never_makes_the_tracer_a_gate():
    for sentence in re.split(r"(?<=[.?!])\s+", read("skills/boundary/SKILL.md")):
        if re.search(r"tracer", sentence, re.I):
            assert not re.search(r"\b(stop|stops|refuse|refuses|block|blocks|gate)\b", sentence, re.I), sentence


# --- Overhaul plan Task 22e: the templates moved into commands, so the skill calls them and the rule text is gone.


def test_boundary_stubs_through_add_app_stub_and_drops_the_exact_line():
    b = text("skills/boundary/SKILL.md")
    assert "vela add app-stub --slug <slug>" in b
    assert "exactly the line" not in b and "Its boundary sheet is still to be read back." not in b  # the command's


def test_boundary_counts_cut_coverage_with_boundary_cover():
    b = text("skills/boundary/SKILL.md")
    assert "vela boundary cover --cut .vela/cuts.json --for-lead" in b
    assert "the trade-offs are yours to say" in b


def test_boundary_writes_the_pick_with_add_cut():
    b = text("skills/boundary/SKILL.md")
    assert "vela add cut --name" in b
    assert "`- **Options considered:**` bullet, `<picked cut> (picked)" not in b  # add cut writes it


def test_boundary_drops_the_five_things_easy_to_get_wrong():
    b = text("skills/boundary/SKILL.md")
    assert "Five things are easy to get wrong" not in b
    assert "New IDs come from `vela next-id <PREFIX>`, so an open session branch" not in b  # add numbers them
    assert "`### UNK-nnn <short name>`, with `**Question:**`" not in b  # add unknown writes it


def test_boundary_writes_contracts_unknowns_and_marks_through_commands():
    b = text("skills/boundary/SKILL.md")
    assert "vela add contract --provider APP-<slug>" in b and "vela add unknown --name" in b
    assert "vela apply --schema marks" in b
    assert "When a command can't express what the lead wants, say so and stop." in b


def test_boundary_checkpoints_with_render_check_and_close_stage():
    b = text("skills/boundary/SKILL.md")  # `vela checkpoint` (Task 21i) isn't built: these three are its steps
    assert "`vela render`, then `vela check --for-lead`" in b and "`vela close stage --checkpoint --for-lead`" in b


def test_boundary_prepares_its_review_with_reviewers_prepare():
    assert 'vela reviewers prepare --checkpoint "after the pages are written"' in text("skills/boundary/SKILL.md")
