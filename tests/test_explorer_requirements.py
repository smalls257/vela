"""The Requirements section's data (explorer/reqs_data.py), on the Heron test plan (tests/fixtures/team-skills/heron-plan).

    python3 -m pytest -q tests/test_explorer_requirements.py

The Violation these guard against is a Paper Tiger: a page that says "met" because every table row exists. The plan cannot see
code or tests, so a row says how many of six checks are met so far, and a check it cannot work out says why in words. Each
case names a thing that must NOT count (an inkling row, a deferred story, a design that traces another requirement) as firmly
as the things that do. The page's drawing is checked by the browser selftest (test_explorer_requirements_browser.py).
"""
import json
import re
import shutil

import pytest

from conftest import REPO, edit, run
from vela import releases, say

HERON = REPO / "tests" / "fixtures" / "team-skills" / "heron-plan"
DATA = re.compile(r'<script type="application/json" id="data">(.*?)</script>', re.S)
TODAY = "2026-10-26"
SIX = ["carried", "release", "epic", "designed", "stories", "open"]
DESKTOP_PAGE = "05-building-blocks/desktop-agent-building-blocks.md"


def dashboard(vault):
    code, out = run("explore", str(vault), "--today", TODAY)
    assert code == 0, out
    page = (vault / "dashboard.html").read_text(encoding="utf-8")
    return json.loads(DATA.search(page).group(1))


@pytest.fixture(scope="module")
def heron(tmp_path_factory):
    vault = tmp_path_factory.mktemp("heron") / "vault"
    shutil.copytree(HERON, vault)
    return dashboard(vault)


def rows_of(data):
    return {r["id"]: r for r in data["requirements"]["rows"]}


def verdicts(row):
    return {c["k"]: c["v"] for c in row["checks"]}


def test_every_requirement_has_a_row_with_the_six_checks_in_the_order_the_work_goes(heron):
    rows = heron["requirements"]["rows"]
    assert [r["id"] for r in rows] == ["CAP-001.FR1", "CAP-001.FR2", "CAP-002.FR1", "CAP-002.FR2", "CAP-003.FR1", "CAP-003.FR2", "CAP-004.FR1", "CAP-005.FR1", "CAP-005.FR2"]
    assert all([c["k"] for c in r["checks"]] == SIX for r in rows)
    assert all(r["met"] == sum(1 for c in r["checks"] if c["v"] == "yes") for r in rows)
    assert heron["requirements"]["notKnown"].startswith("Built and tested: not something the plan knows")


def test_the_requirement_whose_every_check_passes_is_the_one_every_app_and_story_covers(heron):
    row = rows_of(heron)["CAP-005.FR2"]
    assert row["met"] == 6 and set(verdicts(row).values()) == {"yes"}
    assert [a["name"] for a in row["apps"]] == ["Desktop agent"]
    assert row["stories"][0]["stories"] == ["S-03"] and row["designs"][0]["components"] == ["ConsentRecorder", "LocalStore"]


def test_a_requirement_on_no_release_with_its_only_story_put_off_says_both_in_words(heron):
    row = rows_of(heron)["CAP-001.FR1"]
    assert verdicts(row) == {"carried": "yes", "release": "no", "epic": "yes", "designed": "part", "stories": "no", "open": "no"}
    assert row["release"] is None
    assert row["stories"][1]["putOff"] and row["stories"][1]["stories"] == ["S-11"]
    long = {c["k"]: c["long"] for c in row["checks"]}
    assert long["release"] == "on no release, so nothing says when it ships"
    assert long["stories"] == "every story for it is put off in Desktop agent's breakdown and no review date is recorded"
    assert sorted(row["questions"]) == ["UNK-059", "UNK-064", "UNK-072"]


def test_a_requirement_designed_by_one_of_three_apps_is_part_and_names_who_has_no_design(heron):
    row = rows_of(heron)["CAP-003.FR1"]
    assert verdicts(row)["designed"] == "part" and verdicts(row)["stories"] == "part"
    assert [d["designed"] for d in row["designs"]] == [False, True, False]
    assert row["designs"][1]["components"] == ["ConsentGate", "NoteClient"]
    long = {c["k"]: c["long"] for c in row["checks"]}
    assert long["designed"] == "no tech design yet from Consent and identity or Summarizer (the others trace it)"
    assert long["stories"] == "no breakdown yet from Consent and identity or Summarizer"
    assert row["questions"] == ["UNK-064"]
    assert row["release"]["short"] == "February pilot" and row["release"]["date"] == "February 2, 2027"
    assert row["epics"] == [{"key": "EPC-033", "criteria": 1}]


def test_the_criteria_come_with_the_ids_their_trace_lines_name(heron):
    first = rows_of(heron)["CAP-003.FR1"]["criteria"][0]
    assert first["trace"] == ["CAP-001.FR1"] and first["text"].startswith("The digest draws only on")
    held = rows_of(heron)["CAP-003.FR2"]["criteria"]
    assert any("UNK-074" in c["trace"] for c in held)


def test_an_open_question_named_only_on_a_criterion_still_holds_the_requirement(heron):
    """UNK-075 blocks no requirement by its Blocks line; an epic criterion for CAP-003.FR2 names it."""
    row = rows_of(heron)["CAP-003.FR2"]
    assert "UNK-075" in row["questions"] and "UNK-074" in row["questions"]


def test_counts_are_the_rows_each_filter_keeps_and_the_lede_says_them_without_codes(heron):
    data = heron["requirements"]
    rows = data["rows"]
    assert data["counts"] == {"all": 9, "gap": 8, "held": 6, "design": 8}
    for f, n in data["counts"].items():
        assert n == sum(1 for r in rows if f in r["in"])
    assert "9 requirements, none decided yet" in data["lede"] and "only Desktop agent has a tech design" in data["lede"]
    words = [data["lede"], data["notKnown"]] + [c[k] for r in rows for c in r["checks"] for k in ("short", "long")]
    assert [w for w in words if say.leak_in(w)] == []
    assert not re.search(r"\b\d{4}-\d{2}-\d{2}\b", " ".join(words))


def test_an_inkling_allocation_row_carries_nothing(tmp_path):
    """CONVENTIONS: only a row at assumption or later counts as the requirement's owner."""
    vault = tmp_path / "vault"
    shutil.copytree(HERON, vault)
    page = vault / DESKTOP_PAGE
    text = page.read_text(encoding="utf-8")
    row = next(l for l in text.splitlines() if "CAP-005.FR2" in l and l.startswith("|"))
    assert row.rstrip().endswith("| assumption |"), row
    page.write_text(text.replace(row, row.replace("| assumption |", "| inkling |")), encoding="utf-8")
    one = rows_of(dashboard(vault))["CAP-005.FR2"]
    assert verdicts(one)["carried"] == "no" and one["apps"] == []
    assert "Desktop agent only guessed at a share" in {c["k"]: c["long"] for c in one["checks"]}["carried"]
    assert verdicts(one)["designed"] == "no" and verdicts(one)["stories"] == "no"  # nothing carries it, so nothing can design or build it


def test_a_requirement_left_out_of_the_tracer_keeps_the_reason_the_check_quotes(tmp_path):
    vault = tmp_path / "vault"
    shutil.copytree(HERON, vault)
    edit(vault / "04b-releases.md", "- **State:** assumption\n\n| Delivers |", "- **State:** assumption\n- **Tracer:** none, no tracer yet\n- **Not in the tracer:** Reading transcripts (CAP-001.FR1): waits on the CISO review of December 4\n\n| Delivers |")
    row = rows_of(dashboard(vault))["CAP-001.FR1"]
    release = next(c for c in row["checks"] if c["k"] == "release")
    assert release["v"] == "no" and "Not in the tracer says why: waits on the CISO review of December 4" in release["long"]


def test_a_criterion_counts_the_same_for_the_release_check_and_the_page():
    """releases.criteria_count and the requirement's criteria list are one reader."""
    from vela import allocation, cli
    vault = cli.load_vault(HERON)
    for req in allocation.requirements(vault):
        assert releases.criteria_count(req) == len(releases.requirement_criteria(req))
    assert len(releases.requirement_criteria(vault.item("CAP-003.FR2"))) == 5
