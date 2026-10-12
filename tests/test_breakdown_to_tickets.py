"""tools/breakdown_to_tickets.py: a work-breakdown plan, in the skill's real format, to a Jira CSV with nothing added."""
import csv
import subprocess
import sys

import pytest

from conftest import REPO

sys.path.insert(0, str(REPO / "tools"))
import breakdown_to_tickets as b2t  # noqa: E402

FIXTURE = REPO / "tests" / "fixtures" / "breakdown" / "desk-agent-breakdown.md"
TOOL = REPO / "tools" / "breakdown_to_tickets.py"


def convert(tmp_path, text=None):
    source = tmp_path / "desk-agent-breakdown.md"
    source.write_text(FIXTURE.read_text(encoding="utf-8") if text is None else text, encoding="utf-8")
    out = tmp_path / "work"
    problems = b2t.convert(source, out)
    rows = list(csv.DictReader((out / "tickets.csv").open(encoding="utf-8", newline="")))
    return problems, rows, out


def test_every_story_and_task_row_of_the_breakdown_is_one_ticket_in_order(tmp_path):
    problems, rows, out = convert(tmp_path)
    assert problems == []
    assert [(r["Issue Id"], r["Issue Type"], r["Parent"]) for r in rows] == [
        ("S-01", "Story", ""), ("S-01-T1", "Task", "S-01"), ("S-01-T2", "Task", "S-01"),
        ("S-02", "Story", ""), ("S-02-T1", "Task", "S-02"), ("S-02-T2", "Task", "S-02"),
        ("S-03", "Story", ""), ("S-03-T1", "Task", "S-03")]
    assert [r["Summary"] for r in rows if r["Issue Type"] == "Task"] == [
        "Sign and notarise the Mac build", "Windows MSI package", "Capture system audio",
        "Store transcripts encrypted", "Build the digest from a transcript"]
    assert rows[0]["Summary"] == "S-01 Signed installer"


def test_the_trace_and_the_criteria_are_in_the_description_as_the_breakdown_states_them(tmp_path):
    _, rows, _ = convert(tmp_path)
    story = rows[3]["Description"]
    assert "Traces to: CAP-002.FR2@APP-desktop-agent, EPC-003.AC1; components: Audio Capture, Local Store" in story
    assert "- Audio is transcribed on the laptop and never leaves it before the security review passes." in story
    task = rows[4]["Description"]
    assert "Component: Audio Capture" in task and "Size: L" in task
    assert "Traces to: CAP-002.FR2@APP-desktop-agent, EPC-003.AC1; components: Audio Capture, Local Store" in task


def test_sizes_become_points_on_tasks_only_and_the_mapping_is_in_the_readme(tmp_path):
    _, rows, out = convert(tmp_path)
    assert [r["Story Points"] for r in rows] == ["", "5", "2", "", "8", "5", "", "5"]
    readme = (out / "README.md").read_text(encoding="utf-8")
    assert "S = 2, M = 5, L = 8" in readme and "Jira" in readme and "Blocked by" in readme


def test_labels_are_the_vault_ids_of_the_trace_and_blocked_by_is_the_stories_that_block(tmp_path):
    _, _, out = convert(tmp_path)
    with (out / "tickets.csv").open(encoding="utf-8", newline="") as f:
        raw = list(csv.reader(f))
    header = raw[0]
    assert header[:6] == ["Issue Id", "Summary", "Description", "Issue Type", "Parent", "Story Points"]
    assert header.count("Labels") == 2 and header[-1] == "Blocked by"
    by_id = {row[0]: row for row in raw[1:]}
    assert by_id["S-02"][6:8] == ["CAP-002.FR2@APP-desktop-agent", "EPC-003.AC1"]
    assert by_id["S-01-T1"][6:8] == ["CAP-001.FR1@APP-desktop-agent", ""]
    assert [by_id[s][-1] for s in ("S-01", "S-02", "S-03")] == ["", "S-01", "S-02"]
    assert "Q-7 (open question: who may a digest name), the CISO review (outside party)" in by_id["S-03"][2]


def test_not_planned_items_are_listed_in_the_readme_not_dropped(tmp_path):
    _, _, out = convert(tmp_path)
    readme = (out / "README.md").read_text(encoding="utf-8")
    assert "GAP-1: retention of transcripts, until Legal answers." in readme and "DEF-2" in readme


def test_what_cannot_be_mapped_is_a_problem_and_the_row_is_still_written(tmp_path):
    text = FIXTURE.read_text(encoding="utf-8")
    text = text.replace("| Windows MSI package | S | Installer |", "| Windows MSI package | XL | Installer |")
    text = text.replace("- An update replaces the installed version without losing settings.\n",
                        "- An update replaces the installed version without losing settings.\n\nSee also the support runbook.\n")
    text = text.replace("Blocked by: S-02, Q-7", "Blocked by: S-09, Q-7")
    problems, rows, out = convert(tmp_path, text)
    assert len(rows) == 8
    assert any("size 'XL' is not S, M or L" in p for p in problems)
    assert any("line not mapped to a column" in p and "support runbook" in p for p in problems)
    assert any("blocked by S-09, which is not a story" in p for p in problems)
    assert rows[2]["Story Points"] == "" and "See also the support runbook." in rows[0]["Description"]
    assert "## Problems" in (out / "README.md").read_text(encoding="utf-8")


def test_a_story_missing_from_the_summary_or_with_no_trace_is_reported(tmp_path):
    text = FIXTURE.read_text(encoding="utf-8").replace("| S-03 Send the digest | CON-004, EPC-003.AC2 | M | S-02, Q-7 |\n", "")
    text = text.replace("Traces to: CAP-001.FR1@APP-desktop-agent; components: Installer, Updater\n", "")
    problems, rows, _ = convert(tmp_path, text)
    assert "S-03: has a section but is not in the summary table" in problems
    assert "S-01: no 'Traces to:' line" in problems
    assert len(rows) == 8


def test_a_plan_that_is_not_complete_is_flagged(tmp_path):
    problems, _, _ = convert(tmp_path, FIXTURE.read_text(encoding="utf-8").replace("complete-with-gaps", "draft"))
    assert any("status is 'draft'" in p for p in problems)


def run_tool(*argv):
    return subprocess.run([sys.executable, str(TOOL), *argv], capture_output=True, text=True, timeout=60)


def test_the_command_writes_docs_work_in_the_repo_and_exits_0_on_a_clean_plan(tmp_path):
    plan = tmp_path / "docs" / "plan"
    plan.mkdir(parents=True)
    (plan / "desk-agent-breakdown.md").write_text(FIXTURE.read_text(encoding="utf-8"), encoding="utf-8")
    done = run_tool("--repo", str(tmp_path))
    assert done.returncode == 0, done.stderr
    assert (tmp_path / "docs" / "work" / "tickets.csv").is_file() and (tmp_path / "docs" / "work" / "README.md").is_file()


def test_the_command_exits_1_with_problems_and_2_when_there_is_no_single_breakdown(tmp_path):
    plan = tmp_path / "docs" / "plan"
    plan.mkdir(parents=True)
    done = run_tool("--repo", str(tmp_path))
    assert done.returncode == 2 and "found 0" in done.stderr
    (plan / "a-breakdown.md").write_text(FIXTURE.read_text(encoding="utf-8").replace("| S |", "| Q |"), encoding="utf-8")
    done = run_tool("--repo", str(tmp_path))
    assert done.returncode == 1 and "is not S, M or L" in done.stderr
    (plan / "b-breakdown.md").write_text("x", encoding="utf-8")
    assert run_tool("--repo", str(tmp_path)).returncode == 2
