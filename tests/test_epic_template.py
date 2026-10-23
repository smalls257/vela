"""The epic template: a summary with a Still open line, who it is for, then `## Done when` with one headed criterion each and
its stable AC id on the Trace line. Every reader of epic criteria keeps working with both this shape and the numbered one.

The Violation this guards is a Distributed Monolith: six places used to carry their own copy of "find the numbered lines
under the criteria heading". `criteria.read` is the one reader now, and these tests hold each consumer to it."""
import json
import re
import shutil

import pytest
from conftest import REPO, check, findings, run

import session_files
from vela import cli, criteria, export, parse, readability, trace
from vela.explorer import design_data, roles_data

HERON = REPO / "tests" / "sim" / "snapshots" / "heron-desk" / "after-full-1"
NUMBERED = REPO / "tests" / "fixtures" / "readable" / "EPC-001-calendar.md"  # the first shape, kept to prove both read
HEADED = REPO / "tests" / "fixtures" / "readable" / "EPC-001-calendar-headed.md"
EPIC_PATH = "13-epics/EPC-001-calendar.md"


def page_of(path):
    return parse.parse_page(EPIC_PATH, path.read_text(encoding="utf-8"))


def text_page(body):
    return parse.parse_page(EPIC_PATH, "---\nid: EPC-009\ntype: epic\n---\n" + body)


def vault_with(tmp_path, epic):
    vault = tmp_path / "heron"
    session_files.split_copy(HERON, vault)
    shutil.copy(epic, vault / EPIC_PATH)
    run("render", "--vault", str(vault))
    return vault


# ------------------------------------------------------------------------------------------------ the reader

def test_a_headed_criterion_takes_its_id_markers_and_ids_from_the_trace_line():
    found = criteria.read(page_of(HEADED))
    assert [c.n for c in found] == [1, 2, 3, 4, 5, 6, 7]
    first = found[0]
    assert (first.form, first.heading, first.markers, first.trace, first.declared, first.group) == (
        "headed", "One note ten minutes before a client call", ("testing",), ("CAP-001.FR1", "CON-001", "FLO-001"), True, "Timing of the note")
    assert first.text.startswith("For each call that counts") and "Trace" not in first.text
    assert found[4].markers == ("data",) and found[4].group == "Who is on the call"
    assert found[5].trace[-1] == "UNK-026"


def test_both_shapes_of_the_same_epic_read_the_same_criteria():
    old, new = criteria.read(page_of(NUMBERED)), criteria.read(page_of(HEADED))
    assert [c.n for c in old] == [c.n for c in new] == [1, 2, 3, 4, 5, 6, 7]
    assert [c.form for c in old] == ["numbered"] * 7 and [c.form for c in new] == ["headed"] * 7
    assert [c.trace for c in old][:4] == [c.trace for c in new][:4]
    assert old[0].group == "Timing of the note" and new[0].group == "Timing of the note"


def test_the_id_is_written_so_striking_or_adding_a_criterion_renumbers_nothing():
    page = text_page("## Done when\n\n### Gone\n\n~~Old.~~\n\n- Trace: CON-001  ·  AC2\n\n### Kept\n\nA sentence.\n\n- Trace: CON-001  ·  AC3\n")
    found = criteria.read(page)
    assert [(c.n, c.struck, c.heading) for c in found] == [(2, True, "Gone"), (3, False, "Kept")]
    page = text_page("## Done when\n\n### ~~Gone~~\n\nOld.\n\n- Trace: CON-001  ·  AC2  ·  [testing]\n")
    assert [(c.n, c.struck, c.heading, c.markers) for c in criteria.read(page)] == [(2, True, "Gone", ())]


def test_the_trace_line_reads_in_any_order_and_the_ids_exclude_the_ac_and_the_markers():
    parts = criteria.parse_trace("AC4  ·  [security] [data]  ·  CAP-001.FR1, CON-001")
    assert (parts.ids, parts.ac, parts.markers) == (("CAP-001.FR1", "CON-001"), 4, ("security", "data"))
    assert readability.trace_ids("   - Trace: CAP-001.FR1, CON-001  ·  AC4  ·  [testing]") == ["CAP-001.FR1", "CON-001"]
    assert readability.trace_ids("- Trace: AC4") == []


def test_a_criterion_with_no_ac_id_gets_the_next_free_number_and_says_so():
    page = text_page("## Done when\n\n### First\n\nA sentence.\n\n- Trace: CON-001  ·  AC1\n\n### Second\n\nAnother sentence.\n\n- Trace: CON-001\n")
    found = criteria.read(page)
    assert [(c.n, c.declared) for c in found] == [(1, True), (2, False)]
    assert [m for _, m in criteria.problems(page)] == ["The criterion 'Second' has no AC id on its Trace line, so nothing can refer to it by number."]


def test_two_criteria_sharing_an_ac_id_are_named():
    page = text_page("## Done when\n\n### One\n\nA.\n\n- Trace: CON-001  ·  AC1\n\n### Two\n\nB.\n\n- Trace: CON-001  ·  AC1\n")
    assert [m for _, m in criteria.problems(page)] == ["AC1 is on two criteria, 'One' and 'Two'."]


def test_a_numbered_line_under_a_subheading_still_makes_the_subheading_a_group():
    page = text_page("## Epic acceptance criteria\n\n### First\n\n1. One. [testing]\n   - Trace: CON-001\n\n### Second\n\n2. Two.\n")
    found = criteria.read(page)
    assert [(c.n, c.form, c.group, c.markers, c.trace) for c in found] == [
        (1, "numbered", "First", ("testing",), ("CON-001",)), (2, "numbered", "Second", (), ())]


def test_lines_in_fences_and_generated_blocks_and_other_sections_are_not_criteria():
    page = text_page("## Done when\n\n### Real\n\nA.\n\n- Trace: CON-001  ·  AC1\n\n```\n### In a fence\n\nText.\n- Trace: CON-001  ·  AC2\n```\n\n"
                     "## Out of scope\n\n### Not a criterion\n\nText.\n\n- Trace: CON-001  ·  AC3\n")
    assert [c.heading for c in criteria.read(page)] == ["Real"]


# ------------------------------------------------------------------------------------------------ the consumers

def test_concern_markers_on_the_trace_line_count_for_the_trace_rules():
    assert trace.ac_markers(page_of(HEADED)) == {"testing", "data"}


def test_vela_check_reads_the_headed_epic_with_no_error_and_no_reading_load_warning(tmp_path):
    code, out = check(vault_with(tmp_path, HEADED), "2026-10-12")
    assert code == 0, out
    mine = [line for line in out.splitlines() if line.startswith(EPIC_PATH)]
    assert not [line for line in mine if re.search(r" (E\d+|W36\d|W370) ", line)], mine


def test_vela_check_reads_the_numbered_epic_as_before(tmp_path):
    code, out = check(vault_with(tmp_path, NUMBERED), "2026-10-12")
    assert code == 0, out
    assert not [c for c, p in findings(out) if p == EPIC_PATH and c in ("W364", "W370")]


def test_w370_names_a_headed_criterion_with_no_id(tmp_path):
    text = HEADED.read_text(encoding="utf-8").replace("  ·  AC3\n", "\n")
    bad = tmp_path / "bad.md"
    bad.write_text(text, encoding="utf-8")
    code, out = check(vault_with(tmp_path, bad), "2026-10-12")
    line = next(line for line in out.splitlines() if " W370 " in line)
    assert code == 0 and line.startswith(EPIC_PATH) and "A move moves the note" in line and "AC<n>" in line


def test_w364_counts_headed_criteria_too(tmp_path):
    many = "".join(f"### Result {n}\n\nThe till shows result {n}.\n\n- Trace: CON-001  ·  AC{n}\n\n" for n in range(1, 11))
    text = HEADED.read_text(encoding="utf-8")
    start, end = text.index("## Done when"), text.index("## Traces to")
    big = tmp_path / "big.md"
    big.write_text(text[:start] + "## Done when\n\n" + many + text[end:], encoding="utf-8")
    code, out = check(vault_with(tmp_path, big), "2026-10-12")
    assert ("W364", EPIC_PATH) in findings(out)


def test_the_ticket_export_carries_the_headed_criterion_with_its_stable_id():
    old, new = export.criteria(page_of(NUMBERED)), export.criteria(page_of(HEADED))
    assert len(old) == len(new) == 7
    assert new[0].startswith("AC1. One note ten minutes before a client call: For each call that counts")
    assert old[0].startswith("1. For each call that counts")


@pytest.mark.parametrize("source,form", [(NUMBERED, "numbered"), (HEADED, "headed")])
def test_the_explorer_reads_either_shape(tmp_path, source, form):
    vault = vault_with(tmp_path, source)
    code, said = run("explore", str(vault), "--today", "2026-10-12")
    assert code == 0, said
    page = (vault / "dashboard.html").read_text(encoding="utf-8")
    data = json.loads(re.search(r'<script type="application/json" id="data">(.*?)</script>', page, re.S).group(1))
    rows = data["epicCriteria"]["EPC-001"]
    assert [r["n"] for r in rows] == [1, 2, 3, 4, 5, 6, 7]
    assert all(r["trace"].startswith('<details class="r-trace">') for r in rows)
    assert bool(rows[0]["heading"]) == (form == "headed")
    assert rows[0]["html"] and "Trace" not in rows[0]["html"]


def test_a_design_may_cite_a_headed_criterion_by_its_id_even_when_the_numbers_have_gaps():
    page = text_page("## Done when\n\n### A\n\nA.\n\n- Trace: CON-001  ·  AC2\n\n### B\n\nB.\n\n- Trace: CON-001  ·  AC5\n")
    assert design_data.epic_criteria_numbers(page) == [2, 5]


def test_the_roles_data_rows_keep_the_numbered_shape_they_always_had():
    vault = cli.load_vault(HERON)
    rows = roles_data.epic_criteria(vault, type("K", (), {"page": lambda self, p: p.id, "names": readability.NameIndex(vault),
                                                         "key_of": lambda self, e: e.id,
                                                         "without_sessions": lambda self, text, page: text})())
    assert rows["EPC-001"] and set(rows["EPC-001"][0]) == {"n", "heading", "html", "markers", "struck", "group", "trace"}
