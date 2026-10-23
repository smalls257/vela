"""Where a flow starts (starts_data.py): the data the Flows view's "Starts from" picker reads.

Silent Fallback: a flow with two ways in used to read as one list, and a guess at the starts would read as a fact. These
tests hold the three cases (an opening alt, no alt, one way in), that a guess says it is one, and the checker's side: an
opening alt written in words is not an unreadable line, and the check says it walked one start only.
"""
import json
import pathlib
import re
import shutil

import pytest
from conftest import REPO, run
from starts_flows import add_flows

from vela import cli
from vela.explorer import starts_data
from vela.flowcheck import mermaid, readers

TODAY = "2026-11-20"
DATA = re.compile(r'<script type="application/json" id="data">(.*?)</script>', re.S)
WEB, DESK, BOOKING = "APP-website", "APP-call-center", "APP-booking"


@pytest.fixture(scope="module")
def built(tmp_path_factory):
    root = tmp_path_factory.mktemp("starts")
    vault = root / "vault"
    shutil.copytree(REPO / "examples" / "unified-booking", vault)
    add_flows(vault)
    out = root / "d.html"
    assert run("explore", str(vault), "-o", str(out), "--today", TODAY, "--no-open")[0] == 0
    data = json.loads(DATA.search(out.read_text(encoding="utf-8")).group(1))
    return vault, {f["key"]: f for f in data["flows"]}


def owners(flow):
    return {s["n"]: s["start"] for s in flow["steps"]}


def test_an_opening_alt_names_the_starts_in_its_own_words(built):
    _, flows = built
    starts = flows["FLO-010"]["starts"]
    assert starts["source"] == "diagram" and starts["guessed"] is False
    assert [(o["id"], o["label"], o["lane"], o["steps"]) for o in starts["options"]] == [
        ("S1", "A customer books on the website", WEB, [1, 2]),
        ("S2", "A customer calls in", DESK, [3, 4])]
    # the first step both starts share is where they join, and the lane they both reach says where
    assert starts["merge"] == {"step": 5, "lane": BOOKING}
    assert owners(flows["FLO-010"]) == {1: "S1", 2: "S1", 3: "S2", 4: "S2", 5: "", 6: "", 7: ""}


def test_with_no_alt_the_starts_are_the_lanes_that_send_before_anything_sends_to_them(built):
    _, flows = built
    starts = flows["FLO-011"]["starts"]
    assert starts["source"] == "guess"
    assert [(o["label"], o["lane"], o["steps"]) for o in starts["options"]] == [("Public website", WEB, [1, 2]), ("Call center desktop", DESK, [3, 4])]
    assert starts["merge"] == {"step": 5, "lane": BOOKING}
    assert starts["guessed"] is False  # every arrow on the page is stated, so the rule rests on what the page says
    assert owners(flows["FLO-011"]) == owners(flows["FLO-010"])


def test_one_way_in_is_no_starts(built):
    _, flows = built
    assert flows["FLO-012"]["starts"] is None
    assert {s["start"] for s in flows["FLO-012"]["steps"]} == {""}
    assert all(f["starts"] is None for k, f in flows.items() if k in ("FLO-001", "FLO-002", "FLO-003"))  # the example's own flows


def test_a_start_found_on_inferred_arrows_says_it_is_a_guess(built):
    _, flows = built
    starts = flows["FLO-013"]["starts"]
    assert starts is not None and starts["source"] == "guess" and starts["guessed"] is True
    assert [(o["lane"], o["steps"]) for o in starts["options"]] == [("APP-vessel-schedule", [1]), ("PTY-01", [2])]
    assert [m["direction"] for s in flows["FLO-013"]["steps"][:2] for m in s["messages"]] == ["inferred", "inferred"]


def steps(*specs):
    """Played steps as the starts rule reads them: (number, from, to, direction) or (number, lane) for a step inside one lane."""
    out = []
    for n, *rest in specs:
        msg = [{"from": rest[0], "to": rest[1], "contract": "CON-1", "direction": rest[2] if len(rest) > 2 else "stated"}] if len(rest) > 1 else []
        out.append({"n": n, "messages": msg, "self": rest[0] if len(rest) == 1 else None, "named": []})
    return out


def test_the_guess_needs_two_starts_that_both_reach_one_lane():
    two = steps((1, "web"), (2, "web", "booking"), (3, "desk"), (4, "desk", "booking"), (5, "booking", "pricing"), (6, "pricing", "booking"))
    found = starts_data.guess(two)
    assert [o["lane"] for o in found["options"]] == ["web", "desk"] and found["merge"] == {"step": 5, "lane": "booking"}
    # two lanes that never meet are two flows on one page, not two ways into one
    apart = steps((1, "web", "booking"), (2, "booking", "web"), (3, "desk", "pricing"), (4, "pricing", "desk"))
    assert starts_data.guess(apart) is None
    # a lane that merely sends first inside the shared part (Booking after the website) is not a start
    chain = steps((1, "web", "booking"), (2, "booking", "pricing"), (3, "pricing", "booking"))
    assert starts_data.guess(chain) is None


def test_the_guess_is_labeled_only_when_an_inferred_arrow_carried_it():
    inferred = steps((1, "web", "booking", "inferred"), (2, "desk", "booking"), (3, "booking", "pricing"))
    assert starts_data.guess(inferred)["guessed"] is True
    stated = steps((1, "web", "booking"), (2, "desk", "booking"), (3, "booking", "pricing"))
    assert starts_data.guess(stated)["guessed"] is False


def test_a_step_both_starts_could_own_goes_to_the_one_its_words_name():
    options = [{"calls": [("web", "booking", "CON-1")]}, {"calls": [("desk", "booking", "CON-1")]}]
    both = {"n": 2, "named": [], "messages": [{"from": "booking", "to": "web", "contract": "CON-1"}, {"from": "booking", "to": "desk", "contract": "CON-1"}]}
    assert starts_data.tie_steps([both], options) == {}  # it names neither: shared, never guessed
    both["named"] = ["desk"]
    assert starts_data.tie_steps([both], options) == {2: 1}


# ---- the flow check reads the opening alt as the starts, and says it walked one

def tree_of(vault, flow_id):
    catalog = readers.read_catalog(cli.load_vault(vault), {})
    problems = []
    return mermaid.parse_tree(catalog.flows[flow_id], problems), problems


def test_the_checker_reads_an_opening_alt_in_words_as_starts_not_as_unreadable_lines(built):
    vault, _ = built
    tree, problems = tree_of(vault, "FLO-010")
    assert problems == []
    assert [b.label for b in tree.starts] == ["A customer books on the website", "A customer calls in"]
    assert [n.kind for n in tree.nodes] == ["call", "call"]  # the first start's call, then the call both share


def test_words_for_an_option_anywhere_but_the_opening_stay_unreadable(tmp_path):
    vault = tmp_path / "v"
    shutil.copytree(REPO / "examples" / "unified-booking", vault)
    add_flows(vault, ["FLO-010-book-two-ways.md"])
    page = vault / "06-runtime" / "flows" / "FLO-010-book-two-ways.md"
    page.write_text(page.read_text(encoding="utf-8").replace("    B->>P: CON-003 quote the fare\n",
                    "    B->>P: CON-003 quote the fare\n    alt the fare is high\n        B->>P: CON-003 ask again\n    end\n"), encoding="utf-8")
    _, problems = tree_of(vault, "FLO-010")
    assert any("Unreadable line, outside the checked subset: alt the fare is high" in p.text for p in problems), [p.text for p in problems]


def test_a_slice_check_says_it_walked_the_first_start_only(built):
    vault, _ = built
    catalog = readers.read_catalog(cli.load_vault(vault), {})
    from vela import flowcheck
    result = flowcheck.check_catalog(catalog, "FLO-010", TODAY)
    said = [line for line in result.limits if "starts more than one way" in line]
    assert said == ["FLO-010 starts more than one way. The check walked only the first, “A customer books on the website”, and not “A customer calls in”."]
    assert not [f for f in result.findings if f.code == "F10" and "FLO-010" in f.items and "Unreadable" in f.summary]
