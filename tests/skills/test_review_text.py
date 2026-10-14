"""What the review reference says, pinned in one place (overhaul plan Task 3).

Every test that pins this text lives here, so the rewrite that changes it edits this file and no other skill's.
Each section is headed by the file it came from and that file's reason.
"""
import re

from conftest import REPO

PLUGIN = REPO / "plugin"


def text(rel):
    return (PLUGIN / rel).read_text(encoding="utf-8")


def section(body, heading):
    """The text under a `## heading` up to the next `## `."""
    return body.split(f"## {heading}\n", 1)[1].split("\n## ", 1)[0]


LEAD_CODE = re.compile(r"\b[EW]\d{3}\b|GATE-\d|\^c\d|\bQ-[A-Z]{3}-\d{2}|\bF\d\.\d+\b")


FIXTURE = REPO / "examples" / "unified-booking"


# --- From tests/test_reviewers.py: The focused reviewers and the review checkpoints in the session skills.

# ------------------------------------------------------------------ the checkpoint procedure


def test_review_dispatches_one_fresh_reviewer_per_area_with_a_fallback():
    review = text("references/REVIEW.md")
    assert "`vela:area-reviewer`" in review and "all five in one message" in review
    assert "general-purpose subagent" in review and "${CLAUDE_PLUGIN_ROOT}/agents/area-reviewer.md" in review
    assert "Give no conversation" in review
    assert 'If you changed a file, return `{"area": "<your area code>", "error": "changed <path>"}` instead.' in review
    assert "report any file you changed" not in review
    assert "Never review the pages yourself in this conversation." in review


def test_review_merges_in_code_and_never_reads_a_failure_as_clean():
    review = text("references/REVIEW.md")
    assert "vela findings merge .vela/findings/<session id>/<n>" in review
    assert '{"area": "<AREA>", "error": "<what happened>"}' in review
    assert "Never write an empty findings list for a reviewer that did not finish" in review
    assert "An area that did not run is never reported as clean." in review
    assert "- **Coverage:** <the merge's coverage line" in review


def test_review_tells_the_session_to_swap_inner_quotes_like_the_merge():
    review = text("references/REVIEW.md")
    assert "replace each inner straight `\"` with `”`" in review


def test_review_clears_stale_findings_and_numbers_from_the_record():
    review = text("references/REVIEW.md")
    assert "1 plus the number of `### ` headings under `## Reviews`" in review
    assert review.count("rm -rf .vela/findings/<session id>/<n>") == 2
    assert review.index("rm -rf .vela/findings/<session id>/<n> .vela/findings/<session id>/<n>-questions\nmkdir") < review.index("Save each reply")
    assert "no variables" in review


def test_review_defines_a_rerun_as_a_new_checkpoint_with_areas():
    assert "REVIEW-RERUN.md" in text("references/REVIEW.md")  # read only when an area is run again
    review = text("references/REVIEW-RERUN.md")
    assert "Re-run of checkpoint <n>: <areas>" in review
    assert "--areas FIN,REG" in review and "F<n+1>.1" in review
    assert "the ids of earlier checkpoints never change" in review


def test_review_covers_the_minor_gaps():
    review = text("references/REVIEW.md")
    assert "`areas:` block" in review and "`pending` field is `true`" in review
    assert "file name without .md" in review and "basename" not in review
    assert "baseline" in review and "compare it with the baseline" in review
    assert "skip the `## Reviews` section" in review.replace("Skip", "skip")
    assert "`Checkpoint <session id> <n>`" in review
    assert "merge failed: <error>" in review
    assert "R-` id" in review


def test_review_puts_no_cap_on_the_digest():
    review = text("references/REVIEW.md")
    assert "vela questions --open --digest" in review
    # S26: the lead is shown at most three questions, once; nothing is dropped from the ledger.
    assert "no question is dropped, only held back from the conversation" in review
    assert "At most three questions" in review and "Once per session" in review


# ------------------------------------------------------------------ a close, run by its rules, on real records
# The helpers below apply close's rules to session records as a session leaves them, unmarked. What
# the lead says at close (facts, states, beliefs) is the only other input. Each row, mark, subject and
# unknown is derived from those, never written by hand, so the test fails if the rules produce rows
# that check refuses.


def test_review_hands_each_reviewer_a_real_questions_file_and_the_reviewer_refuses_a_placeholder():
    review, agent = text("references/REVIEW.md"), text("agents/area-reviewer.md")
    assert "--json > .vela/findings/<session id>/<n>-questions/<AREA>.json" in review
    assert "`Questions file: .vela/findings/<session id>/<n>-questions/<AREA>.json`" in review
    assert "Never send a placeholder" in review
    assert review.index("-questions/<AREA>.json`. They sit") < review.index("Dispatch the `vela:area-reviewer`")
    assert "a placeholder" in agent and "no questions file" in agent


def test_a_review_digest_puts_at_most_five_questions_to_the_lead_in_a_turn_and_never_pastes_findings():
    """S12: the heron run's turn 38 put 89 question marks to the lead, with the reviewers' raw JSON."""
    review = text("references/REVIEW.md")
    assert "At most three questions" in review and "A turn of 50 questions is a dump" in review
    assert "Never paste a reviewer's reply, or the findings JSON, into the conversation" in review
    assert "no question is dropped" in review


# --- From tests/test_session_experience.py: What the skills make a lead go through (docs/research/2026-10-12-session-
# experience-review.md and the friction pass).

# --- S26 and S43: the review digest is small, plain, once


def test_the_digest_puts_at_most_three_plain_questions_once_per_session():
    review = section(text("references/REVIEW.md"), "5. The digest")
    assert "At most three questions" in review and "Once per session" in review
    assert "first five" not in review and "next five" not in review
    assert "Never twice, never ruled out" in review


# --- S27: no rule codes, raw IDs or gate names in what the lead reads


def test_the_digest_example_carries_no_code():
    example = text("references/REVIEW.md").split("For example, instead of", 1)[1].split("A turn of 50", 1)[0]
    spoken = "\n".join(l for l in example.splitlines() if l.startswith(">"))
    assert spoken and not LEAD_CODE.search(spoken)


# --- S36 to S47


def test_a_review_checkpoint_has_a_reader_copy_path():
    review = text("references/REVIEW.md")
    assert "## Reader copy" in review and "shasum" in review


# --- From tests/test_skills.py: The plugin's skills: frontmatter, size, the files they point at, the plugin
# validator, and the rules each skill exists to hold.

# tech-design-grill vault mode (V1-18): read the slice, link back by ID and commit, never copy vault text.


def test_a_review_is_about_what_this_session_changed_and_a_group_can_wait_on_one_unknown():
    review = text("references/REVIEW.md")
    assert "--changed <paths>" in review and "`Changed: <paths>`" in review
    assert "waits on UNK-050: Q-DAT-02@APP-account-link-service, R-OPS-12, F2.4" in review


# --- From tests/test_v3_final_fixes.py: The v3 final fix wave.

# ------------------------------------------------------------------ 2. a yes to an existence question is one flow


def test_review_types_a_yes_at_close():
    review = text("references/REVIEW.md")
    assert "`type at close: PTY` or `type at close: SV`" in review


# --- From tests/test_v3_fixes.py: Four fixes from the v3 full run (2026-10-06-144750-coastal-merger).

# ------------------------------------------------------------------ 1. a checkpoint reviews only the areas in scope


def test_review_md_dispatches_on_that_model_and_skips_areas_out_of_scope():
    text = (PLUGIN / "references" / "REVIEW.md").read_text(encoding="utf-8")
    assert "model: sonnet" in text and text.count("sonnet") >= 2, "the subagent and the general-purpose fallback"
    assert "skipped (nothing in scope)" in text and "--skipped" in text
    assert "## Question ledger" in text, "reviewers read the ledger page only above its ledger section"


# ------------------------------------------------------------------ 2. the digest: consequential lines first, the rest counted


def test_review_md_and_skills_describe_the_short_digest():
    review = (PLUGIN / "references" / "REVIEW.md").read_text(encoding="utf-8")
    section = review.split("## 5. The digest")[1].split("## 6.")[0]
    assert "--all" in section and "more (normal)" in section
    conventions = (FIXTURE / "CONVENTIONS.md").read_text(encoding="utf-8")
    assert "--all" in conventions and "counted by area" in conventions
