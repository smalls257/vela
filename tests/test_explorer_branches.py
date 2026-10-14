"""The Flows view's error cases (design 19, D8): each flow's branches as the picker shows them, read through the flow
checker's own readers (branches_data.py). The browser draws them; these check what the build hands it."""
import pathlib
import shutil

import pytest
from test_explorer import booking  # noqa: F401  (booking is a fixture)

from vela import cli
from vela.explorer import branches_data, record

FIXTURES = pathlib.Path(__file__).resolve().parent / "fixtures" / "flowcheck"
TODAY = "2026-10-14"


def branches(name):
    root = FIXTURES / name
    vault = cli.load_vault(root)
    return branches_data.extract(vault, record.Keys(vault), TODAY, cli.spec_texts(root))


def option(flow, ident):
    return next(o for g in flow["groups"] for o in g["options"] if o["id"] == ident)


def texts(steps, off=None):
    return [s["short"] for s in steps if off is None or s["differs"] == off]


def test_a_drawn_provider_s_answer_follows_its_drawing_and_the_happy_path_is_the_default():
    flow = branches("20-provider-drawn")["FLO-020"]
    assert flow["state"] == "drawn"
    # the played view's steps: a call and its answer in one step, in plain words, no status codes, no state names
    assert texts(flow["happy"]["steps"]) == ["Website asks Booking to hold a seat.", "Booking asks Ferrymaster to reserve on the ferry. Answer: reserved.",
                                             "Booking answers Website on hold a seat: held.", "It ends here: held."]
    assert [s["kind"] for s in flow["happy"]["steps"]] == ["send", "request", "answer", "end"]
    assert [g["label"] for g in flow["groups"]] == ["Hold a seat", "Reserve on the ferry"]
    assert [o["label"] for g in flow["groups"] for o in g["options"]] == [
        "Hold a seat: Sold out", "Hold a seat: Unavailable", "Reserve on the ferry: Full", "Reserve on the ferry: Times out"]
    sold_out = option(flow, "CON-100.sold_out")
    # Booking answers sold out only when Ferrymaster is full: the path goes through that inner answer, and only the
    # steps that leave the happy path are marked
    assert texts(sold_out["steps"], off=False) == ["Website asks Booking to hold a seat."]
    assert texts(sold_out["steps"], off=True) == ["Booking asks Ferrymaster to reserve on the ferry. Answer: full.", "Booking answers Website on hold a seat: sold out.",
                                                  "It ends here: sold out."]
    timed = option(flow, "CON-101.timeout")
    assert texts(timed["steps"], off=True) == ["Booking asks Ferrymaster to reserve on the ferry: no answer in time.", "Booking answers Website on hold a seat: unavailable.",
                                               "It ends here: unavailable."]
    assert flow["check"] == {"status": "passes", "states": 15, "notChecked": False, "surveyed": True}
    assert all(o["marks"] == [] for g in flow["groups"] for o in g["options"])  # passed, so no word on any option
    assert flow["counts"] == {"branches": 4, "notDrawn": 0, "withFindings": 0, "notChecked": 0}


def test_an_on_rule_gives_a_call_without_alt_its_timeout_branch_and_the_happy_path_goes_on():
    flow = branches("25-grouped-and-on")["FLO-025"]
    assert texts(flow["happy"]["steps"]) == ["Shop asks Inventory to place a hold. Answer: placed.", "Shop asks Tidepay to take the payment. Answer: paid.",
                                             "It ends here: paid."]
    payment = option(flow, "CON-020.timeout")
    assert texts(payment["steps"], off=True) == ["Shop asks Tidepay to take the payment: no answer in time.", "It ends here: refused upstream unavailable."]
    grouped = [option(flow, i) for i in ("CON-010.unavailable", "CON-010.blocked")]
    assert [texts(o["steps"], off=True) for o in grouped] == [["Shop asks Inventory to place a hold. Answer: unavailable.", "It ends here: refused."],
                                                              ["Shop asks Inventory to place a hold. Answer: blocked.", "It ends here: refused."]]


def test_a_broken_invariant_reads_in_plain_words_with_the_expression_kept_for_details():
    flow = branches("06-two-orders-last-item")["FLO-006"]
    broken = next(f for f in flow["findings"] if f["code"] == "F9")
    assert "=" not in broken["summary"] and "implies" not in broken["summary"]
    assert broken["summary"].startswith("This flow can reach a moment when Stock is at")
    assert broken["expression"].startswith("The invariant \"")


@pytest.mark.parametrize("text,said", [
    ("transcripts=read implies consent=calendar_and_transcripts", "This flow can reach a moment when transcripts is at “read” while consent is not at “calendar and transcripts”."),
    ("not (digest=shown and (consent=none or consent=withdrawn))", "This flow can reach a moment when digest is at “shown” while consent is at “none” or consent is at “withdrawn”."),
    ("heron=not_kept implies not consent=calendar_only", "This flow can reach a moment when heron is at “not kept” while consent is at “calendar only”."),
])
def test_invariants_word_themselves(text, said):
    assert branches_data.plain_invariant(text, branches_data.readers.Catalog()) == said


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


def test_every_branch_ends_with_its_ending_or_says_it_has_none():
    flow = branches("20-provider-drawn")["FLO-020"]
    timed = option(flow, "CON-101.timeout")["steps"]
    assert timed[-1]["short"] == "It ends here: unavailable." and timed[-1]["kind"] == "end"
    # a path the diagram leaves without an END says so, in amber
    call = branches_data.step("call", 3, "hold a seat", **{"from": "W", "to": "B", "item": "CON-100"})
    tail = branches_data.played((call,), {}, {}, {}, ended=False)[-1]
    assert tail["short"] == branches_data.NO_ENDING and tail["differs"]


def test_an_ending_reads_as_the_flow_page_says_it_else_as_its_states_mean_else_by_its_name(tmp_path):
    """The band at a branch's end is a sentence, not an END outcome name turned into words: the flow page's
    | Outcome | What the person sees | row first, then the meaning of the state the journey ends in, and only with
    neither the outcome's own name."""
    root = tmp_path / "vault"
    shutil.copytree(FIXTURES / "20-provider-drawn", root)
    flow_page = root / "06-runtime" / "flows" / "FLO-020-20-provider-drawn.md"
    flow_page.write_text(flow_page.read_text(encoding="utf-8") + "\n| Outcome | What the person sees |\n|---|---|\n"
                         "| `sold_out` | The website says the ferry is full. |\n", encoding="utf-8")
    entity = root / "entities" / "booking.md"
    entity.write_text(entity.read_text(encoding="utf-8") + "\n| State | Means | Not in it |\n|---|---|---|\n"
                      "| none | no seat is held | |\n| held | the traveler has a seat held | |\n", encoding="utf-8")
    vault = cli.load_vault(root)
    flow = branches_data.extract(vault, record.Keys(vault), TODAY, cli.spec_texts(root))["FLO-020"]
    assert flow["happy"]["steps"][-1]["short"] == "It ends here: the traveler has a seat held."  # SET booking held
    assert option(flow, "CON-100.sold_out")["steps"][-1]["short"] == "It ends here: the website says the ferry is full."
    assert option(flow, "CON-101.timeout")["steps"][-1]["short"] == "It ends here: unavailable."  # no row, no state set


def test_an_ending_s_words_keep_names_and_join_every_state_it_leaves():
    words = {"heron": {"not_kept": ("the agent says consent wasn't kept", "")}, "digest": {"none": ("no digest yet", "")}}
    end = {"outcome": "told not kept", "outcome_key": "told_not_kept", "leaves": [("digest", "none")]}
    assert branches_data.ending_words(end, {}, words, [("heron", "not_kept")]) == "no digest yet and the agent says consent wasn't kept"
    assert branches_data.ending_words(end, {"told_not_kept": "Heron stays off."}, words, []) == "Heron stays off"
    # one state with no words: the whole ending falls back to its name, never half a sentence
    assert branches_data.ending_words(end, {}, words, [("heron", "on")]) == "told not kept"


def test_a_broken_invariant_reads_in_the_states_own_words_when_the_entity_page_gives_them():
    words = {"heron": {"not_kept": ("the agent says consent wasn't kept", "")},
             "consent": {"calendar_only": ("Consent and identity has kept it (calendar only)", "")}}
    assert branches_data.labeled_invariant("heron=not_kept implies not consent=calendar_only", words) == \
        "The agent says consent wasn't kept, while Consent and identity has kept it (calendar only)."
    # a state with no words: no half-worded sentence; the caller falls back to naming the states
    assert branches_data.labeled_invariant("heron=not_kept implies consent=calendar_only", words) is None


@pytest.mark.parametrize("key,words", [("not_found", "Not found"), ("timeout", "Times out"), ("gave_up", "Gives up after its retries")])
def test_answers_read_in_plain_words(key, words):
    assert branches_data.case_words(key) == words


def test_the_checker_s_stated_limits_show_on_the_branches_that_run_into_them():
    timed = branches("18-webhook-with-timer")["FLO-018"]
    assert timed["limits"] == ["A timer is taken to fire in the end: an order of events in which a timer never fires is not explored."]
    assert timed["happy"]["limits"] == [0] and option(timed, "CON-012.already_settled")["limits"] == [0]
    assert option(timed, "CON-010.unavailable")["limits"] == []  # refused before any timer is armed
    shared = branches("06-two-orders-last-item")["FLO-006"]
    assert shared["limits"][0].startswith("Stock is shared, so the flows that touch it ran two journeys at once")
    assert shared["happy"]["limits"] == [0] and option(shared, "CON-020.out_of_stock")["limits"] == [0]
