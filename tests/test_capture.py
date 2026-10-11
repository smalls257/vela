"""planner capture counts what a vault records for the explorer; the v2 sim script asks the sessions that fill it."""
import json
import shutil

import yaml

from conftest import REPO, edit, run
from planner import capture, cli
from test_capture_rules import BOOKING, CON1, FLOW, STEP5, WEBSITE, set_domains

SIM = REPO / "tests" / "sim"
FIXTURE = REPO / "examples" / "unified-booking"


def copy(tmp_path):
    vault = tmp_path / "v"
    shutil.copytree(FIXTURE, vault)
    return vault


def test_a_vault_that_records_none_of_it_counts_zero_and_fails_both_standing_checks():
    found = capture.counts(cli.load_vault(FIXTURE))
    assert (found["apps_with_domain"], found["releases"], found["requirements"], found["allocation_rows"]) == (0, 0, 0, 0)
    assert found["flow_steps_with_sender"] == 0
    assert not any(ok for _, ok, _ in capture.verdict(found))


def test_domains_pairs_and_asks_are_counted_and_the_verdict_reads_them(tmp_path):
    vault = copy(tmp_path)
    set_domains(vault, {slug: "Area" for slug in ("website", "kiosks", "call-centre", "booking", "pricing", "notifications",
                                                  "vessel-schedule", "customer-identity", "ferrymaster")})
    edit(vault / FLOW, STEP5, f"6. {WEBSITE} → {BOOKING}: asks to hold the seat over {CON1}.\n{STEP5}")
    owner = "- **Owner:** @hl-booking-senior (Booking senior)\n"
    edit(vault / "11-unknowns-and-risks.md", owner, owner + "- **Ask:** outside counsel\n")
    found = capture.counts(cli.load_vault(vault))
    assert found["apps_with_domain"] == found["apps"] == 9
    assert (found["flow_steps_crossing"], found["flow_steps_with_sender"]) == (1, 1)
    assert found["asks"] == ["outside counsel"]
    checks = capture.verdict(found, release_date="2027-01-15", ask_phrase="Outside Counsel")
    assert [ok for _, ok, _ in checks] == [True, True, False, True]  # no release is dated yet


def test_the_command_prints_a_line_and_the_json_the_simulator_reads():
    code, said = run("capture", "--vault", str(FIXTURE))
    assert code == 0 and said.startswith("planner capture: 0 of 9 apps have a domain")
    code, said = run("capture", "--vault", str(FIXTURE), "--json", "--expect-ask", "outside counsel")
    data = json.loads(said)
    assert data["counts"]["apps"] == 9 and data["checks"][-1]["check"] == "an Ask names 'outside counsel'"


def test_the_v2_script_runs_the_three_sessions_between_the_journeys_and_the_epics():
    script = yaml.safe_load((SIM / "scripts" / "trading-complete-v2.yaml").read_text(encoding="utf-8"))
    modes = [s["mode"] for s in script["sessions"]]
    at = modes.index("requirements")
    assert modes[at - 2:at] == ["grill", "close"]
    assert [m for m in modes[at:at + 6]] == ["requirements", "close", "allocate", "close", "releases", "close"]
    assert modes[at + 6] == "epics"
    assert script["capture"] == {"release_date": "2027-01-15", "ask": "outside counsel"}
    facts = " ".join(k["fact"] for k in script["news"]["knows"])
    assert "15 January 2027" in facts and "Learning" in facts and "only outside counsel" in facts
    old = yaml.safe_load((SIM / "scripts" / "trading-complete.yaml").read_text(encoding="utf-8"))
    assert modes[:at] + modes[at + 6:] == [s["mode"] for s in old["sessions"]]  # nothing else changed
