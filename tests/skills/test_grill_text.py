"""What the grill skill says, pinned in one place (overhaul plan Task 3).

Every test that pins this text lives here, so the rewrite that changes it edits this file and no other skill's.
Each section is headed by the file it came from and that file's reason.
"""
import re

from conftest import REPO, skill_text


def read(*parts):
    return REPO.joinpath(*parts).read_text(encoding="utf-8")


def section(text, start, end):
    return text.split(start, 1)[1].split(end, 1)[0]


PLUGIN = REPO / "plugin"


def read_override(*parts):
    return (PLUGIN.joinpath(*parts)).read_text(encoding="utf-8")


def text(rel):
    return (PLUGIN / rel).read_text(encoding="utf-8")


def section_session_experience(body, heading):
    """The text under a `## heading` up to the next `## `."""
    return body.split(f"## {heading}\n", 1)[1].split("\n## ", 1)[0]


def read_tracer_skills(rel):
    return (PLUGIN / rel).read_text(encoding="utf-8")


# --- From tests/test_answer.py: Answering a challenge: START opens an answer session on the challenge's own branch, a
# Grill (or the lead setting the item back) works there, and close pushes to that branch and comments on the open
# challenge PR instead of opening a new one.


def test_grill_takes_the_answer_a_challenge_path():
    grill = read("plugin", "skills", "grill", "SKILL.md")
    assert "take its \"Answer a challenge\" path" in section(grill, "## 1.", "## 2.")


def test_grill_accepts_reopened_to_decided_for_an_epic():
    assert "| EPC-nnn | reopened | decided |" in read("plugin", "skills", "grill", "SKILL.md")
    assert "An epic is at `draft` or `reopened`" in read("plugin", "skills", "grill", "SKILL.md")


# --- From tests/test_cases.py: A contract's case table: the parser reads it, `vela check` warns when it is missing or
# cannot be trusted.


def test_grill_decides_nothing_without_its_case_table():
    from conftest import skill_text
    assert "not decided without its case table" in skill_text("grill")


# --- From tests/test_final_fixes.py: Fixes from the final whole-branch review: each test names the failure it keeps
# out.

# 6. functional requirements are items check validates like contracts


def test_conventions_and_grill_document_the_fr_format():
    conventions = (REPO / "template" / "CONVENTIONS.md").read_text(encoding="utf-8")
    assert "### CAP-nnn.FRn" in conventions and "CAP-001.FR1" in conventions
    grill = (REPO / "plugin" / "skills" / "grill" / "SKILL.md").read_text(encoding="utf-8")
    assert "### CAP-nnn.FRn" in grill and "`**State:**` bullet moves to `decided`" in grill


# 1, M6, M9, M5, M4, 7, M2, M3, README: the words the skills and template must carry


def test_grill_agenda_status_names_the_failed_gate():
    assert "off-agenda: GATE-n" in read("plugin/skills/grill/SKILL.md")


# --- From tests/test_final_wave.py: The last fix wave: the root README describes v2, and close, START, CONVENTIONS
# and the plugin manifest say what the code and the workflow actually do.

# M6: the plugin manifest


def test_grill_sets_a_challenged_item_back_by_its_kind():
    grill = read("plugin", "skills", "grill", "SKILL.md")
    assert "to `reopened` for an epic or to `assumption` for anything else" in grill
    assert "reopen it first" not in grill


# --- From tests/test_handoff_warnings.py: At handoff the lead, and through the manifest the senior, hear what is not
# firm: drafts, missing case tables, providers nobody has designed, and a manifest pinned to a commit that is gone.


def test_the_grill_read_back_tells_the_lead_what_is_not_firm():
    assert "draft or assumption" in skill_text("grill") and "no case table" in skill_text("grill")


# --- From tests/test_ladder.py: vela ladder: the stage an app's pages reach, against its hand-typed stage.


def test_grill_hands_an_app_over():
    grill = (REPO / "plugin" / "skills" / "grill" / "SKILL.md").read_text(encoding="utf-8")
    handoff = (REPO / "plugin" / "skills" / "grill" / "HANDOFF.md").read_text(encoding="utf-8")  # read only when an app is handed over
    assert "## Handing an app over" in grill and "skills/grill/HANDOFF.md" in grill
    assert 'handed_off: "<senior>, <today>, PR pending"' in handoff
    assert "Say once what is not met, as one list" in handoff and "Do not ask about each line." in handoff


# --- From tests/test_override.py: The user can override any rule, and an override is never invisible.

# ------------------------------------------------------------- skill text


def test_grill_offers_the_override_and_still_runs_the_rest_of_the_grill():
    grill = read_override("skills", "grill", "SKILL.md")
    assert "If the lead wants to decide it anyway, do it and record the override" in grill
    assert "the rest of the Grill runs as normal" in grill and "read-back" in grill
    assert "- **Decided by:** @<user's handle>, on behalf of @<owner>" in grill
    assert "This is how GATE-5 passes with the owner away." in grill
    assert "W316 instead of E316" in grill


# --- From tests/test_reader_skills.py: Reader mode in the skill text: no git in a read copy, owner-only skills
# refuse, a reader's decisions are pending, and every skill finds the installed vela by the one order START.md states.


def test_grill_refuses_in_a_reader_copy_naming_the_owner():
    assert "owner's call" in text("skills/grill/SKILL.md") and "published.json" in text("skills/grill/SKILL.md")


def test_grill_marks_a_readers_decisions_pending():
    assert "- **Pending approval:** @<handle>, <today>" in text("skills/grill/SKILL.md")


# --- From tests/test_reviewers.py: The focused reviewers and the review checkpoints in the session skills.

# ------------------------------------------------------------------ the checkpoints replace the sweeps


def test_grill_reads_the_blocking_questions_and_runs_the_checkpoint_on_the_agenda():
    grill = text("skills/grill/SKILL.md")
    assert "vela check --gate grill --item <ID>" in grill and "W807" in grill
    assert "references/REVIEW.md" in grill and '"on the agenda"' in grill
    assert grill.index("--gate grill") < grill.index("write the agenda into the session record")


def test_grill_records_a_decision_over_an_open_blocking_question():
    grill = text("skills/grill/SKILL.md")
    assert "python3 ${CLAUDE_PLUGIN_ROOT}/scripts/vela check --gate grill --item <ID>" in grill
    assert "Repeat `--item`" in grill and "exits 2" in grill and "can be stale" in grill
    assert "REVIEW section 5" in grill and "at most three questions" in grill
    assert "decided with <copy IDs> open (W807)" in grill and "`## Changes` row" in grill


# --- From tests/test_session_experience.py: What the skills make a lead go through (docs/research/2026-10-12-session-
# experience-review.md and the friction pass).

# --- S24: close starts on the lead's word, and still confirms before anything leaves the machine


def test_grill_stays_the_leads_to_start():
    assert "disable-model-invocation: true" in text("skills/grill/SKILL.md"), "grill must stay the lead's to start"


def test_grill_hands_the_lead_to_start_not_to_a_slash_command_they_must_type():
    body = text("skills/grill/SKILL.md")
    assert "Closing a session" in body, "grill must say how its session ends"
    assert "Do not run close yourself" not in body
    assert not re.search(r'[Tt]ell the user: "Run `/vela:close`', body)


# --- S26 and S43: the review digest is small, plain, once


def test_grill_leaves_the_digest_to_review():
    assert "high and blocking lines in full" not in text("skills/grill/SKILL.md")


# --- S27: no rule codes, raw IDs or gate names in what the lead reads


def test_the_grill_gate_prose_carries_no_code():
    grill = section_session_experience(text("skills/grill/SKILL.md"), "2. The gate, per item")
    assert "Never show the lead a gate table or a gate name." in grill
    assert "Show the result as a table" not in grill


# --- S29 and S30: handoff and epics no longer wait on each other


def test_grill_handoff_does_not_require_the_epics_gate():
    grill = section_session_experience(text("skills/grill/SKILL.md"), "3. The questions") + text("skills/grill/SKILL.md").split("## Handing an app over")[1].split("## 4.")[0] + text("skills/grill/HANDOFF.md")
    assert "check --gate epics" not in grill


# --- S36 to S47


def test_grill_marks_its_own_captures():
    assert "→ keep: [[" in text("skills/grill/SKILL.md"), "grill no longer marks its own captures"


# --- From tests/test_skill_commands.py: Skill text that names the v2 commands: vela next at start, the Options
# considered bullet Shape leaves and next reads, and the handoff manifest close writes.


def test_grill_reads_options_considered_as_one_bullet():
    assert "written down in its `**Options considered:**` bullet" in text("skills/grill/SKILL.md")


# --- From tests/test_skills.py: The plugin's skills: frontmatter, size, the files they point at, the plugin
# validator, and the rules each skill exists to hold.

# grill (V1-10)


def test_grill_holds_the_gate_and_writes_each_decision_at_once():
    grill = text("skills/grill/SKILL.md")
    for gate in ("GATE-1", "GATE-2", "GATE-3", "GATE-4", "GATE-5"):
        assert f"| {gate} |" in grill
    assert "If no item passes and the user overrides none, do not start the grill: make no change to any page" in grill
    assert "- **Decision:** [[<session id>]]" in grill
    assert "- **Dissent:** <name>, <date>: <reason>" in grill
    assert "claude, from <name>" in grill
    assert "Keep your recommendation when the user pushes back without a reason." in grill
    assert "Never answer your own question." in grill
    assert "Never batch decisions to the end." in grill


def test_grill_defines_acceptance_agenda_and_the_mark_exception():
    grill = text("skills/grill/SKILL.md")
    assert 'Silence, "ok", "next", "sure" with nothing else, or a change of subject do not count as acceptance.' in grill
    assert "read the final wording back and get a yes" in grill
    assert "says yes in person" in grill and "explicit yes" in grill
    assert "record where the provider stands as well as each consumer" in grill
    assert "(decided)" in grill and "the one exception to leaving marks off until close" in grill
    assert "## Agenda" in grill and "GATE-3 confirmed yes|no" in grill
    assert "blocks every item on that page" in grill
    assert "re-run GATE-4 for every other agenda item" in grill and "E316" in grill
    assert "Stage the session record and the changed pages, by exact path." in grill
    assert "already `decided`, say so" in grill and "change of mind in the Changes table" in grill


# tech-design-grill vault mode (V1-18): read the slice, link back by ID and commit, never copy vault text.


def test_grill_never_drafts_an_ask():
    assert "Never draft an ask, an email or a chase for the user to send." in text("skills/grill/SKILL.md")


# --- From tests/test_tracer_skills.py: The lead-side tracer guidance (S52, step 2): present in each skill, never a
# gate, the example in the plan's format, and no codes read to the lead.


def test_grill_carries_its_tracer_guidance():
    assert "this app's piece of it" in skill_text("grill")


def test_grill_explains_the_tracer_as_the_first_thin_path():
    # The amendment of 2026-10-13: a slice is the unit of done and the tracer is slice one, so a sentence may say both.
    text = skill_text("grill")  # the tracer is defined once, in CONVENTIONS; each skill names it the first thin path
    assert "first thin path" in text and ("Releases" in text or "Slices" in text)


def test_grill_leaves_the_tracer_definition_to_conventions():
    assert "thin path through every app" not in skill_text("grill")  # said once, in CONVENTIONS


def test_grill_never_makes_the_tracer_a_gate():
    for sentence in re.split(r"(?<=[.?!])\s+", read_tracer_skills("skills/grill/SKILL.md")):
        if re.search(r"tracer", sentence, re.I):
            assert not re.search(r"\b(stop|stops|refuse|refuses|block|blocks|gate)\b", sentence, re.I), sentence


# --- From tests/test_v3_final_fixes.py: The v3 final fix wave.

# ------------------------------------------------------------------ W809 and W804 reach the lead; W807 is described as it is


def test_grill_says_w807_prints_only_under_its_gate_and_the_capture_is_the_record():
    grill = text("skills/grill/SKILL.md")
    assert "The W807 stays in the check output as the record." not in grill
    assert "W807 prints only under `--gate grill --item`" in grill and "the capture is the record" in grill


# --- From tests/test_why.py: A decided item keeps the lead's own reasons: the Grill asks for them, and the check
# names the item that has none.


def test_the_grill_asks_for_the_why_in_the_leads_words_and_offers_a_record_for_big_ones():
    grill = skill_text("grill")
    assert "Why this one, in your words?" in grill and "word for word as `- **Why:** <the lead's words>`" in grill
    assert "decision record" in grill and "`state: proposed`" in grill
