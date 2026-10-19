"""Onboarding's vocabulary, the project's stage and the standard path: pure, no vault and no browser.

The Violation these guard against is the Paper Tiger: a path that lists every page and covers no one's need. The path is
a short fixed shape (the five core parts, then three to five role specifics for the audience and stage), and the stage is
worked out from what the plan holds, never typed.
"""
import re
from types import SimpleNamespace

import pytest

from vela import onboarding


def facts(rows=(), slices=(), flows=(), contracts=()):
    """Only what `stage_of` reads: app rows as (stage, handed off), slice statuses, flows, contracts."""
    return {"progress": {"rows": [{"stage": stage, "handoff": {"handedOff": handed}} for stage, handed in rows]},
            "slicePlan": {"list": [{"status": status} for status in slices]}, "flows": list(flows), "map": {"contracts": list(contracts)}}


# ------------------------------------------------------------------ stage

def test_a_plan_with_nothing_past_naming_its_apps_is_in_discovery():
    assert onboarding.stage_of(facts()) == "discovery"
    assert onboarding.stage_of(facts(rows=[("baseline", ""), ("target", "")], slices=["planned"])) == "discovery"


@pytest.mark.parametrize("found", [dict(rows=[("boundaries", "")]), dict(rows=[("epics", "")]), dict(flows=["a flow"]), dict(contracts=["a contract"])])
def test_design_starts_when_an_app_passes_the_boundary_or_a_flow_or_contract_exists(found):
    assert onboarding.stage_of(facts(**found)) == "design"


@pytest.mark.parametrize("found", [dict(rows=[("epics", "Booking senior, 2026-11-10, PR #23")]), dict(slices=["building"]), dict(slices=["planned", "on"]),
                                   dict(slices=["journey passes"]), dict(slices=["live but off"])])
def test_delivery_starts_when_an_app_is_handed_off_or_a_slice_is_being_built(found):
    assert onboarding.stage_of(facts(flows=["a flow"], **found)) == "delivery"


# ------------------------------------------------------------------ the standard path

def test_every_audience_and_stage_has_three_to_five_specifics_all_in_the_vocabulary():
    for audience in onboarding.AUDIENCES:
        for stage in onboarding.STAGES:
            ids = onboarding.SPECIFICS[audience][stage]
            assert 3 <= len(ids) <= 5, (audience, stage)
            assert len(set(ids)) == len(ids) and all(m in onboarding.MODULE_IDS and m not in onboarding.CORE for m in ids), (audience, stage)


def test_the_vocabulary_is_named_once_each_and_names_are_not_ids():
    assert set(onboarding.NAMES) == set(onboarding.MODULE_IDS)
    assert len(onboarding.BY_NAME) == len(onboarding.NAMES), "two modules share a name"
    assert not any(re.search(r"[a-z]-[a-z]", name) for name in onboarding.NAMES.values()), "a name reads like an id"


def test_the_standard_path_is_the_five_core_parts_then_the_specifics_in_the_tables_order():
    for audience in onboarding.AUDIENCES:
        for stage in onboarding.STAGES:
            ids = onboarding.standard_ids(audience, stage)
            assert ids[:5] == ["goal", "approach", "standing", "fit", "people"]
            assert ids[5:] == list(onboarding.SPECIFICS[audience][stage])


def test_the_audience_bound_parts_are_keyed_by_role_and_the_rest_are_shared():
    assert onboarding.path_keys("eng", ["goal", "fit", "people", "contracts"]) == ["goal", "fit@eng", "people@eng", "contracts"]


def test_the_lead_can_stress_play_down_and_hide_specifics_but_never_move_the_core():
    tuning = SimpleNamespace(stress=("journeys",), play_down=("apps",), hide=("open-questions",))  # what onboardtune.RoleTuning holds
    ids = onboarding.standard_ids("eng", "design", tuning)  # apps, contracts, journeys, open-questions
    assert ids == ["goal", "approach", "standing", "fit", "people", "journeys", "contracts", "apps"]
    assert onboarding.hidden_ids("eng", "design", tuning) == ["open-questions"]
    assert onboarding.hidden_ids("eng", "design", None) == []


# ------------------------------------------------------------------ who the person is, as a role

@pytest.mark.parametrize("record, cached, picked, want", [
    ("qa", "eng", "exec", ("qa", "record")), ("", "eng", "exec", ("eng", "choice")), ("", "", "exec", ("exec", "door")),
    ("", "", "", ("", "")), ("nonsense", "eng", "", ("eng", "choice")), ("", "nonsense", "mgr", ("mgr", "door")), ("lead", "", "exec", ("lead", "record"))])
def test_the_leads_record_wins_then_the_persons_own_choice_then_the_door_they_picked(record, cached, picked, want):
    assert onboarding.role_for(record, cached, picked) == want


@pytest.mark.parametrize("said, role", [("exec sponsor", "exec"), ("product owner", "product"), ("engineer", "eng"), ("QA lead", "qa"),
                                        ("delivery manager", "mgr"), ("solution lead", "lead"), ("Engineering", "eng"), ("QA", "qa"), ("Managers", "mgr"), ("mgr", "mgr")])
def test_a_role_is_understood_the_way_a_person_says_it(said, role):
    assert onboarding.ROLE_WORDS[said.casefold()] == role
