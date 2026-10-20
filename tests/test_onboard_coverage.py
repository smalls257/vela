"""Every fact the vault holds that an onboarding module claims to cover is in the module, at every stage of a plan.

The Violation these guard against is a Silent Fallback: a module that says "Not recorded yet" over a vault that holds the
thing (a filter that drops the undated release, a path with no Slices module at the design stage), or lists fewer items
than the vault has. The exec reads Dates and Slices at every stage; what ships when and in which pieces is what an exec
asks first.
"""
import pytest

from conftest import REPO
from vela import cli, onboarding, onboardmodules
from vela.explorer import asks_data, build

SNAPSHOTS = REPO / "tests" / "sim" / "snapshots"
STAGES = {"discovery-empty": SNAPSHOTS / "coastal-merger" / "empty",
          "heron-full-1": SNAPSHOTS / "heron-desk" / "after-full-1",
          "heron-design-2": SNAPSHOTS / "heron-desk" / "after-design-2",
          "trading-80b": SNAPSHOTS / "trading-coach" / "after-80b",
          "booking": REPO / "examples" / "unified-booking"}
_cache = {}


def facts_of(name):
    if name not in _cache:
        root = STAGES[name]
        _cache[name] = build.extract(cli.load_vault(root), root, "2026-10-19")
    return _cache[name]


@pytest.fixture(params=sorted(STAGES))
def plan(request):
    facts = facts_of(request.param)
    return request.param, facts, onboardmodules.build_all(facts)


def test_the_exec_path_carries_the_slices_and_the_dates_at_every_stage(plan):
    name, facts, _ = plan
    stage = onboarding.stage_of(facts)
    for stage_name in onboarding.STAGES:
        assert {"slices", "dates", "risks", "decisions-waiting"} <= set(onboarding.SPECIFICS["exec"][stage_name]), (name, stage_name)
    assert "slices" in onboarding.standard_ids("exec", stage)


def test_slices_lists_every_slice_the_vault_holds_and_is_silent_only_when_it_holds_none(plan):
    name, facts, modules = plan
    rows, module = facts["slicePlan"]["list"], modules["slices"]
    assert bool(module["notRecorded"]) == (not rows), name
    assert [i["key"] for i in module["items"]] == [s["key"] for s in rows], name
    for s, i in zip(rows, module["items"]):
        if s.get("doneWhen"):
            assert "Done when" in i["note"], (name, s["key"])
        if s["journeyDue"]:
            assert onboardmodules.date_phrase(s["journeyDue"]) in i["note"] or i["tone"] == "late", (name, s["key"])


def test_dates_lists_every_release_dated_or_not_and_every_journey_date(plan):
    name, facts, modules = plan
    releases = facts["releases"]["states"][1:] if facts["releases"]["count"] else []
    module = modules["dates"]
    due = [s for s in facts["slicePlan"]["list"] if s["journeyDue"]]
    assert bool(module["notRecorded"]) == (not releases and not due), name
    shown = [i for i in module["items"] if i["key"].startswith("release:")]
    assert len(shown) == len(releases), (name, "a release with no date is still a release")
    for s, i in zip(releases, shown):
        assert i["pill"] == (onboardmodules.date_phrase(s["target"]) if s["target"] else "no date yet"), (name, s["name"])
        assert i["note"] and ("ships" in i["note"]), (name, s["name"])
    assert len(module["items"]) == len(releases) + len(due), name


def test_dates_names_the_requirements_no_release_ships(plan):
    name, facts, modules = plan
    shipped = {r for s in facts["releases"]["states"] for r in s.get("delivers", [])}
    left = [e["title"] for k, e in facts["entities"].items() if e["kind"] == "requirement" and k not in shipped]
    if facts["releases"]["count"] and left:
        assert any(left[0] in b for b in modules["dates"]["body"]), (name, left[0])
    else:
        assert not any("on no release" in b for b in modules["dates"]["body"]), name


def test_risks_decisions_goals_and_questions_are_all_there(plan):
    name, facts, modules = plan
    assert bool(modules["risks"]["notRecorded"]) == (not facts["riskList"]), name
    assert len(modules["risks"]["items"]) == len(facts["riskList"]), name
    trees = [t for t in facts["garden"]["trees"] if t.get("state")]
    waiting = [t for t in trees if t["state"] in ("proposed", "pending", "overridden")]
    assert len(modules["decisions-waiting"]["items"]) == len(waiting), name
    refs = {i["key"] for i in modules["standing"]["items"]}
    assert {onboardmodules.decision_ref(t) for t in trees} <= refs, name
    assert {onboardmodules.decision_ref(t) for t in trees} <= {i["key"] for i in modules["fit@exec"]["items"]}, name
    assert len(modules["goal"]["items"]) == len([g for g in facts["goals"] if onboardmodules.say_text(g["goalText"])]), name
    open_asks = [a for a in facts["asks"] if a["state"] == "open"]
    assert len(modules["open-questions"]["items"]) == len(open_asks), name
    if not open_asks:
        assert not modules["open-questions"]["notRecorded"]


def test_every_owner_and_every_person_holding_an_answer_is_listed_by_the_name_the_plan_gives_them(plan):
    name, facts, modules = plan
    items = modules["people@exec"]["items"]
    keys = {i["key"] for i in items}
    for handle in facts["owners"]:
        assert "owner:" + handle in keys, (name, handle)
    for a in facts["asks"]:
        if a["state"] == "open" and a["ask"]["key"].startswith("@"):
            assert any(i["label"] == a["ask"]["name"] and i["key"] == "owner:" + a["ask"]["key"] for i in items), (name, a["ask"]["key"])


def test_a_decision_whose_pick_carries_its_reason_in_brackets_is_still_the_pick():
    picked, rejected = asks_data.parse_options('Cut C, four epics (picked): "The constraints already split the work."; Cut A, one epic: rejected, no seam')
    assert picked["label"] == "Cut C, four epics" and picked["why"] == "The constraints already split the work."
    assert [r["label"] for r in rejected] == ["Cut A, one epic"]
