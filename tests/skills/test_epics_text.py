"""What the epics skill says, pinned in one place (overhaul plan Task 3).

Every test that pins this text lives here, so the rewrite that changes it edits this file and no other skill's.
Each section is headed by the file it came from and that file's reason.
"""
import re
import shlex

from conftest import REPO, skill_text, assert_offered_then_asked
from vela import cli


def read(*parts):
    return REPO.joinpath(*parts).read_text(encoding="utf-8")


PLUGIN = REPO / "plugin"


def read_override(*parts):
    return (PLUGIN.joinpath(*parts)).read_text(encoding="utf-8")


def text_of(*parts):
    return (REPO.joinpath(*parts)).read_text(encoding="utf-8")


def words(count, start=0):
    """Distinct words, so a long paragraph is not also a repeated phrase."""
    return " ".join(f"item{n}" for n in range(start, start + count)) + ". "


LINT = REPO / "plugin" / "references" / "lint-words.txt"


def text(rel):
    return (PLUGIN / rel).read_text(encoding="utf-8")


def read_tracer_skills(rel):
    return (PLUGIN / rel).read_text(encoding="utf-8")


# --- From tests/test_answer.py: Answering a challenge: START opens an answer session on the challenge's own branch, a
# Grill (or the lead setting the item back) works there, and close pushes to that branch and comments on the open
# challenge PR instead of opening a new one.


def test_epics_accepts_reopened_to_decided_for_an_epic():
    # `vela decide` writes the reopened -> decided Changes row (decide_epic); the skill only says it decides the same way
    assert "A reopened epic decides the same way" in read("plugin", "skills", "epics", "SKILL.md")


# --- From tests/test_final_fixes.py: Fixes from the final whole-branch review: each test names the failure it keeps
# out.

# 1, M6, M9, M5, M4, 7, M2, M3, README: the words the skills and template must carry


def test_epics_stages_what_render_rewrote():
    epics = read("plugin/skills/epics/SKILL.md")
    # rule deletion: `vela close stage --checkpoint` stages by exact path and the hook denies hand staging
    assert "Stage every file `vela render` reported" not in epics
    assert "`vela render`" in epics and "vela close stage --checkpoint" in epics


def test_epics_writes_owning_team_now():
    # `vela add epic --team` writes the owning team with the skeleton; the skill no longer narrates it (rule deletion)
    epics = read("plugin/skills/epics/SKILL.md")
    assert "`vela add epic --title" in epics and "--team <@team>" in epics and "and the owning team" not in epics


# --- From tests/test_override.py: The user can override any rule, and an override is never invisible.

# ------------------------------------------------------------- skill text


def test_epics_keeps_the_override_bullets():
    epics = read_override("skills", "epics", "SKILL.md")
    # rule deletion: closegate blocks a close that removed an override since the branch point (E321, E322)
    assert "Keep every `**Override:**`, `**Decided by:**` and `**Confirmed by:**` bullet" not in epics


# --- From tests/test_reading_load.py: Pages a person can hold in mind: plain names in prose, IDs on a Trace line, and
# the five reading-load warnings.

# ---------------------------------------------------------------- the rule is written where sessions read it


def test_epics_says_split_a_wall():
    assert "split" in text_of("plugin", "skills", "epics", "SKILL.md")


# --- From tests/test_readload.py: The second five reading-load warnings (design session 16): a paragraph, a table
# cell, a stock phrase, a template opening and an abbreviation that costs the reader more than a careful writer would.

# ------------------------------------------------------------------------------------------------ the lint word list (16-D2)


def test_epics_never_names_a_listed_word():
    """Naming a word in a prompt raises its odds, so the list lives in the lint and the reviewer, and the drafter never
    sees it."""
    from vela import reading
    words = reading.lint_words(LINT.read_text(encoding="utf-8"))
    relative = "skills/epics/SKILL.md"
    text = (REPO / "plugin" / relative).read_text(encoding="utf-8")
    for word in words:
        assert not reading.lint_pattern(word).search(text.replace("lint-words.txt", "")), f"{relative} names '{word}'"


# --- From tests/test_reviewers.py: The focused reviewers and the review checkpoints in the session skills.

# ------------------------------------------------------------------ the checkpoints replace the sweeps


def test_epics_reads_the_question_gate():
    assert "`E805`" in text("skills/epics/SKILL.md")


def test_epics_offers_the_e805_override_with_its_exact_bullet():
    epics = text("skills/epics/SKILL.md")
    assert "- **Override:** E805 by @<handle>" not in epics  # rule deletion: decisions/override.py writes the line
    assert "turns E805 into W805" not in epics
    assert "`vela questions --open --digest`" in epics
    assert "kind `override`" in epics and "kind `defer`" in epics and "`vela apply <file> --for-lead`" in epics
    assert "Defer it to whoever can answer" in epics and "--gate epics --app <APP-id>" in epics
    assert "Never call the epics complete past an E805 the lead has neither taken nor overridden." in epics
    assert "the override is the only way to a clean `--gate epics`" in epics


# --- From tests/test_session_experience.py: What the skills make a lead go through (the constraints the skills put on a lead's session).

# --- S24: close starts on the lead's word, and still confirms before anything leaves the machine


def test_epics_stays_the_leads_to_start():
    assert_offered_then_asked("epics")


def test_epics_hands_the_lead_to_start_not_to_a_slash_command_they_must_type():
    body = text("skills/epics/SKILL.md")
    assert "Closing a session" in body, "epics must say how its session ends"
    assert "Do not run close yourself" not in body
    assert not re.search(r'[Tt]ell the user: "Run `/vela:close`', body)


# --- S26 and S43: the review digest is small, plain, once


def test_epics_leaves_the_digest_to_review():
    assert "high and blocking lines in full" not in text("skills/epics/SKILL.md")


# --- S29 and S30: handoff and epics no longer wait on each other


def test_epics_use_the_app_scope():
    epics = text("skills/epics/SKILL.md")
    assert "--gate epics --app <APP-id>" in epics and "Report those separately" not in epics


# --- S36 to S47


def test_epics_read_the_releases():
    assert "04b-releases.md" in text("skills/epics/SKILL.md")


# --- From tests/test_skills.py: The plugin's skills: frontmatter, size, the files they point at, the plugin
# validator, and the rules each skill exists to hold.

# epics (V1-17): the check finds the frontier, only the lead's confirmation decides, the gate closes.


def test_epics_skill_reads_the_gaps_and_runs_the_gate():
    epics = text("skills/epics/SKILL.md")
    assert "`vela epics frontier --team <@team> --for-lead`" in epics
    assert "2 or 3 ways to cut" in epics and "exactly one owning team" in epics
    assert "4 to 7 criteria" in epics and "## Done when" in epics
    assert "`[testing]`" in epics
    assert "offer `/vela:requirements` on that `CAP-nnn`, then `/vela:allocate`" in epics and "Never write the requirement into the epic." in epics
    assert "Set an epic to `decided` only when the solution lead confirms" in epics
    assert "in groups of about five" in epics
    assert "while a criterion lacks a yes it files nothing" not in epics and "Exit 3 means already decided" not in epics  # decide_epic says it
    assert "every criterion has a yes, its own or its group's" in epics
    assert "It does not mean they are decided" in epics and "check --gate epics --app <APP-id>" in epics
    assert "list each epic still at `draft`" in epics
    assert "`vela epics lint <EPC-id> --for-lead`" in epics and "rewrite the criterion at the boundary" in epics
    assert "writes the number and the Trace line" not in epics and "More than 7 means the epic should be split" not in epics
    assert "A cut giving an epic more than about seven criteria is a cut to split" in epics  # section 3 owns the split
    assert "`modes: [epics, shape, grill]` and the title `Epics: <team>`" in epics
    assert "check --gate epics" in epics
    assert "Never say an app's epics are complete while one remains." in epics


def test_epics_skill_frontmatter_instruction_names_the_epics_mode():
    epics = text("skills/epics/SKILL.md")
    assert "`modes: [epics, shape, grill]`" in epics and "`modes: [shape, grill]`" not in epics


# tech-design-grill vault mode (V1-18): read the slice, link back by ID and commit, never copy vault text.


def test_epics_skill_disposes_of_e805_by_answer_defer_or_override_and_never_leaves_it_unplaced():
    """S11: the heron run offered "leave the gate failing", the lead took it, and the question had no owner."""
    epics = text("skills/epics/SKILL.md")
    assert "Defer it to whoever can answer" in epics and "kind `defer`" in epics  # defer numbers the unknown
    assert "- Leave the gate failing." not in epics
    assert "is not a route" in epics and "Offer the three routes once" in epics


# --- From tests/test_tracer_skills.py: The lead-side tracer guidance (S52, step 2): present in each skill, never a
# gate, the example in the plan's format, and no codes read to the lead.


def test_epics_carries_its_tracer_guidance():
    assert "first epic is on the first thin path (the tracer" in read_tracer_skills("skills/epics/SKILL.md")


def test_epics_explains_the_tracer_as_the_first_thin_path():
    # The amendment of 2026-10-13: a slice is the unit of done and the tracer is slice one, so a sentence may say both.
    text = skill_text("epics")  # the tracer is defined once, in CONVENTIONS; each skill names it the first thin path
    assert "first thin path" in text and ("Releases" in text or "Slices" in text)


def test_epics_leaves_the_tracer_definition_to_conventions():
    assert "thin path through every app" not in skill_text("epics")  # said once, in CONVENTIONS


def test_epics_never_makes_the_tracer_a_gate():
    for sentence in re.split(r"(?<=[.?!])\s+", read_tracer_skills("skills/epics/SKILL.md")):
        if re.search(r"tracer", sentence, re.I):
            assert not re.search(r"\b(stop|stops|refuse|refuses|block|blocks|gate)\b", sentence, re.I), sentence


# --- From tests/test_v3_final_fixes.py: The v3 final fix wave.

# ------------------------------------------------------------------ asked copies hold the gates, so the views list them


def test_epics_says_e805_holds_asked_questions_too():
    epics = text("skills/epics/SKILL.md")
    assert "nobody has disposed, or that was asked and still waits for its answer" in epics


# --- Task 22d (overhaul plan 2.3): the mechanics moved into commands; the skill names them and keeps the judgment.

EPICS = PLUGIN / "skills" / "epics" / "SKILL.md"


def test_epics_leaves_ac_numbering_to_add_epic():
    """Rule deletion: AC numbers are written by `vela add epic`, so the skill no longer tells the model to pick one."""
    epics = EPICS.read_text(encoding="utf-8")
    assert "next `AC` number" not in epics
    assert "vela add epic --id <EPC-id> --criterion" in epics


def test_epics_leaves_the_boundary_test_to_lint():
    """Rule deletion: the three-step boundary test is `vela epics lint`; the skill rewrites at the boundary."""
    epics = EPICS.read_text(encoding="utf-8")
    assert "Before you propose a criterion, run the boundary test" not in epics
    assert not re.search(r"^1\. Its `- Trace:` line", epics, re.M) and "Redis or Kafka" not in epics
    assert "`vela epics lint --fix-shape <EPC-id>`" in epics


def test_epics_offers_the_e805_routes_once_without_a_rerun_warning():
    """Rule deletion: the E805 loop's warning goes; a deferral is said once and the session moves on."""
    epics = EPICS.read_text(encoding="utf-8")
    assert "do not re-run it" not in epics
    assert "After a deferral the gate lists the question until close: say so once" in epics


def test_epics_decides_through_the_command_with_a_group_per_read_back():
    epics = EPICS.read_text(encoding="utf-8")
    assert "`vela decide <EPC-id> --group AC1-AC5 ^cA ^cB --readback ^cN --yes ^cM --for-lead`" in epics
    assert "`--override GATE-3 --reason-from ^cR`" in epics
    assert "commit with the message `grill: EPC-nnn decided`" not in epics  # decide commits


def test_epics_reads_back_by_name_with_a_worked_example():
    epics = EPICS.read_text(encoding="utf-8")
    assert "**Say names, not IDs,**" in epics and "in your own sentences as well as relayed ones" in epics
    example = epics.split("A group read back, to copy:", 1)[1].split("\n\n", 2)[1]
    assert example.startswith("> ") and not re.search(r"\b(?:EPC|CON|FLO|CAP|UNK|APP)-|\bAC\d", example)


def test_epics_description_is_the_plans():
    head = EPICS.read_text(encoding="utf-8").split("---", 2)[1]
    assert "Cut one team's handed-off work into epics with acceptance criteria, then grill each with the solution lead." in head


def test_epics_says_the_lead_facing_words():
    epics = EPICS.read_text(encoding="utf-8")
    assert "the app's handoff list" in epics and "not decided yet, until a grill decides it" in epics
    assert "Decide it anyway (I'll note that the open question was skipped)" in epics
    assert "Grill" not in epics.replace("Grill rows", "").replace("## 6. Grill", "") and "the senior" not in epics  # grill lower case
    assert "Nobody has answered who carries the liability for points balances." in epics


def test_epics_names_only_commands_that_exist():
    parser = cli.build_parser()
    epics = EPICS.read_text(encoding="utf-8")
    calls = re.findall(r"`vela ((?:epics|add|decide|check|apply|questions|render|conventions|terms)\b[^`]*)`", epics)
    assert len(calls) >= 10, calls
    for call in calls:
        argv = shlex.split(re.sub(r"\^c\w+", "^c01", re.sub(r"<[^>]*>", "X", call)))
        _, extras = parser.parse_known_args(argv)
        assert not extras, (call, extras)


# --- Library Task 5: a tracker link is offered for the Library; `links:` stays as written.


def test_epics_offers_the_tracker_link_to_the_library():
    body = (PLUGIN / "skills/epics/SKILL.md").read_text(encoding="utf-8")
    assert "vela library add" in body and "for the Library" in body and "`links:` stays as written" in body


def test_epics_drafts_the_paragraph_of_each_item_it_files_now():
    body = (REPO / "plugin" / "skills" / "epics" / "SKILL.md").read_text(encoding="utf-8")
    assert "Draft" in body and "paragraph" in body and "START.md" in body
    assert "Draft the paragraph when the item is filed" in body or "Draft each filed item's paragraph now" in body


# ---- trim, stage 2 and 3 (lane D): what a command enforces or prints is not said here again

def test_epics_leaves_what_the_commands_enforce_to_them():
    epics = EPICS.read_text(encoding="utf-8")
    assert "## Never" not in epics
    assert "Never name a component, table or technology in a criterion" not in epics  # epicslint holds it
    assert "Never edit a generated block" not in epics  # the hook and E401 hold it
    assert "It numbers the epic and writes the frontmatter" not in epics
    assert "needs one marked criterion, or a waiver in the cell" not in epics  # W503 / E503 under --gate epics
    assert "Contents: 1 start" not in epics


def test_epics_stays_under_its_word_cap():
    assert len(EPICS.read_text(encoding="utf-8").split()) <= 1860  # 2,021 before the trim; 1,806 after
