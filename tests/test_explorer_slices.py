"""The dashboard's Slices view and the tracer tag, both read from slices.read_slices (slices_data.py), and the build
plan grouped by slice. The browser draws them; these check what the build hands it."""
import shutil

from test_explorer import BOOKING, booking, built  # noqa: F401  (booking is a fixture)

from planner import breakdown
from planner.explorer import plan_data


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
    assert rows["SLC-001"]["joins"][0] == {"id": "CON-001", "key": "CON-001"}
    assert all(j["key"] in E for x in P["list"] for j in x["joins"])
    assert rows["SLC-003"]["notIn"][0]["text"].startswith("Amend and cancel at a kiosk")
    section = next(s for s in data["sections"] if s["id"] == "slices")
    assert section["children"] == [x["key"] for x in P["list"]]


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
    assert 'View("slices"' in page and "Nodes.wire(head" in page and 'Legend.open("slices"' in page


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
