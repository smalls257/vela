"""A person's own onboarding path: choices only, so nothing the plan doesn't hold can reach them.

The Violation these guard against is the invented fact. The file holds module ids, their order, a depth and a yes or no
for diagrams; any other key, and any text, is refused when the file is written and again when it is read.
"""
import json

import pytest

from vela import onboardpath


def path(**changes):
    found = dict(handle="sam", audience="eng", modules=["goal", "contracts"], depth="normal", diagrams=True)
    found.update(changes)
    return onboardpath.make(**found)


def test_a_path_holds_module_ids_an_order_a_depth_and_whether_they_want_diagrams():
    made, said = path()
    assert said == [] and made.modules == ("goal", "contracts") and made.diagrams is True and made.brought_back == ()
    assert onboardpath.as_data(made) == {"handle": "sam", "audience": "eng", "modules": ["goal", "contracts"], "depth": "normal", "diagrams": True, "broughtBack": []}


@pytest.mark.parametrize("changes, said", [
    (dict(handle="../x"), "not a handle"), (dict(handle=""), "not a handle"), (dict(audience="sales"), "not a role"),
    (dict(depth="deep"), "not a depth"), (dict(diagrams="yes"), "diagrams must be yes or no"), (dict(modules=[]), "at least one module"),
    (dict(modules=["goal", "vendors"]), "'vendors' is not a module Vela builds"), (dict(modules=["goal", "goal"]), "'goal' is listed twice")])
def test_a_choice_outside_the_vocabulary_is_refused_with_why(changes, said):
    made, problems_ = path(**changes)
    assert made is None and any(said in p for p in problems_), problems_


def test_a_module_the_lead_hid_needs_to_be_asked_for_by_name_and_is_recorded():
    made, said = path(hidden=("contracts",))
    assert made is None and "--bring-back contracts" in said[0]
    made, said = path(hidden=("contracts",), bring_back=("contracts",))
    assert said == [] and made.brought_back == ("contracts",)
    made, said = path(bring_back=("risks",))
    assert made is None and "names a module that is not on the path" in said[0]


def test_the_file_round_trips_and_holds_nothing_but_choices():
    made, _ = path()
    again, said = onboardpath.from_text("sam", onboardpath.to_text(made))
    assert said == [] and again == made
    text = json.loads(onboardpath.to_text(made))
    assert set(text) == onboardpath.KEYS


@pytest.mark.parametrize("raw, said", [("{", "not readable"), ("[]", "one object"), ('{"modules": "goal"}', "should be a list"),
                                       ('{"audience": "eng", "modules": ["goal"], "note": "Booking is late"}', "'note', which is not a choice")])
def test_a_file_with_text_in_it_or_that_is_not_readable_is_refused(raw, said):
    found, problems_ = onboardpath.from_text("sam", raw)
    assert found is None and said in problems_[0]


def test_the_file_lives_under_the_handle_in_the_working_folder():
    assert onboardpath.file_for("sam") == ".vela/onboard/sam.json"


@pytest.mark.parametrize("handle", ["../x", "a/b", "sam smith", "-sam", "x" * 40, "sam.json", ""])
def test_a_handle_that_could_name_another_file_is_never_a_path(handle):
    assert onboardpath.HANDLE.match(handle) is None
    made, said = path(handle=handle)
    assert made is None and "not a handle" in said[0]
