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


HEADINGS = {1: "1. Find the session and mark the captures", 2: "2. Write the items and the prose",
            3: "3. Still yes, then the read-back", 4: "4. Check, then finish and send",
            5: "5. The pull request, and what you tell the lead", 6: "6. No session open"}


def csec(n):
    """Close's numbered section n (the trim of October 23 cut nine sections to six), up to the next `## `."""
    return CLOSE_SKILL.split(f"## {HEADINGS[n]}\n", 1)[1].split("\n## ", 1)[0]


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
    # rule deletion: `close push` and `close pr` pick the route themselves, so the skill no longer says it
    assert "for an answer session it comments on the challenge's pull request instead" not in CLOSE_SKILL
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
    seven = csec(4)
    order = ["vela check-slice --changed", "vela close gate --for-lead", "vela close push --for-lead",
             "vela record add --tag decision", "vela close finish --summary", "vela close push --consent ^cN"]
    at = [seven.index(step) for step in order]
    assert at == sorted(at), order
    assert '--mark "drop: the yes to send this for review"' in seven
    assert (CLOSE_SKILL.index("vela close sync-main") < CLOSE_SKILL.index("vela close gate --for-lead")
            < CLOSE_SKILL.index("vela close pr --prose"))
    assert "captured with `vela record add` while the record is still open" in read(
        "tests", "replay", "step_45_close_push_notice.py")


def test_close_relays_the_gate_grouped_and_in_its_own_words():
    seven = csec(4)
    assert "grouped by what holds the close up" in seven
    assert "say which slices still run end to end and which break" in seven
    assert "may keep any as it is" in seven
    assert "as it prints them" not in CLOSE_SKILL and "in its words" not in CLOSE_SKILL
    # rule deletion: START's "Relaying a command" and its plain-names rule say it for every mode
    assert "Never pass raw git or `gh` error text on" not in CLOSE_SKILL
    # (START's "Relaying a command" is pinned in test_start_text.py)


def test_a_command_that_cant_do_it_is_a_stop_not_a_recipe():
    assert "never fall back to doing its steps by hand" in CLOSE


def test_close_says_grill_in_lower_case():
    own = (REPO / "plugin" / "skills" / "close" / "SKILL.md").read_text(encoding="utf-8")
    assert not re.search(r"\bGrill\b", own)
    assert (REPO / "plugin" / "lib" / "vela" / "terms.py").is_file()


# --- From tests/test_deferrals.py: A matter left for a Grill is an open question with an owner and a date, never a
# sentence that nothing will read again.


def test_close_turns_a_deferral_into_a_question_with_an_owner_and_a_date():
    four = csec(2)
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
    step3 = csec(2)
    assert "numbers past every open session branch" not in step3 and "never number an item by hand" not in step3  # next_id owns it
    assert "every session branch" in add.__doc__
    assert '"refs/heads/session/", "refs/remotes/origin/session/"' in read("plugin/lib/vela/cli.py")


# --- From tests/test_final_wave.py: The last fix wave: the root README describes v2, and close, START, CONVENTIONS
# and the plugin manifest say what the code and the workflow actually do.

# M1: a stale session branch merges main before render


def test_close_merges_a_moved_main_before_render():
    # The merge recipe moved into `vela close sync-main` (tests/test_sync_main.py pins its behavior); the skill
    # runs it before render and checkpoints through `close stage`.
    step = csec(4)
    assert step.index("vela close sync-main") < step.index("vela render")
    assert "vela close stage --checkpoint" not in step and "--accept-not-compared" not in step  # sync-main prints both
    assert close_sync.CHECKPOINT == "vela close stage --checkpoint" and "--accept-not-compared" in close_sync.ACCEPT
    assert "Exit 3 for uncommitted edits" not in step and "Exit 1: main changed lines" not in step
    assert "git merge" not in step and "-X ours" not in step and "--theirs" not in step
    assert "long-lived PR" in read("README.md") and "merge `origin/main`" in read("README.md")


def test_close_says_the_draft_commit_holds_whole_pages_and_review_lists_only_prose():
    draft = csec(2)
    assert "vela close stage --draft" in draft
    assert "the drafted pages whole" in close_stage.__doc__
    assert "Leave out the bullets, table rows and headings" in voice_review()


def test_close_pr_body_carries_the_no_examples_line():
    body = (PLUGIN / "skills" / "close" / "PR-BODY.md").read_text(encoding="utf-8")
    assert '"No examples for <type>: drafted without examples" line house-voice gave' in body


def test_pr_body_is_the_sentences_a_reviewer_reads():
    """Task 22a: `close pr` builds the lists; PR-BODY.md keeps only what code can't write."""
    body = (PLUGIN / "skills" / "close" / "PR-BODY.md").read_text(encoding="utf-8")
    assert len(body.split()) < 340  # the paragraph on what the body never says (the notes stay private) is new
    assert "two or three sentences" in body and "Don't repeat the list" in body and "**What changed**" in body
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
    assert not hasattr(prbody, "stage_line")  # the stage is not in the body any more


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
    # rule deletion: `check` says it (E321's fix writes the grammar) and the close gate asks about a removed override
    assert "fix its grammar, never delete it" not in close
    import inspect
    from vela import closegate, override
    assert "E321" in inspect.getsource(override) and "Write - **Override:**" in inspect.getsource(override)
    assert "Was that on purpose?" in inspect.getsource(closegate.unagreed_removals) or "Was that on purpose?" in inspect.getsource(closegate)


# --- From tests/test_reader_skills.py: Reader mode in the skill text: no git in a read copy, owner-only skills
# refuse, a reader's decisions are pending, and every skill finds the installed vela by the one order START.md states.


def test_close_has_a_reader_section_that_commits_and_pushes_nothing():
    pointer = CLOSE_SKILL.split("Run `vela role`.", 1)[1].split("## 1.")[0]
    assert "skills/close/READER.md" in pointer and "In a reader copy" in pointer
    assert "Never say a PR exists unless `gh` printed its URL." in CLOSE_SKILL
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
    assert "Ask it as one of close's leftovers" in ledger and "Never invent a source" in ledger
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
    assert "Questions still open" not in read("plugin", "lib", "vela", "prbody.py").split("def body")[1]


def test_close_keeps_its_existing_guards():
    for kept in ("run the voice review once as", "VOICE-REVIEW.md", "HARVEST.md", "vela voice harvest list --json",
                 "vela close sync-main", "vela voice settle --checkpoint", "vela voice settle --rewrites"):
        assert kept in CLOSE, kept
    assert "### Voice review" not in CLOSE_SKILL  # the review is a paragraph in section 2 now
    assert len(CLOSE_SKILL.split()) <= 1610  # was 3061 before the first trim; 2,585 after it; 1,557 after the second
    assert "nor the inbox, `voice/local/` or `voice/corpus/`" not in CLOSE_SKILL  # guard.py holds the allow-list


# --- From tests/test_session_experience.py: What the skills make a lead go through (the constraints the skills put on a lead's session).

# --- S24: close starts on the lead's word, and still confirms before anything leaves the machine


def test_close_can_be_started_by_the_model():
    close = skill_text("close").split("---\n", 2)[1]
    assert "disable-model-invocation" not in close


def test_close_asks_one_confirmation_before_it_pushes_and_never_starts_on_its_own():
    assert "Close starts on the lead's word, never yours." in CLOSE_SKILL
    assert "Sending is the only step that leaves the machine, and it takes its own yes." in CLOSE_SKILL
    assert re.search(r"`vela close push --for-lead` and say its notice.*; wait\.", csec(4), re.S)
    # rule deletion: START says when close starts and that only a yes after the notice sends, and `close push` refuses
    # a yes captured before the notice (decisions/consent.py:after_send_notice)
    assert 'A bare "close" is consent to file, not to send.' not in CLOSE_SKILL
    # START's "Closing a session" holds when close starts and the only yes that sends (pinned in test_start_text.py)


# --- S25: record by default, ask only the few unsettled items, never the tool's own filing


def test_close_files_by_default_and_asks_at_most_three_unsettled_items():
    sec1 = csec(1)
    assert "vela marks plan --json" in sec1 and "at most three" in sec1 and "in one message" in sec1
    assert "never show the lead marks, capture numbers or a list to approve" in sec1
    assert "`vela apply <file> --for-lead`" in sec1 and "by group and in the lead's words" in sec1
    # rule deletion: conversation rule 7 and `say.LEAD_LIMIT` offer the rest
    assert "There are four more; want them?" not in CLOSE_SKILL


def test_worked_examples_kept():
    for example in ("I'd write the January 18 slot down as a constraint, from your account. Right?",
                    "Nobody has said who could settle whether a call digest is a client record. I'd ask legal and "
                    "chase it on November 6. Is that the right person?",
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
    seven = csec(4)
    # rule deletion: `close finish --replace` says it (commands/closefinish.py), when a manifest already exists
    assert "run it with `--replace` only once they say so in this session" not in seven
    assert "it only once they agree to the changes; then finish again with --replace." in read(
        "plugin", "lib", "vela", "closefinish.py")
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
    # rule deletion: `close pr` refuses a branch `close push` hasn't pushed (close_push.pushed_marker; tests/test_close_pr.py)
    assert "Do not open a PR for a branch that is not pushed." not in CLOSE_SKILL
    assert "isn't pushed by close push yet" in read("plugin", "lib", "vela", "commands", "close_push.py")
    assert "`org/team`" in prbody.__doc__ and "the lead's own\n  handle is dropped" in prbody.__doc__


def test_close_finds_the_open_session_through_session_open():
    close = skill_text("close")
    assert "vela session open --switch" in close
    # rule deletion: with several open it exits 3 and prints "Run again with --id <id> to pick one"
    # (tests/test_session_open.py::test_several_open_exits_3_and_lists)
    assert "--id <the one they picked>" not in close


def test_close_pr_body_reviewers_and_staging():
    assert "still\n  run in `vela check` and in CI" in prbody.__doc__
    assert "gh api user" not in CLOSE_22A and "If nobody remains, leave out" not in CLOSE_22A
    assert "git add -A" not in CLOSE and "vela close finish" in CLOSE_SKILL  # only the CLI stages


def test_close_never_stages_the_inbox():
    assert "it never stages the notes" not in skill_text("close") and "nor the inbox" not in skill_text("close")  # guard.py owns the allow-list (tests/test_guard.py)
    assert "The notes stay on this machine" in skill_text("close")


def test_close_drafts_prose_through_house_voice():
    four = csec(2)
    assert "through `${CLAUDE_PLUGIN_ROOT}/skills/house-voice/SKILL.md`" in four
    assert "vela close drafts --json" in four and "vela close stage --draft" in four
    assert "`vela style` on each drafted page" in four and "until it prints nothing" in four
    # rule deletion: house-voice owns merged prose (`vela prose replace`) and closedrafts.WHY["adr"] names `vela add adr`
    assert "vela prose replace --page" not in four and "vela add adr --state decided" not in four
    assert "vela add adr --state decided" in closedrafts.WHY["adr"]
    assert "Prose to draft" not in CLOSE


def test_close_knows_an_epic_owes_its_summary():
    assert "owes its summary" in closedrafts.__doc__  # close drafts lists it; the skill drafts it


def test_close_ends_with_the_dashboard_line_close_finish_gives():
    last = CLOSE_SKILL.split("\n## ")[-1]
    assert last.startswith("6. No session open")
    assert "vela close dashboard --for-lead" in last and "vela close dashboard --put-back --for-lead" in last
    assert "the dashboard line `close finish` gave" in csec(5)
    # rule deletion: `close finish` and `close dashboard` print the failed-build line (closefinish.DASHBOARD_FAILED)
    assert "A failed build never undoes the close" not in last and "never called up to date unless it built" not in last
    assert "If none is open, change no page and go to section 6." in CLOSE_SKILL
    for gone in ("The explorer could not be built", "The dashboard is rebuilt in your folder but not committed",
                 "never pipe it", "Rebuild dashboard", "dashboard/<today>"):
        assert gone not in CLOSE_SKILL, gone
    assert "never undoes the close" in closefinish.__doc__ and "Everything else is filed" in closefinish.DASHBOARD_FAILED


# --- From tests/test_split_opening.py: S50: a page kept two openings that disagree.


def test_close_replaces_the_opening_it_rewrites_instead_of_adding_one():
    assert "A page has one opening" not in CLOSE_SKILL  # W371 holds it


# --- From tests/test_v3_final_fixes.py: The v3 final fix wave.

# ------------------------------------------------------------------ 2. a yes to an existence question is one flow


# ------------------------------------------------------------------ W809 and W804 reach the lead; W807 is described as it is


def test_close_lists_w809_and_w804_to_the_lead():
    four = csec(4)
    for said in ("Ask about a possibly untyped subject", "a ledger row that no longer fits", "in plain words",
                 "Never delete a ledger row or an override to quiet a check", "vela check --for-lead"):
        assert said in four, said
    # rule deletion: the codes went (NEW-11: W809's fix names `vela add subject`, which the lead never hears as a code)
    assert "W809" not in CLOSE_SKILL and "W804" not in CLOSE_SKILL


# --- From tests/test_voice_review.py: The voice review at close: a fresh-context agent flags paragraphs, the drafter
# rewrites each once, and voicecheck keeps every fact the draft carried.


def test_a_decline_is_a_stub_entry_and_conventions_say_so():
    assert "vela voice harvest decline" in text("skills/close/HARVEST.md")  # the command writes the bare line
    sentence = "A voice-harvest paragraph the lead declined is one entry in the stub's `harvest_declined`, `PR <n> <page> <hash>`"
    for path in ("plugin/template", "tests/stub-conventions", "examples/unified-booking"):
        assert sentence in (REPO / path / "CONVENTIONS.md").read_text(encoding="utf-8")


# --- From tests/test_voicecheck.py: vela voicecheck: a voice rewrite may change words, never the IDs, numbers, dates,
# wikilinks, code spans or table cells they carry.

# Through the CLI.


# --- From tests/test_voicescore.py: vela voicescore: an optional style-embedding reading of each prose paragraph
# against the owner's own range.

# --- the close skill ------------------------------------------------------------------------


def test_voice_review_scores_without_touching_the_pr_body():
    assert "--score" in voice_review() and "- **Voice review:**" not in CLOSE_22A


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
    assert len(harvest.split()) <= 330  # includes the line saying a decline is kept as a hash, none of the words
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
    assert "skills/house-voice/SKILL.md" in csec(2)  # drafting prose goes through house-voice; the opening need not name it
    at = body.index(line)
    first_command = body.index("`vela ")
    first_question = min(i for i in (body.find('?"'), body.find("?\")"), body.find("Ask ")) if i >= 0)
    assert at < first_command and at < first_question


def test_close_keeps_the_one_relay_line_and_the_hard_stop():
    assert "When a command can't express what the lead wants, say so and stop" in CLOSE_SKILL
    assert "Never say a PR exists unless `gh` printed its URL." in CLOSE_SKILL


def test_close_has_flow_end_codes_fixed_with_the_lead_before_the_session_closes():
    assert "an outside actor becomes a party only on their yes" in CLOSE_SKILL
    # rule deletion: the codes are `check`'s and `check-slice`'s to explain (rules.py reads E351, W354 and W374)
    assert "E351, W354, W374" not in CLOSE_SKILL


# --- Drafting as each item settles: close drafts only what `close drafts` still lists, runs the voice reviewer once on
# every paragraph the session touched, and shows the lead only the new or changed ones.


def test_close_drafts_only_what_is_missing_or_stale_and_reviews_everything_touched():
    four = csec(2)
    assert "draft only its `paragraphs`" in four
    assert "run the voice review once as" in four and "show the lead only new or changed paragraphs" in four
    # rule deletion: `close drafts --json` marks a paragraph drafted as an item settled `done` and lists only what is
    # missing or stale (tests/test_close_drafts.py), and START says so under "Draft the paragraph when the item is filed"
    assert "Paragraphs written as items settled are `done`; leave them" not in four
    assert "every prose paragraph this session touched" in read("plugin", "skills", "close", "VOICE-REVIEW.md")
    assert len(four.split()) < 330


def test_close_no_longer_rebuilds_every_paragraph_at_the_end():
    for gone in ("It lists every paragraph this session owes", "Keep the owner's wording wherever its facts still hold",
                 "Skip it if nothing was drafted", "a fresh reader checks the drafts"):
        assert gone not in CLOSE_SKILL, gone


def test_a_session_on_main_moves_to_its_own_branch_before_finish():
    """After `close finish` the session is closed and `record add` can't take the send yes, so a lead who learns at step 4
    that main needs a review branch can never send. The move is offered at step 1, while the session is open."""
    text = (REPO / "plugin" / "skills" / "close" / "SKILL.md").read_text(encoding="utf-8")
    send = text[text.index("Then send, in this order"):text.index("## 5. The pull request")]
    step1, step4 = send[send.index("1. Run `vela close push --for-lead`"):send.index("2. Capture")], send[send.index("4. Run"):]
    assert "review needs its own branch" in step1 and "`vela session branch --for-lead`" in step1
    assert "still open" in step1
    assert "session branch" not in step4


# --- The trim of October 23 (review finding 4): close is the one skill that sends, and it can start cold with START
# never read in the conversation. START is a Read result that compaction can drop; SKILL text is re-attached.


def test_close_carries_the_four_hard_stops_itself():
    for stop in ("Never edit anything under `~/.claude`.",
                 "Never commit or push company material, or anything from `.inbox/`, `voice/local/` or `voice/corpus/`, "
                 "without the owner's explicit consent in this session.",
                 "Never say a PR, comment, push or commit exists unless the tool printed it, and never report a failed "
                 "step as done.",
                 "Never invent what a person said, a source, or an ID the vault does not hold."):
        assert stop in CLOSE_SKILL, stop


def test_close_reconfirms_before_the_read_back_and_sends_in_its_order():
    three = csec(3)
    assert three.index("**Still yes?**") < three.index("**The read-back.**")
    assert "act only on its \"Still yes\" item" in three and "everything else it lists is section 4's" in three
    assert CLOSE_SKILL.index("## 3.") < CLOSE_SKILL.index("vela close sync-main") < CLOSE_SKILL.index("vela close push --for-lead")
    send = csec(4)
    order = ["1. Run `vela close push --for-lead`", "2. Capture the lead's answer", "3. Run `vela close finish",
             "4. Run `vela close push --consent"]
    at = [send.index(step) for step in order]
    assert at == sorted(at), order
