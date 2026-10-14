"""/vela:tickets and the new build-plan format: the Heron plan re-shaped (tests/fixtures/team-skills/heron-plan) holds every
story, task and size of the original, reads clean in the explorer, converts to the same tickets, and is held against the vault.

    python3 -m pytest tests/test_tickets.py
"""
import csv
import io
import re
import shutil

import pytest

from conftest import REPO, edit, run
from vela import breakdown, cli, tickets
from vela.edge import teamdocs
from vela.explorer import plan_data

FIXTURES = REPO / "tests" / "fixtures" / "team-skills"
VAULT = FIXTURES / "heron-plan"
PLAN = VAULT / "docs" / "plan" / "desktop-agent-breakdown.md"
ORIGINAL = FIXTURES / "heron-original-breakdown.md"
# What the original Heron plan gives the reader: 12 story sections, 42 task rows, 153 points (S 2, M 5, L 8).
ORIGINAL_COUNTS = {"stories": 12, "tasks": 42, "points": 153}


@pytest.fixture
def vault(tmp_path):
    out = tmp_path / "vault"
    shutil.copytree(VAULT, out)
    return out


def plan_text(root):
    return (root / "docs" / "plan" / "desktop-agent-breakdown.md").read_text(encoding="utf-8")


def counts(path):
    plan = breakdown.read(path.read_text(encoding="utf-8"))
    entry = plan_data.totals([plan_data.story_entry(s, plan["summary"], {}, set(), []) for s in plan["stories"]])
    return {"stories": entry["stories"], "tasks": entry["tasks"], "points": entry["points"]}


# ---- the re-shaped plan keeps everything the original had

def test_the_reshaped_plan_has_the_originals_stories_tasks_and_points():
    assert counts(ORIGINAL) == ORIGINAL_COUNTS
    assert counts(PLAN) == ORIGINAL_COUNTS


def test_every_original_task_and_size_is_still_there_under_the_same_story():
    old = {s.id: [tuple(r) for r in s.tasks] for s in breakdown.read(ORIGINAL.read_text(encoding="utf-8"))["stories"]}
    new = {s.id: [tuple(r) for r in s.tasks] for s in breakdown.read(PLAN.read_text(encoding="utf-8"))["stories"]}
    assert list(new) == list(old)
    for sid, rows in old.items():
        assert new[sid][:len(rows)] == rows, sid
    assert len(new["S-07b"]) == 2  # the two tasks the original sized in prose are table rows now, and counted in no total


def test_the_plan_reads_with_nothing_the_reader_could_not_map():
    plan = breakdown.read(PLAN.read_text(encoding="utf-8"))
    assert plan["problems"] == []
    assert plan["meta"]["status"] == "complete-with-gaps" and plan["meta"]["vault"]["app"] == "APP-desktop-agent"
    assert len(breakdown.read(ORIGINAL.read_text(encoding="utf-8"))["problems"]) > 0


def test_the_original_design_is_unchanged_beside_it():
    design = (VAULT / "docs" / "tech-design" / "desktop-agent.md").read_text(encoding="utf-8")
    assert design.startswith("---\nslug: desktop-agent\nstatus: complete-with-gaps") and len(design.split("\n")) == 425


def test_the_explorer_builds_the_plan_and_the_design_with_the_same_counts(tmp_path, vault):
    code, said = run("explore", str(vault), "--today", "2026-11-20", "-o", str(tmp_path / "page.html"), "--no-open")
    assert code == 0, said
    assert "complete-with-gaps, 12 stories, 42 tasks, 153 points, 0 things it could not read" in said
    assert "design desktop-agent.md: complete-with-gaps, 8 components" in said


def test_the_ticket_rows_of_the_original_are_all_in_the_new_plan_except_the_stories_it_now_calls_deferred():
    old = breakdown.build_rows(breakdown.read(ORIGINAL.read_text(encoding="utf-8"))["stories"])
    new = breakdown.build_rows(breakdown.read(PLAN.read_text(encoding="utf-8"))["stories"])
    key = lambda r: (r["Issue Id"], r["Summary"], r["Issue Type"], r["Parent"], r["Story Points"])
    kept = {key(r) for r in new}
    lost = [r["Issue Id"] for r in old if key(r) not in kept]
    assert lost == ["S-04", "S-07b", "S-11"]  # merged or deferred: named under "Not ticketed", not exported as empty tickets
    assert len(new) == len(old) - 3 + 0 and all(r["Description"].count("Acceptance criteria") for r in new if r["Issue Type"] == "Story")


# ---- the format

def test_a_tracer_fact_bullet_marks_the_tracer_and_is_not_read_as_a_criterion():
    story = next(s for s in breakdown.read(PLAN.read_text(encoding="utf-8"))["stories"] if s.id == "S-05")
    assert story.tracer and story.slice == "tracer"
    assert not any("Tracer" in c for c in story.criteria)
    entry = plan_data.story_entry(story, {}, {}, set(), [])
    assert entry["tracer"] is True and entry["fit"].startswith("cannot tell")


def test_a_plan_without_the_new_lines_reads_as_it_always_did():
    story = next(s for s in breakdown.read(ORIGINAL.read_text(encoding="utf-8"))["stories"] if s.id == "S-02")
    assert (story.done_when, story.components, story.slice, story.fit, story.state, story.tracer) == (None, None, "", None, "planned", False)


def test_blocked_by_none_means_no_blockers_and_the_rest_is_a_note():
    text = PLAN.read_text(encoding="utf-8")
    story = next(s for s in breakdown.read(text)["stories"] if s.id == "S-01")
    assert story.blocked.startswith("none. D-001") and breakdown.blockers(story) == []
    assert plan_data.blockers_of(story.blocked, set()) == []
    entry = plan_data.story_entry(story, {}, {}, set(), [])
    assert entry["blockers"] == [] and "not a gate" in entry["blockedText"]
    assert plan_data.blockers_of("none yet; S-02 later", set()) == []


def test_deferred_and_merged_stories_keep_their_fields_and_are_in_no_total():
    stories = {s.id: s for s in breakdown.read(PLAN.read_text(encoding="utf-8"))["stories"]}
    assert stories["S-07b"].state == "deferred" and stories["S-07b"].criteria and stories["S-07b"].tasks and stories["S-07b"].blocked
    assert stories["S-11"].state == "deferred" and stories["S-11"].criteria and stories["S-11"].blocked
    assert stories["S-04"].state == "merged" and not stories["S-04"].built


def test_a_slice_line_that_starts_with_another_word_is_a_problem():
    bad = PLAN.read_text(encoding="utf-8").replace("Slice: vertical", "Slice: sideways", 1)
    assert any("not tracer, vertical or layer" in p for p in breakdown.read(bad)["problems"])


# ---- the checks against the vault

def check(root, text=None):
    text = text or plan_text(root)
    return tickets.check(text, cli.load_vault(root), "")


def test_the_heron_plan_is_held_against_its_vault_and_flags_only_what_a_person_should_look_at(vault):
    found = check(vault)
    flagged = sorted({f.story for f in found if f.flag})
    assert flagged == ["S-01", "S-07a", "S-10"]  # no criterion to quote, a layer, no criterion to quote
    assert not [f for f in found if f.kind in ("criteria", "blocked", "release", "reading")]
    assert tickets.summary(plan_text(vault), found) == "9 stories, 42 tasks, 3 flagged"


def test_a_reworded_criterion_is_found(vault):
    page = vault / "docs" / "plan" / "desktop-agent-breakdown.md"
    sentence = "For a person who has not switched Heron on, Heron records no agreement and reads nothing."
    edit(page, sentence, "For a person who has not switched Heron on, Heron records no agreement and reads nothing at all.")
    found = [f for f in check(vault) if f.kind == "criteria"]
    assert len(found) == 1 and found[0].story == "S-02" and "EPC-032.AC4 is reworded" in str(found[0])
    assert sentence in str(found[0])


def test_a_story_that_quotes_nothing_is_found(vault):
    page = vault / "docs" / "plan" / "desktop-agent-breakdown.md"
    edit(page, "- After a person withdraws, no digest or prep note is shown to them, and any digest or prep note held for them on the laptop is deleted.\n", "")
    found = [f for f in check(vault) if f.kind == "criteria"]
    assert [f.story for f in found] == ["S-03"] and "no acceptance criterion quotes EPC-032.AC6" in str(found[0])


def test_an_app_requirement_with_no_story_is_found_unless_a_plan_gap_accepts_it(vault):
    page = vault / "docs" / "plan" / "desktop-agent-breakdown.md"
    text = plan_text(vault)
    cut = text.replace("CAP-005.FR2@APP-desktop-agent, CON-004, EPC-032.AC5, EPC-032.AC6", "CON-004, EPC-032.AC5, EPC-032.AC6")
    found = [f for f in check(vault, cut) if f.kind == "coverage" and f.flag]
    assert [str(f) for f in found] == ["No story builds Stop reading when a withdrawal is not confirmed (CAP-005.FR2) for Desktop agent"]
    accepted = check(vault)
    assert [f for f in accepted if f.kind == "coverage"] and not [f for f in accepted if f.kind == "coverage" and f.flag]


def test_a_trace_to_an_id_the_vault_does_not_hold_and_a_blocker_that_is_not_a_story_are_found(vault):
    text = plan_text(vault).replace("EPC-033.AC5, EPC-034.AC1", "EPC-033.AC5, EPC-099.AC1", 1).replace("Blocked by: S-01 for the real binary only", "Blocked by: S-77 for the real binary only", 1)
    found = [str(f) for f in check(vault, text)]
    assert any("EPC-099.AC1, which isn't in the plan" in f for f in found)
    assert any("S-77, which is not a story in this plan" in f for f in found)


def test_the_tracer_comes_first_in_the_build_order(vault):
    text = plan_text(vault).replace("1. S-01 (tracer)", "9. S-01 (tracer)", 1)
    ordered = text.replace("2. S-02 (tracer)", "1. S-02 (tracer)", 1).replace("9. S-01 (tracer)", "2. S-01 (tracer)", 1)
    assert not [f for f in check(vault, ordered) if f.kind == "slice" and "part of the tracer, but" in f.text]
    lines = ordered.split("\n")
    s05 = next(i for i, ln in enumerate(lines) if ln.startswith("3. S-05"))
    s06 = next(i for i, ln in enumerate(lines) if ln.startswith("5. S-06"))
    lines.insert(s06, lines.pop(s05))
    late = "\n".join(lines)
    assert [f.story for f in check(vault, late) if "part of the tracer, but" in f.text] == ["S-05"]


def test_no_tracer_story_is_a_finding_until_the_plan_records_an_override(vault):
    bare = plan_text(vault).replace("- **Tracer:** yes\n", "").replace("Slice: tracer", "Slice: vertical")
    assert any("No story is marked as part of the tracer" in f.text for f in check(vault, bare))
    overridden = bare.replace("## Build order", "- **Override:** the team lead starts with packaging; the tracer waits on OQ-001.\n\n## Build order", 1)
    assert not any("No story is marked as part of the tracer" in f.text for f in check(vault, overridden))


def test_a_release_fit_that_names_the_wrong_date_is_found(vault):
    text = plan_text(vault).replace("cannot tell for 2027-02-02. Sizes add to at most 14", "cannot tell for 2027-03-01. Sizes add to at most 14", 1)
    found = [f for f in check(vault, text) if f.kind == "release"]
    assert [f.story for f in found] == ["S-02"] and "doesn't start from 2027-02-02" in str(found[0])


# ---- the command

def test_check_prints_findings_and_the_summary_and_writes_nothing(vault):
    code, said = run("tickets", "check", "--vault", str(vault))
    assert code == 1 and said.rstrip().endswith("9 stories, 42 tasks, 3 flagged")
    assert not (vault / "docs" / "work").exists()


def test_write_markdown_gives_one_section_per_story_tracer_first_with_criteria_written_out(vault):
    code, said = run("tickets", "write", "--vault", str(vault), "--format", "markdown")
    assert code == 1 and "9 stories, 42 tasks, 3 flagged" in said
    body = (vault / "docs" / "work" / "tickets.md").read_text(encoding="utf-8")
    headings = re.findall(r"^## (S-\d+[a-z]?) ", body, re.M)
    assert headings[:3] == ["S-01", "S-02", "S-05"] and len(headings) == 9
    assert "When a person switches Heron on, they are offered calendar entries" in body and "S-01-T1" in body
    assert "## Not ticketed" in body and "S-07b" in body and "## When to create them" in body


def test_write_csv_is_the_jira_import_with_its_readme(vault):
    code, said = run("tickets", "write", "--vault", str(vault), "--format", "csv", "--out", str(vault / "out"))
    rows = list(csv.DictReader(io.StringIO((vault / "out" / "tickets.csv").read_text(encoding="utf-8"), newline="")))
    assert [r["Issue Id"] for r in rows if r["Issue Type"] == "Story"] == ["S-01", "S-02", "S-03", "S-05", "S-06", "S-07a", "S-08", "S-09", "S-10"]
    assert sum(r["Issue Type"] == "Task" for r in rows) == 42
    readme = (vault / "out" / "README.md").read_text(encoding="utf-8")
    assert "vela tickets" in readme and "## Not ticketed" in readme


def test_a_plan_naming_no_app_of_the_vault_is_an_error_not_a_pass(vault):
    page = vault / "docs" / "plan" / "desktop-agent-breakdown.md"
    edit(page, "  app: APP-desktop-agent\n", "")
    code, said = run("tickets", "check", "--vault", str(vault))
    assert code == 2 and "names no app of this vault" in said


# ---- vela next

def test_next_suggests_breakdown_after_a_complete_design_and_tickets_after_a_complete_plan(tmp_path, vault):
    plan = vault / "docs" / "plan" / "desktop-agent-breakdown.md"
    kept = plan.read_text(encoding="utf-8")
    plan.unlink()
    assert teamdocs.team_step(vault).startswith("the APP-desktop-agent team: their design is") and "/vela:breakdown" in teamdocs.team_step(vault)
    code, said = run("next", "--vault", str(vault), "--today", "2026-11-20")
    assert "vela next: for the Desktop agent team: their design is" in said
    plan.write_text(kept, encoding="utf-8")
    assert teamdocs.team_step(vault).startswith("the APP-desktop-agent team: their build plan is") and "/vela:tickets" in teamdocs.team_step(vault)
    run("tickets", "write", "--vault", str(vault))
    assert teamdocs.team_step(vault) is None


def test_next_says_nothing_new_while_the_design_is_in_progress(vault):
    edit(vault / "docs" / "tech-design" / "desktop-agent.md", "status: complete-with-gaps", "status: in-progress")
    (vault / "docs" / "plan" / "desktop-agent-breakdown.md").unlink()
    assert teamdocs.team_step(vault) is None


# ---- slices: a story names the vault slice it is part of

def add_slices(root):
    (root / "slices").mkdir()
    for sid, title, flows, after in (("SLC-001", "Switch on and get the digest", "FLO-001, FLO-002", ""),
                                     ("SLC-002", "Get a prep note", "FLO-003", "- **After:** SLC-001\n")):
        (root / "slices" / f"{sid}-x.md").write_text(
            f"---\nid: {sid}\ntype: slice\ntitle: {title}\nauthored: authored\n---\n\n# {title}\n\nWhat it makes work.\n\n"
            f"- **Flows:** {flows}\n{after}", encoding="utf-8")


def test_a_story_names_its_vault_slice_on_its_slice_line():
    text = PLAN.read_text(encoding="utf-8").replace("Slice: vertical", "Slice: vertical, SLC-002 Get a prep note", 1)
    stories = breakdown.read(text)["stories"]
    assert [s.slice_id for s in stories if s.slice_id] == ["SLC-002"]
    assert next(s for s in stories if s.slice_id).slice == "vertical"


def test_a_story_naming_a_slice_the_vault_lacks_is_flagged_and_naming_the_tracer_makes_it_a_tracer_story(vault):
    add_slices(vault)
    text = plan_text(vault).replace("Slice: vertical", "Slice: vertical, SLC-009", 1)
    assert [f.text for f in check(vault, text) if f.kind == "slice" and "SLC-009" in f.text] == ["names the slice SLC-009, which isn't in the plan"]
    bare = plan_text(vault).replace("- **Tracer:** yes\n", "").replace("Slice: tracer", "Slice: vertical, SLC-001")
    assert not any("No story is marked as part of the tracer" in f.text for f in check(vault, bare))


def test_tickets_are_grouped_by_slice_the_tracer_first(vault):
    add_slices(vault)
    text = plan_text(vault)
    later = [s.id for s in breakdown.read(text)["stories"] if s.slice == "vertical" and s.built][-1]
    text = re.sub(rf"(### {later}\b[^\n]*\n(?:(?!### ).*\n)*?)Slice: vertical", r"\1Slice: vertical, SLC-002", text, count=1)
    body = tickets.markdown_text(text, "plan.md", cli.load_vault(vault))
    headings = re.findall(r"^## (S-\d+[a-z]?) ", body, re.M)
    tracers = [s.id for s in breakdown.read(text)["stories"] if s.slice == "tracer" and s.built]
    assert headings[:len(tracers)] == [h for h in headings if h in tracers]
    assert headings[len(tracers)] == later  # the slice it names comes before stories that name none
    assert "then grouped by slice" in body
