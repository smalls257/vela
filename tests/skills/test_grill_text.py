"""What the grill skill says, pinned in one place (overhaul plan Task 3, rewritten by Task 22c).

Every test that pins this text lives here, so the rewrite that changes it edits this file and no other skill's.
Each section is headed by the file it came from and that file's reason. Task 22c moved the gate table, the nine
section-4 writes and the agenda grammar into `vela check --gate grill`, `vela decide` and the `agenda` kind; the
rule-deletion asserts below keep each moved rule from coming back as a second copy in the skill (Shield).
"""
import re

from conftest import REPO, run, skill_text, assert_offered_then_asked


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
# grill (or the lead setting the item back) works there, and close pushes to that branch and comments on the open
# challenge PR instead of opening a new one.


def test_grill_takes_the_answer_a_challenge_path():
    grill = read("plugin", "skills", "grill", "SKILL.md")
    start = section(grill, "## 2.", "## 3.")
    assert "take its \"Answer a challenge\" path" in start
    assert "`vela decide --reopen <ID> --why ^cN`" in start and "`resolve` kind" in start


def test_grill_reopens_through_decide_not_by_hand():
    # `decide --reopen` sets an epic back to reopened and anything else to assumption, and writes the Changes row.
    grill = read("plugin", "skills", "grill", "SKILL.md")
    assert "| EPC-nnn | reopened | decided |" not in grill
    assert "to `reopened` for an epic or to `assumption` for anything else" not in grill
    assert "an epic" in section(grill, "## 4.", "## 5.")


# --- From tests/test_cases.py: A contract's case table: the gate reports it missing, the grill offers to write it.


def test_grill_offers_to_write_a_missing_case_table():
    grill = skill_text("grill")
    assert "For a missing case table" in grill and "one case at a time with your recommendation" in grill


# --- From tests/test_final_fixes.py: functional requirements are items check validates like contracts


def test_conventions_document_the_fr_format_and_grill_decides_it_with_decide():
    conventions = (REPO / "plugin" / "template" / "CONVENTIONS.md").read_text(encoding="utf-8")
    assert "### CAP-nnn.FRn" in conventions and "CAP-001.FR1" in conventions
    grill = (REPO / "plugin" / "skills" / "grill" / "SKILL.md").read_text(encoding="utf-8")
    assert "a requirement, a release, a slice, an epic, an app's share" in grill
    assert "`**State:**` bullet moves to `decided`" not in grill  # decide_fr writes it


# --- Task 22c: the agenda grammar is the `agenda` kind's


def test_grill_files_the_agenda_through_its_kind():
    grill = read("plugin/skills/grill/SKILL.md")
    assert "`agenda` kind" in grill
    assert "START's resume reads it" not in grill  # rule deletion: decisions/agenda.py keeps the agenda current
    for gone in ("off-agenda: GATE-n", "GATE-3 confirmed yes|no", "write the agenda into the session record",
                 "- CON-003: GATE-3 confirmed yes, status open, override: GATE-5"):
        assert gone not in grill, gone


def test_grill_says_how_a_decision_file_is_filed():
    grill = read("plugin/skills/grill/SKILL.md")
    assert "`vela apply`" in grill and "`--schema <kind>`" in grill
    assert "`vela apply <file> --for-lead`" not in grill  # rule deletion: START's relaying rule covers --for-lead
    assert '"version": 1' not in grill  # the decision file's shape is `vela apply`'s, not the skill's


# --- From tests/test_handoff_warnings.py: At handoff the lead, and through the manifest the team lead, hear what is not
# settled: drafts, missing case tables, providers nobody has designed.


def test_the_grill_read_back_tells_the_lead_what_is_not_settled():
    import inspect
    from vela import handoffpreview
    handoff = text("skills/grill/HANDOFF.md")
    # the command prints the list (a draft, a missing case table, an undesigned provider); the skill only says to say it
    assert "still a draft or not decided yet" in inspect.getsource(handoffpreview) and "no case" in inspect.getsource(handoffpreview)
    assert "still a draft or not decided yet" not in handoff and "no case table" not in handoff
    assert "epics and other apps' gaps are never on it" not in handoff


# --- From tests/test_ladder.py: the handoff, read back from `vela handoff preview`.


def test_grill_hands_an_app_over():
    grill = (REPO / "plugin" / "skills" / "grill" / "SKILL.md").read_text(encoding="utf-8")
    handoff = (REPO / "plugin" / "skills" / "grill" / "HANDOFF.md").read_text(encoding="utf-8")
    assert "## Handing an app over" in grill and "skills/grill/HANDOFF.md" in grill
    assert 'handed_off: "<team lead\'s handle>, <today>"` and `handed_off_pr: pending' in handoff  # no handoff kind yet (15b)
    assert "Say once what is not met, as one list" in handoff and "Do not ask about each line." in handoff
    assert "`vela handoff preview <APP-id> --for-lead`" in handoff


def test_handoff_leaves_the_checklist_to_handoff_preview():
    handoff = text("skills/grill/HANDOFF.md")
    assert 'vela conventions "Handoff"' not in handoff  # no such section; the preview prints the list
    assert "take from them what the senior would accept without a yes" not in handoff
    assert "senior" not in handoff.lower()


def test_handoff_reads_back_by_name():
    handoff = text("skills/grill/HANDOFF.md")
    assert "Read back, by name," in handoff and "this app's piece of it" in handoff


# --- From tests/test_override.py: The user can override any rule, and an override is never invisible.


def test_grill_offers_the_override_and_still_runs_the_rest_of_the_grill():
    grill = read_override("skills", "grill", "SKILL.md")
    assert "Decide it anyway (I'll note that the open question was skipped)" in grill
    assert "ask the reason once" in grill and "Never refuse, and never ask twice." in grill
    assert "The rest of the grill runs as normal" in grill and "read-back" in grill
    assert "--override <rule> --reason-from ^cR --until <date>" not in grill and "--on-behalf @<owner>" not in grill
    assert "the override is filed with the decision in section 4" not in grill
    from vela import cli
    helped = cli.build_parser()._subparsers._group_actions[0].choices["decide"].format_help()
    for flag in ("--override RULE", "--reason-from ^cR", "--until YYYY-MM-DD", "--on-behalf @owner", "--dissent ^cJ", "--provider ^cP"):
        assert flag in helped, flag  # `decide --help` lists the flags the skill no longer spells out
    for gone in ("- **Decided by:** @<user's handle>, on behalf of @<owner>", "This is how GATE-5 passes",
                 "W316 instead of E316", "`- **Override:** GATE-n by @<user's handle> on <today>"):
        assert gone not in grill, gone  # decide writes the override bullets


def test_grill_tells_the_lead_how_an_absent_owner_confirms_by_name():
    grill = read_override("skills", "grill", "SKILL.md")
    assert "Ines can confirm it later by adding a 'Confirmed by' line to the page" in grill
    assert "`- **Confirmed by:** @<owner> on <date>`" not in grill


# --- From tests/test_reader_skills.py: a reader's decisions are pending, and only the owner hands an app over.


def test_grill_refuses_a_handoff_in_a_reader_copy_naming_the_owner():
    # NEW-13 was dropped: `vela handoff preview` is read-only on purpose, so a reader can see what a handoff leaves
    # unmet. The stop is step 0 of HANDOFF.md, a branch file read only when a handoff item comes up.
    handoff = text("skills/grill/HANDOFF.md")
    assert handoff.split("0. ", 1)[1].startswith("Run `vela role`. In a reader copy, stop")
    assert "Only the plan's owner can hand an app to its team" in handoff and "published.json" in handoff
    assert "`SKILL.md` has already stopped a reader copy" not in handoff  # Fossil Comment: SKILL.md no longer does
    assert "owner's call: it stamps their commit" not in text("skills/grill/SKILL.md")


def test_grill_leaves_the_pending_marker_to_decide():
    grill = text("skills/grill/SKILL.md")
    assert "- **Pending approval:** @<handle>, <today>" not in grill
    assert "in a reader copy that the owner sees it before it counts" not in grill  # decide writes it


# --- From tests/test_reviewers.py: The review checkpoint and the gate's owed questions before the agenda.


def test_grill_reads_the_blocking_questions_and_runs_the_checkpoint_on_the_agenda():
    grill = text("skills/grill/SKILL.md")
    assert "vela check --gate grill --item <ID> --for-lead" in grill
    assert "references/REVIEW.md" in grill and '"on the agenda"' in grill
    assert grill.index("--gate grill") < grill.index("**The agenda.**")


def test_grill_records_a_decision_over_an_open_blocking_question():
    grill = text("skills/grill/SKILL.md")
    assert "sh ${CLAUDE_PLUGIN_ROOT}/scripts/run-vela" not in grill  # rule deletion: START's "Where vela runs from"
    assert "repeating `--item`" in grill and "decided with <copy IDs> open (W807)" in grill
    for gone in ("exits 2", "at most three questions", "Per item it says ready, or not ready", "skipping any the record already answers"):
        assert gone not in grill, gone  # the gate's output and REVIEW's digest say these
    assert "can be stale" not in grill  # the gate skips owed questions the record answers


# --- From tests/test_session_experience.py


def test_grill_stays_the_leads_to_start():
    assert_offered_then_asked("grill")


def test_grill_hands_the_lead_to_start_not_to_a_slash_command_they_must_type():
    body = text("skills/grill/SKILL.md")
    assert "Closing a session" in body, "grill must say how its session ends"
    assert "Do not run close yourself" not in body
    assert not re.search(r'[Tt]ell the user: "Run `/vela:close`', body)


def test_grill_leaves_the_digest_to_review():
    assert "high and blocking lines in full" not in text("skills/grill/SKILL.md")


def test_the_grill_gate_prose_carries_no_code():
    grill = section_session_experience(text("skills/grill/SKILL.md"), "3. The gate and the agenda")
    assert "never as a table" in grill
    assert "Show the result as a table" not in grill


def test_grill_handoff_does_not_require_the_epics_gate():
    body = text("skills/grill/SKILL.md")
    grill = (section_session_experience(body, "1. The questions")
             + body.split("## Handing an app over")[1].split("## 4.")[0] + text("skills/grill/HANDOFF.md"))
    assert "check --gate epics" not in grill


def test_grill_leaves_the_capture_marks_to_decide():
    grill = text("skills/grill/SKILL.md")
    assert "→ keep: [[" not in grill and "the one exception to leaving marks off until close" not in grill
    assert "vela decide <ID> --readback ^cN --yes ^cM --why ^cK --for-lead" in grill


def test_grill_leaves_options_considered_to_the_gate():
    assert "`**Options considered:**` bullet" not in text("skills/grill/SKILL.md")


# --- From tests/test_skills.py: the rules the grill exists to hold


def test_grill_holds_the_loop_and_files_each_decision_at_once():
    grill = text("skills/grill/SKILL.md")
    assert "If no item passes and the user overrides none after you offered it for each item their answers settled, do not start the grill: make no change to any page" in grill
    assert "claude, from <name>" not in grill  # rule deletion: START's "Captures during the session" owns origins
    assert "Keep your recommendation when the user pushes back without a reason." in grill
    assert "Never answer your own question." in grill
    assert "## 4. File each decision as its branch closes" in grill and "Before the next question:" in grill
    assert "Never batch decisions to the end" not in grill and "## Never" not in grill  # the line above says it


def test_grill_defines_acceptance_and_the_owner_rule():
    grill = text("skills/grill/SKILL.md")
    assert 'Silence, "ok", "next", "sure" with nothing else, or a change of subject do not count as acceptance.' in grill
    assert "read the final wording back and get a yes" in grill
    assert "says yes in person" in grill and "explicit yes" in grill
    assert "ask where the provider stands" in grill
    # rule deletion: `vela decide` prints the already-decided answer and the reopen choice
    for gone in ("it is already decided. Say so", "change of mind in the Changes table", "Exit 3", "Exit 1",
                 "It runs the gate again, writes everything the decision needs"):
        assert gone not in grill, gone


def test_grill_never_drafts_an_ask():
    # rule deletion: MODES "The lead does the asking" and START step 1 hold it, for every mode
    assert "Never draft an ask, an email or a chase for the user to send." not in text("skills/grill/SKILL.md")
    # (MODES "The lead does the asking" and START step 1 are pinned in test_modes_text.py and test_start_text.py)


# --- From tests/test_tracer_skills.py: the tracer, never a gate, no codes read to the lead.


def test_grill_carries_its_tracer_guidance():
    assert "this app's piece of it" in skill_text("grill")


def test_grill_explains_the_tracer_as_the_first_thin_path():
    text = skill_text("grill")
    assert "first thin path" in text and ("Releases" in text or "Slices" in text)


def test_grill_leaves_the_tracer_definition_to_conventions():
    assert "thin path through every app" not in skill_text("grill")


def test_grill_never_makes_the_tracer_a_gate():
    for sentence in re.split(r"(?<=[.?!])\s+", read_tracer_skills("skills/grill/SKILL.md")):
        if re.search(r"tracer", sentence, re.I):
            assert not re.search(r"\b(stop|stops|refuse|refuses|block|blocks|gate)\b", sentence, re.I), sentence


# --- From tests/test_v3_final_fixes.py: W807 is described as it is


def test_grill_says_the_capture_is_the_record_of_an_open_owed_question():
    grill = text("skills/grill/SKILL.md")
    assert "The W807 stays in the check output as the record." not in grill
    assert "that capture is the record" in grill


# --- From tests/test_why.py: the lead's own reasons, copied by decide


def test_the_grill_asks_for_the_why_in_the_leads_words_and_offers_a_record_for_big_ones():
    grill = skill_text("grill")
    assert "Why this one, in your words?" in grill and "A declined reason is captured as given" in grill
    assert "decision record" in grill and "`vela add adr`" in grill  # the flags are `vela add adr --help`'s
    assert "word for word as `- **Why:** <the lead's words>`" not in grill  # decide copies it


# --- Task 22c: the rewrite's own first callers and rule deletions


def test_questions_section_is_first():
    grill = text("skills/grill/SKILL.md")
    numbered = re.findall(r"^## (\d+)\. (.+)$", grill, re.M)
    assert numbered[0] == ("1", "The questions"), numbered
    assert [n for n, _ in numbered] == ["1", "2", "3", "4"]  # "Handing an app over" is unnumbered


def test_flow_check_line_is_the_commands_not_the_skills():
    grill = text("skills/grill/SKILL.md")
    assert "Run `vela check-slice --changed --for-lead`" in grill
    # rule deletion: how to record a finding the lead lives with is gates.flow_reason's model line (NEW-12), through
    # `vela apply`, never a hand-written `## Overrides` bullet (tests/test_gates.py)
    assert "which you record under the slice page's `## Overrides`" not in grill
    assert "'not fully checked' takes no override" not in grill
    assert "not ready while `vela check-slice` reports a finding on it" not in grill
    assert "It moves to `planned` only when every flow it names" not in grill
    from vela import gates
    assert "vela apply (kind override, the slice page" in gates.FLOW_OVERRIDE_ROUTE


def test_grill_names_only_commands_that_exist():
    from test_skill_commands_exist import calls, is_a_mention, parse_error
    from vela import cli
    parser = cli.build_parser()
    found = []
    for name in ("SKILL.md", "HANDOFF.md"):
        for line, written, argv in calls(PLUGIN / "skills" / "grill" / name):
            found.append(written)
            if not is_a_mention(parser, argv):
                assert parse_error(parser, argv) is None, f"{name}:{line}: {written}"
    for command in ("check --gate grill", "decide", "add unknown", "add adr", "handoff preview", "record add",
                    "check-slice --changed", "apply"):
        assert any(command in w for w in found), command


def test_the_gate_table_rows_are_gone():
    grill = text("skills/grill/SKILL.md")
    for gate in ("GATE-1", "GATE-2", "GATE-3", "GATE-4", "GATE-5"):
        assert f"| {gate} |" not in grill, gate
    assert "| Gate | Passes when | If it fails, offer |" not in grill
    assert "Search `11-unknowns-and-risks.md`" not in grill
    assert "blocks every item on that page" not in grill  # gates.py reads model.blocked_units


def test_the_nine_write_bullets_are_gone():
    grill = text("skills/grill/SKILL.md")
    for gone in ("Set its state to `decided`: the page's `state:` field",
                 "Add `- **Decision:** [[<session id>]]` under the page's `## History`",
                 "- **Dissent:** <name>, <date>: <reason>",
                 "If the user overrode a gate for it, add the `**Override:**` bullet",
                 "Add a row to `## Changes`: `| <ID> | <old state> | decided |",
                 "Mark the deciding capture line now",
                 "Commit with the message `grill: <ID> decided`",
                 "Stage the session record and the changed pages, by exact path.",
                 "with `state: proposed` and the Why as its Context"):
        assert gone not in grill, gone


def test_the_never_list_is_gone():
    grill = text("skills/grill/SKILL.md")
    assert "## Never" not in grill
    # E304 holds a fact without a source; the clause naming "rules that used to be listed here" was a Fossil Comment
    assert "Never write `fact`" not in grill and "used to be listed here" not in grill


def test_decide_says_it_is_already_decided_and_offers_the_reopen():
    from types import SimpleNamespace
    from vela.commands import decide
    result = decide.already_result(SimpleNamespace(id="CON-001", name="The booking API", state="decided"))
    said = result.lines[0].plain
    assert "is already decided. Shall I reopen it? Reopening records the change of mind." in said
    assert any(c["command"] == "vela decide --reopen CON-001 --why <the lead's reason>" for c in result.needs_lead)


def test_grill_is_leaner_than_it_was():
    assert len(text("skills/grill/SKILL.md").split()) <= 1480  # 2,342 before the first trim; 2,046 after it; 1,407 after the second; +24 for the one-option question and the release date
    # 415 before the first trim; 364 after it; step 0 (a reader stops, the review's fix for NEW-13) made it 396
    assert len(text("skills/grill/HANDOFF.md").split()) <= 410


def test_grill_reads_back_by_name_and_keeps_ids_out_of_its_own_wording():
    grill = section_session_experience(text("skills/grill/SKILL.md"), "1. The questions")
    assert "Say names, not IDs, in your own words too." in grill
    assert "> Record consent: the desktop agent asks for both choices" in grill
    assert "The rider app's part of 'unlock a bike with a card on file'" in grill
    assert "as `CAP-nnn.FRn@APP-<slug>`, and set each row" not in text("skills/grill/SKILL.md")


def test_grill_description_and_lower_case_name():
    grill = text("skills/grill/SKILL.md")
    assert "the only session that sets decided. Offer it when" in grill.split("---", 2)[1]
    body = grill.split("---", 2)[2] + text("skills/grill/HANDOFF.md")
    for proper in ("A Grill", "a Grill", "the Grill", "Grill row", "a Grill's"):
        assert proper not in body, proper
    assert "the vault" not in body and "the senior" not in body


def test_new_unknown_goes_through_add_unknown():
    four = section(text("skills/grill/SKILL.md"), "## 4.", "## Ends when")
    assert "`vela add unknown --capture ^cN --blocks <ID> --for-lead`" in four
    assert "re-run GATE-4 for every other agenda item" not in four


# --- grill SKILL.md section 1, house-voice "Sound sure": full3 T118 opened a part with "It's November 3. Procurement
# reports that ... still hasn't come", an invented present-tense fact the lead then built on.
def test_a_grill_scenario_is_a_hypothetical_built_from_the_record():
    from conftest import REPO
    grill = (REPO / "plugin/skills/grill/SKILL.md").read_text(encoding="utf-8")
    assert 'frame it as a hypothetical ("Suppose' in grill
    assert "Build it only from what the plan, the inbox or the lead has said" in grill
    assert "Never state a new dated event, or what a third party reported, as if it had happened" in grill
    assert '"It\'s 8:58,' not in grill  # the old example was itself a present-tense fact



# --- grill SKILL.md section 2, MODES: a lead's yes in shape, boundary or releases was saved as an assumption and lost
# (full3 D4, D7, D8). The rule is in `vela decide` (decisions/ready.py); the skills only say to follow it.
def test_a_grill_opens_with_the_items_the_lead_already_said_yes_to():
    from conftest import REPO
    grill = (REPO / "plugin/skills/grill/SKILL.md").read_text(encoding="utf-8")
    assert "ready to decide" in grill and "Open the agenda with them" in grill


def test_grill_drafts_the_paragraph_of_each_item_it_files_now():
    body = (REPO / "plugin" / "skills" / "grill" / "SKILL.md").read_text(encoding="utf-8")
    assert "Draft" in body and "paragraph" in body and "START.md" in body
    assert "Draft the paragraph when the item is filed" in body or "Draft each filed item's paragraph now" in body
