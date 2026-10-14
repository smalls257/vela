"""Where a slice's recorded flow check stands now (flowcheck/standing.py), as the handoff and the dashboard say it: from
the record check-slice writes, read by its own reader, and never a pass the record does not hold (R0)."""
from conftest import REPO

from planner import flowcheck, handoff
from planner.flowcheck import readers, record, standing

FIXTURES = REPO / "tests" / "fixtures" / "flowcheck"
TODAY = "2026-10-14"
HOLD_FLOW = "06-runtime/flows/FLO-501-place-a-hold.md"


def files_of(case="30-impact-walk"):
    root = FIXTURES / case
    return {p.relative_to(root).as_posix(): p.read_text(encoding="utf-8") for p in sorted(root.rglob("*")) if p.is_file()}


def recorded(catalog, key, version="v1", max_states=flowcheck.DEFAULT_MAX_STATES, max_seconds=flowcheck.DEFAULT_MAX_SECONDS,
             budget=True):
    """The store check-slice writes for one slice, through record's own writer and reader."""
    prepared = flowcheck.prepare(catalog, key, TODAY)
    explored = flowcheck.explore_prepared(prepared, max_states, max_seconds)
    result = flowcheck.finish(catalog, prepared, explored, TODAY)
    kept = record.to_record(result, explored, record.fingerprint(prepared, max_states, max_seconds, version), TODAY,
                            (max_states, max_seconds) if budget else None)
    store, warning = record.read_store(record.dump_store({"format": record.FORMAT, "slices": {key: kept}}))
    assert warning == ""
    return store


def test_a_slice_with_no_record_is_not_checked_never_passed():
    catalog = readers.read_vault(files_of())
    found = standing.standing(catalog, {"format": 1, "slices": {}}, "SLC-001", TODAY, "v1")
    assert (found.state, found.words, found.passed) == (standing.MISSING, "not checked", False)
    assert found.line() == "not checked. No full flow check of it has been recorded yet."


def test_a_record_that_holds_says_passed_with_its_date():
    catalog = readers.read_vault(files_of())
    found = standing.standing(catalog, recorded(catalog, "SLC-001"), "SLC-001", TODAY, "v1")
    assert (found.state, found.words, found.checked) == (standing.PASSED, "passed", TODAY)
    assert found.line() == f"passed, recorded {TODAY}"


def test_a_record_of_a_slice_that_changed_since_is_not_checked_since_its_date():
    files = files_of()
    store = recorded(readers.read_vault(files), "SLC-001")
    files[HOLD_FLOW] = files[HOLD_FLOW].replace("END held", "END kept_aside")
    assert "kept_aside" in files[HOLD_FLOW]
    found = standing.standing(readers.read_vault(files), store, "SLC-001", TODAY, "v1")
    assert (found.state, found.words, found.passed) == (standing.STALE, f"not checked since {TODAY}", False)
    # another checker's record does not hold either
    again = standing.standing(readers.read_vault(files_of()), store, "SLC-001", TODAY, "v2")
    assert again.state == standing.STALE and again.open == ()


def test_findings_are_counted_and_named():
    catalog = readers.read_vault(files_of("01-unhandled-409"))
    found = standing.standing(catalog, recorded(catalog, "FLO-001"), "FLO-001", TODAY, "v1")
    assert (found.state, found.words) == (standing.FINDINGS, "1 finding")
    assert found.open and found.line().startswith("1 finding (")


def test_a_check_that_stopped_early_is_not_fully_checked():
    catalog = readers.read_vault(files_of())
    store = recorded(catalog, "SLC-002", max_states=1)
    found = standing.standing(catalog, store, "SLC-002", TODAY, "v1")
    assert (found.state, found.words, found.passed) == (standing.NOT_FULLY, "not fully checked", False)
    # an old record that does not say its budget is judged against the defaults, so a small run reads as stale
    old = recorded(catalog, "SLC-002", max_states=1, budget=False)
    assert standing.standing(catalog, old, "SLC-002", TODAY, "v1").state == standing.STALE


def test_a_record_that_does_not_read_is_not_a_pass():
    catalog = readers.read_vault(files_of())
    store = recorded(catalog, "SLC-001")
    store["slices"]["SLC-001"]["explored"] = {"findings": [{"nonsense": 1}]}
    assert standing.standing(catalog, store, "SLC-001", TODAY, "v1").state == standing.STALE
    store, warning = record.read_store("{half")
    assert warning and standing.standing(catalog, store, "SLC-001", TODAY, "v1").state == standing.MISSING


def test_the_handoff_record_lists_each_slice_s_check_and_still_reads():
    catalog = readers.read_vault(files_of())
    store = recorded(catalog, "SLC-001")
    found = standing.standings(catalog, store, ["SLC-001", "SLC-002"], TODAY, "v1")

    class Slice:
        def __init__(self, key, label):
            self.key, self.label = key, label
    lines = handoff.check_lines([Slice("SLC-001", "SLC-001 Hold an item"), Slice("SLC-002", "SLC-002 Pay for it")], found)
    assert lines == [f"- SLC-001 Hold an item: passed, recorded {TODAY}",
                     "- SLC-002 Pay for it: not checked. No full flow check of it has been recorded yet."]
    entry = handoff.Entry("APP-x", "app", "05-building-blocks/x.md", "decided", "0123456789ab")
    text = handoff.write("APP-x", [entry], "abc1234", TODAY, (), "X", lines)
    assert handoff.CHECKS_HEADING in text and lines[1] in text
    facts, entries = handoff.read(text)  # the section is the senior's to read; the table is unchanged
    assert entries == [entry] and facts["App"] == "APP-x"
