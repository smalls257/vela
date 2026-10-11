"""The checks that see the gaps the explorer used to hide: flow senders, domains, release dates, asks, requirements."""
import json
import re
import shutil

from conftest import REPO, edit, run
from planner import cli, flows, rules, schema

FIXTURE = REPO / "examples" / "unified-booking"
FLOW = "06-runtime/flows/FLO-001-hold-pay-confirm.md"
STEP5 = "5. [[CAP-022-notify-customer|Notify customer]]."
CON1 = "[[booking-building-blocks#CON-001 Booking API|Booking API]]"
CON7 = "[[booking-building-blocks#CON-007 Tidepay payment outcome|Tidepay payment outcome]]"
WEBSITE = "[[website-building-blocks|Public website]]"
BOOKING = "[[booking-building-blocks|Booking]]"
TODAY = "2026-11-20"


def copy(tmp_path):
    vault = tmp_path / "v"
    shutil.copytree(FIXTURE, vault)
    return vault


def check(vault):
    return run("check", "--vault", str(vault), "--today", TODAY)[1]


def with_step(tmp_path, step):
    """The example's hold flow with one more step ahead of its last."""
    vault = copy(tmp_path)
    edit(vault / FLOW, STEP5, f"6. {step}\n{STEP5}")
    return vault


def test_a_step_with_a_sender_pair_the_contract_joins_is_clean(tmp_path):
    out = check(with_step(tmp_path, f"{WEBSITE} → {BOOKING}: asks to hold the seat over {CON1}."))
    assert "E350" not in out and "W351" not in out, out


def test_the_ascii_arrow_reads_like_the_unicode_one():
    assert flows.split_pair("A -> B: sends it.") == ("A", "B")
    assert flows.split_pair("[[x|A]] → [[y|B]]: sends it.") == ("[[x|A]]", "[[y|B]]")
    assert flows.split_pair("The channel sends it over the wire.") == ()


def test_a_pair_the_contract_does_not_join_is_an_error(tmp_path):
    out = check(with_step(tmp_path, f"{BOOKING} → [[pricing-building-blocks|Pricing]]: asks for a hold over {CON1}."))
    assert "E350" in out


def test_a_pair_that_sends_to_itself_is_an_error(tmp_path):
    assert "E350" in check(with_step(tmp_path, f"{BOOKING} → {BOOKING}: writes the hold over {CON1}."))


def test_an_outside_provider_is_named_by_its_name(tmp_path):
    out = check(with_step(tmp_path, f"Tidepay -> {BOOKING}: reports the outcome over {CON7}."))
    assert "E350" not in out, out


def test_a_step_that_links_a_contract_and_names_no_pair_warns_only(tmp_path):
    code, out = run("check", "--vault", str(with_step(tmp_path, f"The channel holds the seat over {CON1}.")), "--today", TODAY)
    assert "W351" in out and "E350" not in out and code == 0, out


def test_steps_read_back_their_pair_and_their_contracts(tmp_path):
    model = cli.load_vault(with_step(tmp_path, f"{WEBSITE} → {BOOKING}: asks to hold the seat over {CON1}."))
    step = next(s for s in flows.steps(model) if s.number == 6 and s.page.id == "FLO-001")
    assert [flows.endpoint(model, step.page, t) for t in step.pair] == ["APP-website", "APP-booking"]
    assert [c.id for c in step.contracts] == ["CON-001"]


def set_domains(vault, mapping):
    for slug, domain in mapping.items():
        path = vault / "05-building-blocks" / f"{slug}-building-blocks.md"
        path.write_text(path.read_text(encoding="utf-8").replace("\n---\n", f"\ndomain: {domain}\n---\n", 1), encoding="utf-8")


def test_once_one_app_has_a_domain_the_rest_of_a_large_initiative_warn(tmp_path):
    vault = copy(tmp_path)
    assert "W352" not in check(vault)  # no app names one: nothing to match
    set_domains(vault, {"website": "Channels"})
    assert check(vault).count("W352") == 8  # nine apps, one named


def test_a_small_initiative_is_not_asked_for_domains(tmp_path):
    vault = copy(tmp_path)
    set_domains(vault, {"website": "Channels"})
    model = cli.load_vault(vault)
    keep = {"website", "kiosks"}
    model.pages[:] = [p for p in model.pages if p.type != "app-building-blocks" or p.name.split("-building")[0] in keep]
    assert len(model.apps) < schema.DOMAIN_MIN_APPS
    assert list(rules.domain_rules(model, TODAY)) == []


def test_domains_that_differ_only_by_case_or_a_trailing_s_warn(tmp_path):
    vault = copy(tmp_path)
    set_domains(vault, {"website": "Channels", "kiosks": "Channels", "call-centre": "channel"})
    out = check(vault)
    assert "W353" in out and "call-centre" in out, out


def test_a_release_target_must_be_a_date(tmp_path):
    vault = copy(tmp_path)
    (vault / "04b-releases.md").write_text(
        "---\nid: releases\ntype: initiative-section\ntitle: Releases\narc42: \"§4\"\nstate: assumption\n"
        "owner: \"@hl-solution-lead\"\nauthored: mixed\n---\n\n# Releases\n\n## Release one\n\n- **Target:** January\n"
        "- **State:** assumption\n\n| Delivers | Criteria | Note |\n|---|---|---|\n\n", encoding="utf-8")
    assert "E344" in check(vault)


def test_an_ask_that_names_the_owner_warns(tmp_path):
    vault = copy(tmp_path)
    owner = "- **Owner:** @hl-booking-senior (Booking senior)\n"
    edit(vault / "11-unknowns-and-risks.md", owner, owner + "- **Ask:** @hl-booking-senior\n")
    assert "W355" in check(vault)


def test_a_changing_capability_with_no_requirements_warns_and_a_requirement_with_no_criteria_warns(tmp_path):
    vault = copy(tmp_path)
    assert "W356" in check(vault)
    cap = vault / "capabilities/CAP-014-hold-a-seat.md"
    cap.write_text(cap.read_text(encoding="utf-8").rstrip("\n") +
                   "\n\n## Functional requirements\n\n### CAP-014.FR1 Hold a seat\n\nA seat is held while paying.\n\n"
                   "- **State:** assumption\n- **Source:** SRC-04\n", encoding="utf-8")
    out = check(vault)
    assert "W357" in out and "CAP-014 is new but has no functional requirements" not in out


def test_the_explorer_draws_a_recorded_sender_as_stated_even_against_the_provider(tmp_path):
    """CON-001 is provided by Booking; a step that says the website sends first is stated, website to booking."""
    vault = with_step(tmp_path, f"{WEBSITE} → {BOOKING}: waits on {CON1}.")
    code, said = run("explore", str(vault), "--today", TODAY)
    assert code == 0, said
    page = (vault / ".planner" / "explorer.html").read_text(encoding="utf-8")
    data = json.loads(re.search(r'<script type="application/json" id="data">(.*?)</script>', page, re.S).group(1))
    flow = next(f for f in data["flows"] if f["key"] == "FLO-001")
    step = next(s for s in flow["steps"] if s["n"] == 6)
    assert step["messages"] == [{"from": "APP-website", "to": "APP-booking", "contract": "CON-001",
                                 "direction": "stated", "kind": "send"}]
