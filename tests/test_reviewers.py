"""The focused reviewers and the review checkpoints in the session skills.

Each assertion pins a rule whose loss would be silent: a reviewer that writes, a persona that
creeps back, a sweep kept alongside the checkpoint that replaced it, a cap on questions, or an
area that failed and reads as clean."""
import re

import yaml

from conftest import REPO
from planner import reviews

PLUGIN = REPO / "plugin"


def text(rel):
    return (PLUGIN / rel).read_text(encoding="utf-8")


def frontmatter(rel):
    return yaml.safe_load(text(rel).split("---\n", 2)[1])


# ------------------------------------------------------------------ the agent

def test_the_area_reviewer_reads_and_never_writes():
    meta = frontmatter("agents/area-reviewer.md")
    assert meta["name"] == "area-reviewer"
    assert meta["tools"] == "Read, Grep, Glob"
    assert len(meta["description"]) >= 40


def test_the_area_reviewer_returns_the_fields_the_merge_reads():
    body = text("agents/area-reviewer.md")
    for field in reviews.FIELDS:
        assert f'"{field}":' in body, field
    assert '{"area": "<your area code>", "findings": []}' in body
    assert '{"area": "<your area code>", "error": "<what stopped you>"}' in body
    assert "R-FIN-01" in body and "`pending` is `true`" in body
    assert "skip the `## Reviews` section" in body
    assert "never an empty findings list" in body


def test_the_area_reviewer_covers_the_five_areas_by_label_only():
    body = text("agents/area-reviewer.md")
    for code, label in (("FIN", "Finance and liabilities"), ("DAT", "Data and lawful basis"),
                        ("PTN", "Partners and contracts"), ("REG", "Regulation and liability"),
                        ("OPS", "Operations and people")):
        assert f"| `{code}` {label} |" in body
    lowered = body.lower()
    assert not re.search(r"\bpersonas?\b|\barchetypes?\b|\byou are an?\b", lowered)
    assert "Never read another reviewer's output" in body
    assert "There is no limit." in body


# ------------------------------------------------------------------ the checkpoint procedure

def test_review_dispatches_one_fresh_reviewer_per_area_with_a_fallback():
    review = text("references/REVIEW.md")
    assert "`planner:area-reviewer`" in review and "all five in one message" in review
    assert "general-purpose subagent" in review and ".claude/skills/planner/agents/area-reviewer.md" in review
    assert "Give no conversation" in review
    assert 'If you changed a file, return `{"area": "<your area code>", "error": "changed <path>"}` instead.' in review
    assert "report any file you changed" not in review
    assert "Never review the pages yourself in this conversation." in review


def test_review_merges_in_code_and_never_reads_a_failure_as_clean():
    review = text("references/REVIEW.md")
    assert "planner findings merge .git/planner-findings/<session id>/<n>" in review
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
    assert review.count("rm -rf .git/planner-findings/<session id>/<n>") == 2
    assert review.index("rm -rf .git/planner-findings/<session id>/<n>\nmkdir") < review.index("Save each reply")
    assert "no variables" in review


def test_review_defines_a_rerun_as_a_new_checkpoint_with_areas():
    review = text("references/REVIEW.md")
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
    assert "planner questions --open --digest" in review
    assert "There is no cap." in review and "Never drop a line to keep it short." in review
    assert not re.search(r"\b(?:at most|no more than|up to) (?:\d+|one|two|three|four|five) (?:questions|lines)", review)


def test_a_reviews_section_in_the_documented_form_passes_check(tmp_path):
    import shutil

    from conftest import check, findings
    vault = tmp_path / "ub"
    shutil.copytree(REPO / "examples" / "unified-booking", vault)
    record = vault / "sessions" / "2026-11-19-owed-questions.md"
    text = record.read_text(encoding="utf-8").replace("## Changes", """## Reviews

### 1. after the read-back, 2026-11-19

- **Coverage:** FIN found 1; DAT checked, none; PTN checked, none; REG did not run (no findings file); OPS checked, none
- **Dropped:** none

| Finding | Area | Severity | Copy | Question | Quote |
|---|---|---|---|---|---|
| F1.1 | FIN | normal | new | Who tells the loyalty scheme \\| and when? | "because points are earned at reservation" in [[04a-capability-delta]] |

## Changes""")
    record.write_text(text, encoding="utf-8")
    code, out = check(vault, "2026-11-20")
    assert code == 0 and findings(out) == [], out


# ------------------------------------------------------------------ the checkpoints replace the sweeps

def test_dump_runs_the_checkpoint_after_the_pre_mortem_and_the_sweep_is_gone():
    dump = text("skills/dump/SKILL.md")
    assert "references/REVIEW.md" in dump and '"after the pre-mortem"' in dump
    assert "concern sweep" not in dump
    assert "nobody has named yet" not in dump
    assert "to fetch:" in dump


def test_discover_runs_the_checkpoint_after_the_read_back_and_the_implications_list_is_gone():
    discover = text("skills/discover/SKILL.md")
    assert "references/REVIEW.md" in discover and '"after the read-back"' in discover
    assert "What these sources imply" not in discover
    assert "### PTY-nn <name>" in discover and "### SV-nn <name>" in discover
    assert "planner questions --subject <ID>" in discover


def test_modes_has_no_question_cap_and_no_sweep():
    modes = text("references/MODES.md")
    assert "at most two questions" not in modes and "concern sweep" not in modes
    assert "## Owed questions" in modes and "There is no cap on questions and no quota" in modes
    assert modes.count("question ledger rows") == 4


def test_the_checks_every_area_makes_live_in_the_agent_and_not_in_the_skills():
    agent = text("agents/area-reviewer.md")
    assert "## Checks every area makes" in agent
    for line in ("service levels, hours or limits that differ", "dates, terms or numbers that disagree",
                 "a plan that a fact contradicts", "must follow a customer across systems",
                 "who gains and who loses under each reading of the ask"):
        assert line in agent
    for skill in ("skills/dump/SKILL.md", "skills/discover/SKILL.md"):
        body = text(skill)
        assert "Add to that focus" not in body and "who gains and who loses" not in body
        assert "service levels" not in body


def test_round_two_fixes_in_dump_discover_and_the_reviewer():
    dump, disc = text("skills/dump/SKILL.md"), text("skills/discover/SKILL.md")
    agent = text("agents/area-reviewer.md")
    assert "python3 .claude/skills/planner/bin/planner questions --subject <ID>" in disc
    assert "It is not a verdict on any idea." in dump
    assert "Never present the checkpoint's digest as a verdict" in dump
    assert "say aloud any pair of lines" in disc and "never two facts" in disc
    assert '"after the read-back" (the "Here\'s what I think exists" step' in disc
    assert 'type at close: PTY' in dump and 'type at close: SV' in dump
    assert "any contract or document the captures themselves name" in dump
    assert "A team that loses under one reading is a stakeholder, even if nobody named them" in agent


def test_shape_runs_the_checkpoint_before_options_with_what_must_be_true():
    shape = text("skills/shape/SKILL.md")
    assert "references/REVIEW.md" in shape and '"before options"' in shape
    assert shape.index("run the review checkpoint") < shape.index("Show the options.")
    assert '"what must be true" set' in shape and "`assumed` ledger row" in shape
    assert "planner check --gate shape" in shape


def test_grill_reads_the_blocking_questions_and_runs_the_checkpoint_on_the_agenda():
    grill = text("skills/grill/SKILL.md")
    assert "planner check --gate grill --item <ID>" in grill and "W807" in grill
    assert "references/REVIEW.md" in grill and '"on the agenda"' in grill
    assert grill.index("--gate grill") < grill.index("write the agenda into the session record")


def test_epics_reads_the_question_gate():
    assert "`E805`" in text("skills/epics/SKILL.md")
