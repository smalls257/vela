"""Flow steps: every sender and receiver is a known app or outside party, and the dashboard never invents a self-arrow.

Silent Fallback: a step whose ends could not be read used to be drawn as the first app its words mention sending to
itself, as if the page had said so. These tests hold the check codes (E351, W354, W374) and the dashboard's data.
"""
import json
import re

from conftest import REPO, edit, run
from flow_ends_vault import FLOW, TODAY, booking_with_flow_ends
from vela import cli
from vela.explorer import build

PAGE = "06-runtime/flows/FLO-009-confirm-by-text.md"
DATA = re.compile(r'<script type="application/json" id="data">(.*?)</script>', re.S)


def check(vault):
    return run("check", "--vault", str(vault), "--today", TODAY)[1]


def lines(out, code):
    return [x for x in out.splitlines() if f" {code} " in x and "FLO-009" in x]


def flow_data(vault):
    out = vault / "d.html"
    assert run("explore", str(vault), "-o", str(out), "--today", TODAY, "--no-open")[0] == 0
    return json.loads(DATA.search(out.read_text(encoding="utf-8")).group(1))


def record(tmp_path):
    vault = booking_with_flow_ends(tmp_path)
    data = flow_data(vault)
    flow = next(f for f in data["flows"] if f["key"] == "FLO-009")
    return data, {s["n"]: s for s in flow["steps"]}


# ---- the check

def test_an_end_that_is_no_app_and_no_party_is_an_error_that_says_the_fix(tmp_path):
    out = check(booking_with_flow_ends(tmp_path))
    found = lines(out, "E351")
    assert len(found) == 1 and "Ferry passenger" in found[0] and "receiver" in found[0], out
    assert "link its page" in found[0] and "vela add subject --subject-type PTY" in found[0], found


def test_a_registered_party_is_a_known_end(tmp_path):
    vault = booking_with_flow_ends(tmp_path)
    edit(vault / PAGE, "Ferry passenger", "Tidepay")
    assert not lines(check(vault), "E351")


def test_an_app_written_as_plain_text_warns_with_the_link_to_write(tmp_path):
    found = lines(check(booking_with_flow_ends(tmp_path)), "W354")
    assert len(found) == 3, found  # Booking and Notifications in step 2, Notifications in step 3
    assert "[[booking-building-blocks|Booking]]" in found[0] and "[[notifications-building-blocks|Notifications]]" in found[1]


def test_a_linked_app_does_not_warn(tmp_path):
    vault = booking_with_flow_ends(tmp_path)
    assert not [x for x in lines(check(vault), "W354") if "Step 1" in x]


def test_a_step_naming_two_apps_with_no_pair_and_no_contract_warns(tmp_path):
    found = lines(check(booking_with_flow_ends(tmp_path)), "W374")
    assert len(found) == 1 and "Step 5" in found[0] and "who hands what to whom" in found[0], found


def test_a_step_inside_one_app_or_with_a_pair_or_a_contract_does_not_warn(tmp_path):
    out = check(booking_with_flow_ends(tmp_path))
    assert not [x for x in lines(out, "W374") if "Step 4" in x or "Step 1" in x or "Step 2" in x]
    vault = booking_with_flow_ends(tmp_path / "again")
    edit(vault / PAGE, "5. Booking and Notifications agree", "5. Booking -> Notifications: agree")
    assert not lines(check(vault), "W374")


def test_the_codes_are_in_conventions_and_its_table():
    text = (REPO / "plugin" / "template" / "CONVENTIONS.md").read_text(encoding="utf-8")
    for code in ("E351", "W354", "W374"):
        assert f"| {code} |" in text and f"{code} " in text.split("## Flow steps", 1)[1].split("## Flow check", 1)[0]


# ---- the dashboard's data

def test_a_step_whose_ends_could_not_be_read_is_never_drawn_as_a_self_arrow(tmp_path):
    _, steps = record(tmp_path)
    for step in steps.values():
        assert not any(m["from"] == m["to"] for m in step["messages"]), step
    assert steps[5]["self"] is None and steps[5]["messages"] == [] and steps[5]["unrecorded"] is True


def test_a_step_that_names_exactly_one_lane_and_no_pair_is_that_lanes_own_action(tmp_path):
    _, steps = record(tmp_path)
    assert steps[4]["self"] == "APP-notifications" and not steps[4]["unrecorded"]


def test_an_end_the_plan_does_not_know_gets_its_own_gap_lane_named_as_written(tmp_path):
    data, steps = record(tmp_path)
    lane = next(x for x in data["lanes"] if x["id"] == "gap:ferry passenger")
    assert lane["name"] == "Ferry passenger" and lane["gap"] is True and lane["kind"] == "outside"
    assert [(m["from"], m["to"]) for m in steps[3]["messages"]] == [("APP-notifications", "gap:ferry passenger")]
    assert sum(1 for x in data["lanes"] if x.get("gap")) == 1  # the apps written as plain text are lanes already


def test_a_pair_with_no_contract_draws_an_arrow_between_its_ends(tmp_path):
    _, steps = record(tmp_path)
    (message,) = steps[2]["messages"]
    assert (message["from"], message["to"], message["contract"], message["direction"]) == ("APP-booking", "APP-notifications", "", "stated")
    assert message["says"] and "->" not in message["says"]
    assert steps[2]["self"] is None


def test_a_pair_with_a_contract_still_draws_it_over_the_contract(tmp_path):
    _, steps = record(tmp_path)
    assert [(m["from"], m["to"], m["contract"]) for m in steps[1]["messages"]] == [("APP-website", "APP-booking", "CON-001")]


def test_a_registered_party_no_contract_joins_gets_a_party_lane_not_a_gap(tmp_path):
    vault = booking_with_flow_ends(tmp_path)
    edit(vault / PAGE, "Ferry passenger", "FERRYMASTER vendor")
    data = flow_data(vault)
    lane = next(x for x in data["lanes"] if x["id"] == "PTY-02")
    assert lane["kind"] == "partner" and not lane.get("gap")
    assert not [x for x in data["lanes"] if x.get("gap")]
