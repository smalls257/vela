"""Which capability depends on which: the rule lives in explorer/capdeps.py and reads flows only.

    python3 -m pytest -q tests/test_explorer_capdeps.py

The Violation these guard against is a Paper Tiger: a dependency picture that passes on the data it was given and
claims a lean no journey needs. Each case names a thing that must NOT make a dependency (an app, an allocation, a
guessed capability) as firmly as the things that must.
"""
import json

from vela import cli
from vela.explorer import build, capdeps

from test_explorer import BOOKING


def step(*contracts, ref=None, messages=()):
    return {"contracts": list(contracts), "ref": ref, "messages": [{"contract": c} for c in messages]}


def flow(key, caps, steps=(), how="frontmatter"):
    return {"key": key, "capabilities": list(caps), "capabilitiesFrom": how if caps else "", "steps": list(steps)}


def edge(result, a, b):
    return next((e for e in result["edges"] if e["from"] == a and e["to"] == b), None)


def test_the_primary_capability_depends_on_every_other_one_the_flow_lists():
    out = capdeps.derive([flow("FLO-1", ["CAP-A", "CAP-B", "CAP-C"], [step("CON-1"), step("CON-2")])])
    assert [(e["from"], e["to"]) for e in out["edges"]] == [("CAP-A", "CAP-B"), ("CAP-A", "CAP-C")]
    ab = edge(out, "CAP-A", "CAP-B")
    assert ab["contracts"] == ["CON-1", "CON-2"] and (ab["nFlows"], ab["nContracts"]) == (1, 2)
    assert ab["flows"] == [{"flow": "FLO-1", "lists": True, "repeats": [], "contracts": ["CON-1", "CON-2"]}]
    assert edge(out, "CAP-B", "CAP-C") is None and edge(out, "CAP-B", "CAP-A") is None  # only the primary leans


def test_a_message_contract_counts_as_crossed_even_when_the_step_lists_none():
    out = capdeps.derive([flow("FLO-1", ["CAP-A", "CAP-B"], [step(messages=["CON-9"])])])
    assert edge(out, "CAP-A", "CAP-B")["contracts"] == ["CON-9"]


def test_a_flow_with_one_capability_makes_no_dependency():
    out = capdeps.derive([flow("FLO-1", ["CAP-A"], [step("CON-1")])])
    assert out == {"edges": [], "noCapabilities": []}


def test_a_step_that_repeats_another_flow_makes_the_primary_depend_on_that_flows_primary():
    flows = [flow("FLO-1", ["CAP-A"], [step("CON-1", ref="FLO-2")]), flow("FLO-2", ["CAP-B", "CAP-Z"], [step("CON-2")])]
    out = capdeps.derive(flows)
    ab = edge(out, "CAP-A", "CAP-B")
    assert ab["flows"] == [{"flow": "FLO-1", "lists": False, "repeats": ["FLO-2"], "contracts": ["CON-1", "CON-2"]}]
    assert edge(out, "CAP-A", "CAP-Z") is None  # through that flow's primary only
    assert edge(out, "CAP-B", "CAP-Z") is not None  # and FLO-2 still makes its own


def test_repeating_a_flow_of_the_same_primary_or_with_no_capabilities_makes_nothing():
    same = capdeps.derive([flow("FLO-1", ["CAP-A"], [step(ref="FLO-2")]), flow("FLO-2", ["CAP-A"], [step("CON-2")])])
    bare = capdeps.derive([flow("FLO-1", ["CAP-A"], [step(ref="FLO-2")]), flow("FLO-2", [], [step("CON-2")])])
    guessed = capdeps.derive([flow("FLO-1", ["CAP-A"], [step(ref="FLO-2")]), flow("FLO-2", ["CAP-B"], [step("CON-2")], how="steps")])
    assert same["edges"] == bare["edges"] == guessed["edges"] == []


def test_a_flow_that_lists_and_repeats_the_same_target_is_one_flow_on_the_edge():
    flows = [flow("FLO-1", ["CAP-A", "CAP-B"], [step("CON-1", ref="FLO-2")]), flow("FLO-2", ["CAP-B"], [step("CON-2")])]
    ab = edge(capdeps.derive(flows), "CAP-A", "CAP-B")
    assert ab["nFlows"] == 1 and ab["flows"][0]["lists"] and ab["flows"][0]["repeats"] == ["FLO-2"]
    assert ab["contracts"] == ["CON-1", "CON-2"]


def test_flows_and_contracts_are_counted_once_per_edge():
    flows = [flow("FLO-1", ["CAP-A", "CAP-B"], [step("CON-1"), step("CON-1", "CON-2")]),
             flow("FLO-2", ["CAP-A", "CAP-B"], [step("CON-2", "CON-3")]), flow("FLO-3", ["CAP-A", "CAP-B"], [])]
    ab = edge(capdeps.derive(flows), "CAP-A", "CAP-B")
    assert (ab["nFlows"], ab["nContracts"], ab["contracts"]) == (3, 3, ["CON-1", "CON-2", "CON-3"])
    assert [f["flow"] for f in ab["flows"]] == ["FLO-1", "FLO-2", "FLO-3"]


def test_edges_that_lean_both_ways_are_flagged_on_both():
    flows = [flow("FLO-1", ["CAP-A", "CAP-B"], [step("CON-1")]), flow("FLO-2", ["CAP-B", "CAP-A"], [step("CON-2")]),
             flow("FLO-3", ["CAP-A", "CAP-C"], [step("CON-3")])]
    out = capdeps.derive(flows)
    assert edge(out, "CAP-A", "CAP-B")["both"] and edge(out, "CAP-B", "CAP-A")["both"]
    assert not edge(out, "CAP-A", "CAP-C")["both"]


def test_flows_with_no_recorded_capabilities_are_counted_not_guessed_at():
    flows = [flow("FLO-1", [], [step("CON-1")]), flow("FLO-2", ["CAP-A", "CAP-B"], [step("CON-2")], how="steps"),
             flow("FLO-3", ["CAP-A", "CAP-B"], [step("CON-3")])]
    out = capdeps.derive(flows)
    assert out["noCapabilities"] == ["FLO-1", "FLO-2"]
    assert [f["flow"] for f in edge(out, "CAP-A", "CAP-B")["flows"]] == ["FLO-3"]  # the guess makes no edge


def test_the_result_does_not_depend_on_the_order_flows_arrive_in():
    flows = [flow("FLO-2", ["CAP-B", "CAP-C"], [step("CON-2")]), flow("FLO-1", ["CAP-A", "CAP-B"], [step("CON-1")])]
    assert capdeps.derive(flows) == capdeps.derive(list(reversed(flows)))


def test_the_built_page_carries_the_derivation_of_its_own_flows():
    root = BOOKING
    data = build.extract(cli.load_vault(root), root, "2026-10-10")
    assert data["capDeps"] == capdeps.derive(data["flows"])
    caps = {c["key"] for c in data["trace"]["capabilities"]}
    assert all(e["from"] in caps and e["to"] in caps and e["from"] != e["to"] for e in data["capDeps"]["edges"])
    assert all(c in {x["id"] for x in data["map"]["contracts"]} for e in data["capDeps"]["edges"] for c in e["contracts"])
    assert data["capDeps"]["edges"], "the example plan lists several capabilities on some flows, so it has dependencies"
    assert json.dumps(data["capDeps"])  # plain data, nothing the page cannot carry
