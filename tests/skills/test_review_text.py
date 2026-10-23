"""What the review reference says, pinned in one place (overhaul plan Task 3; rewritten by Task 22j).

Every test that pins this text lives here, so the rewrite that changes it edits this file and no other skill's.
Task 22j moved REVIEW sections 1 and 2 (numbering, the commit, the page list, the owed questions, which areas to skip,
the packet files) into `vela reviewers prepare`, and "never twice" into `vela questions --digest --session`. The
re-run file was folded into one paragraph naming `--rerun N --areas`.
"""
import re

from conftest import REPO

PLUGIN = REPO / "plugin"
REVIEW = (PLUGIN / "references" / "REVIEW.md").read_text(encoding="utf-8")


def section(heading):
    """The text under a `## heading` up to the next `## `."""
    return REVIEW.split(f"## {heading}\n", 1)[1].split("\n## ", 1)[0]


LEAD_CODE = re.compile(r"\b[EW]\d{3}\b|GATE-\d|\^c\d|\bQ-[A-Z]{3}-\d{2}|\bF\d\.\d+\b|\b(?:FIN|DAT|PTN|REG|OPS)\b|vela ")
FIXTURE = REPO / "examples" / "unified-booking"


def test_review_prepares_the_checkpoint_with_one_command():
    prep = section("1 and 2. Prepare the checkpoint")
    assert '`vela reviewers prepare --checkpoint "<the checkpoint and its focus>" --focus' in prep
    assert "`.vela/review/<n>/<AREA>.md`" in prep  # where the packets live (schedule: REVIEW must say so)
    assert "commits the stub and the changed pages" not in prep and "clears the findings folder" not in prep  # reviewers.py docstring owns it


def test_review_spells_the_command_boundary_no_longer_does():
    assert "run `vela reviewers prepare --checkpoint" in REVIEW  # boundary names its checkpoint and focus only


def test_review_sections_one_and_two_lost_their_recipes():
    """Rule deletion: `reviewers prepare` numbers, commits, lists pages, saves the owed questions and skips areas."""
    for recipe in ("1 plus the number of `### ` headings", "`Checkpoint <session id> <n>`",
                   "git diff --name-only --diff-filter=d", 'grep -n "^## Question ledger"', "`areas:` block",
                   "`pending` field is `true`", "rm -rf .vela/findings", "mkdir -p .vela/findings",
                   "-questions/<AREA>.json", "subject_page", "git diff -U0", "## Numbering", "## Reader copy"):
        assert recipe not in REVIEW, recipe


def test_the_rerun_file_is_gone_and_review_names_the_flags():
    assert not (PLUGIN / "references" / "REVIEW-RERUN.md").exists()
    for path in [*PLUGIN.rglob("*.md"), *PLUGIN.rglob("*.py"), *PLUGIN.rglob("*.json")]:
        assert "REVIEW-RERUN" not in path.read_text(encoding="utf-8"), path
    assert "--rerun 1 --areas FIN,REG" in REVIEW and "earlier finding IDs never change" in REVIEW


def test_review_dispatches_one_fresh_reviewer_per_area_with_a_fallback():
    dispatch = section("3. One reviewer per area")
    assert "`vela:area-reviewer`" in dispatch and "all five in one message" in dispatch
    assert "general-purpose subagent" in dispatch and "${CLAUDE_PLUGIN_ROOT}/agents/area-reviewer.md" in dispatch
    assert "Give no conversation" in dispatch and "its packet's text, word for word" in dispatch
    assert 'If you changed a file, return `{"area": "<your area code>", "error": "changed <path>"}` instead.' in dispatch
    assert "Never review the pages yourself in this conversation." in dispatch
    assert "Never send a placeholder" in dispatch
    assert "model: sonnet" in dispatch and dispatch.count("sonnet") >= 2  # the subagent and the fallback


def test_review_watches_for_a_reviewer_that_changed_a_file():
    dispatch = section("3. One reviewer per area")
    assert "baseline" in dispatch and "compare it with the baseline" in dispatch and "shasum" in dispatch


def test_review_merges_in_code_and_never_reads_a_failure_as_clean():
    merge = section("4. Merge")
    assert "vela findings merge .vela/findings/<session id>/<n> --changed <paths>" in merge
    assert '{"area": "<AREA>", "error": "<what happened>"}' in REVIEW
    assert "Never write an empty findings list for a reviewer that did not finish" in REVIEW
    assert "An area that did not run is never reported as clean" in merge
    assert "- **Coverage:** <the merge's coverage line" in merge
    assert "merge failed: <error>" in merge and "R-` id" not in merge and "is dropped: it was owed" not in merge  # reviews.merge drops them
    assert "replace each inner straight `\"` with `”`" in merge
    assert "file name without .md" in merge


def test_the_digest_is_the_session_command_and_never_twice_is_its_bookkeeping():
    digest = section("5. The digest")
    assert "`vela questions --digest --session <session id> --for-lead`" in digest
    assert "At most three questions" in digest and "Once per session" in digest and "Never twice, never ruled out" not in digest  # the command keeps count
    assert "first five" not in digest and "next five" not in digest
    assert "A turn of 50 questions is a dump" in digest
    assert "Never paste a reviewer's reply, or the findings JSON, into the conversation" in digest
    assert "no question is dropped" in REVIEW.lower() or "Nothing is dropped" in digest


def test_the_digest_tail_offers_the_rest_by_subject_not_by_command():
    """Voice audit S11: the tail read "List them: vela questions --open --digest --all --area FIN" to the lead."""
    digest = section("5. The digest")
    assert "List them: vela questions" not in REVIEW and "more (normal)" not in REVIEW
    assert '"Six more are about cost and four about who sees client data; want the next three?"' in digest
    assert "No copy ID, finding ID, area code, severity or command in what the lead hears" in digest


def test_the_digest_example_carries_no_code():
    example = REVIEW.split("For example, instead of", 1)[1].split("A turn of 50", 1)[0]
    spoken = "\n".join(line for line in example.splitlines() if line.startswith(">"))
    assert spoken and not LEAD_CODE.search(spoken)


def test_a_review_is_about_what_this_session_changed_and_a_group_can_wait_on_one_unknown():
    assert "--changed <paths>" in REVIEW
    assert "waits on UNK-050: Q-DAT-02@APP-account-link-service, R-OPS-12, F2.4" in REVIEW


def test_review_types_a_yes_at_close():
    assert "`type at close: PTY` or `type at close: SV`" in REVIEW


def test_the_short_digest_is_described_in_conventions():
    conventions = (FIXTURE / "CONVENTIONS.md").read_text(encoding="utf-8")
    assert "--all" in conventions and "counted by area" in conventions


def test_the_reviewer_refuses_a_placeholder():
    agent = (PLUGIN / "agents" / "area-reviewer.md").read_text(encoding="utf-8")
    assert "a placeholder" in agent and "no questions file" in agent


def test_review_stays_trimmed():
    assert len(REVIEW.split()) <= 1510  # was 1702; prepare/merge mechanics live in the commands (now 1462)
