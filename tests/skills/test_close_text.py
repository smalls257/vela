"""What the close skill says, pinned in one place (overhaul plan Task 3).

Every test that pins this text lives here, so the rewrite that changes it edits this file and no other skill's.
Each section is headed by the file it came from and that file's reason.
"""
import os
import re
import shlex
import shutil
import subprocess
import textwrap

import pytest
from conftest import REPO, skill_text
from vela import cli, closefinish, guard, mergeplan, prbody, progress, schema
from vela.commands import close_gate, close_push, close_stage, close_sync
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


def recipe_commands():
    """The fenced voicecheck block in close's text, with the path to vela pointed at this repo."""
    found = re.search(r"^ *```\n( *tmp=\$\(mktemp\)\n.*?)^ *```", close_text(), re.S | re.M)
    block = textwrap.dedent(found.group(1))
    assert "${CLAUDE_PLUGIN_ROOT}/scripts/vela" in block
    return block.replace("${CLAUDE_PLUGIN_ROOT}/scripts/vela", str(PLUGIN / "scripts" / "vela"))


def git_in(repo, *args):
    cmd = ["git", "-c", "user.name=T", "-c", "user.email=t@example.invalid", "-c", "commit.gpgsign=false", *args]
    return subprocess.run(cmd, cwd=repo, check=True, capture_output=True, text=True, timeout=60).stdout


def close_voicecheck(repo, page):
    """Run close's block for one page, then close's exit-0 and exit-1 branches."""
    scratch = repo.parent / (repo.name + "-scratch")
    scratch.mkdir(exist_ok=True)
    # macOS mktemp ignores TMPDIR, so mktemp itself is pointed at the scratch folder
    script = f'mktemp() {{ command mktemp "{scratch}/t.XXXXXX"; }}\n' + recipe_commands().replace("<page>", page)
    env = {**os.environ, "TMPDIR": str(scratch)}
    code = subprocess.run(["bash", "-c", script], cwd=repo, capture_output=True, text=True, env=env, timeout=60).returncode
    assert list(scratch.iterdir()) == [], "the recipe left its temp file behind"
    if code == 0:
        git_in(repo, "add", page)
        git_in(repo, "commit", "-qm", "draft: voice rewrite for s")
    elif code in (1, 2):
        git_in(repo, "restore", "--", page)
    return code


DRAFT = "Booking holds a seat for 10 minutes while the customer pays on Tidepay's page.\n"


def draft_repo(tmp_path):
    git_in(tmp_path, "init", "-q")
    (tmp_path / "page.md").write_text(DRAFT, encoding="utf-8")
    (tmp_path / "record.md").write_text("Changes\n", encoding="utf-8")
    git_in(tmp_path, "add", "page.md", "record.md")
    git_in(tmp_path, "commit", "-qm", "draft: prose for s")
    (tmp_path / "record.md").write_text("Changes\n| row | added by step 3 |\n", encoding="utf-8")


def guard_command():
    found = re.search(r"^ *```\n( *git diff --quiet HEAD -- <page>.*?)^ *```", close_text(), re.S | re.M)
    return textwrap.dedent(found.group(1))


GIT_IDENTITY = {"GIT_AUTHOR_NAME": "T", "GIT_AUTHOR_EMAIL": "t@example.invalid",
                "GIT_COMMITTER_NAME": "T", "GIT_COMMITTER_EMAIL": "t@example.invalid"}


def harvest_text():
    """Close's own opening of the harvest part, then the steps in HARVEST.md, which close reads only when it harvests."""
    opening = close_text().split("### Harvest the owner's edits", 1)[1].split("## 5.", 1)[0]
    return opening + (PLUGIN / "skills" / "close" / "HARVEST.md").read_text(encoding="utf-8")


def run_git(repo, *args, stdin=None):
    return subprocess.run(["git", *args], cwd=repo, input=stdin, capture_output=True, text=True, check=True, timeout=60).stdout


@pytest.fixture
def pr_repo(tmp_path):
    run_git(tmp_path, "init", "-q")
    return tmp_path


def harvest_block(first_line):
    found = re.search(r"^ *```\n( *" + re.escape(first_line) + r".*?)^ *```", harvest_text(), re.S | re.M)
    assert found, first_line
    return textwrap.dedent(found.group(1))


def fresh_shell(repo, block, **slots):
    for slot, value in slots.items():
        block = block.replace(f"<{slot}>", value)
    return subprocess.run(["bash", "-c", block], cwd=repo, capture_output=True, text=True, timeout=60)


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
    assert len(calls) >= 12, calls
    for call in calls:
        argv = shlex.split(re.sub(r"<[^>]*>", "X", call))
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
    close = skill_text("close")
    assert "left for a grill, or is decided later, is never kept as prose" in close
    assert "`**Owner:**`" in close and "`**Ask by:**`" in close


# --- From tests/test_final_fixes.py: Fixes from the final whole-branch review: each test names the failure it keeps
# out.

# 1, M6, M9, M5, M4, 7, M2, M3, README: the words the skills and template must carry


def test_close_stages_what_render_rewrote():
    # close stages through `vela close finish`, which runs `close stage --close`, whose allow-list includes what render
    # rewrote (tests/test_close_stage.py)
    assert "vela close finish" in CLOSE_SKILL and "close stage --close" in closefinish.__doc__


def test_close_leaves_the_owning_team_epics_wrote():
    close = skill_text("close")
    assert "and its `**Owning team:**` line" not in close and "close leaves it as written" in close


def test_close_checks_remote_session_records_before_taking_an_id():
    """Close numbers through `vela next-id`, which reads every local and remote session branch itself (Task 1 of
    the overhaul dropped the grep recipe; `tests/test_next_id.py` pins what the command counts)."""
    close = skill_text("close")
    step3 = close.split("## 3.")[1].split("## 4.")[0]
    assert "vela next-id <its prefix>" in step3 and "every session branch" in step3
    cli = read("plugin/lib/vela/cli.py")
    assert '"refs/heads/session/", "refs/remotes/origin/session/"' in cli


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
    assert "holds each drafted page whole, including its structured section-3 edits" in draft
    assert "Commit the drafts on their own" not in draft
    review = (PLUGIN / "skills" / "close" / "VOICE-REVIEW.md").read_text(encoding="utf-8")
    assert "List only the prose paragraphs this section drafted" in review


# M5: house-voice's no-examples line has a place in the PR body


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


def test_close_numbers_new_unknowns_with_the_command_not_by_eye():
    from conftest import REPO
    assert "vela next-id UNK" in (REPO / "plugin" / "skills/close/SKILL.md").read_text(encoding="utf-8")


def test_close_numbers_new_items_one_way():
    """Close once said `vela next-id` in section 2 and "grep the vault ... add one to the highest" in section 3. Two
    ways to number is how two branches take one ID; the command counts every session branch, so it is the only way."""
    from conftest import REPO
    close = (REPO / "plugin" / "skills" / "close" / "SKILL.md").read_text(encoding="utf-8")
    assert "grep the vault for the existing IDs" not in close and "Add one to the highest" not in close
    assert "vela next-id <its prefix>" in close


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


def test_close_writes_a_ledger_row_for_every_copy_taken_and_every_finding():
    close = skill_text("close")
    assert "### The question ledger" in close
    assert "`R-<AREA>-nn`" in close and "Its state is `open` unless the lead took it." in close
    assert "Never write `answered` without an item link and a source" in close
    assert "<!-- generated:undisposed-questions sha=00000000: do not edit, run vela render -->" in close


def test_close_proposes_catalog_entries_and_never_edits_the_catalog():
    close = skill_text("close")
    assert "### Gaps the catalog missed" in close
    assert "Never ask the lead whether a gap turned up late" in close  # S25: the answer was no, 11 times in 11
    assert "Never edit `${CLAUDE_PLUGIN_ROOT}/catalog/questions.yaml`" in close
    assert "vela questions --stats" in close and "Pruning is the maintainer's call." in close


def test_close_reports_questions_and_reviews_in_the_pr_body():
    for label in ("**Questions:**", "**Catalog proposals:**", "vela check --gate shape", "vela questions --open --digest"):
        assert label not in CLOSE_22A, label  # close pr collects them
    assert '("Questions still open", f.open_questions, "none")' in read("plugin", "lib", "vela", "prbody.py")


def test_close_writes_answered_rows_in_the_grammar_check_reads():
    """An answered row needs answer: and a source check can verify. "The lead's own words in quotes"
    with no page is E802, so close must never be told to write one."""
    close = skill_text("close")
    assert "the lead's own words in double quotes" not in close
    assert "quote the words section 3 wrote" not in close
    assert "| SRC-nn | <name>'s first-hand account of <subject> | @<lead> | <today> | exists | said in session <id> |" in close
    assert "never words this close wrote. With no such source, the row is `assumed`." in close
    assert "E801, E802 or E803" in close and "Never delete a row to quiet the check" in close
    assert "Never delete a ledger row or an override to quiet the check" in close
    assert "By is the handle of whoever recorded or decided the row" in close
    assert "`git show origin/main:11-unknowns-and-risks.md`" in close
    assert "`[[<id>#<n>. <checkpoint>, <date>]]`" in close


def test_close_types_the_subjects_dump_named_and_never_invents_a_fact():
    close = skill_text("close")
    assert "### Type the subjects Dump named" in close
    assert "`type at close: PTY`" in close and "`type at close: SV`" in close
    for label in ("**Relationship:**", "**Agreements:**", "**Holder:**", "**Owner:**"):
        assert label in close
    assert "Never fill a fact from general knowledge" in close
    assert "Only `**Owner:**` may say `not known yet`." in close and "`none known`" in close
    assert "`→ keep: [[11-unknowns-and-risks#<heading>|UNK-nnn]] (open)`" in close
    assert "A finding the lead did not take has no capture, so it gets no mark." in close


def test_close_keeps_the_grill_record_of_a_decision_over_open_questions():
    close = skill_text("close")
    assert "decided with <copy IDs> open (W807)" in close
    assert "write no row for those copies" in close


def test_close_keeps_its_existing_guards():
    close = skill_text("close")
    for kept in ("### Voice review", "**Voicescore, optional.**", "### Harvest the owner's edits",
                 "vela close sync-main", "never stages the inbox, `voice/local/` or `voice/corpus/`",
                 "vela voicecheck"):
        assert kept in close, kept
    assert len(close.splitlines()) < 500


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
    sec2 = section_session_experience(skill_text("close"), "2. Mark every capture")
    assert "without asking" in sec2 and "at most three items" in sec2
    assert "numbered list" not in sec2.split("Defaults:")[0].replace("never show it to the lead as a numbered list", "")
    assert "Never ask the lead for bookkeeping" in sec2


def test_close_never_asks_for_minutes_handles_or_the_late_gap():
    close = skill_text("close")
    assert "Did any other gap turn up late" not in close
    assert "Ask the user how long" not in close and "git log --format=%ct" not in close  # close pr counts the minutes
    assert "Never ask the lead whether a gap turned up late" in close


# --- S36 to S47


def test_close_keeps_the_marks_allocate_and_releases_wrote():
    close = skill_text("close")
    assert "Allocate or Releases session already marked `(assumption)`" in close


# --- From tests/test_skill_commands.py: Skill text that names the v2 commands: vela next at start, the Options
# considered bullet Shape leaves and next reads, and the handoff manifest close writes.


def test_close_writes_options_considered_as_one_bullet():
    assert "`**Options considered:**` bullet, at page level or under the item's heading" in skill_text("close")
    assert "`- **Options considered:** <picked option> (picked); <option>: rejected, <reason>; ...`" in skill_text("close")


def test_close_writes_the_handoff_manifest_when_a_senior_takes_an_app():
    seven = section(CLOSE_SKILL, "## 7. Finish and send", "## 8.")
    assert "run it with `--replace` only once they say so in this session" in seven
    assert "not settled at handoff" in seven
    assert "The close commit comes first" in closefinish.__doc__
    assert closefinish.MANIFEST_MESSAGE == "Handoff manifest for {app}"


def test_the_bullet_close_writes_is_what_vela_next_reads():
    form = re.search(r"`(- \*\*Options considered:\*\* [^`]+)`", skill_text("close")).group(1)
    filled = (form.replace("<picked option>", "versioned API").replace("<option>", "one shared schema")
              .replace("<reason>", "kiosks lag six months").replace("; ...", ""))
    assert suggestion("") == ("shape", "CON-001")
    assert suggestion(filled) == ("grill", "CON-001")


# --- From tests/test_skills.py: The plugin's skills: frontmatter, size, the files they point at, the plugin
# validator, and the rules each skill exists to hold.

# Session start, dump and close (V1-08). Each assertion pins a rule whose loss would be silent.


def test_close_marks_honestly_and_never_claims_a_pr():
    close = skill_text("close")
    assert "Never propose `fact`." in close
    assert "A `(claude)` line is parked unless the user picks it." in close
    assert "It is never parked." in close
    assert "Promoted on a nod" in close
    assert "Never say a PR exists unless `gh` printed its URL." in CLOSE_SKILL  # the hard stop
    assert "Do not open a PR for a branch that is not pushed." in CLOSE_SKILL
    assert "`org/team`" in prbody.__doc__ and "the lead's own\n  handle is dropped" in prbody.__doc__


def test_close_finds_the_open_session_through_session_open():
    close = skill_text("close")
    assert "vela session open --switch" in close and "--id <the one they picked>" in close


def test_close_parks_every_claude_origin_and_never_decides_its_unknowns():
    close = skill_text("close")
    assert "including `(claude, from <name>)`" in close
    assert "kept as an UNK with an owner and an ask-by date, or dropped with a reason" in close
    assert "Claude never decides it alone" in close and "This rule wins over the park default" in close
    assert "A person's `wild` line is parked, never dropped." in close
    assert "(\"Kept on Claude's suggestion (check these)\", f.kept_on_claude, None)" in read("plugin", "lib", "vela", "prbody.py")
    assert "vela next-id <its prefix>" in close


def test_close_pr_body_reviewers_and_staging():
    assert "Decisions the owner hasn't heard read back" in prbody.__doc__
    assert "gh api user" not in CLOSE_22A and "If nobody remains, leave out" not in CLOSE_22A
    assert "git add -A" not in CLOSE and "vela close finish" in CLOSE_SKILL  # only the CLI stages


def test_close_keeps_the_grill_mark_and_names_a_nod():
    close = skill_text("close")
    assert "keeps its mark" in close and "Promoted on a nod" in close


# discover and shape (V1-11). There is no probe skill: unknowns are offered at start and in MODES.md.


def test_close_never_stages_the_inbox():
    assert "never stages the inbox" in skill_text("close")  # close stage owns it (tests/test_guard.py)


def test_close_fix_round_after_shape():
    close = skill_text("close")
    assert "never an `inkling`" in close and "`**Options considered:**` bullet" in close
    assert "grill to confirm" in close and "GATE-2" in close
    assert "Discover already wrote its facts" in close


def test_close_leaves_the_marks_discover_and_boundary_wrote():
    close = skill_text("close")
    assert "a Discover already marked `(fact)`, or a Boundary, Requirements, Allocate or Releases session already marked `(assumption)`, keeps its mark" in close


# house voice (V1-09): close now drafts prose through it, and only through it.


def test_close_drafts_prose_through_house_voice():
    close = skill_text("close")
    assert "Read `${CLAUDE_PLUGIN_ROOT}/skills/house-voice/SKILL.md` and follow it" in close
    assert "draft: prose for <id>" in close
    assert "Prose to draft" not in close


# epics (V1-17): the check finds the frontier, only the lead's confirmation decides, the gate closes.


def test_close_knows_an_epic_owes_its_summary():
    assert "owes its summary" in skill_text("close")


def test_close_still_adds_changes_rows_for_every_epic():
    assert "Still add the `## Changes` rows for every epic" in skill_text("close")


# tech-design-grill vault mode (V1-18): read the slice, link back by ID and commit, never copy vault text.


def test_close_knows_boundary_already_wrote_its_pages():
    assert "Boundary already wrote its app, contract and runtime pages" in skill_text("close")


def test_close_turns_a_waits_on_capture_into_unknown_rows():
    close = skill_text("close")
    assert "A capture `waits on UNK-nnn: <IDs>` makes each ID's row `unknown`" in close and "changed in place" in close


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
    text = skill_text("close")
    assert "A page has one opening: the one you rewrite replaces the old one, and you never write a new opening beside it." in text
    assert "draw W371; keep one and fold what the others add under a heading." in text
    assert "W363, W365, W368 and W371" in text


# --- From tests/test_v3_final_fixes.py: The v3 final fix wave.

# ------------------------------------------------------------------ 2. a yes to an existence question is one flow


def test_close_gives_a_typed_capture_one_mark_and_writes_the_existence_row():
    close = skill_text("close")
    marks = close.split("## 2. Mark every capture", 1)[1].split("## 3.", 1)[0]
    assert "Any other capture whose words start with a copy ID or a finding ID is kept as its ledger row" in marks
    assert "It gets one mark, to the subject" in marks
    typing = close.split("### Type the subjects Dump named", 1)[1].split("### The question ledger", 1)[0]
    for rule in ("`answered`, `item:` linking the new subject", "first-hand", "the row is `unknown`",
                 "write no second row"):
        assert rule in typing, rule
    assert "give each copy a capture answers its row below" not in close
    assert "write its row below for each copy a capture answers" in typing


def test_close_allocates_ids_before_it_writes_the_marks():
    close = skill_text("close")
    two = close.split("## 2. Mark every capture", 1)[1].split("## 3.", 1)[0]
    assert "Write each mark into the line" not in two
    three = close.split("## 3. Write the promoted items", 1)[1].split("## 4.", 1)[0]
    assert three.index("Write each mark into the line") > three.index("### Subjects, the question ledger and catalog gaps")
    assert "### Gaps the catalog missed" in skill_text("close")  # the ledger part, read before the marks are written


# ------------------------------------------------------------------ W809 and W804 reach the lead; W807 is described as it is


def test_close_lists_w809_and_w804_to_the_lead():
    six = section(CLOSE_SKILL, "## 6. Bring in main and check", "## 7.")
    for said in ("W809", "W804", "offer to type the subject", "fix the row", "Never delete it without a yes",
                 "vela check --for-lead"):
        assert said in six, said


# --- From tests/test_voice_review.py: The voice review at close: a fresh-context agent flags paragraphs, the drafter
# rewrites each once, and voicecheck keeps every fact the draft carried.


def test_close_dispatches_a_fresh_reviewer_and_never_reviews_itself():
    close = close_text()
    assert "Dispatch the `vela:voice-reviewer` subagent with the Agent tool" in close
    assert "everything in `${CLAUDE_PLUGIN_ROOT}/agents/voice-reviewer.md` after the frontmatter" in close
    assert "Never review the drafts yourself in this conversation." in close
    assert '"**Voice review:** not run: <the reason>"' in close


def test_close_rewrites_once_and_keeps_the_draft_when_a_fact_moves():
    close = close_text()
    assert "Rewrite each paragraph the reviewer flags once" in close
    assert "Do not send the rewrite back for review." in close
    assert "Then commit the rewrites that passed with the message `draft: voice rewrite for <id>`" in close
    assert "run `git restore -- <page>`" in close and "keeps its earlier draft whole" in close
    assert "Run it for no other file." in close
    assert "Never commit a rewrite voicecheck could not check." in close


def test_close_covers_the_empty_broken_and_meddling_reviewer():
    close = close_text()
    assert "you must not change any file, and you must report any file you changed" in close
    assert "If the output differs from step 1 of this part, the reviewer changed a file: stop and show the user." in close
    assert "returned anything but the table, treat the review as not run" in close
    assert "If it flagged no paragraph, skip steps 4 and 5 of this part" in close
    for kind in ("wikilink", "code span", "date", "ID", "number (with its units or currency)", "table cell",
                 "version", "frontmatter line", "negation"):
        assert kind in close


@pytest.mark.skipif(shutil.which("git") is None, reason="git is not installed")
def test_a_rewrite_that_lost_a_number_is_restored_and_other_work_survives(tmp_path):
    draft_repo(tmp_path)
    (tmp_path / "page.md").write_text("Booking keeps the seat for ten minutes while the customer pays.\n", encoding="utf-8")
    assert close_voicecheck(tmp_path, "page.md") == 1
    assert (tmp_path / "page.md").read_text(encoding="utf-8") == DRAFT
    assert "added by step 3" in (tmp_path / "record.md").read_text(encoding="utf-8")


@pytest.mark.skipif(shutil.which("git") is None, reason="git is not installed")
def test_a_step_three_edit_on_a_rewritten_page_survives_the_restore(tmp_path):
    draft_repo(tmp_path)
    page = tmp_path / "page.md"
    page.write_text(DRAFT + "- capture mark from step 3\n", encoding="utf-8")
    (tmp_path / "record.md").write_text("Changes\n| staged by step 2 |\n", encoding="utf-8")
    git_in(tmp_path, "add", "record.md")
    guard = guard_command().replace("<page>", "page.md").replace("<id>", "s")
    subprocess.run(["bash", "-c", guard], cwd=tmp_path, check=True, env={**os.environ, **GIT_IDENTITY}, timeout=60)
    assert git_in(tmp_path, "log", "-1", "--format=%s").strip() == "Checkpoint s"
    assert git_in(tmp_path, "show", "--name-only", "--format=", "HEAD").split() == ["page.md"]
    assert git_in(tmp_path, "status", "--porcelain", "record.md").startswith("M")
    page.write_text("Booking keeps the seat for ten minutes while the customer pays.\n- capture mark from step 3\n", encoding="utf-8")
    assert close_voicecheck(tmp_path, "page.md") == 1
    assert page.read_text(encoding="utf-8") == DRAFT + "- capture mark from step 3\n"


@pytest.mark.skipif(shutil.which("git") is None, reason="git is not installed")
def test_a_rewrite_voicecheck_could_not_read_is_restored(tmp_path):
    draft_repo(tmp_path)
    (tmp_path / "page.md").write_bytes(b"\xff\xfe not text\n")
    assert close_voicecheck(tmp_path, "page.md") == 2
    assert (tmp_path / "page.md").read_text(encoding="utf-8") == DRAFT
    assert "added by step 3" in (tmp_path / "record.md").read_text(encoding="utf-8")


@pytest.mark.skipif(shutil.which("git") is None, reason="git is not installed")
def test_a_clean_rewrite_is_committed_and_other_work_stays_uncommitted(tmp_path):
    draft_repo(tmp_path)
    rewrite = "Booking holds the seat for 10 minutes while the customer pays on Tidepay's page.\n"
    (tmp_path / "page.md").write_text(rewrite, encoding="utf-8")
    assert close_voicecheck(tmp_path, "page.md") == 0
    assert git_in(tmp_path, "log", "-1", "--format=%s").strip() == "draft: voice rewrite for s"
    assert git_in(tmp_path, "status", "--porcelain").strip() == "M record.md"


# Harvest: the owner's edits to merged drafts become examples, on the owner's yes only.


def test_harvest_is_owner_only():
    close = close_text()
    assert "Only the vault's owner harvests, and only their own edits." in close
    assert "The owner is the `author` of the `source: owner` examples" in close
    assert 'say "Harvest is owner-only."' in close
    assert "Did you write this change?" in close
    assert "The owner's answer is the check that the edit is theirs." in close


def test_harvest_finds_drafts_through_the_merged_prs():
    close = close_text()
    assert 'gh pr list --state merged --search "head:session/"' in close
    assert "git fetch origin pull/<number>/head" in close
    assert "--author @me" in close and "--limit 10" in close
    assert "gh pr view <number> --json commits" in close
    assert 'say "gh could not list merged PRs, so nothing was harvested."' in close


def test_harvest_saves_word_for_word_on_an_explicit_yes():
    close = close_text()
    assert "Save it only on an explicit yes." in close
    assert "Save the merged paragraph word for word" in close
    assert "source: owner-edit" in close and "harvested_from: '<full hash of the baseline draft commit>'" in close


def test_harvest_keeps_five_active_and_retires_the_seed_first():
    close = close_text()
    assert f"A type keeps at most {schema.VOICE_ACTIVE_MAX} active examples." in close
    assert "the oldest `public-seed` example first, then the oldest `owner-edit`, then the oldest `owner`" in close
    assert "never delete an example" in close


# The two folders and the gh failure rule, added after the brief was written.


def test_harvest_asks_committed_or_local_and_recommends_local_for_employer_text():
    harvest = harvest_text()
    assert "`voice/examples/<type>/`" in harvest and "`voice/local/<type>/`" in harvest
    assert "If the owner's employer owns the text, or the owner is not sure, recommend local only." in harvest
    assert "May this text be committed to the vault?" in harvest
    assert "no step below stages it" in harvest
    assert "never stages the inbox, `voice/local/` or `voice/corpus/`" in close_text()


def test_harvest_reads_both_folders_and_retires_seeds_only_within_a_folder():
    harvest = harvest_text()
    assert "`voice/examples/` and `voice/local/`" in harvest
    assert "in either folder" in harvest
    assert "A local example never retires a committed seed" in harvest
    assert "in a local-only save only local examples may retire" in harvest


def test_harvest_writes_the_paragraph_with_a_quoted_heredoc_and_a_cmp_check():
    harvest = harvest_text()
    assert "sed -n '<first>,<last>p'" in harvest
    assert "cat .vela/harvest/<pr>-<n>.txt >> <file>" in harvest
    assert "| cmp - .vela/harvest/<pr>-<n>.txt" in harvest
    assert "do not repair the file" in harvest


def test_every_gh_step_in_harvest_says_it_failed_and_never_reads_failure_as_no_edits():
    harvest = harvest_text()
    assert 'Never read a failure as "no edits found".' in harvest
    assert 'say "gh could not read your handle, so nothing was harvested."' in harvest
    assert 'say "gh could not list merged PRs, so nothing was harvested."' in harvest
    assert 'say "gh could not read the commits of PR <number>, so its edits were not checked."' in harvest
    assert 'say "git could not fetch PR <number>, so it was not checked."' in harvest
    assert 'Say "no edits found" only when every merged PR was checked.' in harvest
    for call in ("`gh api user", "`gh pr list", "`gh pr view", "`git fetch origin pull"):
        line = next(l for l in harvest.splitlines() if call in l)
        assert "fails" in line or "could not" in line, call


# Fix round 1: order, jump targets, the PR's own commits, the retire rule, the cap, quoting, the limit.


def test_the_rewrite_commit_sentence_ends_voice_review_before_harvest():
    close = close_text()
    sentence = "Then commit the rewrites that passed with the message `draft: voice rewrite for <id>`"
    assert close.count(sentence) == 1
    review_file = (PLUGIN / "skills" / "close" / "VOICE-REVIEW.md").read_text(encoding="utf-8")
    assert review_file.rstrip().endswith(sentence + ", staging each page by exact path.")  # the last thing the review does
    assert close.index("### Voice review") < close.index("### Harvest the owner's edits") < close.index("## 5. Read back decided wording")


def test_no_jump_says_a_bare_step_5_and_a_skipped_review_still_runs_harvest():
    close = close_text()
    assert "go on to step 5" not in close
    review = (PLUGIN / "skills" / "close" / "VOICE-REVIEW.md").read_text(encoding="utf-8")
    assert review.count('go on to the part "Harvest the owner\'s edits"') >= 3
    harvest = harvest_text()
    exits = re.findall(r"go on to ([^.]*)\.", harvest)
    assert exits and all(e == "section 5, Read back decided wording" for e in exits)
    assert "Harvest does not depend on the voice review: run it even when the review did not run." in harvest


def test_harvest_builds_on_the_prs_own_commits_and_reads_the_merged_text_from_its_head():
    harvest = harvest_text()
    assert harvest.count("origin/main") == 1 and "never from `origin/main`" in harvest
    view = harvest.index("gh pr view <number> --json commits")
    fetch = harvest.index("git fetch origin pull/<number>/head")
    merged = harvest.index("git show FETCH_HEAD:<page>")
    assert view < merged and fetch < merged
    assert "both `draft: prose for` and `draft: voice rewrite for`" in harvest
    assert "the baseline is the last draft commit in the PR's list that touched it" in harvest
    assert "Skip the PR if there are none." in harvest
    assert "`Co-Authored-By: Claude` trailer or a `Claude-Session:` trailer" in harvest
    assert "the owner did not edit the page, so skip it" in harvest


def test_the_owner_is_asked_who_wrote_the_change_before_being_asked_to_save():
    harvest = harvest_text()
    assert harvest.index("Did you write this change?") < harvest.index("Save the merged paragraph as a <type> example?")
    assert "If it is no, or still unclear, record a decline" in harvest
    assert "and do not ask the save question" in harvest


def test_harvest_dedupes_per_paragraph_and_records_declines_in_the_session_record():
    harvest = harvest_text()
    assert "Skip a paragraph that is already saved or declined" in harvest
    assert "the same `page`, a `harvested_from` equal to the baseline's full hash, and a body equal to the merged paragraph" in harvest
    assert "`Harvest declined: PR <number> <page> <hash>`" in harvest
    assert "grep -rh '^Harvest declined: ' sessions/" in harvest


def test_two_owner_examples_in_a_folder_retire_that_folders_seed():
    harvest = harvest_text()
    assert "2 or more, retire that folder's active `public-seed` examples of the type" in harvest
    assert "as `/vela:voice-seed` does. A local save retires only local seeds." in harvest


def test_a_local_save_the_cap_blocks_stores_nothing_and_says_so():
    harvest = harvest_text()
    assert "If the cap blocks a local-only save, store nothing" in harvest
    assert "The cap blocks a local save: <type> holds 5 active examples" in harvest


def test_harvest_quotes_free_values_and_rechecks_the_frontmatter():
    harvest = harvest_text()
    assert "page: '<page path>'" in harvest
    assert "harvested_from: '<full hash of the baseline draft commit>'" in harvest
    assert harvest.index("| cmp - .vela/harvest/<pr>-<n>.txt") < harvest.index("confirm it parses as YAML")


def test_harvest_says_when_the_pr_limit_hid_older_prs():
    harvest = harvest_text()
    assert "If it returns 10 PRs, say" in harvest
    assert "--limit 20" not in harvest
    assert "older PRs were not checked." in harvest


# Fix round 2.


def test_the_skill_names_the_headline_and_body_fields_and_drops_authors():
    harvest = harvest_text()
    assert "`oid`, `messageHeadline` and `messageBody`" in harvest
    assert "`authors`" not in harvest
    assert "`messageHeadline` starts with `draft: `, `Checkpoint ` or `Close session `" in harvest
    assert "each one whose `messageBody` carries a `Co-Authored-By: Claude` trailer or a `Claude-Session:` trailer" in harvest
    assert "git diff -U0 <oid>^ <oid> -- <page>" in harvest
    assert "Never compare the baseline with the tip" in harvest


@pytest.mark.skipif(shutil.which("shasum") is None, reason="shasum is not installed")
def test_the_decline_hash_command_is_reproducible(tmp_path):
    import hashlib
    paragraph = "Line one.\nLine two, with a tab\tand text.\n"
    harvest = harvest_text()
    assert "shasum < .vela/harvest/<pr>-<n>.txt | cut -c1-12" in harvest
    assert "rm -f .vela/harvest/<pr>-<n>.txt" in harvest
    (tmp_path / "p.txt").write_text(paragraph, encoding="utf-8")
    out = subprocess.run(["bash", "-c", "shasum < p.txt | cut -c1-12"], cwd=tmp_path, capture_output=True, text=True,
                         check=True, timeout=60).stdout.strip()
    assert out == hashlib.sha1(paragraph.encode()).hexdigest()[:12]


def test_a_decline_is_a_bare_line_under_captures_and_conventions_say_so():
    harvest = harvest_text()
    assert "insert one bare line `Harvest declined: PR <number> <page> <hash>` directly under `## Captures`" in harvest
    assert "It is never a bullet." in harvest
    sentence = "A harvest decline is one bare line, `Harvest declined: PR <n> <page> <hash>`, directly under `## Captures`, never a bullet."
    for path in ("template", "tests/stub-conventions", "examples/unified-booking"):
        assert sentence in (REPO / path / "CONVENTIONS.md").read_text(encoding="utf-8")


def test_the_full_hash_is_stored_and_a_no_asks_no_save_question():
    harvest = harvest_text()
    assert "harvested_from: '<full hash of the baseline draft commit>'" in harvest
    assert "short hash" not in harvest
    no = harvest.index("do not ask the save question")
    assert harvest.index("Did you write this change?") < no < harvest.index("Save the merged paragraph as a <type> example?")


def test_retirement_runs_only_after_the_cmp_check_confirms_the_save():
    harvest = harvest_text()
    assert "and change no example yet" in harvest
    assert harvest.index("| cmp - .vela/harvest/<pr>-<n>.txt") < harvest.index("Only now apply the retirements you planned in step 7")
    assert harvest.index("Plan the room before you save") < harvest.index("| cmp - .vela/harvest/<pr>-<n>.txt")


def test_step_references_name_their_section():
    close = close_text()
    assert "See section 3." in close and "See step 3." not in close
    assert "from sections 2 and 3," in close and "step 2 or 3" not in close
    assert "the work that section 7 stages" in close and "that step 7 stages" not in close


# I1: Claude Code's Bash keeps no shell variable between calls, so harvest's temp file has a
# fixed path every later call can name, and each block must run on its own in a fresh shell.


def test_harvest_names_its_temp_file_and_keeps_no_shell_variable():
    harvest = harvest_text()
    assert "$tmp" not in harvest and "mktemp" not in harvest
    assert "mkdir -p .vela/harvest" in harvest
    assert "`<n>` is the paragraph's order" in harvest
    assert "rm -rf .vela/harvest" in harvest


def test_harvest_step_four_and_step_eight_each_run_in_a_fresh_shell(pr_repo):
    repo = pr_repo
    (repo / ".gitignore").write_text(".vela/\n", encoding="utf-8")  # as template/.gitignore does
    run_git(repo, "add", ".gitignore")
    page = "04-solution-strategy.md"
    (repo / page).write_text("# Strategy\n\nFirst line of the owner's paragraph.\nIt’s kept   word for word.\n\nTail.\n",
                             encoding="utf-8")
    run_git(repo, "add", page)
    run_git(repo, "-c", "user.name=T", "-c", "user.email=t@example.invalid", "-c", "commit.gpgsign=false", "commit", "-qm", "merged")
    run_git(repo, "fetch", "-q", ".", "HEAD")
    slots = {"page": page, "first": "3", "last": "4", "pr": "42", "n": "1"}
    extracted = fresh_shell(repo, harvest_block("mkdir -p .vela/harvest"), **slots)
    assert extracted.returncode == 0, extracted.stderr
    stored = repo / ".vela" / "harvest" / "42-1.txt"
    assert stored.read_text(encoding="utf-8") == "First line of the owner's paragraph.\nIt’s kept   word for word.\n"
    assert re.fullmatch(r"[0-9a-f]{12}\n", extracted.stdout), extracted.stdout
    assert run_git(repo, "status", "--porcelain") == "", "the temp file must not dirty the working tree"

    example = repo / "voice" / "examples" / "decision" / "VX-decision-004.md"
    example.parent.mkdir(parents=True)
    example.write_text("---\nid: VX-decision-004\nstate: active\n---\n\n", encoding="utf-8")
    saved = fresh_shell(repo, harvest_block("cat .vela/harvest/<pr>-<n>.txt >> <file>"), file=str(example), **slots)
    assert saved.returncode == 0, saved.stderr
    assert example.read_text(encoding="utf-8").endswith("\n\nFirst line of the owner's paragraph.\nIt’s kept   word for word.\n")
    assert not stored.exists(), "step 8 removes the temp file on every exit"


def test_harvest_step_eight_fails_on_a_changed_body_and_still_removes_the_file(pr_repo):
    repo = pr_repo
    stored = repo / ".vela" / "harvest" / "7-2.txt"
    stored.parent.mkdir(parents=True)
    stored.write_text("The paragraph.\n", encoding="utf-8")
    example = repo / "VX-decision-001.md"
    example.write_text("---\nid: VX-decision-001\n---\n\nSomething already here.\n", encoding="utf-8")
    saved = fresh_shell(repo, harvest_block("cat .vela/harvest/<pr>-<n>.txt >> <file>"), file=str(example), pr="7", n="2")
    assert saved.returncode != 0
    assert not stored.exists()


def test_close_voicecheck_block_is_self_contained():
    block = recipe_commands()
    assert block.startswith("tmp=$(mktemp)\n") and 'rm -f "$tmp"; (exit $code)' in block


# --- From tests/test_voicecheck.py: vela voicecheck: a voice rewrite may change words, never the IDs, numbers, dates,
# wikilinks, code spans or table cells they carry.

# Through the CLI.


def test_close_and_the_reviewer_carry_the_redundant_route():
    root = REPO / "plugin"
    close = skill_text("close")
    reviewer = (root / "agents" / "voice-reviewer.md").read_text(encoding="utf-8")
    assert '--redundant "<sentence>"' in close and "named by the reviewer" in close or "the reviewer named as redundant" in close
    assert "Redundant sentences" in reviewer and "Redundant sentence (exact)" in reviewer


# --- From tests/test_voicescore.py: vela voicescore: an optional style-embedding reading of each prose paragraph
# against the owner's own range.

# --- the close skill ------------------------------------------------------------------------


def test_close_scores_drafts_only_when_available_and_never_gates_on_it():
    part = voice_review()
    assert "vela voicescore" in part
    assert "at least 5 active `owner` and `owner-edit` examples" in part
    assert "information, not a gate" in part
    assert "Never block, rewrite or skip a paragraph because of its voicescore" in part
    assert '"voicescore: not run (<reason>)"' in part
    assert "voicescore: 3 of 4 paragraphs inside your range; ¶2 outside (p96)" in part


def test_close_still_runs_the_voicecheck_fact_guard_unchanged():
    part = voice_review()
    assert 'python3 ${CLAUDE_PLUGIN_ROOT}/scripts/vela voicecheck "$tmp" <page>; code=$?; rm -f "$tmp"; (exit $code)' in part
    assert "Never commit a rewrite voicecheck could not check." in part


def test_the_pr_body_reports_voicescore_in_the_voice_review_line():
    assert "voicescore: not run (not asked for)" in read("plugin", "lib", "vela", "prbody.py")
    assert "- **Voice review:**" not in CLOSE_22A




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
