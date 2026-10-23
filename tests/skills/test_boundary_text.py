"""What the boundary skill says, pinned in one place (overhaul plan Task 3).

Every test that pins this text lives here, so the rewrite that changes it edits this file and no other skill's.
Each section is headed by the file it came from and that file's reason.
"""
import re

from conftest import REPO, skill_text, assert_offered_then_asked

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


# --- From tests/test_session_experience.py: What the skills make a lead go through (the constraints the skills put on a lead's session).

# --- S24: close starts on the lead's word, and still confirms before anything leaves the machine


def test_boundary_stays_the_leads_to_start():
    assert_offered_then_asked("boundary")


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
    assert "a correction needs its own yes" in b
    start = text("references/START.md")  # the yes rule lives there once, for every mode
    assert "A line is written after a yes to that line." in start and "A yes that covers a group you read out" in start
    assert "write a line only after the yes `START.md` defines" not in b
    assert "read the sheet back in two groups" in b.lower()
    assert 'what it writes is "not decided yet"' in b and "never `addressed`" in b
    assert "as `(assumption)`" in b  # each capture is marked an assumption through `vela apply`
    assert "never `decided`" not in b  # rule deletion: the checks hold `decided`
    assert "→ keep: [[<page>#<heading>|<ID>]] (assumption)" in b
    assert 'the checkpoint "after the pages are written"' in b and "questions --subject <ID>" in b
    assert "/vela:grill Desktop agent" in b and "/vela:grill <APP-id>" not in b  # by name, not by ID


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
    assert "`vela add app-stub --for-lead`" in b
    assert "exactly the line" not in b and "Its boundary sheet is still to be read back." not in b  # the command's


def test_boundary_counts_cut_coverage_with_boundary_cover():
    b = text("skills/boundary/SKILL.md")
    assert "vela boundary cover --cut .vela/cuts.json --for-lead" in b
    assert "the trade-offs are yours" in b


def test_boundary_writes_the_pick_with_add_cut():
    b = text("skills/boundary/SKILL.md")
    assert "`vela add cut --for-lead`" in b
    assert "it marks the pick's capture" not in b  # rule deletion: the command marks it
    assert "`- **Options considered:**` bullet, `<picked cut> (picked)" not in b  # add cut writes it


def test_boundary_drops_the_five_things_easy_to_get_wrong():
    b = text("skills/boundary/SKILL.md")
    assert "Five things are easy to get wrong" not in b
    assert "New IDs come from `vela next-id <PREFIX>`, so an open session branch" not in b  # add numbers them
    assert "`### UNK-nnn <short name>`, with `**Question:**`" not in b  # add unknown writes it


def test_boundary_writes_contracts_unknowns_and_marks_through_commands():
    b = text("skills/boundary/SKILL.md")
    assert "`vela add contract --for-lead`" in b and "`vela add unknown --for-lead`" in b
    assert "`vela apply` (`--schema marks`)" in b
    assert "Commands write the templated parts" not in b and "won't write `decided`" not in b and "It writes the required bullets" not in b
    assert "which commits by exact path" not in b and "sends a stub back to Boundary" not in b
    # rule deletion: START's first line says it once for every mode skill
    assert "When a command can't express what the lead wants, say so and stop." not in b
    assert "When a command can't express what the lead wants, say so and stop" in text("references/START.md")


def test_boundary_checkpoints_with_render_check_and_close_stage():
    b = text("skills/boundary/SKILL.md")  # `vela checkpoint` (Task 21i) isn't built: these three are its steps
    assert "Then `vela render`, `vela check --for-lead`" in b and "`vela close stage --checkpoint --for-lead`" in b


def test_boundary_prepares_its_review_with_reviewers_prepare():
    # rule deletion: REVIEW.md spells `reviewers prepare` for every checkpoint; boundary names the checkpoint and its focus
    b = text("skills/boundary/SKILL.md")
    assert 'vela reviewers prepare --checkpoint "after the pages are written"' not in b
    assert 'the review checkpoint in `${CLAUDE_PLUGIN_ROOT}/references/REVIEW.md` "after the pages are written"' in b
    assert "run `vela reviewers prepare --checkpoint" in text("references/REVIEW.md")


def test_flow_check_line_carried_as_written():
    b = text("skills/boundary/SKILL.md")
    assert ("After writing a case table, run `vela check-slice --changed --for-lead`, say which slices it checked and why, "
            "and settle each finding with its owners") in b
    assert "run `vela check-slice FLO-nnn`" not in b
    assert b.index("**A case table for each contract") < b.index("vela check-slice --changed")
    assert '`vela conventions "Flow check"` for the sequence diagram' in b


def test_boundary_names_only_commands_that_exist():
    from vela import cli
    from test_skill_commands_exist import calls, is_a_mention, parse_error
    parser = cli.build_parser()
    found = list(calls(PLUGIN / "skills" / "boundary" / "SKILL.md")) + list(calls(PLUGIN / "skills" / "boundary" / "PAGES.md"))
    named = {" ".join(argv[:2]) for _, _, argv in found}
    for command in ("boundary cover", "add cut", "add app-stub", "add contract", "add unknown",
                    "close stage", "check-slice --changed"):
        assert command in named, command
    for line, call, argv in found:
        assert is_a_mention(parser, argv) or parse_error(parser, argv) is None, f"line {line}: {call}"


def test_boundary_reads_back_by_name_in_plain_labels():
    b = text("skills/boundary/SKILL.md")
    start = text("references/START.md")  # rule deletion: START's plain-names bullet covers a command's lines too
    assert "in your own sentences as well as in what a command prints" not in b
    assert "No ID, capture number, check code, gate name or rule name, in your sentences or a command's." in start
    assert "CONVERSATION-VOICE.md`, rule 7" not in b and "about four things to judge" not in b  # rule deletion: START and CONVERSATION-VOICE say it
    assert "A read-back by name:" in b and "Not this:" in b
    for label in ("**Doesn't do:**", "**Main parts:**", "**What it offers other apps:**",
                  "**What it needs from others:**", "**When something fails:**"):
        assert label in b, label
    assert "Is that the direction?" not in b and "a 409 that names the item" not in b
    assert "team senior" not in b and "a Grill" not in b
    assert 'Spell names in American English, capitalized ones too ("Route Optimizer")' in b


def test_boundary_keeps_the_first_thin_path_words_releases_reads():
    b = text("skills/boundary/SKILL.md")  # releasebrief finds the flow page by "first thin path"
    assert "We build this journey first, as the first thin path: ..." in b


def test_pages_leaves_to_add_what_add_writes():
    pages = text("skills/boundary/PAGES.md")
    assert "no reader has to guess the direction" not in pages and "padding" not in pages and "no \"no strategy is set yet\"" not in pages
    assert "fill the stub `vela add app-stub` wrote" in pages and "`vela add contract` writes the heading" in pages
    assert "`type: app-building-blocks`, `title`, `state: assumption`" not in pages  # the stub's frontmatter
    assert "one `### CON-nnn <name>` each, with every required bullet" not in pages
    assert "| Case | When | Status | Answer | Emits | Sets |" in pages  # the case table stays the session's


# --- plugin/skills/boundary/PAGES.md, MODES.md: the stub writes no row and no line. A skill that
# still said to replace or write an `unexamined` row (a Fossil Comment) had the model write empty rows the code
# deliberately left out; the judge scored them as padding (full3, four duplicates).
def test_no_skill_or_reference_tells_the_model_to_write_an_unexamined_row():
    stale = re.compile(r"unexamined[`\"']?\s+(?:concern\s+)?(?:cell\s+)?rows?\b", re.I)
    found = [f"{path.relative_to(PLUGIN)}: {m.group(0)}"
             for path in sorted([*(PLUGIN / "skills").rglob("*.md"), *(PLUGIN / "references").rglob("*.md")])
             for m in stale.finditer(path.read_text(encoding="utf-8"))]
    assert found == []


def test_pages_names_the_field_the_code_writes_and_no_line():
    pages = read("skills/boundary/PAGES.md")
    assert "`stub: boundary`" in pages and "Not looked at yet" not in pages
    assert "touched no concern page" in pages



def test_boundary_says_what_to_do_with_the_ready_to_decide_hand_off():
    from conftest import REPO
    text = (REPO / "plugin/skills/boundary/SKILL.md").read_text(encoding="utf-8")
    assert "run `vela decide` on it" not in text and "ready to decide, offer the lead a short grill" not in text  # MODES.md owns it


# --- Library Task 5: a spec, wiki or repo link is offered for the Library; the page's `links:` stay as they are.


def test_boundary_offers_links_to_the_library_and_keeps_links_front_matter():
    body = (PLUGIN / "skills/boundary/SKILL.md").read_text(encoding="utf-8")
    assert "vela library add" in body and "for the Library" in body
    assert "The page's `links:` stay as they are" in body


def test_boundary_drafts_the_paragraph_of_each_item_it_files_now():
    body = (REPO / "plugin" / "skills" / "boundary" / "SKILL.md").read_text(encoding="utf-8")
    assert "Draft" in body and "paragraph" in body and "START.md" in body
    assert "Draft the paragraph when the item is filed" in body or "Draft each filed item's paragraph now" in body


def test_boundary_stays_lean():
    """Sensor against regrowth: 2,552 words before the trim (now 2,387); PAGES.md 1,001 before (now about 930)."""
    assert len(text("skills/boundary/SKILL.md").split()) <= 1650  # 2,387 before the second trim; 1,598 after
    assert len(text("skills/boundary/PAGES.md").split()) <= 960
