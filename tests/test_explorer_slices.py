"""The dashboard's Slices view and the tracer tag, both read from slices.read_slices (slices_data.py), and the build
plan grouped by slice. The browser draws them; these check what the build hands it."""
import shutil

from test_explorer import BOOKING, booking, built  # noqa: F401  (booking is a fixture)

from vela import breakdown
from vela.explorer import plan_data


def test_the_slices_view_reads_the_slice_pages(booking):  # noqa: F811
    _, data = booking
    P, E = data["slicePlan"], data["entities"]
    assert P["onPages"] and P["statuses"] == ["planned", "building", "journey passes", "live but off", "on"]
    rows = {x["id"]: x for x in P["list"]}
    assert [x["id"] for x in P["list"]] == ["SLC-001", "SLC-002", "SLC-003", "SLC-004"]
    assert [(i, rows[i]["after"]) for i in rows] == [("SLC-001", []), ("SLC-002", ["SLC-001"]), ("SLC-003", ["SLC-002"]), ("SLC-004", ["SLC-001"])]
    assert rows["SLC-001"]["tracer"] and not rows["SLC-002"]["tracer"]
    assert all(x["status"] == "" for x in P["list"])  # none planned yet: the view says so
    assert all(E[x["key"]]["kind"] == "slice" for x in P["list"])
    assert [f["id"] for f in rows["SLC-001"]["flows"]] == ["FLO-001", "FLO-003"]
    assert all(E[f["key"]]["kind"] == "flow" for f in rows["SLC-001"]["flows"])
    # FLO-001's steps name the pairs that cross Booking (CON-001 from each channel, CON-002 to Notifications); FLO-002 and FLO-003 name none
    hold = ["APP-booking", "APP-call-center", "APP-kiosks", "APP-notifications", "APP-website"]
    assert {x["id"]: ([j["id"] for j in x["joins"]], x["apps"]) for x in P["list"]} == {
        "SLC-001": (["CON-001", "CON-002"], hold), "SLC-002": (["CON-001", "CON-002"], hold),
        "SLC-003": (["CON-001", "CON-002"], hold), "SLC-004": ([], [])}
    assert all(x["check"]["status"] == "not fully checked" and x["check"]["open"] == ["unreadable or undeclared"] and x["overdue"] == "" for x in P["list"])  # as W391 says
    assert rows["SLC-003"]["notIn"][0]["text"].startswith("Amend and cancel at a kiosk")
    section = next(s for s in data["sections"] if s["id"] == "slices")
    assert section["children"] == [x["key"] for x in P["list"]]


KIOSK_FLOW = """---
id: FLO-009
type: flow
title: A kiosk books
state: assumption
owner: "@hl-solution-lead"
authored: authored
---

# A kiosk books

A customer at a kiosk holds a seat.

## Steps

1. [[kiosks-building-blocks|Kiosks]] → [[booking-building-blocks|Booking]]: holds a seat, over [[booking-building-blocks#CON-001 Booking API|Booking API]].
"""


def test_a_row_carries_its_joins_both_sides_the_apps_in_it_and_a_journey_past_due(tmp_path):
    vault = tmp_path / "v"
    shutil.copytree(BOOKING, vault)
    (vault / "06-runtime" / "flows" / "FLO-009-a-kiosk-books.md").write_text(KIOSK_FLOW, encoding="utf-8")
    page = next((vault / "slices").glob("SLC-003-*.md"))
    page.write_text(page.read_text(encoding="utf-8").replace("[[FLO-001-hold-pay-confirm|FLO-001]]", "[[FLO-009-a-kiosk-books|FLO-009]]")
                    .replace("- **Owner:**", "- **Status:** building\n- **Journey due:** 2026-11-19\n- **Owner:**", 1), encoding="utf-8")
    _, data = built(tmp_path, vault, "2026-11-20", "kiosk")
    row = next(x for x in data["slicePlan"]["list"] if x["id"] == "SLC-003")
    assert row["joins"] == [{"id": "CON-001", "key": "CON-001", "from": "Kiosks", "to": "Booking"}]
    assert [data["entities"][a]["id"] for a in row["apps"]] == ["APP-booking", "APP-kiosks"]
    assert row["journeyDue"] == "2026-11-19" and row["overdue"].endswith("journey by November 19, 2026, and nothing says how it went")
    assert row["check"]["status"] == "not fully checked"  # building with nothing drawn: what check's W395 says
    key = row["key"]
    assert data["lights"][key]["level"] == "warning" and data["ranked"][0] == key  # it is in What needs you


def test_a_row_carries_its_flow_check_state_and_overrides_with_their_end_dates(tmp_path):
    from test_slices import FLOWCHECK, page, write
    rule = '- **Override:** "F8 CON-020 declined until 2026-10-01" by @lead on 2026-09-13: the refund flow lands next sprint\n'
    vault = tmp_path / "v"
    shutil.copytree(FLOWCHECK / "05-hold-never-released", vault)
    write(vault, "SLC-001", page("SLC-001", "Hold and pay", "**Status:** planned", "**Flows:** [[FLO-005-05-hold-never-released|FLO-005]]",
                                 extra="\n## Overrides\n\n" + rule))
    _, data = built(tmp_path, vault, "2026-10-13", "checked")
    check = data["slicePlan"]["list"][0]["check"]
    assert check["status"] == "fails" and check["open"] == ["stops halfway"] and check["covered"] == 0
    assert [(o["code"], o["item"], o["until"], o["ended"]) for o in check["overrides"]] == [("F8", "CON-020", "2026-10-01", True)]


def test_a_row_says_the_last_full_check_as_recorded_and_never_a_pass_the_record_does_not_hold(tmp_path):
    """The dashboard reads check-slice's record through flowcheck.standing: no record is "not checked", a record that
    holds says its result and date, and a slice changed since says "not checked since"."""
    from conftest import run
    from test_slices import FLOWCHECK, page, write
    vault = tmp_path / "v"
    shutil.copytree(FLOWCHECK / "05-hold-never-released", vault)
    write(vault, "SLC-001", page("SLC-001", "Hold and pay", "**Status:** planned", "**Flows:** [[FLO-005-05-hold-never-released|FLO-005]]"))
    _, data = built(tmp_path, vault, "2026-10-13", "none")
    assert data["slicePlan"]["list"][0]["recorded"]["state"] == "not checked"
    assert run("check-slice", "SLC-001", "--vault", str(vault), "--today", "2026-10-13")[0] == 1
    _, data = built(tmp_path, vault, "2026-10-13", "held")
    said = data["slicePlan"]["list"][0]["recorded"]
    assert (said["state"], said["words"], said["checked"], said["open"]) == ("findings", "1 finding", "2026-10-13", ["stops halfway"])
    flow = next((vault / "06-runtime" / "flows").glob("FLO-005-*.md"))
    flow.write_text(flow.read_text(encoding="utf-8").replace("END declined", "END refused", 1), encoding="utf-8")
    _, data = built(tmp_path, vault, "2026-10-14", "later")
    said = data["slicePlan"]["list"][0]["recorded"]
    assert said["state"] == "stale" and said["words"] == "not checked since 2026-10-13" and not said["passed"]


def test_the_tracer_reads_from_the_tracer_slice_and_from_release_one_without_slice_pages(booking, tmp_path):  # noqa: F811
    _, data = booking
    assert data["releases"]["tracer"]["slice"] == "SLC-001" and data["releases"]["tracer"]["flows"] == ["FLO-001", "FLO-003"]
    vault = tmp_path / "old"
    shutil.copytree(BOOKING, vault)
    shutil.rmtree(vault / "slices")
    (vault / "04b-releases.md").write_text(
        "---\nid: releases\ntype: initiative-section\ntitle: Releases\nstate: assumption\nowner: \"@hl-solution-lead\"\n"
        "authored: authored\n---\n\n# Releases\n\nOne release.\n\n## Release one: website\n\n- **Target:** 2027-02-01\n"
        "- **State:** assumption\n- **Tracer:** [[FLO-001-hold-pay-confirm|FLO-001]], a customer books on the website\n", encoding="utf-8")
    _, old = built(tmp_path, vault, "2026-11-20", "old")
    assert old["releases"]["tracer"]["flows"] == ["FLO-001"] and old["releases"]["tracer"]["words"] == "a customer books on the website"
    first = old["slicePlan"]["list"][0]
    assert not old["slicePlan"]["onPages"] and first["key"] == "" and first["page"] and first["tracer"]


def test_the_page_carries_the_slices_view_and_its_key(booking):  # noqa: F811
    page, _ = booking
    assert 'View("slices"' in page and 'Legend.open("slices"' in page and "Slices.hashParts()" in page and "sl-layout" in page


PLAN = """### S-01 Hold a seat

Traces to: CAP-014.FR1
Slice: vertical, SLC-001 A customer books on the website

| Task | Size | Component |
|---|---|---|
| Write the hold | S | Hold service |

### S-02 Amend online

Traces to: CAP-021.FR1
Slice: vertical, SLC-004

| Task | Size | Component |
|---|---|---|
| Write the amend | M | Booking API |
"""


def test_a_story_naming_the_tracer_slice_is_a_tracer_story_and_each_carries_its_slice():
    stories, _, _ = breakdown.parse(PLAN)
    entries = [plan_data.story_entry(s, {}, {}, set(), [], "SLC-001") for s in stories]
    assert [(e["id"], e["sliceId"], e["tracer"]) for e in entries] == [("S-01", "SLC-001", True), ("S-02", "SLC-004", False)]
    assert not plan_data.story_entry(stories[0], {}, {}, set(), [])["tracer"]  # no slice pages, no tracer slice
