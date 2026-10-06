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
    assert '{"area": "FIN", "findings": []}' in body
    assert '{"area": "FIN", "error": "<what stopped you>"}' in body
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
    assert "Never review the pages yourself in this conversation." in review


def test_review_merges_in_code_and_never_reads_a_failure_as_clean():
    review = text("references/REVIEW.md")
    assert "planner findings merge .git/planner-findings/<session id>-<n>" in review
    assert '{"area": "<AREA>", "error": "<what happened>"}' in review
    assert "Never write an empty findings list for a reviewer that did not finish" in review
    assert "An area that did not run is never reported as clean." in review
    assert "- **Coverage:** <the merge's coverage line" in review


def test_review_tells_the_session_to_swap_inner_quotes_like_the_merge():
    review = text("references/REVIEW.md")
    assert "replace each inner straight `\"` with `”`" in review


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
