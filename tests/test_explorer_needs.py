"""The data behind Needs you (explorer/needs_data.py, vela/needsyou.py) as the dashboard build assembles it.

    python3 -m pytest -q tests/test_explorer_needs.py

The Violation these guard against is a Distributed Monolith between the block and the build: D.needs is gathered from
the questions, the grills, the readers' pending decisions and the apps' handoff fields, so a change to how any of them
is recorded must show up here, not as a block that quietly lists less. The browser side is test_explorer_needs_browser.py.
"""
from conftest import edit
from grills_vault import TODAY, booking_grills
from vela import cli
from vela.explorer import build


def extract(root):
    return build.extract(cli.load_vault(root), root, TODAY)


def test_every_ready_grill_is_a_line_for_its_owners(tmp_path):
    data = extract(booking_grills(tmp_path))
    ready = [r for r in data["grills"]["rows"] if r["group"] != "one-away"]
    lines = [line for line in data["needs"]["lines"] if line["kind"] == "grill"]
    assert sorted(line["grill"] for line in lines) == sorted(r["id"] for r in ready) and lines
    by_id = {r["id"]: r for r in ready}
    assert all(line["for"] == [o.lower() for o in by_id[line["grill"]]["owner"]] for line in lines)
    assert all(line["key"] in data["entities"] for line in lines)  # a line opens something the page knows


def test_open_questions_are_lines_with_their_ask_by_standing(tmp_path):
    data = extract(booking_grills(tmp_path))
    opened = {u["id"]: u for u in data["asks"] if u["state"] == "open"}
    lines = {line["key"]: line for line in data["needs"]["lines"] if line["kind"] == "question"}
    assert set(lines) == set(opened) and lines
    assert all(line["date"] == opened[k]["askBy"] for k, line in lines.items())
    assert all(line["standing"] == ("late" if line["date"] and line["date"] < TODAY else "none" if not line["date"] else line["standing"]) for line in lines.values())


def test_the_lines_come_most_urgent_first(tmp_path):
    tiers = [line["tier"] for line in extract(booking_grills(tmp_path))["needs"]["lines"]]
    assert tiers == sorted(tiers) and len(set(tiers)) > 1


def test_an_app_handed_over_this_week_is_a_line_for_the_person_it_names(tmp_path):
    root = booking_grills(tmp_path)
    page = root / "05-building-blocks" / "booking-building-blocks.md"
    edit(page, 'handed_off: "Booking senior, 2026-11-10"', 'handed_off: "Booking senior, 2026-01-12"')
    data = extract(root)
    handed = [line for line in data["needs"]["lines"] if line["kind"] == "handed"]
    assert [(line["key"], line["named"], line["date"]) for line in handed] == [("APP-booking", "booking senior", "2026-01-12")]
    assert data["entities"]["APP-booking"]["title"] == "Booking"


def test_a_handoff_dated_after_today_is_not_yet_a_line(tmp_path):
    data = extract(booking_grills(tmp_path))  # the example hands Booking over on 2026-11-10, after TODAY
    assert not [line for line in data["needs"]["lines"] if line["kind"] == "handed"]


def test_a_pending_decision_waits_on_the_owner_of_what_it_is_on(tmp_path):
    root = booking_grills(tmp_path)
    page = root / "05-building-blocks" / "booking-building-blocks.md"
    text = page.read_text(encoding="utf-8")
    at = text.index("### CON-001 ")
    nxt = text.index("\n- **", at)
    page.write_text(text[:nxt] + "\n- **Pending approval:** @hl-booking-senior, 2026-01-14" + text[nxt:], encoding="utf-8")
    data = extract(root)
    pending = [line for line in data["needs"]["lines"] if line["kind"] == "proposal"]
    assert [(line["key"], line["by"], line["date"]) for line in pending] == [("CON-001", "@hl-booking-senior", "2026-01-14")]
    page_owner = data["entities"][data["entities"]["CON-001"]["pageKey"]]["ownerKey"]
    assert page_owner and pending[0]["for"] == [page_owner.lower()]  # the contract names no owner, so its page's owner answers
