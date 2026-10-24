"""Which way a played arrow points, and what it says (flows_data.py).

Leaky Narrative / Paper Tiger: a flow that draws Booking calling the Call center desktop looks finished and says the opposite of
the record. A request goes from the consumer that calls to the provider that answers; only an event or a webhook (a push) goes
provider to consumer. The page's own sequence diagram, read once by the flow checker's parser, beats any guess. And one arrow is
labeled once: the sentence of a step shows on the step, never again under each of its arrows.
"""
import json
import re
import shutil

import pytest
from conftest import REPO, run

from vela.explorer import flows_data
from vela.explorer.flows_data import Drawing

DATA = re.compile(r'<script type="application/json" id="data">(.*?)</script>', re.S)
WEB, DESK, KIOSK, BOOKING, SCHEDULE, TIDEPAY = "APP-website", "APP-call-center", "APP-kiosks", "APP-booking", "APP-vessel-schedule", "PTY-01"


def contract(push, consumers=(WEB, DESK), provider=BOOKING):
    return {"id": "CON-1", "title": "Booking API", "provider": provider, "consumers": list(consumers), "push": push}


def test_a_request_goes_from_each_consumer_to_the_provider():
    got = flows_data.inferred(contract(push=False), [])
    assert [(m["from"], m["to"], m["direction"]) for m in got] == [(WEB, BOOKING, "inferred"), (DESK, BOOKING, "inferred")]


def test_a_push_goes_from_the_provider_to_each_consumer():
    got = flows_data.inferred(contract(push=True), [])
    assert [(m["from"], m["to"], m["direction"]) for m in got] == [(BOOKING, WEB, "inferred"), (BOOKING, DESK, "inferred")]


def test_a_step_that_names_one_consumer_draws_only_that_one():
    got = flows_data.inferred(contract(push=False), [DESK])
    assert [(m["from"], m["to"]) for m in got] == [(DESK, BOOKING)]


def test_a_contract_with_no_kind_is_read_as_a_request():
    """The vault has no field for it; consumers calling the provider is what an API is."""
    assert flows_data.inferred({"id": "C", "title": "T", "provider": BOOKING, "consumers": [WEB]}, [])[0]["from"] == WEB


def test_the_diagrams_pair_is_stated_and_beats_the_guess_even_for_a_push():
    drawing = Drawing([(SCHEDULE, BOOKING, "CON-1", "capacity check")])
    (m,) = flows_data.inferred(contract(push=True), [], drawing)
    assert (m["from"], m["to"], m["direction"], m["words"]) == (SCHEDULE, BOOKING, "stated", "capacity check")


def test_a_contract_drawn_between_several_pairs_is_picked_by_the_lanes_the_sentence_names_else_guessed():
    drawing = Drawing([(WEB, BOOKING, "CON-1", "hold a seat"), (DESK, BOOKING, "CON-1", "hold a seat"), (KIOSK, BOOKING, "CON-1", "hold a seat")])
    assert [(m["from"], m["direction"]) for m in flows_data.inferred(contract(push=False), [DESK, BOOKING], drawing)] == [(DESK, "stated")]
    guessed = flows_data.inferred(contract(push=False), [], Drawing([(WEB, BOOKING, "CON-1", "a"), (DESK, BOOKING, "CON-1", "b")]))
    assert {m["direction"] for m in guessed} == {"inferred"}


def test_a_contract_drawn_twice_between_the_same_lanes_hands_out_its_words_in_order():
    drawing = Drawing([(BOOKING, SCHEDULE, "CON-6", "BKHOLD over MQ"), (BOOKING, SCHEDULE, "CON-6", "BKCONF over MQ")])
    assert [drawing.words("CON-6", BOOKING, SCHEDULE) for _ in range(3)] == ["BKHOLD over MQ", "BKCONF over MQ", "BKCONF over MQ"]


@pytest.fixture(scope="module")
def example(tmp_path_factory):
    root = tmp_path_factory.mktemp("direction")
    vault = root / "vault"
    shutil.copytree(REPO / "examples" / "unified-booking", vault)
    out = root / "d.html"
    assert run("explore", str(vault), "-o", str(out), "--today", "2026-11-20", "--no-open")[0] == 0
    data = json.loads(DATA.search(out.read_text(encoding="utf-8")).group(1))
    return data, {f["key"]: f for f in data["flows"]}


def arrows(flow):
    return {(m["contract"], m["from"], m["to"]): m for s in flow["steps"] for m in s["messages"]}


def test_the_example_marks_its_event_and_its_webhook_as_pushes_and_its_apis_as_requests(example):
    data, _ = example
    assert {c["id"]: c["push"] for c in data["map"]["contracts"]} == {
        "CON-001": False, "CON-002": True, "CON-003": False, "CON-004": False, "CON-005": False, "CON-006": False, "CON-007": True}


def test_the_example_flows_without_a_strict_diagram_draw_callers_to_providers_and_pushes_the_other_way(example):
    _, flows = example
    amend = arrows(flows["FLO-002"])
    assert ("CON-001", WEB, BOOKING) in amend and ("CON-001", BOOKING, WEB) not in amend  # the website calls Booking
    assert ("CON-003", BOOKING, "APP-pricing") in amend  # Booking calls Pricing
    assert ("CON-007", TIDEPAY, BOOKING) in amend  # the webhook comes from Tidepay
    assert ("CON-002", BOOKING, "APP-notifications") in amend  # the event goes out
    assert {m["direction"] for m in amend.values()} == {"inferred"}


def test_the_hold_flow_takes_its_directions_and_words_from_its_own_diagram(example):
    _, flows = example
    hold = arrows(flows["FLO-001"])
    stated = {k: m for k, m in hold.items() if m["direction"] == "stated"}
    assert [(c, f, t) for c, f, t in stated if c != "CON-001"] == [
        ("CON-004", BOOKING, SCHEDULE), ("CON-005", BOOKING, "APP-customer-identity"), ("CON-003", BOOKING, "APP-pricing"),
        ("CON-006", BOOKING, "APP-ferrymaster"), ("CON-002", BOOKING, "APP-notifications")]
    assert hold[("CON-004", BOOKING, SCHEDULE)]["says"] == "Capacity check"
    assert hold[("CON-005", BOOKING, "APP-customer-identity")]["says"] == "Customer lookup"


def test_one_arrow_one_label_and_never_the_steps_whole_sentence(example):
    _, flows = example
    for key, flow in flows.items():
        for step in flow["steps"]:
            for m in step["messages"]:
                if not m["contract"]:
                    continue  # a recorded pair that names no contract keeps the step's words: there is nothing else to call it
                assert m["says"] and m["says"] != step["text"] and len(m["says"]) < 40, (key, step["n"], m["says"])
                assert m["answer"] == "", (key, step["n"])


def test_step_two_of_the_old_hold_flow_no_longer_repeats_its_sentence_under_six_arrows(example):
    _, flows = example
    holding = next(s for s in flows["FLO-001"]["steps"] if s["n"] == 4)
    says = [m["says"] for m in holding["messages"]]
    assert len(says) == 4 and len(set(says)) == 4 and holding["text"] not in says
