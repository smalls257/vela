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
    # one app put it off and the other two have no breakdown at all: the sentence covers each carrying app (S2)
    assert long["stories"] == ("put off in the breakdown of Desktop agent, and no review date is recorded; "
                               "no breakdown yet from Consent and identity or Summarizer")
    assert row["checks"][4]["short"] == "put off"
    assert sorted(row["questions"]) == ["UNK-059", "UNK-064", "UNK-072"]


def test_a_requirement_designed_by_one_of_three_apps_is_part_and_names_who_has_no_design(heron):
    row = rows_of(heron)["CAP-003.FR1"]
    assert verdicts(row)["designed"] == "part" and verdicts(row)["stories"] == "part"
    assert [d["designed"] for d in row["designs"]] == [False, True, False]
    assert row["designs"][1]["components"] == ["ConsentGate", "NoteClient"]
    long = {c["k"]: c["long"] for c in row["checks"]}
    assert long["designed"] == "no tech design yet from Consent and identity or Summarizer; Desktop agent traces it"
    assert long["stories"] == "no breakdown yet from Consent and identity or Summarizer"
    assert row["questions"] == ["UNK-064"]
    assert row["release"]["short"] == "February pilot, Client Delivery London" and row["release"]["date"] == "February 2, 2027"
    assert row["release"]["key"] == "release:1"
    # the name is the lead's heading, quoted, never a guessed article ("delivered in the the rest"), and the unknown a note names is said as a question
    release = {c["k"]: c["long"] for c in row["checks"]}["release"]
    assert release == ("delivered in “Release one: February pilot, Client Delivery London”, February 2, 2027; "
                       "dropped if the answer to “Digest as client record” says the digest is a client record")
    assert row["epics"] == [{"key": "EPC-033", "criteria": 1}]


def test_the_criteria_come_with_the_ids_their_trace_lines_name(heron):
    first = rows_of(heron)["CAP-003.FR1"]["criteria"][0]
    assert [t["id"] for t in first["trace"]] == ["CAP-001.FR1"] and first["text"].startswith("The digest draws only on")
    assert first["trace"][0]["key"] == "CAP-001.FR1" and not first["trace"][0]["waits"]
    held = rows_of(heron)["CAP-003.FR2"]["criteria"]
    waiting = [t for c in held for t in c["trace"] if t["waits"]]
    assert [t["id"] for t in waiting] == ["UNK-074"] and waiting[0]["said"].startswith("waits on: ")


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


def test_each_requirement_lists_the_criteria_it_always_did():
    """The counts vela-next's own bullet counter gave on this plan before the reader moved (measured there), not derived from it."""
    from vela import allocation, cli
    vault = cli.load_vault(HERON)
    counts = {r.id: releases.criteria_count(r) for r in allocation.requirements(vault)}
    assert counts == {"CAP-001.FR1": 5, "CAP-001.FR2": 5, "CAP-002.FR1": 8, "CAP-002.FR2": 8, "CAP-003.FR1": 5, "CAP-003.FR2": 5,
                      "CAP-004.FR1": 5, "CAP-005.FR1": 7, "CAP-005.FR2": 4}


# --------------------------------------------------------------------------- the review's scenario vaults

def changed(tmp_path, page, old, new, name="vault"):
    vault = tmp_path / name
    shutil.copytree(HERON, vault)
    edit(vault / page, old, new)
    return vault


CAP1 = "capabilities/CAP-001-read-calendar-and-transcripts.md"
FIRST_FR2_CRITERION = "- Reads only the signed-in person's own calendar.\n"


def own_criterion_trace(tmp_path, unknown):
    page = (HERON / CAP1).read_text(encoding="utf-8")
    first = next(l for l in page.split("### CAP-001.FR2")[1].splitlines() if l.startswith("- ") and "**" not in l)
    return changed(tmp_path, CAP1, first + "\n", first + f"\n  - Trace: {unknown}\n")


def test_an_open_question_on_the_requirements_own_criterion_holds_it_and_the_chip_says_the_same(tmp_path):
    """M1: the check and the panel's chip are one answer, from Python."""
    row = rows_of(dashboard(own_criterion_trace(tmp_path, "UNK-071")))["CAP-001.FR2"]
    assert "UNK-071" in row["questions"] and verdicts(row)["open"] == "no" and "held" in row["in"]
    chips = [t for c in row["criteria"] for t in c["trace"] if t["id"] == "UNK-071"]
    assert len(chips) == 1 and chips[0]["waits"] and chips[0]["said"].startswith("waits on: ")


def test_a_resolved_question_on_the_requirements_own_criterion_holds_nothing(tmp_path):
    row = rows_of(dashboard(own_criterion_trace(tmp_path, "UNK-053")))["CAP-001.FR2"]
    assert "UNK-053" not in row["questions"] and verdicts(row)["open"] == "yes"
    chip = next(t for c in row["criteria"] for t in c["trace"] if t["id"] == "UNK-053")
    assert not chip["waits"] and chip["key"] == "UNK-053"


def test_a_trace_line_of_words_makes_no_chips_a_constraint_opens_its_page_and_a_missing_id_says_so(tmp_path, heron):
    rows = rows_of(heron)
    assert all(c["trace"] == [] for c in rows["CAP-002.FR1"]["criteria"] if "none that morning" in c["text"])  # "Trace: the Summarizer runtime page" is prose
    cst = next(t for c in rows["CAP-001.FR1"]["criteria"] for t in c["trace"] if t["id"] == "CST-008")
    assert cst["key"] == "read:constraints" and cst["said"].startswith("Teams transcripts exist only where")
    row = rows_of(dashboard(own_criterion_trace(tmp_path, "CAP-999")))["CAP-001.FR2"]
    lost = next(t for c in row["criteria"] for t in c["trace"] if t["id"] == "CAP-999")
    assert lost["key"] == "" and lost["said"] == "not in this plan"


def test_a_design_that_does_not_trace_it_is_not_a_missing_design(tmp_path):
    """S1: Desktop agent has a design; it just lacks the row. The words and the next step say so."""
    vault = changed(tmp_path, "docs/tech-design/desktop-agent.md", "| CAP-003.FR2@APP-desktop-agent | NoteClient |\n", "")
    row = rows_of(dashboard(vault))["CAP-003.FR2"]
    designed = next(c for c in row["checks"] if c["k"] == "designed")
    assert designed["v"] == "no"
    assert designed["long"] == "no tech design yet from Summarizer; Desktop agent's tech design does not trace it"
    assert "Add it to the Trace table of the tech design of Desktop agent." in designed["next"]
    assert [(d["title"], d["say"]) for d in row["designs"]] == [("Design does not trace it", "Desktop agent: its tech design does not trace it"),
                                                              ("No design yet", "Summarizer: no tech design yet")]


def test_a_design_entry_for_another_apps_share_does_not_count_for_this_app(tmp_path):
    """N5."""
    vault = changed(tmp_path, "docs/tech-design/desktop-agent.md", "| CAP-003.FR2@APP-desktop-agent | NoteClient |", "| CAP-003.FR2@APP-summarizer | NoteClient |")
    row = rows_of(dashboard(vault))["CAP-003.FR2"]
    assert [d["designed"] for d in row["designs"]] == [False, False]


def test_a_requirement_is_grouped_by_the_page_it_is_written_on_not_by_its_id_prefix(tmp_path):
    """S5: CAP-005's page has a mistyped id; its requirements still sit under their own page, with its title."""
    vault = changed(tmp_path, "capabilities/CAP-005-record-persons-consent.md", "id: CAP-005\n", "id: CAP-055\n")
    rows = rows_of(dashboard(vault))
    assert rows["CAP-005.FR1"]["capabilityKey"] == "CAP-055" and rows["CAP-005.FR1"]["capabilityTitle"] == "Record a person's consent"
    assert rows["CAP-004.FR1"]["capabilityKey"] == "CAP-004"


def test_a_requirement_whose_capability_page_is_gone_is_named_and_not_dropped_in_silence(tmp_path):
    """N10: the allocation and the release still name CAP-005.FR1 and FR2."""
    vault = tmp_path / "vault"
    shutil.copytree(HERON, vault)
    (vault / "capabilities" / "CAP-005-record-persons-consent.md").unlink()
    data = dashboard(vault)["requirements"]
    assert len(data["rows"]) == 7
    assert [o["id"] for o in data["orphans"]] == ["CAP-005.FR1", "CAP-005.FR2"]
    assert "named by" in data["orphans"][0]["said"] and "no requirement of that ID is written" in data["orphans"][0]["said"]


def test_a_release_row_of_some_criteria_says_which_in_words(tmp_path):
    vault = changed(tmp_path, "04b-releases.md", "CAP-004.FR1 Write a prep note for one meeting\\|Write a prep note for one meeting]] | all |", "CAP-004.FR1 Write a prep note for one meeting\\|Write a prep note for one meeting]] | AC1, AC2 |")
    long = next(c["long"] for c in rows_of(dashboard(vault))["CAP-004.FR1"]["checks"] if c["k"] == "release")
    assert "only criteria 1 and 2 of it" in long


def test_what_to_do_is_said_with_session_names_never_slash_commands(heron):
    words = [c["next"] for r in heron["requirements"]["rows"] for c in r["checks"]] + [heron["requirements"]["lede"]]
    assert not [w for w in words if "/vela:" in w]
