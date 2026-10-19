"""What each onboarding module says, built from real vaults: grounded, in the voice, and linked to places that exist.

The Violation these guard against is the invented fact. A module is a template filled from the plan, so the tests ask
of every module in every vault: does it hold a code or an ID, a British spelling, a link to a thing the page doesn't
have? When the plan is silent, does it say so and who to ask? Do two builds say the same thing?
"""
import json
import pathlib
import re

import pytest

from conftest import REPO
from vela import cli, onboarding, onboardmodules, say, spelling, terms
from vela.explorer import build

SNAPSHOTS = REPO / "tests" / "sim" / "snapshots"
VAULTS = {"heron-after-full-1": (SNAPSHOTS / "heron-desk" / "after-full-1", "design"),
          "trading-after-80b": (SNAPSHOTS / "trading-coach" / "after-80b", "delivery"),
          "booking-example": (REPO / "examples" / "unified-booking", "delivery"),
          "coastal-empty": (SNAPSHOTS / "coastal-merger" / "empty", "discovery"),
          "mini": (REPO / "tests" / "fixtures" / "mini", None)}
ROUTE = re.compile(r"^#(?:home|map|asks|role=\w+|s=[a-z]+)(?:&open=[^&#]+)?$|^#(?:map|asks)&open=[^&#]+$|^#s=apps&v=progress$")
_cache = {}


def data(name):
    if name not in _cache:
        root = VAULTS[name][0]
        _cache[name] = build.extract(cli.load_vault(root), root, "2026-10-19")
    return _cache[name]


def texts(module):
    yield module["gist"], module["title"], module["lede"], module["tryIt"]
    yield from module["body"]
    for it in module["items"]:
        yield it["label"], it["pill"], it["note"]
    for link in module["links"]:
        yield link["label"]


def words(module):
    return " ".join(t for group in texts(module) for t in group if t)


@pytest.fixture(params=sorted(VAULTS))
def vault(request):
    return request.param, data(request.param), onboardmodules.build_all(data(request.param))


def test_every_vault_gets_every_module_once_and_audience_parts_once_per_audience(vault):
    name, facts, modules = vault
    want = set(onboarding.MODULE_IDS) - set(onboarding.AUDIENCE_BOUND)
    want |= {f"{m}@{a}" for m in onboarding.AUDIENCE_BOUND for a in onboarding.AUDIENCES}
    assert set(modules) == want
    for key, module in modules.items():
        assert module["id"] == key.split("@")[0] and module["gist"] and module["title"] and 2 <= module["minutes"] <= 8, key


def test_the_stage_is_worked_out_from_the_plan_not_typed():
    for name, (root, stage) in VAULTS.items():
        if stage:
            assert onboarding.stage_of(data(name)) == stage, name


def test_no_module_shows_an_id_a_check_code_a_handle_or_a_british_spelling(vault):
    name, facts, modules = vault
    for key, module in modules.items():
        text = words(module)
        for kind in say.ID_KINDS:
            assert not say.LEAD_PATTERNS[kind].search(text), (name, key, kind, text[:200])
        assert not say.LEAD_PATTERNS["handle"].search(text) and not say.LEAD_PATTERNS["ISO date"].search(text), (name, key)
        assert not spelling.british_words(text), (name, key, spelling.british_words(text))


def test_every_link_and_item_goes_to_a_route_the_dashboard_has_and_a_thing_it_holds(vault):
    name, facts, modules = vault
    for key, module in modules.items():
        hrefs = [l["href"] for l in module["links"]] + [i["href"] for i in module["items"] if i["href"]]
        for href in hrefs:
            assert ROUTE.match(href), (name, key, href)
            found = re.search(r"open=([^&]+)", href)
            if found:
                from urllib.parse import unquote
                assert unquote(found.group(1)) in facts["entities"], (name, key, href)
        for it in module["items"]:
            assert not it["key"] or it["key"] in facts["entities"], (name, key, it["key"])


def test_two_builds_of_one_plan_say_the_same_thing(vault):
    name, facts, modules = vault
    assert json.dumps(onboardmodules.build_all(facts), sort_keys=True) == json.dumps(modules, sort_keys=True)


def test_a_module_the_plan_is_silent_on_says_so_and_who_to_ask_and_is_not_filled_in():
    modules = onboardmodules.build_all(data("coastal-empty"))
    for key in ("goal", "approach", "standing", "fit@eng", "slices", "contracts", "risks"):
        module = modules[key]
        assert module["gist"].startswith("Not recorded yet: "), key
        assert module["items"] == [] and module["notRecorded"]["ask"] and module["notRecorded"]["ask"] in " ".join(module["body"]), key
    assert modules["goal"]["notRecorded"]["ask"] == "Solution lead", "the owner of the goals page, by the name its handle gives"




def test_where_things_stand_counts_decisions_and_says_what_was_ruled_out():
    standing = onboardmodules.build_all(data("booking-example"))["standing"]
    assert standing["gist"].startswith("4 decisions settled") and "2 questions still open" in standing["gist"]
    first = standing["items"][0]
    assert first["label"] == "One Booking application rather than a shared adapter library" and first["pill"] == "decided"
    assert first["note"].startswith("Ruled out: Shared adapter library used by all three front ends")
    assert first["href"] == "#s=decisions&open=ADR-0001" and first["key"] == "ADR-0001"
    assert [i["pill"] for i in standing["items"]] == ["decided"] * 4 + ["open"] * 2, "the decisions, then the most urgent open questions"


def test_the_goal_is_the_plans_first_goal_and_why_now_is_its_first_release_date():
    facts = data("booking-example")
    goal = onboardmodules.build_all(facts)["goal"]
    assert goal["gist"] == "The first goal: " + facts["goals"][0]["goalText"] + "." and len(goal["gist"].split()) <= 40
    assert [i["label"] for i in goal["items"]] == [g["goalText"] for g in facts["goals"]]
    assert not any("aimed at" in b for b in goal["body"]), "no release has a date here, so no 'why now' is made up"
    heron = onboardmodules.build_all(data("heron-after-full-1"))["goal"]
    assert any(b == "The first release is aimed at 2 February 2027." for b in heron["body"])


def test_kept_terms_are_named_where_they_are_used_and_each_has_a_definition():
    modules = onboardmodules.build_all(data("booking-example"))
    assert modules["approach"]["terms"] == ["slice", "tracer"] and modules["slices"]["terms"] == ["slice"]
    for module in modules.values():
        assert set(module["terms"]) <= set(terms.TERMS)
    assert onboardmodules.build_all(data("coastal-empty"))["approach"]["terms"] == []


def test_a_role_sees_what_it_touches_and_the_engineer_does_not_see_unchanged_apps():
    facts = data("booking-example")
    eng = onboardmodules.build_all(facts)["fit@eng"]
    apps = [e for e in facts["entities"].values() if e["kind"] == "app"]
    changing = [e for e in apps if e["change"] not in ("unchanged", "integrated")]
    assert len(eng["items"]) == len(changing) < len(apps)
    assert eng["gist"] == f"As an engineer, you will mostly deal with the apps being built or changed: {len(changing)} here."


def test_people_are_named_as_people_with_what_they_own_and_who_holds_open_answers():
    people = onboardmodules.build_all(data("booking-example"))["people@eng"]
    first = people["items"][0]
    assert first["label"] == "Harborline/booking team" and first["note"] == "Owns Booking" and "@" not in first["label"]
    assert any(i["pill"] == "holds answers" for i in people["items"])


def test_the_depth_rule_is_one_table_the_page_and_the_command_share():
    assert onboardmodules.DEPTHS == {"gist": {"body": 0, "items": 3}, "normal": {"body": 2, "items": 6}, "everything": {"body": None, "items": None}}


def test_the_tracer_is_named_without_claiming_an_order_the_plan_does_not_show():
    approach = onboardmodules.build_all(data("booking-example"))["approach"]
    assert any(re.match(r"The tracer is [^:]+\.$", b) for b in approach["body"]) and not any("first slice" in b for b in approach["body"])


def test_a_date_is_only_given_to_the_release_it_belongs_to():
    import copy
    facts = copy.deepcopy(data("heron-after-full-1"))
    states = facts["releases"]["states"]
    later = copy.deepcopy(states[1])
    later["name"] = later["heading"] = "Release two"
    states[1]["target"] = ""
    states.append(later)
    body = onboardmodules.build_all(facts)["goal"]["body"]
    assert "The next dated release, Release two, is due 2 February 2027." in body
    assert not any(b.startswith("The first release") for b in body)
    states.pop()
    assert not any("release" in b for b in onboardmodules.build_all(facts)["goal"]["body"])


def test_counts_of_one_agree_with_their_verb():
    import copy
    facts = copy.deepcopy(data("booking-example"))
    facts["slicePlan"]["list"] = facts["slicePlan"]["list"][:1]
    facts["slicePlan"]["list"][0]["status"] = "journey passes"
    assert onboardmodules.slices(facts)["gist"] == "1 of 1 slice has passed its journey."
    key = next(iter(facts["failure"]))
    facts["failure"] = {key: facts["failure"][key]}
    gist = onboardmodules.failure(facts)["gist"]
    assert gist.startswith("1 of 1 app says") or gist.startswith("0 of 1 app say"), gist
    facts["asks"] = [a for a in facts["asks"] if a["state"] == "open"][:1]
    assert onboardmodules.blocked(facts)["gist"] == "1 person holds answers the plan is waiting on."
    for name in sorted(VAULTS):
        waiting = copy.deepcopy(data(name))
        lit = [k for k in waiting["ranked"] if k in waiting["entities"] and waiting["lights"][k]["level"] in onboardmodules.LEVEL_WORD]
        if lit:
            waiting["ranked"] = lit[:1]
            assert onboardmodules.needs_you(waiting)["gist"].startswith("1 thing needs the lead"), name
            return
    pytest.fail("no vault in the table has anything waiting")


def test_every_control_a_try_prompt_names_is_a_label_the_dashboard_has():
    assets = "\n".join(p.read_text(encoding="utf-8").lower() for p in (REPO / "plugin" / "lib" / "vela" / "explorer" / "assets").rglob("*") if p.suffix in (".js", ".html", ".css"))
    named = {"approach": ["slices", "path"], "standing": ["decision log"], "open-questions": ["who to ask"], "needs-you": ["what's waiting"],
             "journeys": ["present"], "contracts": ["map"], "slices": ["slices"], "apps": ["map"], "progress": ["progress"]}
    assert set(named) == set(onboardmodules.TRY)
    for mid, controls in named.items():
        prompt = onboardmodules.TRY[mid][1].lower()
        for control in controls:
            assert control in prompt and control in assets, (mid, control)
    assert "needs you" not in " ".join(p[1] for p in onboardmodules.TRY.values()).lower()
