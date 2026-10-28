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
        "Sign and notarize the Mac build", "Windows MSI package", "Capture system audio",
        "Store transcripts encrypted", "Build the digest from a transcript"]
    assert rows[0]["Summary"] == "Signed installer"


def test_the_summary_and_the_grouped_criteria_are_in_the_description_and_the_trace_is_in_the_labels(tmp_path):
    _, rows, _ = convert(tmp_path)
    story = rows[3]["Description"]
    assert "This story captures a meeting's audio on the laptop" in story
    assert "- Audio is transcribed on the laptop, and nothing leaves it before the security review passes. (covers AC1)" in story
    assert "Traces to" not in story
    assert "Written without the team's records, so what this story relies on is named by ID only: CAP-002.FR2." in story
    task = rows[4]["Description"]
    assert task == "Component: Audio Capture\nSize: L\nStory: Capture a meeting locally (S-02)"


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
    assert by_id["S-02"][6:8] == ["CAP-002.FR2", "EPC-003"]
    assert by_id["S-01-T1"][6:8] == ["CAP-001.FR1", ""]
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


# ---- the work-breakdown skill's real output (a Heron plan from the sim): every construct it writes is read, not flagged

HERON = REPO / "tests" / "fixtures" / "breakdown" / "heron-desktop-agent-breakdown.md"
HERON_TICKETS = REPO / "tests" / "fixtures" / "breakdown" / "heron-desktop-agent-tickets.csv"


def heron_stories():
    from vela import breakdown
    stories, _, problems = breakdown.parse(HERON.read_text(encoding="utf-8"))
    return {s.id: s for s in stories}, problems


def test_the_real_plan_has_no_unreadable_lines_for_the_constructs_the_skill_writes():
    stories, problems = heron_stories()
    assert problems == [] and len(stories) == 15
    assert all(s.criteria for s in stories.values()), "every story's bullets sit under an Acceptance criteria label"
    assert stories["S-11"].criteria_label.startswith("Acceptance criteria. No epic criterion covers this story")
    assert [i for i, s in stories.items() if s.open_notes] == ["S-06", "S-08", "S-09"]
    assert stories["S-06"].open_notes[0].startswith("Open for `tech-design-grill`: what `earlier_calls` returns")
    assert [i for i, s in stories.items() if s.conflicts] == ["S-11"]
    assert stories["S-11"].conflicts[0].startswith("Conflict with an epic criterion: EPC-001.AC5 says everyone invited appears")
    assert all(s.extra == [] for s in stories.values())


def test_a_story_that_says_it_traces_to_nothing_is_stated_not_unreadable():
    stories, _ = heron_stories()
    assert stories["S-14"].traces.startswith("no requirement row or epic criterion")


def test_criteria_open_notes_and_conflicts_land_in_the_description_under_labels_and_the_story_is_labeled(tmp_path):
    source = tmp_path / "heron-breakdown.md"
    source.write_text(HERON.read_text(encoding="utf-8"), encoding="utf-8")
    problems = b2t.convert(source, tmp_path / "work")
    assert problems and all("has no ticket copy yet" in p for p in problems)
    with (tmp_path / "work" / "tickets.csv").open(encoding="utf-8", newline="") as f:
        raw = list(csv.reader(f))
    header, by_id = raw[0], {row[0]: row for row in raw[1:]}
    assert len(raw) == 1 + 15 + 112

    def labels(row):
        return [c for c in row[6:len(header) - 1] if c]

    desc = by_id["S-06"][2].splitlines()
    assert "Acceptance criteria:" in desc and desc.index("Open for the design:") > desc.index("Acceptance criteria:")
    assert any(line.startswith("- Open for `tech-design-grill`: what `earlier_calls` returns") for line in desc)
    assert "needs-design" in labels(by_id["S-06"]) and "conflict" not in labels(by_id["S-06"])
    clash = by_id["S-11"][2].splitlines()
    assert clash[clash.index("Conflicts:") + 1].startswith("- Conflict with an epic criterion: EPC-001.AC5 says everyone invited")
    assert "conflict" in labels(by_id["S-11"]) and "needs-design" not in labels(by_id["S-11"])
    assert "needs-design" not in labels(by_id["S-06-T1"]), "tasks carry their story's trace labels, not its flags"
    assert "Acceptance criteria. No epic criterion covers this story, so these are the design's behavior:" in clash


def test_the_tickets_for_the_real_plan_are_stable(tmp_path):
    source = tmp_path / "heron-breakdown.md"
    source.write_text(HERON.read_text(encoding="utf-8"), encoding="utf-8")
    b2t.convert(source, tmp_path / "a")
    b2t.convert(source, tmp_path / "b")
    written = (tmp_path / "a" / "tickets.csv").read_bytes()
    assert written == (tmp_path / "b" / "tickets.csv").read_bytes() == HERON_TICKETS.read_bytes()


def test_a_range_of_stories_is_every_story_between_and_sizes_read_as_counts_or_letters():
    from vela import breakdown
    assert breakdown.story_refs("S-03 to S-05, G-012, S-09") == ["S-03", "S-04", "S-05", "S-09"]
    assert breakdown.size_counts("2S 4M 1L") == breakdown.size_counts("M+M+M+M+S+S+L") == {"S": 2, "M": 4, "L": 1}


def test_a_lettered_story_and_a_retired_one(tmp_path):
    # From the heron run: S-07a/S-07b were dropped silently, and S-04 "(merged into S-05)" became an empty ticket.
    plan = tmp_path / "docs" / "plan"
    plan.mkdir(parents=True)
    (plan / "x-breakdown.md").write_text("""---
status: complete
prereqs: []
---
| Story | Traces to | Size | Blocked by |
|---|---|---|---|
| S-04 | | | |
| S-07a | CON-001 | S | none |
| S-07b | CON-001 | S | S-07a |

### S-04 (merged into S-05)
Merged into S-05 on 2026-10-12. The ID is retired.

### S-07a Gate
Traces to: CON-001
Acceptance criteria:
- the gate holds
| Task | Size | Component |
|---|---|---|
| Add the gate | S | Agent |
Blocked by: none

### S-07b Transport
Traces to: CON-001
Acceptance criteria:
- it sends
| Task | Size | Component |
|---|---|---|
| Send it | S | Agent |
Blocked by: S-07a

## Build order
1. S-07a
2. S-07b
""", encoding="utf-8")
    out = tmp_path / "out"
    subprocess.run([sys.executable, str(TOOL), "--repo", str(tmp_path), "--out", str(out)], capture_output=True, text=True, timeout=120)
    csv = (out / "tickets.csv").read_text(encoding="utf-8")
    assert "S-07a," in csv and "S-07b," in csv and "S-07b-T1" in csv
    assert "\nS-04," not in csv
    assert "S-04: merged into S-05, so not exported" in (out / "README.md").read_text(encoding="utf-8")
