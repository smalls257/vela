"""The Flows view's error cases (design 19, D8): each flow's branches as the picker shows them, read through the flow
checker's own readers (branches_data.py). The browser draws them; these check what the build hands it."""
import pathlib

import pytest
from test_explorer import booking  # noqa: F401  (booking is a fixture)

from planner import cli
from planner.explorer import branches_data, record

FIXTURES = pathlib.Path(__file__).resolve().parent / "fixtures" / "flowcheck"
TODAY = "2026-10-14"


def branches(name):
    root = FIXTURES / name
    vault = cli.load_vault(root)
    return branches_data.extract(vault, record.Keys(vault), TODAY, cli.spec_texts(root))


def option(flow, ident):
    return next(o for g in flow["groups"] for o in g["options"] if o["id"] == ident)


def texts(steps, off=None):
    return [s["text"] for s in steps if off is None or s["alt"] == off]


def test_a_drawn_provider_s_answer_follows_its_drawing_and_the_happy_path_is_the_default():
    flow = branches("20-provider-drawn")["FLO-020"]
    assert flow["state"] == "drawn"
    assert texts(flow["happy"]["steps"]) == ["hold a seat", "reserve on the ferry", "200 reserved", "200 held", "Booking: held", "Ends: held"]
    assert [g["label"] for g in flow["groups"]] == ["Hold a seat", "Reserve on the ferry"]
    assert [o["label"] for g in flow["groups"] for o in g["options"]] == [
        "Hold a seat: Sold out", "Hold a seat: Unavailable", "Reserve on the ferry: Full", "Reserve on the ferry: Times out"]
    sold_out = option(flow, "CON-100.sold_out")
    # Booking answers sold out only when Ferrymaster is full: the path goes through that inner answer, and only the
    # steps that leave the happy path are marked
    assert texts(sold_out["steps"], off=False) == ["hold a seat", "reserve on the ferry"]
    assert texts(sold_out["steps"], off=True) == ["409 full", "409 sold out", "Ends: sold out"]
    timed = option(flow, "CON-101.timeout")
    assert texts(timed["steps"], off=True) == ["Times out", "503 unavailable", "Ends: unavailable"]
    assert flow["check"] == {"status": "passes", "states": 15, "notChecked": False, "surveyed": True}
    assert all(o["marks"] == [] for g in flow["groups"] for o in g["options"])  # passed, so no word on any option
    assert flow["counts"] == {"branches": 4, "notDrawn": 0, "withFindings": 0, "notChecked": 0}


def test_an_on_rule_gives_a_call_without_alt_its_timeout_branch_and_the_happy_path_goes_on():
    flow = branches("25-grouped-and-on")["FLO-025"]
    assert texts(flow["happy"]["steps"])[-3:] == ["take the payment", "200 paid", "Ends: paid"]
    payment = option(flow, "CON-020.timeout")
    assert texts(payment["steps"], off=True) == ["Times out", "Ends: refused upstream unavailable"]
    grouped = [option(flow, i) for i in ("CON-010.unavailable", "CON-010.blocked")]
    assert [texts(o["steps"], off=True) for o in grouped] == [["409 unavailable", "Ends: refused"], ["423 blocked", "Ends: refused"]]


def test_a_case_nobody_handles_is_an_option_that_cannot_be_picked_and_carries_its_finding():
    flow = branches("01-unhandled-409")["FLO-001"]
    gap = option(flow, "CON-010.unavailable")
    assert not gap["drawn"] and gap["steps"] == [] and gap["marks"] == ["not drawn", "finding"]
    assert [flow["findings"][i]["code"] for i in gap["findings"]] == ["F1"]
    assert flow["counts"]["notDrawn"] == 1 and flow["counts"]["withFindings"] == 1


def test_a_check_that_stops_early_marks_every_option_not_fully_checked(monkeypatch):
    monkeypatch.setattr(branches_data, "CHECK_STATES", 2)
    flow = branches("20-provider-drawn")["FLO-020"]
    assert flow["check"]["notChecked"] and flow["check"]["status"] == "not fully checked"
    every = [flow["happy"]] + [o for g in flow["groups"] for o in g["options"]]
    assert all("not fully checked" in o["marks"] for o in every)  # never read as passed (R0)
    assert flow["counts"]["notChecked"] == len(every)


def test_a_finding_on_one_answer_marks_that_option_and_a_finding_about_no_answer_is_about_the_whole_flow():
    flow = branches("20-provider-not-drawn")["FLO-020"]
    assert [flow["findings"][i]["code"] for i in flow["flowWide"]] == ["F12"]
    assert all(not o["findings"] for g in flow["groups"] for o in g["options"])


def test_an_unreadable_diagram_or_one_with_no_alt_gets_the_one_line_note():
    assert branches("10-unreadable-and-undeclared")["FLO-010"] == {"state": "none", "note": branches_data.NOT_DRAWN_NOTE}


def test_the_build_hands_every_flow_its_branches(booking):  # noqa: F811
    _, data = booking
    assert set(data["branches"]) == {f["key"] for f in data["flows"]}
    # the example's diagrams are drawn the old way, so each flow shows as today with the one-line note
    assert all(b == {"state": "none", "note": branches_data.NOT_DRAWN_NOTE} for b in data["branches"].values())


@pytest.mark.parametrize("key,words", [("not_found", "Not found"), ("timeout", "Times out"), ("gave_up", "Gives up after its retries")])
def test_answers_read_in_plain_words(key, words):
    assert branches_data.case_words(key) == words
