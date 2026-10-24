"""Where a flow starts (starts_data.py): the data the Flows view's "Starts from" picker reads.

Silent Fallback: a flow with two ways in used to read as one list, and a guess at the starts would read as a fact. These
tests hold the three cases (an opening alt, no alt, one way in), that a guess says it is one, and the checker's side: an
opening alt written in words is not an unreadable line, and the check walks every start.
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
    assert all(f["starts"] is None for k, f in flows.items() if k in ("FLO-002", "FLO-003"))  # the example's own one-way flows


def test_a_start_found_on_inferred_arrows_says_it_is_a_guess(built):
    _, flows = built
    starts = flows["FLO-013"]["starts"]
    assert starts is not None and starts["source"] == "guess" and starts["guessed"] is True
    assert [(o["lane"], o["steps"]) for o in starts["options"]] == [(WEB, [1]), (DESK, [2])]
    assert [m["direction"] for s in flows["FLO-013"]["steps"][:2] for m in s["messages"]] == ["inferred", "inferred"]


def test_the_example_hold_flow_has_three_starts_and_the_picker_shows_them(built):
    """FLO-001 says the website, the call center desktop and the kiosk app follow one sequence: three ways in, joined at Booking."""
    _, flows = built
    starts = flows["FLO-001"]["starts"]
    assert starts["source"] == "diagram" and starts["guessed"] is False and starts["unmatched"] == []
    assert [(o["label"], o["lane"], o["steps"]) for o in starts["options"]] == [
        ("A customer books on the website", WEB, [1]), ("A customer calls in", DESK, [2]), ("A customer uses a kiosk", "APP-kiosks", [3])]
    assert starts["merge"] == {"step": 4, "lane": BOOKING}
    assert owners(flows["FLO-001"]) == {1: "S1", 2: "S2", 3: "S3", 4: "", 5: "", 6: "", 7: ""}


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


def starts_vault(tmp_path, diagram_edit=None):
    vault = tmp_path / "v"
    shutil.copytree(REPO / "examples" / "unified-booking", vault)
    # the contracts the starts call say whether they can time out, so each start's calls are compiled and explored, not refused
    for name, contracts in (("booking", ("### CON-001 Booking API", "### CON-002 Booking state changed")), ("pricing", ("### CON-003 Quote a fare",))):
        blocks = vault / "05-building-blocks" / f"{name}-building-blocks.md"
        text = blocks.read_text(encoding="utf-8")
        for contract in contracts:
            if contract in text and "**Can time out:**" not in text.split(contract, 1)[1].split("\n### ", 1)[0]:
                text = text.replace(contract, contract + "\n\n- **Can time out:** no", 1)
        blocks.write_text(text, encoding="utf-8")
    add_flows(vault, ["FLO-010-book-two-ways.md"])
    page = vault / "06-runtime" / "flows" / "FLO-010-book-two-ways.md"
    if diagram_edit:
        page.write_text(diagram_edit(page.read_text(encoding="utf-8")), encoding="utf-8")
    return vault


def test_the_check_walks_every_start_so_a_defect_in_the_second_is_found(tmp_path):
    from vela import flowcheck
    # the phone start calls a contract nobody wrote: the check must say so, and say nothing about "first start only"
    vault = starts_vault(tmp_path, lambda t: t.replace("D->>B: CON-001 hold a seat", "D->>B: CON-999 hold a seat"))
    result = flowcheck.check_catalog(readers.read_catalog(cli.load_vault(vault), {}), "FLO-010", TODAY)
    assert any(f.code == "F10" and "CON-999" in f.summary for f in result.findings), [f.summary for f in result.findings]
    assert not [line for line in result.limits if "start" in line]


def test_every_start_runs_to_the_shared_steps_and_the_trace_names_the_start(tmp_path):
    from vela import flowcheck
    from vela.flowcheck import build
    vault = starts_vault(tmp_path)
    catalog = readers.read_catalog(cli.load_vault(vault), {})
    program, _ = build.build(catalog, ["FLO-010"], TODAY)
    fork = next(i for i in program.code if i.kind == "fork")
    assert fork.data["labels"] == ["A customer books on the website", "A customer calls in"]
    assert len(set(fork.data["targets"])) == 2
    # each start's own call is compiled, and the fork really branches: two different targets, each reaching its own call
    calls = [program.code[t].kind for t in fork.data["targets"]]
    assert fork.data["targets"][0] != fork.data["targets"][1] and calls == ["call", "call"], calls
    result = flowcheck.check_catalog(catalog, "FLO-010", TODAY)
    # a finding in EACH start's own call: the second start is explored too, not only named
    said = {f.summary.split(":")[1].split(" does not")[0].strip() for f in result.findings if f.code == "F1"}
    assert {"Public website", "Call center desktop"} <= said, [f.summary[:90] for f in result.findings]
    assert result.states > 2 and not [f for f in result.findings if f.code == "F10" and "Unreadable" in f.summary]


def test_a_given_before_the_opening_alt_still_names_the_starts(tmp_path):
    vault = starts_vault(tmp_path, lambda t: t.replace("    alt A customer books", "    Note over B: GIVEN seat free\n    alt A customer books"))
    tree, problems = tree_of(vault, "FLO-010")
    assert [b.label for b in tree.starts] == ["A customer books on the website", "A customer calls in"]
    assert [n.kind for n in tree.head] == ["given"] and not [p for p in problems if "alt" in p.text or "Unreadable" in p.text]


def test_an_option_written_as_an_answer_inside_the_opening_alt_is_flagged(tmp_path):
    vault = starts_vault(tmp_path, lambda t: t.replace("else A customer calls in", "else timeout"))
    _, problems = tree_of(vault, "FLO-010")
    assert any("written as an answer" in p.text for p in problems)


def flow_data(vault, tmp_path, key="FLO-010"):
    out = tmp_path / "d.html"
    assert run("explore", str(vault), "-o", str(out), "--today", TODAY, "--no-open")[0] == 0
    return next(f for f in json.loads(DATA.search(out.read_text(encoding="utf-8")).group(1))["flows"] if f["key"] == key)


def test_a_start_no_step_carries_is_kept_and_said_never_swapped_for_a_guess(tmp_path):
    from starts_flows import DESK, BOOKING, HOLD, STATE
    line = f"4. {DESK} → {BOOKING}: asks to hold a seat, over {HOLD}."
    vault = starts_vault(tmp_path)
    page = vault / "06-runtime" / "flows" / "FLO-010-book-two-ways.md"
    text = page.read_text(encoding="utf-8")
    assert line in text
    page.write_text(text.replace(line, line.replace(HOLD, STATE)), encoding="utf-8")
    starts = flow_data(vault, tmp_path)["starts"]
    assert starts["source"] == "diagram"  # the diagram's own words, not the lanes' names
    assert [o["label"] for o in starts["options"]] == ["A customer books on the website", "A customer calls in"]
    assert starts["options"][1]["steps"] == [] and starts["unmatched"] == ["A customer calls in"]


def test_a_shared_step_over_a_start_s_contract_is_not_a_third_start(tmp_path):
    from starts_flows import WEB, BOOKING, HOLD
    vault = starts_vault(tmp_path)
    page = vault / "06-runtime" / "flows" / "FLO-010-book-two-ways.md"
    text = page.read_text(encoding="utf-8")
    marker = "\n```mermaid"
    text = text.replace(marker, f"8. {WEB} → {BOOKING}: confirms the hold, over {HOLD}.\n" + marker, 1)
    page.write_text(text, encoding="utf-8")
    flow = flow_data(vault, tmp_path)
    assert [o["steps"] for o in flow["starts"]["options"]] == [[1, 2], [3, 4]]
    assert flow["starts"]["merge"]["step"] == 5 and flow["steps"][-1]["start"] == ""


def test_a_timer_a_start_arms_is_the_timer_the_shared_steps_await():
    from test_flowcheck import FIXTURES, TODAY as T, files_of
    files = files_of("17-lost-event-with-timer")
    path = next(k for k in files if k.startswith("06-runtime/flows/"))
    files[path] = """---
id: FLO-008
type: flow
title: An order waits for its invoice
state: assumption
---

# An order waits for its invoice

```mermaid
sequenceDiagram
participant S as Shop
participant B as Billing
alt A shopper orders
    Note over S: SET order waiting
    Note over S: TIMER invoice_wait 2d
else A clerk orders
    Note over S: SET order waiting
end
S-)B: EVT-008 order placed
par Billing handles order placed
    B-)S: EVT-009 invoice ready
    Note over B: END handled
end
Note over S: AWAIT EVT-009
alt received
    Note over S: SET order invoiced
    Note over S: END invoiced
else invoice_wait
    Note over S: SET order expired
    Note over S: END expired
end
```
"""
    from vela import flowcheck
    result = flowcheck.check_slice(files, "FLO-008", T)
    # the await builds with the timer the first start armed, so nothing is refused for a timer that was never started
    assert not [f for f in result.findings if f.code == "F10"], [(f.code, f.summary) for f in result.findings]
