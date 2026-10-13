"""What the skills make a lead go through (docs/research/2026-10-12-session-experience-review.md and the friction pass).

These test the constraint, not the wording: who may start a close and what stops a push, how many questions a digest puts
to the lead, what the lead's words may contain, what the tool files without asking. Each one fails on the skill text the
review quoted."""
import re

import pytest

from conftest import REPO

PLUGIN = REPO / "plugin"
MODE_SKILLS = ("dump", "discover", "shape", "boundary", "requirements", "allocate", "releases", "epics", "grill")


def text(rel):
    return (PLUGIN / rel).read_text(encoding="utf-8")


def section(body, heading):
    """The text under a `## heading` up to the next `## `."""
    return body.split(f"## {heading}\n", 1)[1].split("\n## ", 1)[0]


# --- S24: close starts on the lead's word, and still confirms before anything leaves the machine

def test_close_can_be_started_by_the_model_but_the_modes_cannot():
    close = text("skills/close/SKILL.md").split("---\n", 2)[1]
    assert "disable-model-invocation" not in close
    for mode in MODE_SKILLS:
        assert "disable-model-invocation: true" in text(f"skills/{mode}/SKILL.md"), f"{mode} must stay the lead's to start"


def test_close_asks_one_confirmation_before_it_pushes_and_never_starts_on_its_own():
    starting = section(text("skills/close/SKILL.md"), "Starting a close")
    assert "never by yours" in starting
    assert re.search(r"Before section 7 pushes.*wait for a yes", starting, re.S)
    assert "A bare \"close\" is consent to file, not to send." in starting
    start = section(text("references/START.md"), "Closing a session")
    assert "Never start close" in start and "Before it does, close says what will be sent and waits for a yes" in start


@pytest.mark.parametrize("mode", MODE_SKILLS)
def test_a_mode_hands_the_lead_to_start_not_to_a_slash_command_they_must_type(mode):
    body = text(f"skills/{mode}/SKILL.md")
    assert "Closing a session" in body, f"{mode} must say how its session ends"
    assert "Do not run close yourself" not in body
    assert not re.search(r'[Tt]ell the user: "Run `/planner:close`', body)


# --- S26 and S43: the review digest is small, plain, once

def test_the_digest_puts_at_most_three_plain_questions_once_per_session():
    review = section(text("references/REVIEW.md"), "5. The digest")
    assert "At most three questions" in review and "Once per session" in review
    assert "first five" not in review and "next five" not in review
    assert "Never twice, never ruled out" in review
    for body in (text(f"skills/{m}/SKILL.md") for m in MODE_SKILLS):
        assert "high and blocking lines in full" not in body
    assert "no cap" not in text("references/MODES.md").lower()


# --- S27: no rule codes, raw IDs or gate names in what the lead reads

LEAD_CODE = re.compile(r"\b[EW]\d{3}\b|GATE-\d|\^c\d|\bQ-[A-Z]{3}-\d{2}|\bF\d\.\d+\b")
SPOKEN = re.compile(r'(?:\b[Ss]ay|[Tt]ell (?:the )?(?:user|lead)|\bask)\b[^"\n]{0,80}?: "([^"\n]{10,})"')


def spoken_lines():
    for path in sorted(PLUGIN.glob("skills/*/SKILL.md")) + sorted(PLUGIN.glob("references/*.md")):
        for line in SPOKEN.findall(path.read_text(encoding="utf-8")):
            yield path.relative_to(PLUGIN), line


def test_no_line_a_skill_tells_the_model_to_say_carries_a_code():
    bad = [(str(path), line) for path, line in spoken_lines() if LEAD_CODE.search(line)]
    assert not bad, bad


def test_the_digest_example_and_the_grill_gate_prose_carry_no_code():
    example = text("references/REVIEW.md").split("For example, instead of", 1)[1].split("A turn of 50", 1)[0]
    spoken = "\n".join(l for l in example.splitlines() if l.startswith(">"))
    assert spoken and not LEAD_CODE.search(spoken)
    grill = section(text("skills/grill/SKILL.md"), "2. The gate, per item")
    assert "Never show the lead a gate table or a gate name." in grill
    assert "Show the result as a table" not in grill


def test_start_forbids_codes_in_conversation_and_names_what_counts():
    plain = section(text("references/START.md"), "Plain names and a page a person can hold")
    for kind in ("check code", "gate name", "capture number", "copy ID", "finding ID"):
        assert kind in plain, kind


# --- S25: record by default, ask only the few unsettled items, never the tool's own filing

def test_close_files_by_default_and_asks_at_most_three_unsettled_items():
    sec2 = section(text("skills/close/SKILL.md"), "2. Mark every capture")
    assert "without asking" in sec2 and "at most three items" in sec2
    assert "numbered list" not in sec2.split("Defaults:")[0].replace("never show it to the lead as a numbered list", "")
    assert "Never ask the lead for bookkeeping" in sec2


def test_close_never_asks_for_minutes_handles_or_the_late_gap():
    close = text("skills/close/SKILL.md")
    assert "Did any other gap turn up late" not in close
    assert "Ask the user how long" not in close and "Never ask." in close
    assert "Never ask the lead whether a gap turned up late" in close


def test_the_handle_is_asked_once_and_kept():
    start = text("references/START.md")
    assert ".planner/handle" in start and "never again in any skill" in start
    assert ".planner/*" in (REPO / "template" / ".gitignore").read_text(encoding="utf-8")  # so the file is never committed


# --- S29 and S30: handoff and epics no longer wait on each other

def test_handoff_does_not_require_the_epics_gate_and_epics_use_the_app_scope():
    grill = section(text("skills/grill/SKILL.md"), "3. The questions") + text("skills/grill/SKILL.md").split("## Handing an app over")[1].split("## 4.")[0]
    assert "check --gate epics" not in grill
    conventions = (REPO / "template" / "CONVENTIONS.md").read_text(encoding="utf-8")
    handoff = conventions.split("\n## Handoff\n", 1)[1].split("\n## ", 1)[0]
    assert "check --gate epics" not in handoff.split("Epics come after handoff")[0]
    assert "Epics come after handoff" in handoff and "--gate epics --app <APP-id>" in handoff
    epics = text("skills/epics/SKILL.md")
    assert "--gate epics --app <APP-id>" in epics and "Report those separately" not in epics


# --- S36 to S47

def test_a_challenge_promises_a_red_check_only_for_a_decided_item():
    challenge = text("skills/challenge/SKILL.md")
    assert "Never promise a red check for an item that is not `decided`." in challenge


def test_ask_cannot_cat_any_file():
    meta = text("skills/ask/SKILL.md").split("---\n", 2)[1]
    assert "Bash(cat" not in meta


def test_import_never_writes_decided():
    imported = text("skills/import/SKILL.md")
    assert "never `decided`" in imported and "or `decided` at all" in imported


def test_a_dropped_requirement_is_never_struck_through():
    requirements = text("skills/requirements/SKILL.md")
    assert "stays, struck through" not in requirements and "never strike its heading through" in requirements


def test_boundary_tests_cuts_against_requirements_and_epics_read_the_releases():
    assert "functional requirements" in text("skills/boundary/SKILL.md").split("## 2.")[0]
    assert "Test each cut against the functional requirements" in text("skills/boundary/SKILL.md")
    assert "04b-releases.md" in text("skills/epics/SKILL.md")


def test_start_stages_the_explorer_pins_and_leaves_the_rest():
    start = text("references/START.md")
    assert "stage it by exact path when it changed" in start
    assert "(`findings/`, `owed/`, `pr-body*.md`, `handle`)" in start


def test_a_review_checkpoint_has_a_reader_copy_path():
    review = text("references/REVIEW.md")
    assert "## Reader copy" in review and "shasum" in review


def test_session_modes_are_listed_the_same_everywhere():
    from planner import schema
    conventions = (REPO / "template" / "CONVENTIONS.md").read_text(encoding="utf-8")
    listed = re.search(r"- `modes` on a session: a list of ([^.]+)\.", conventions).group(1)
    assert set(re.findall(r"`(\w+)`", listed)) == set(schema.SESSION_MODES)
    modes = text("references/MODES.md")
    rows = re.findall(r"^\| ([A-Za-z &]+) \(`(\w+)`\) \|", modes, re.M)
    names = {name for name, _ in rows}
    start = text("references/START.md")
    shown = re.search(r"display name in `MODES.md`: ([^.]+)\.", start).group(1)
    start_names = set(re.split(r", | or ", shown))
    assert names - {"Answer", "Challenge"} <= start_names and "Releases" in start_names
    assert {code for _, code in rows} == set(schema.SESSION_MODES)


def test_every_mode_that_marks_at_once_is_named_in_start_and_close():
    start, close = text("references/START.md"), text("skills/close/SKILL.md")
    names = {"grill": "Grill", "discover": "Discover", "boundary": "Boundary", "requirements": "Requirements",
             "allocate": "Allocate", "releases": "Releases"}
    marks = start.split("Leave the mark off until close")[1].split("\n")[0]
    for mode, name in names.items():
        assert "→ keep: [[" in text(f"skills/{mode}/SKILL.md"), f"{mode} no longer marks its own captures"
        assert name in marks, f"START does not name {name} among the modes that mark at once"
    assert "Allocate or Releases session already marked `(assumption)`" in close

