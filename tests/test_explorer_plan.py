"""The build plan in the explorer: finding a team's work breakdown, reading it with the tool's own parser, and what the page
is given from it (explorer/breakdown_find.py, plan_data.py; level 4 of Inside this app, DESIGN-INSIDE.md).

    python3 -m pytest tests/test_explorer_plan.py

The page's drawing is checked in the browser's #selftest (tests/test_explorer_browser.py); this file checks the data.
"""
import csv
import io
import json
import re
import shutil
import sys

import pytest

from conftest import REPO, edit, run
from vela import breakdown
from vela.explorer import plan_data

sys.path.insert(0, str(REPO / "tools"))
import breakdown_to_tickets as b2t  # noqa: E402

EXAMPLE = REPO / "examples" / "unified-booking"
DEMO_DESIGNS = REPO / "prototypes" / "explorer" / "demo_designs"
DEMO_PLAN = DEMO_DESIGNS / "booking" / "docs" / "plan" / "booking-breakdown.md"
PRICING_PAGE = "05-building-blocks/pricing-building-blocks.md"
PRICING_DOC = "docs/tech-design/pricing.md"
PRICING_PLAN = "docs/plan/pricing-breakdown.md"
DATA = re.compile(r'<script type="application/json" id="data">(.*?)</script>', re.S)


@pytest.fixture
def world(tmp_path):
    """A vault and, beside it, a team repository with the Pricing design and a plan whose prereqs name it."""
    vault, team = tmp_path / "vault", tmp_path / "team"
    shutil.copytree(EXAMPLE, vault)
    (team / "docs/tech-design").mkdir(parents=True)
    (team / "docs/plan").mkdir(parents=True)
    shutil.copy(DEMO_DESIGNS / "pricing" / PRICING_DOC, team / PRICING_DOC)
    text = DEMO_PLAN.read_text(encoding="utf-8").replace("docs/tech-design/booking.md", PRICING_DOC)
    (team / PRICING_PLAN).write_text(text, encoding="utf-8")
    with open(vault / ".vela.yaml", "a", encoding="utf-8") as config:
        config.write(f"designs: {{APP-pricing: ../team/{PRICING_DOC}}}\n")
    return vault, team


def explore(vault, *extra):
    return run("explore", str(vault), "--today", "2026-11-20", *extra)


def data_of(vault):
    page = (vault / "dashboard.html").read_text(encoding="utf-8")
    return json.loads(DATA.search(page).group(1))


def plans_on_the_page(vault):
    return sorted(p["appId"] for p in data_of(vault)["plans"].values())


# ---------------------------------------------------------------- discovery

def test_a_plan_beside_the_design_whose_prereqs_name_it_is_found(world):
    vault, _ = world
    code, said = explore(vault)
    assert code == 0, said
    assert "(APP-pricing): using the build plan" in said and "beside its design, because it points to pricing.md" in said, said
    assert plans_on_the_page(vault) == ["APP-pricing"]


def test_a_plan_that_names_another_design_is_not_taken_and_the_report_says_what_was_looked_at(world):
    vault, team = world
    edit(team / PRICING_PLAN, f"prereqs:\n  - {PRICING_DOC}", "prereqs:\n  - docs/tech-design/other.md")
    code, said = explore(vault)
    assert code == 0, said
    assert plans_on_the_page(vault) == []
    assert "no build plan yet for Pricing (APP-pricing)" in said and "none of them is for the pricing.md design" in said, said


def test_a_design_with_no_plan_folder_is_named_in_the_report(world):
    vault, team = world
    shutil.rmtree(team / "docs/plan")
    code, said = explore(vault)
    assert code == 0, said
    assert "no build plan yet for Pricing (APP-pricing)" in said and "no *-breakdown.md in" in said, said


def test_two_plans_naming_one_design_is_a_warning_and_the_first_is_used(world):
    vault, team = world
    shutil.copy(team / PRICING_PLAN, team / "docs/plan/a-breakdown.md")
    code, said = explore(vault)
    assert code == 0, said
    assert "warning: Pricing (APP-pricing): 2 plans name pricing.md" in said and "using a-breakdown.md" in said, said


def test_breakdown_on_the_app_page_wins_over_beside_the_design(world):
    vault, team = world
    other = team / "docs/plan/elsewhere-breakdown.md"
    shutil.copy(team / PRICING_PLAN, other)
    edit(vault / PRICING_PAGE, "id: APP-pricing\n", "id: APP-pricing\nbreakdown: ../team/docs/plan/elsewhere-breakdown.md\n")
    code, said = explore(vault)
    assert code == 0, said
    assert "breakdown: on its page" in said, said
    assert data_of(vault)["plans"]["APP-pricing"]["file"] == "elsewhere-breakdown.md"


def test_breakdowns_in_vela_yaml_names_a_plan_with_no_design_loaded(world):
    vault, team = world
    with open(vault / ".vela.yaml", "a", encoding="utf-8") as config:
        config.write(f"breakdowns: {{APP-booking: ../team/{PRICING_PLAN}}}\n")
    code, said = explore(vault)
    assert code == 0, said
    assert "(APP-booking): using the build plan" in said and "breakdowns: in .vela.yaml" in said, said
    assert plans_on_the_page(vault) == ["APP-booking", "APP-pricing"]


def test_a_breakdown_path_that_leads_nowhere_is_a_warning_and_never_a_failed_build(world):
    vault, _ = world
    edit(vault / PRICING_PAGE, "id: APP-pricing\n", "id: APP-pricing\nbreakdown: ../team/nothing-breakdown.md\n")
    code, said = explore(vault)
    assert code == 0, said
    assert "warning: Pricing (APP-pricing): breakdown: on its page is ../team/nothing-breakdown.md, which is not a file" in said, said


def test_a_web_address_is_never_fetched(world):
    vault, _ = world
    edit(vault / PRICING_PAGE, "id: APP-pricing\n", "id: APP-pricing\nbreakdown: https://example.com/x-breakdown.md\n")
    code, said = explore(vault)
    assert code == 0, said
    assert "is a web address" in said, said


def test_a_named_breakdown_beats_every_lookup_and_a_missing_one_stops_the_build(world):
    vault, team = world
    code, said = explore(vault, f"--breakdown=APP-pricing={team / PRICING_PLAN}")
    assert code == 0, said
    assert "using the build plan" not in said and plans_on_the_page(vault) == ["APP-pricing"]
    code, said = explore(vault, f"--breakdown=APP-pricing={team / 'docs/plan/nope.md'}")
    assert code != 0 and "--breakdown: no breakdown at" in said, said
    code, said = explore(vault, "--breakdown=pricing")
    assert code != 0 and "--breakdown takes APP-x=path" in said, said


def test_a_plan_the_reader_cannot_fully_read_is_listed_on_the_page_and_in_the_report(world):
    vault, team = world
    edit(team / PRICING_PLAN, "status: complete-with-gaps", "status: draft")
    code, said = explore(vault)
    assert code == 0, said
    plan = next(iter(data_of(vault)["plans"].values()))
    assert any("frontmatter status is 'draft'" in p for p in plan["problems"]), plan["problems"]
    assert "frontmatter status is 'draft'" in said, said


def test_the_tickets_file_beside_the_plan_gets_a_relative_link(world):
    vault, team = world
    (team / "docs/work").mkdir()
    (team / "docs/work/tickets.csv").write_text("x\n", encoding="utf-8")
    code, said = explore(vault)
    assert code == 0, said
    plan = next(iter(data_of(vault)["plans"].values()))
    assert plan["ticketsHref"].endswith("team/docs/work/tickets.csv") and not plan["ticketsHref"].startswith("/"), plan["ticketsHref"]


# ---------------------------------------------------------------- one reader for the tool and the page

def test_the_tool_and_the_page_use_the_same_reader():
    assert b2t.parse is breakdown.parse and b2t.build_rows is breakdown.build_rows
    assert not hasattr(plan_data, "parse_story_sections"), "the page must not carry a second parser"


def test_copy_as_jira_csv_is_the_file_the_tool_writes(tmp_path):
    wrapped = plan_data.plans_for([f"APP-booking={DEMO_PLAN}"])["APP-booking"]
    out = tmp_path / "work"
    assert b2t.convert(DEMO_PLAN, out) == []
    written = (out / "tickets.csv").read_bytes().decode("utf-8")
    assert breakdown.csv_text(breakdown.build_rows(wrapped["read"]["stories"])) == written
    rows = list(csv.reader(io.StringIO(written, newline="")))
    assert len(rows) == 1 + 8 + 21


# ---------------------------------------------------------------- what the page is given

def test_what_blocks_a_story_is_told_apart():
    known = {"UNK-009"}
    got = plan_data.blockers_of("S-01, UNK-009 (open question), the CISO review (outside party), Q-7 (open question: who), D-001 (deferred), UNK-777, none", known)
    assert [(b["kind"], b["ref"]) for b in got] == [("story", "S-01"), ("question", "UNK-009"), ("outside", ""), ("plan-question", "Q-7"), ("gap", "D-001"), ("other", "")]
    assert plan_data.blockers_of("none", known) == []
    # A clause that names nothing is part of the sentence, not a blocker of its own (seen on Heron: "not recorded in
    # the vault", "drops from the plan if no." each drawn as a box in What waits on what).
    got = plan_data.blockers_of("not recorded in the vault, drops from the plan if no.", known)
    assert got == [], got
    # The design's open questions and deferrals are named by their IDs, one node each, however many clauses name them.
    got = plan_data.blockers_of("certificate holders (OQ-009); OQ-009 again for pushes, D-004 is a pilot measurement", known)
    assert [(b["kind"], b["ref"]) for b in got] == [("plan-question", "OQ-009"), ("gap", "D-004")], got
    assert plan_data.blockers_of("S-02 and S-03", known) == [{"kind": "story", "ref": "S-02", "text": "S-02"}, {"kind": "story", "ref": "S-03", "text": "S-03"}]


def entry_for(tmp_path, text):
    path = tmp_path / "booking-breakdown.md"
    path.write_text(text, encoding="utf-8")
    wrapped = plan_data.plans_for([f"APP-booking={path}"])["APP-booking"]
    return plan_data.plan_entry("APP-booking", wrapped, {"UNK-009", "UNK-010", "UNK-011"}, None)


def test_the_demo_plan_reads_clean_with_one_empty_coverage_row(tmp_path):
    plan = entry_for(tmp_path, DEMO_PLAN.read_text(encoding="utf-8"))
    assert plan["problems"] == []
    assert [s["id"] for s in plan["stories"]] == [f"S-0{n}" for n in range(1, 9)]
    assert plan["totals"] == {"stories": 8, "built": 8, "tasks": 21, "points": 90, "bySize": {"S": {"tasks": 7, "points": 14}, "M": {"tasks": 12, "points": 60}, "L": {"tasks": 2, "points": 16}}}
    assert [r["target"] for r in plan["coverage"]["targets"] if not r["stories"]] == ["EPC-036.AC4"]
    assert all(r["stories"] for r in plan["coverage"]["components"])


def test_a_size_total_that_is_not_its_tasks_is_a_problem_and_is_never_fixed_up(tmp_path):
    text = DEMO_PLAN.read_text(encoding="utf-8").replace("| M+M+S | none |", "| L | none |", 1)
    plan = entry_for(tmp_path, text)
    assert any("S-01: the summary table says its size is 'L', but its tasks add up to M+M+S" in p for p in plan["problems"]), plan["problems"]
    assert plan["stories"][0]["size"] == "M+M+S"


def test_a_target_a_story_traces_but_the_coverage_table_omits_is_a_problem(tmp_path):
    text = DEMO_PLAN.read_text(encoding="utf-8").replace("| CON-005 | S-02 |\n", "", 1)
    plan = entry_for(tmp_path, text)
    assert any("S-02 traces to CON-005, but the Coverage table has no row for it" in p for p in plan["problems"]), plan["problems"]


def test_a_story_with_no_task_for_a_component_leaves_that_component_empty(tmp_path):
    text = DEMO_PLAN.read_text(encoding="utf-8").replace("| M | Event publisher |", "| M | Event dispatcher |").replace("| S | Event publisher |", "| S | Event dispatcher |")
    plan = entry_for(tmp_path, text)
    row = next(c for c in plan["coverage"]["components"] if c["name"] == "Event publisher")
    assert row["stories"] == [] and row["stated"] == ["S-07"]


def test_a_trace_the_vault_does_not_hold_is_listed_not_dropped(tmp_path):
    wrapped = plan_data.plans_for([f"APP-booking={DEMO_PLAN}"])["APP-booking"]
    plan = plan_data.plan_entry("APP-booking", wrapped, {"CON-001"}, None)
    assert {"id": "CAP-013.FR1@APP-booking", "story": "S-01"} in plan["unresolved"]
    assert not any(u["id"] == "CON-001" for u in plan["unresolved"])


def test_a_story_blocked_by_an_open_vault_question_says_which(tmp_path):
    plan = entry_for(tmp_path, DEMO_PLAN.read_text(encoding="utf-8"))
    s2 = next(s for s in plan["stories"] if s["id"] == "S-02")
    assert [(b["kind"], b["ref"]) for b in s2["blockers"]] == [("question", "UNK-010"), ("question", "UNK-011")]
    s3 = next(s for s in plan["stories"] if s["id"] == "S-03")
    assert [b["kind"] for b in s3["blockers"]] == ["story", "outside"]


def test_the_demo_build_gives_the_booking_plan_its_tickets_and_the_reverse_trace_data(tmp_path):
    vault = tmp_path / "vault"
    sys.path.insert(0, str(REPO / "prototypes" / "explorer"))
    import make_demo_vault
    make_demo_vault.main(vault)
    out = tmp_path / "page.html"
    from vela.explorer import build
    shutil.copytree(DEMO_DESIGNS / "booking", tmp_path / "booking")  # beside the page, so the relative links need no walk through the home folder
    booking = tmp_path / "booking/docs/tech-design/booking.md"
    said = build.generate(vault, out, "2026-11-20", design_args=[f"APP-booking={booking}"])
    page = json.loads(DATA.search(out.read_text(encoding="utf-8")).group(1))
    plan = page["plans"]["APP-booking"]
    assert plan["problems"] == [] and plan["unresolved"] == [], (plan["problems"], plan["unresolved"])
    assert any("(APP-booking): using the build plan" in line for line in said)
    assert any(t == "CAP-014.FR1@APP-booking" for s in plan["stories"] for t in s["traces"])
    assert plan["ticketsHref"].endswith("docs/work/tickets.csv")


# ---------------------------------------------------------------- a real plan from the work-breakdown skill

HERON = REPO / "tests" / "fixtures" / "breakdown" / "heron-desktop-agent-breakdown.md"
HERON_COMPONENTS = ["CalendarSource", "SignIn / TokenStore", "FolderSource", "CallClassifier and ClientMatcher", "ManagedSettings", "RecordSource", "NoteAssembler",
                    "ContentCheck", "Rewriter", "PopulationFilter", "NoteScheduler", "NoteStore", "NoteWindow", "Diagnostics"]


def heron_entry(tmp_path, text=None):
    path = tmp_path / "desktop-agent-breakdown.md"
    path.write_text(HERON.read_text(encoding="utf-8") if text is None else text, encoding="utf-8")
    wrapped = plan_data.plans_for([f"APP-heron={path}"])["APP-heron"]
    design = {"path": "desktop-agent.md", "components": [{"name": n} for n in HERON_COMPONENTS], "trace": {}}
    return plan_data.plan_entry("APP-heron", wrapped, {"UNK-018"}, design)


def test_the_real_plan_reads_with_nothing_the_page_could_not_read(tmp_path):
    plan = heron_entry(tmp_path)
    assert plan["problems"] == [], plan["problems"]
    assert plan["totals"]["stories"] == 15 and plan["totals"]["tasks"] == 112


def test_a_story_carries_its_open_notes_and_the_criterion_it_conflicts_with(tmp_path):
    stories = {s["id"]: s for s in heron_entry(tmp_path)["stories"]}
    assert len(stories["S-06"]["openNotes"]) == 1 and stories["S-06"]["conflicts"] == []
    assert [c["ref"] for c in stories["S-11"]["conflicts"]] == ["EPC-001.AC5"]
    assert stories["S-11"]["conflicts"][0]["text"].startswith("Conflict with an epic criterion: EPC-001.AC5 says")
    assert stories["S-01"]["openNotes"] == [] and stories["S-01"]["conflicts"] == []


def test_a_note_that_names_its_own_story_does_not_make_it_wait_for_itself(tmp_path):
    stories = {s["id"]: s for s in heron_entry(tmp_path)["stories"]}
    assert "S-06" not in [b["ref"] for b in stories["S-06"]["blockers"]]
    assert [b["ref"] for b in stories["S-14"]["blockers"] if b["kind"] == "story"][:3] == ["S-03", "S-04", "S-05"]


def test_a_coverage_target_with_several_rows_is_all_of_them_and_a_component_may_be_named_in_parts(tmp_path):
    plan = heron_entry(tmp_path)
    by_target = {r["target"]: r for r in plan["coverage"]["targets"]}
    assert set(by_target["CAP-001.FR3@APP-heron"]["stated"]) == {"S-06", "S-07", "S-09", "S-10", "S-11", "S-12"}
    comp = next(c for c in plan["coverage"]["components"] if c["name"] == "CallClassifier and ClientMatcher")
    assert comp["stories"] == ["S-02", "S-08"]
    assert not any(c["name"].startswith("CAP-") for c in plan["coverage"]["components"]), "a requirement row is not a component"


def test_a_summary_size_written_as_counts_is_held_against_the_tasks_and_a_wrong_one_is_still_a_problem(tmp_path):
    text = HERON.read_text(encoding="utf-8").replace("| 2S 4M | G-001, UNK-013 |", "| 3S 4M | G-001, UNK-013 |", 1)
    plan = heron_entry(tmp_path, text)
    assert any("S-01: the summary table says its size is '3S 4M'" in p for p in plan["problems"]), plan["problems"]


def test_a_breakdown_path_outside_docs_plan_or_not_markdown_is_not_read(world, tmp_path):
    """E23. A page from outside can name any file; what is read ends up in dashboard.html and in every published copy."""
    vault, team = world
    private = tmp_path / "salary-notes.txt"
    shutil.copy(team / PRICING_PLAN, private)
    edit(vault / PRICING_PAGE, "id: APP-pricing\n", f"id: APP-pricing\nbreakdown: {private}\n")
    code, said = explore(vault)
    assert code == 0, said
    assert "is not a Markdown file, so it isn't read" in said, said
    assert data_of(vault)["plans"]["APP-pricing"]["file"] != "salary-notes.txt"
