"""planner next reaches /planner:requirements and /planner:allocate on a vault whose epics were cut without them,
and planner capture counts the links the skills now ask for."""
import json
import shutil

from conftest import REPO, edit, run

SNAPSHOTS = REPO / "tests" / "sim" / "snapshots"
NO_REQUIREMENTS = SNAPSHOTS / "trading-coach" / "after-80b"
WITH_RELEASE = SNAPSHOTS / "trading-coach" / "after-capture-boundary"
EMPTY = SNAPSHOTS / "coastal-merger" / "empty"
CAP_1 = "capabilities/CAP-001-teach-a-stock-lesson.md"
TODAY = "2026-10-11"


def copy(source, tmp_path):
    vault = tmp_path / "v"
    shutil.copytree(source, vault)
    return vault


def said(vault):
    return run("next", "--vault", str(vault), "--today", TODAY)[1]


def test_next_names_requirements_on_a_vault_with_epics_and_no_requirements_even_with_a_probe_open():
    assert said(NO_REQUIREMENTS).startswith("planner next: for the whole plan: write the requirements for Teach a stock lesson (CAP-001)"), said(NO_REQUIREMENTS)


def test_next_names_allocate_once_a_requirement_exists_and_no_app_carries_it(tmp_path):
    vault = copy(NO_REQUIREMENTS, tmp_path)
    (vault / CAP_1).write_text((WITH_RELEASE / CAP_1).read_text(encoding="utf-8"), encoding="utf-8")
    assert said(vault).startswith("planner next: for the whole plan: decide which app owns Learn one stock at a time (CAP-001.FR1)"), said(vault)


def test_a_partly_filled_vault_with_a_release_still_goes_on_to_its_open_question():
    assert said(WITH_RELEASE).startswith("planner next: Coach: ask about "), said(WITH_RELEASE)


def test_an_overdue_question_still_comes_before_requirements(tmp_path):
    vault = copy(NO_REQUIREMENTS, tmp_path)
    code, out = run("next", "--vault", str(vault), "--today", "2031-01-01")
    assert out.startswith("planner next: Coach: ask about "), out


def test_an_empty_vault_still_starts_with_dump_or_discover():
    assert said(EMPTY).startswith("planner next: for the whole plan: no app page exists yet"), said(EMPTY)


def test_capture_counts_apps_with_a_code_link_and_epics_with_a_tracker_link_as_info(tmp_path):
    vault = copy(NO_REQUIREMENTS, tmp_path)
    code, out = run("capture", "--vault", str(vault))
    assert code == 0 and "  info  0 of 2 apps have a code or wiki link; 0 of 3 epics have a tracker link." in out, out
    edit(vault / "05-building-blocks" / "coach-building-blocks.md", "\ntype: app-building-blocks\n",
         "\ntype: app-building-blocks\nlinks: {Repo: https://code.example.com/coach}\n")
    edit(vault / "13-epics" / "EPC-001-coach-lessons-and-list.md", "\ntype: epic\n",
         "\ntype: epic\nlinks: {Tracker: https://tracker.example.com/browse/COA-1}\n")
    counts = json.loads(run("capture", "--vault", str(vault), "--json")[1])["counts"]
    assert (counts["apps_with_link"], counts["epics_with_link"]) == (1, 1)
    assert "  info  1 of 2 apps have a code or wiki link; 1 of 3 epics have a tracker link." in run("capture", "--vault", str(vault))[1]
