"""What the close skill says, pinned in one place (overhaul plan Task 3).

Every test that pins this text lives here, so the rewrite that changes it edits this file and no other skill's.
Each section is headed by the file it came from and that file's reason.
"""
import re
import shlex

from conftest import REPO, skill_text
from vela import cli, closedrafts, closefinish, guard, markrules, mergeplan, prbody, progress
from vela.commands import add, close_gate, close_push, close_stage, close_sync, voice, voice_settle
from vela.decisions import add_subject, ledger_rows
from vela.model import build
from vela.parse import parse_page


def section(text, start, end):
    return text.split(start, 1)[1].split(end, 1)[0]


CLOSE = skill_text("close")
CLOSE_SKILL = (REPO / "plugin" / "skills" / "close" / "SKILL.md").read_text(encoding="utf-8")
# What Task 22a owns: SKILL.md (its opening, sections 1 and 6 to 9), READER.md and PR-BODY.md.
CLOSE_22A = "\n".join((REPO / "plugin" / "skills" / "close" / name).read_text(encoding="utf-8")
                      for name in ("SKILL.md", "READER.md", "PR-BODY.md"))


def read(*parts):
    return (REPO.joinpath(*parts)).read_text(encoding="utf-8")


def close_section(start, end):
    return skill_text("close").split(start, 1)[1].split(end, 1)[0]


PLUGIN = REPO / "plugin"


def text(rel):
    return (PLUGIN / rel).read_text(encoding="utf-8")


def text_of(*parts):
    return (REPO.joinpath(*parts)).read_text(encoding="utf-8")


def words(count, start=0):
    """Distinct words, so a long paragraph is not also a repeated phrase."""
    return " ".join(f"item{n}" for n in range(start, start + count)) + ". "


LINT = REPO / "plugin" / "references" / "lint-words.txt"


def section_session_experience(body, heading):
    """The text under a `## heading` up to the next `## `."""
    return body.split(f"## {heading}\n", 1)[1].split("\n## ", 1)[0]


APP = """---
id: APP-shop
type: app-building-blocks
title: Shop
state: decided
owner: "@t"
authored: mixed
change: changed
stage: target
sources: [SRC-01]
---

# Shop

### CON-001 Sale API

- **Consumers:** [[till-building-blocks|Till]]
- **Change:** new
- **State:** assumption
{options}
"""


def suggestion(options):
    page = parse_page("05-building-blocks/shop-building-blocks.md", APP.format(options=options))
    [row] = progress.grid(build([page], {"initiative": "INI-900", "title": "Mini"}), "2026-01-15")
    return row.mode, row.subject


def close_text():
    return skill_text("close")


def voice_review():
    return (PLUGIN / "skills" / "close" / "VOICE-REVIEW.md").read_text(encoding="utf-8")  # read by close at the voice review


# --- From tests/test_answer.py: Answering a challenge: START opens an answer session on the challenge's own branch, a
# Grill (or the lead setting the item back) works there, and close pushes to that branch and comments on the open
# challenge PR instead of opening a new one.


def test_close_finds_an_answer_record_on_a_shared_branch():
    # close finds it through `vela session open`, which reads every record on a shared branch
    # (tests/test_session_open.py::test_two_records_on_one_branch_finds_the_open_one)
    assert "vela session open --switch" in section(skill_text("close"), "## 1.", "## 2.")


def test_close_leaves_the_answer_session_route_to_close_push_and_pr():
    """An answer session pushes to its challenge's branch and comments on that PR: `close push` and `close pr` own it."""
    assert "challenge's\n   branch" in close_push.__doc__ and "gh pr comment" in close_push.__doc__
    eight = section(CLOSE_SKILL, "## 8.", "## What you tell")
    assert "for an answer session it comments on the challenge's pull request instead" in eight
    for recipe in ("git push origin <branch>", "gh pr comment <number>", "gh pr list --head", "E316 for <ID>"):
        assert recipe not in CLOSE_22A, recipe


# --- From tests/test_close_text.py: Close's text after the overhaul's Task 22a-1: sections 1, 6 and 7 run commands
# instead of git recipes.


def test_moved_recipes_are_gone_from_close():
    for recipe in ("merge-base --is-ancestor", "-X ours", "git branch -r --list", "git branch --list 'session/*'",
                   "git add -A", "git merge --abort", "git grep -l '^status: open'"):
        assert recipe not in CLOSE, recipe


def test_sections_one_and_six_to_nine_hold_no_git_or_gh_recipe():
    """Task 22a: finishing, sending, the PR and the dashboard are `close finish`, `close push`, `close pr` and
    `close dashboard` now; each sentence that ran git or gh by hand went in the same commit as the call."""
    for recipe in ("git add", "git commit", "git push", "gh pr create", "gh pr comment", "gh api user", "merge-base",
                   "-X ours", "git log --format=%ct", "--consent-block", "--reviewer", "git status --short",
                   "grep -rn -F", "vela handoff <APP-id>", "vela ladder", "--serve", "set `status: closed`",
                   "Strip the leading `@`", "<Mode name>", ".vela/pr-body.md", "W705", "W806"):
        assert recipe not in CLOSE_22A, recipe


def test_close_names_only_commands_that_exist():
    parser = cli.build_parser()
    calls = re.findall(r"`vela ((?:close|session|guard|conventions|check-slice|check|record|whoami|role|render|apply"
                       r"|marks|add|prose|voice|style) [^`]*)`", CLOSE)
    assert len(calls) >= 20, calls
    for call in calls:
        if "--help" in call:
            continue
        argv = shlex.split(re.sub(r"<[^>]*>", "X", call).replace("^cN", "^c1").replace("^cM", "^c2").replace("^cK", "^c3"))
        args, extras = parser.parse_known_args(argv)
        assert not extras, (call, extras)


def test_the_moved_rules_keep_their_reasons_in_code():
    assert "theirs" in mergeplan.__doc__ and "theirs" in close_sync.__doc__  # one wrong side loses the owner's edits
    assert "git add -A" in close_stage.__doc__ and "allow-list" in close_stage.__doc__
    assert ".inbox/" in guard.__doc__
    assert "Edit tool" in close_gate.__doc__


def test_close_finish_push_pr_in_order():
    """The yes to send is numbered after `close push`'s notice and captured while the record is still open, so
    `close finish` commits it; then the push cites it and `close pr` quotes it (tests/replay/step_45 and step_70)."""
    seven = section(CLOSE_SKILL, "## 7. Finish and send", "## 8.")
    order = ["vela check-slice --changed", "vela close gate --for-lead", "vela close push --for-lead",
             "vela record add --origin", "vela close finish --summary", "vela close push --consent ^cN"]
    at = [seven.index(step) for step in order]
    assert at == sorted(at), order
    assert '--mark "drop: the yes to send this for review"' in seven
    assert (CLOSE_SKILL.index("vela close sync-main") < CLOSE_SKILL.index("vela close gate")
            < CLOSE_SKILL.index("vela close pr --prose"))
    assert "captured with `vela record add` while the record is still open" in read(
        "tests", "replay", "step_45_close_push_notice.py")


def test_close_relays_the_gate_grouped_and_in_its_own_words():
    seven = section(CLOSE_SKILL, "## 7. Finish and send", "## 8.")
    assert "group it by what holds the close up, about four at a time" in seven
    assert "which slices still run end to end and which break, and where" in seven
    assert "may keep any as it is" in seven
    assert "as it prints them" not in CLOSE_SKILL and "in its words" not in CLOSE_SKILL
    assert "Never pass raw git or `gh` error text on" in CLOSE_SKILL


def test_a_command_that_cant_do_it_is_a_stop_not_a_recipe():
    assert "never fall back to doing its steps by hand" in CLOSE


def test_close_says_grill_in_lower_case():
    own = (REPO / "plugin" / "skills" / "close" / "SKILL.md").read_text(encoding="utf-8")
    assert not re.search(r"\bGrill\b", own)
    assert (REPO / "plugin" / "lib" / "vela" / "terms.py").is_file()


# --- From tests/test_deferrals.py: A matter left for a Grill is an open question with an owner and a date, never a
# sentence that nothing will read again.


def test_close_turns_a_deferral_into_a_question_with_an_owner_and_a_date():
    four = section(CLOSE_SKILL, "## 4. Draft the prose", "### Voice review")
    assert "is never kept as prose" in four and "vela add unknown --blocks <ID>" in four
    assert any(rule.name == "deferral-unknown" for rule in markrules.RULES)


# --- From tests/test_final_fixes.py: Fixes from the final whole-branch review: each test names the failure it keeps
# out.

# 1, M6, M9, M5, M4, 7, M2, M3, README: the words the skills and template must carry


def test_close_stages_what_render_rewrote():
    # close stages through `vela close finish`, which runs `close stage --close`, whose allow-list includes what render
    # rewrote (tests/test_close_stage.py)
    assert "vela close finish" in CLOSE_SKILL and "close stage --close" in closefinish.__doc__


def test_close_leaves_the_owning_team_epics_wrote():
    assert "and its `**Owning team:**` line" not in CLOSE
    assert "Never delete an `**Ask:**`, `**Target:**` or `**Owning team:**` line" in CLOSE_SKILL


def test_close_checks_remote_session_records_before_taking_an_id():
    """Close numbers through `vela add`, which reads every local and remote session branch itself."""
    step3 = section(CLOSE_SKILL, "## 3.", "## 4.")
    assert "numbers past every open session branch" in step3 and "never number an item by hand" in step3
    assert "every session branch" in add.__doc__
    assert '"refs/heads/session/", "refs/remotes/origin/session/"' in read("plugin/lib/vela/cli.py")


# --- From tests/test_final_wave.py: The last fix wave: the root README describes v2, and close, START, CONVENTIONS
# and the plugin manifest say what the code and the workflow actually do.

# M1: a stale session branch merges main before render


def test_close_merges_a_moved_main_before_render():
    # The merge recipe moved into `vela close sync-main` (tests/test_sync_main.py pins its behavior); the skill
    # runs it before render and checkpoints through `close stage`.
    step = close_section("## 6. Bring in main and check", "## 7.")
    assert step.index("vela close sync-main") < step.index("vela render")
    assert "vela close stage --checkpoint" in step
    assert "git merge" not in step and "-X ours" not in step and "--theirs" not in step
    assert "long-lived PR" in read("README.md") and "merge `origin/main`" in read("README.md")


def test_close_says_the_draft_commit_holds_whole_pages_and_review_lists_only_prose():
    draft = close_section("## 4. Draft the prose", "### Voice review")
    assert "vela close stage --draft" in draft
    assert "the drafted pages whole" in close_stage.__doc__
    assert "Leave out the bullets, table rows and headings" in voice_review()


def test_close_pr_body_carries_the_no_examples_line():
    body = (PLUGIN / "skills" / "close" / "PR-BODY.md").read_text(encoding="utf-8")
    assert '"No examples for <type>: drafted without examples" line house-voice gave' in body


def test_pr_body_is_the_sentences_a_reviewer_reads():
    """Task 22a: `close pr` builds the lists; PR-BODY.md keeps only what code can't write."""
    body = (PLUGIN / "skills" / "close" / "PR-BODY.md").read_text(encoding="utf-8")
    assert len(body.split()) < 260
    assert "two or three sentences" in body and "Don't repeat any of it" in body
    for heading in ("**Promoted on a nod:**", "**May still say the old value:**", "**Minutes.**", "**Stage:**"):
        assert heading not in body, heading
    assert "the two or three sentences a reviewer reads first" in prbody.__doc__


# --- From tests/test_handoff_warnings.py: At handoff the lead, and through the manifest the senior, hear what is not
# firm: drafts, missing case tables, providers nobody has designed, and a manifest pinned to a commit that is gone.


def test_the_close_manifest_step_tells_the_lead_what_is_not_firm():
    assert "not settled at handoff" in skill_text("close")  # the words the handoff record's heading now uses


# --- From tests/test_ladder.py: vela ladder: the stage an app's pages reach, against its hand-typed stage.


def test_close_reports_the_stage_as_a_line_and_never_asks():
    assert "vela ladder" not in CLOSE_22A  # close pr writes the stage line itself
    assert prbody.stage_line("Till", "design", "boundary").startswith("Ready to move on: ")


def test_close_writes_the_handoff_pr_number():
    assert "replace `pending`" not in CLOSE_22A
    assert "Handoff PR number for <APP-id>" in close_push.__doc__ and "W325" in close_push.__doc__


# --- From tests/test_next_id.py: vela next-id: a number an open session branch already holds is never handed out
# again (UNK-026 twice, heron run).


def test_close_numbers_new_items_one_way():
    """Close once said `vela next-id` in section 2 and "grep the vault ... add one to the highest" in section 3. Two
    ways to number is how two branches take one ID; `vela add` numbers past every session branch, so it is the only way."""
    assert "grep the vault for the existing IDs" not in CLOSE and "Add one to the highest" not in CLOSE
    assert "vela next-id" not in CLOSE and "vela add unknown" in CLOSE_SKILL


# --- From tests/test_override.py: The user can override any rule, and an override is never invisible.

# ------------------------------------------------------------- skill text


def test_close_keeps_the_override_bullets():
    close = skill_text("close")
    assert "Keep every `**Override:**`, `**Decided by:**` and `**Confirmed by:**` bullet as written" in close
    assert "fix its grammar, never delete it" in close
    assert '("Overrides", f.overrides, "none")' in read("plugin", "lib", "vela", "prbody.py")


# --- From tests/test_reader_skills.py: Reader mode in the skill text: no git in a read copy, owner-only skills
# refuse, a reader's decisions are pending, and every skill finds the installed vela by the one order START.md states.


def test_close_has_a_reader_section_that_commits_and_pushes_nothing():
    pointer = CLOSE_SKILL.split("## Reader copy", 1)[1].split("## 1. Find the session")[0]
    assert "skills/close/READER.md" in pointer and "Never say a PR exists" in pointer
    reader = text("skills/close/READER.md")  # read only when `vela role` says reader
    assert len(reader.split()) < 150
    assert ("This is a read-only copy, so I'll save your notes here and stop. Nothing leaves your machine. To send your "
            "changes to the owner, run /vela:propose.") in reader
    assert "Pending approval" in reader and "Never write a handoff manifest" in reader and "Never say a PR exists" in reader
    assert "grep -l" not in reader and "git restore" not in reader  # every close command takes the reader path itself


# --- From tests/test_reading_load.py: Pages a person can hold in mind: plain names in prose, IDs on a Trace line, and
# the five reading-load warnings.

# ---------------------------------------------------------------- the rule is written where sessions read it


def test_close_says_a_trace_line_quiets_the_reading_load():
    assert "or a `- Trace:` line, to quiet it" in text_of("plugin", "skills", "close", "SKILL.md")


# --- From tests/test_readload.py: The second five reading-load warnings (design session 16): a paragraph, a table
# cell, a stock phrase, a template opening and an abbreviation that costs the reader more than a careful writer would.

# ------------------------------------------------------------------------------------------------ the lint word list (16-D2)


def test_close_never_names_a_listed_word():
    """Naming a word in a prompt raises its odds, so the list lives in the lint and the reviewer, and the drafter never
    sees it."""
    from vela import reading
    words = reading.lint_words(LINT.read_text(encoding="utf-8"))
    relative = "skills/close/SKILL.md"
    text = (REPO / "plugin" / relative).read_text(encoding="utf-8")
    for word in words:
        assert not reading.lint_pattern(word).search(text.replace("lint-words.txt", "")), f"{relative} names '{word}'"


# --- From tests/test_reviewers.py: The focused reviewers and the review checkpoints in the session skills.

# ------------------------------------------------------------------ close writes the ledger and proposes entries


def test_ledger_is_the_conversation_only_and_the_rows_are_code():
    """Task 22b: `marks plan` drafts the ledger rows and `apply` writes and numbers them; LEDGER.md keeps how to ask
    about a row the lead's words leave unclear, and drafting a catalog entry."""
    ledger = text("skills/close/LEDGER.md")
    assert len(ledger.split()) < 300
    assert "Ask it as one of section 2's leftovers" in ledger and "Never invent a source" in ledger
    assert "write no row for those copies" in ledger
    assert "never ask whether a gap turned up late" in ledger
    assert "Never edit `${CLAUDE_PLUGIN_ROOT}/catalog/questions.yaml`" in ledger and "pruning is the maintainer's call" in ledger
    for gone in ("### The question ledger", "`R-<AREA>-nn`", "git show origin/main", "type at close: PTY",
                 "<!-- generated:undisposed-questions", "E801, E802 or E803", "vela questions --stats"):
        assert gone not in CLOSE, gone
    assert "written and numbered by code" in ledger_rows.__doc__
    assert "Every required fact, or nothing" in add_subject.__doc__ and "E808" in add_subject.__doc__


def test_close_reports_questions_and_reviews_in_the_pr_body():
    for label in ("**Questions:**", "**Catalog proposals:**", "vela check --gate shape", "vela questions --open --digest"):
        assert label not in CLOSE_22A, label  # close pr collects them
    assert '("Questions still open", f.open_questions, "none")' in read("plugin", "lib", "vela", "prbody.py")


def test_close_keeps_its_existing_guards():
    for kept in ("### Voice review", "### Harvest the owner's edits", "vela close sync-main",
                 "never stages the inbox, `voice/local/` or `voice/corpus/`", "vela voice settle --checkpoint",
                 "vela voice settle --rewrites"):
        assert kept in CLOSE, kept
    assert len(CLOSE_SKILL.split()) <= 2300


# --- From tests/test_session_experience.py: What the skills make a lead go through (docs/research/2026-10-12-session-
# experience-review.md and the friction pass).

# --- S24: close starts on the lead's word, and still confirms before anything leaves the machine


def test_close_can_be_started_by_the_model():
    close = skill_text("close").split("---\n", 2)[1]
    assert "disable-model-invocation" not in close


def test_close_asks_one_confirmation_before_it_pushes_and_never_starts_on_its_own():
    starting = section_session_experience(skill_text("close"), "Starting a close")
    assert "never by yours" in starting
    assert re.search(r"Before section 7 pushes.*wait for a yes", starting, re.S)
    assert "A bare \"close\" is consent to file, not to send." in starting


# --- S25: record by default, ask only the few unsettled items, never the tool's own filing


def test_close_files_by_default_and_asks_at_most_three_unsettled_items():
    sec2 = section_session_experience(CLOSE_SKILL, "2. Mark every capture")
    assert "vela marks plan --json" in sec2 and "without asking" in sec2 and "at most three items" in sec2
    assert "never show the lead the marks, a capture number or a list to approve" in sec2
    assert "There are four more; want them?" in sec2  # conversation rule 7: offer the rest
    assert "vela apply <file> --for-lead" in sec2 and "from its counts" in sec2


def test_worked_examples_kept():
    for example in ("I'd write the 18 January slot down as a constraint, from your account. Right?",
                    "Nobody has said who could settle whether a call digest is a client record. I'd ask legal and "
                    "chase it on 6 November. Is that the right person?",
                    "I kept the 8 fixed limits as constraints, set aside 12 what-ifs and dropped 5 that repeat other "
                    "lines.",
                    "I'll send this for review to Ines and the payments team. OK?"):
        assert example in CLOSE_SKILL, example


def test_sections_two_to_five_hold_no_rule_the_commands_own():
    """Task 22b: the default marks are `marks plan`, the grammar is `apply` and `add`, the paragraph list is
    `close drafts`, the voice and harvest git dances are `voice settle` and `voice harvest`. A number in two places
    drifts, so the opening limits live only in `style` and `check`."""
    for gone in ("80 words", "900 words", "three links", "W363", "W365", "W368", "W371", "W389", "two weeks from today",
                 "shasum", "awk", "cmp -", "mktemp", "git restore", "git diff", "git add", "git commit", "git push",
                 "git fetch", "gh pr", "gh api", "merge-base", "-X ours", "Defaults:", "Never ask the lead for bookkeeping",
                 "`→ keep:", "A person's `wild` line is parked", "Never propose `fact`", "Promoted on a nod",
                 "vela voicecheck", "voicescore-input", "vela query refs", "Allocate already wrote", "## Also open"):
        assert gone not in CLOSE, gone
    assert "never proposes `fact`" in markrules.__doc__ and "A capture that already has a mark keeps it" in markrules.__doc__
    assert "Claude never decides" in markrules.__doc__


def test_close_never_asks_for_minutes_handles_or_the_late_gap():
    assert "Did any other gap turn up late" not in CLOSE
    assert "Ask the user how long" not in CLOSE and "git log --format=%ct" not in CLOSE  # close pr counts the minutes
    assert "never ask whether a gap turned up late" in text("skills/close/LEDGER.md")


# --- S36 to S47


# --- From tests/test_skill_commands.py: Skill text that names the v2 commands: vela next at start, the Options
# considered bullet Shape leaves and next reads, and the handoff manifest close writes.


def test_close_writes_the_handoff_manifest_when_a_senior_takes_an_app():
    seven = section(CLOSE_SKILL, "## 7. Finish and send", "## 8.")
    assert "run it with `--replace` only once they say so in this session" in seven
    assert "not settled at handoff" in seven
    assert "The close commit comes first" in closefinish.__doc__
    assert closefinish.MANIFEST_MESSAGE == "Handoff manifest for {app}"


def test_the_bullet_shape_leaves_is_what_vela_next_reads():
    """`marks plan` keeps a shape session's pick as an assumption with its options considered; `vela next` reads it."""
    filled = "- **Options considered:** versioned API (picked); one shared schema: rejected, kiosks lag six months"
    assert suggestion("") == ("shape", "CON-001")
    assert suggestion(filled) == ("grill", "CON-001")
    assert any(rule.name == "shape-pick" for rule in markrules.RULES)


# --- From tests/test_skills.py: The plugin's skills: frontmatter, size, the files they point at, the plugin
# validator, and the rules each skill exists to hold.

# Session start, dump and close (V1-08). Each assertion pins a rule whose loss would be silent.


def test_close_marks_honestly_and_never_claims_a_pr():
    assert "never Claude's to keep or drop: the lead chooses" in CLOSE_SKILL
    assert "Never say a PR exists unless `gh` printed its URL." in CLOSE_SKILL  # the hard stop
    assert "Do not open a PR for a branch that is not pushed." in CLOSE_SKILL
    assert "`org/team`" in prbody.__doc__ and "the lead's own\n  handle is dropped" in prbody.__doc__
    assert '("Kept on Claude\'s suggestion (check these)", f.kept_on_claude, None)' in read("plugin", "lib", "vela", "prbody.py")


def test_close_finds_the_open_session_through_session_open():
    close = skill_text("close")
    assert "vela session open --switch" in close and "--id <the one they picked>" in close


def test_close_pr_body_reviewers_and_staging():
    assert "Decisions the owner hasn't heard read back" in prbody.__doc__
    assert "gh api user" not in CLOSE_22A and "If nobody remains, leave out" not in CLOSE_22A
    assert "git add -A" not in CLOSE and "vela close finish" in CLOSE_SKILL  # only the CLI stages


def test_close_never_stages_the_inbox():
    assert "never stages the inbox" in skill_text("close")  # close stage owns it (tests/test_guard.py)


def test_close_drafts_prose_through_house_voice():
    four = section(CLOSE_SKILL, "## 4. Draft the prose", "### Voice review")
    assert "Read `${CLAUDE_PLUGIN_ROOT}/skills/house-voice/SKILL.md` and follow it" in four
    assert "vela close drafts --json" in four and "vela close stage --draft" in four
    assert "vela style <each drafted page>" in four and "until it prints nothing" in four
    assert "vela prose replace --page" in four and "vela add adr --state decided" in four
    assert "Prose to draft" not in CLOSE


def test_close_knows_an_epic_owes_its_summary():
    assert "owes its summary" in closedrafts.__doc__  # close drafts lists it; the skill drafts it


def test_close_ends_with_the_dashboard_line_close_finish_gives():
    last = CLOSE_SKILL.split("\n## ")[-1]
    assert last.startswith("9. The dashboard")
    assert "vela close dashboard --for-lead" in last and "vela close dashboard --branch" in last
    assert "A failed build never undoes the close" in last and "never called up to date unless it built" in last
    assert "go straight to section 9, which has its own path for a close with no session" in CLOSE_SKILL
    for gone in ("The explorer could not be built", "The dashboard is rebuilt in your folder but not committed",
                 "never pipe it", "Rebuild dashboard", "dashboard/<today>"):
        assert gone not in CLOSE_SKILL, gone
    assert "never undoes the close" in closefinish.__doc__ and "Everything else is filed" in closefinish.DASHBOARD_FAILED


# --- From tests/test_split_opening.py: S50: a page kept two openings that disagree.


def test_close_replaces_the_opening_it_rewrites_instead_of_adding_one():
    assert ("A page has one opening: the one you rewrite replaces the old one, and you never write a new opening "
            "beside it.") in CLOSE_SKILL


# --- From tests/test_v3_final_fixes.py: The v3 final fix wave.

# ------------------------------------------------------------------ 2. a yes to an existence question is one flow


# ------------------------------------------------------------------ W809 and W804 reach the lead; W807 is described as it is


def test_close_lists_w809_and_w804_to_the_lead():
    six = section(CLOSE_SKILL, "## 6. Bring in main and check", "## 7.")
    for said in ("W809", "W804", "offer to type the subject", "fix the row", "Never delete it without a yes",
                 "vela check --for-lead"):
        assert said in six, said


# --- From tests/test_voice_review.py: The voice review at close: a fresh-context agent flags paragraphs, the drafter
# rewrites each once, and voicecheck keeps every fact the draft carried.


def test_a_decline_is_a_bare_line_under_captures_and_conventions_say_so():
    assert "vela voice harvest decline" in text("skills/close/HARVEST.md")  # the command writes the bare line
    sentence = "A harvest decline is one bare line, `Harvest declined: PR <n> <page> <hash>`, directly under `## Captures`, never a bullet."
    for path in ("template", "tests/stub-conventions", "examples/unified-booking"):
        assert sentence in (REPO / path / "CONVENTIONS.md").read_text(encoding="utf-8")


# --- From tests/test_voicecheck.py: vela voicecheck: a voice rewrite may change words, never the IDs, numbers, dates,
# wikilinks, code spans or table cells they carry.

# Through the CLI.


# --- From tests/test_voicescore.py: vela voicescore: an optional style-embedding reading of each prose paragraph
# against the owner's own range.

# --- the close skill ------------------------------------------------------------------------


def test_the_pr_body_reports_voicescore_in_the_voice_review_line():
    assert "voicescore: not run (not asked for)" in read("plugin", "lib", "vela", "prbody.py")
    assert "- **Voice review:**" not in CLOSE_22A
    assert "--score" in voice_review()


def test_voice_review_dispatches_a_fresh_reviewer_and_voice_settle_does_the_git():
    review = voice_review()
    assert len(review.split()) < 320
    assert "Dispatch the `vela:voice-reviewer` subagent with the Agent tool" in review
    assert "everything in `${CLAUDE_PLUGIN_ROOT}/agents/voice-reviewer.md` after the frontmatter" in review
    assert "you must not change any file, and you must report any file you changed" in review
    assert "Never review the drafts yourself in this conversation." in review
    assert "rewrite each paragraph it flagged once" in review and "Don't send the rewrite back for review" in review
    assert review.index("vela voice settle --checkpoint") < review.index("vela voice settle --rewrites")
    assert '--redundant <page> "<the sentence exactly as it stood>"' in review
    assert "restores only the pages that fail" in voice_settle.__doc__ and "Checkpoint <id>" in voice_settle.__doc__
    reviewer = (REPO / "plugin" / "agents" / "voice-reviewer.md").read_text(encoding="utf-8")
    assert "Redundant sentences" in reviewer and "Redundant sentence (exact)" in reviewer


def test_harvest_asks_the_two_questions_and_voice_save_files_the_sample():
    harvest = text("skills/close/HARVEST.md")
    assert len(harvest.split()) <= 300
    assert harvest.index("Did you write this change?") < harvest.index(
        "Keep this paragraph as a sample of how you describe how things work?")
    assert "May this text be committed to the vault?" in harvest
    assert "If the owner's employer owns the text, or they aren't sure, recommend this machine only." in harvest
    assert "vela voice harvest decline" in harvest and "vela voice save --from" in harvest
    assert "--retire-consent ^cK" in harvest and "don't repair it" in harvest
    assert "vela voice harvest list --json" in CLOSE_SKILL
    assert 'a `gh` failure read as "no edits found"' in voice.__doc__ and "--commit-consent" in voice.__doc__
    assert "Harvest is owner-only." in read("plugin", "lib", "vela", "commands", "voice.py")


# --- The conversation voice (the lead's extra requirement for every rewritten mode skill): close reads the owner's
# VOICE.md, then CONVERSATION-VOICE, before its first command or question, and drafts page prose through house-voice.


def test_close_loads_the_conversation_voice_before_its_first_command_and_question():
    body = CLOSE_SKILL.split("---\n", 2)[2]
    line = next(l for l in body.splitlines() if "references/CONVERSATION-VOICE.md" in l)
    assert "voice/VOICE.md" in line and line.index("voice/VOICE.md") < line.index("CONVERSATION-VOICE.md")
    assert "`house-voice`" in line
    at = body.index(line)
    first_command = body.index("`vela ")
    first_question = min(i for i in (body.find('?"'), body.find("?\")"), body.find("Ask ")) if i >= 0)
    assert at < first_command and at < first_question


def test_close_keeps_the_one_relay_line_and_the_hard_stop():
    assert "When a command can't express what the lead wants, say so and stop" in CLOSE_SKILL
    assert "Never say a PR exists unless `gh` printed its URL." in CLOSE_SKILL
