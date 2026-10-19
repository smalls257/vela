"""The onboarding data a page carries (D.onboard), and what `vela explore` may and may not put in it.

The Violation these guard against is a Distributed Monolith between the shared page and one person's page: the shared
dashboard.html is committed, so it must carry the standard path and nobody's own; a person's page is built beside it.
"""
import json
import re
import shutil

import pytest

from conftest import REPO, run
from vela import onboarding, onboardpath
from vela.explorer import build, onboard_data
from vela import cli

TODAY = "2026-10-19"
HERON = REPO / "tests" / "sim" / "snapshots" / "heron-desk" / "after-full-1"
BOOKING = REPO / "examples" / "unified-booking"
PAGE = "The onboarding page, line "


@pytest.fixture
def vault(tmp_path):
    root = tmp_path / "vault"
    shutil.copytree(HERON, root)
    return root


def page_data(path):
    """The data a built page carries, read back as the page's own script would."""
    text = path.read_text(encoding="utf-8")
    return json.loads(re.search(r'<script type="application/json" id="data">(.*?)</script>', text, re.S).group(1))


def save_path(vault, handle="sam", audience="eng", modules=("goal", "contracts"), **more):
    made, said = onboardpath.make(handle, audience, list(modules), **more)
    assert made is not None, said
    target = vault / onboardpath.file_for(handle)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(onboardpath.to_text(made), encoding="utf-8")


def tune(vault, text):
    (vault / "ONBOARDING.md").write_text(text, encoding="utf-8")


def test_the_page_carries_the_onboarding_data_for_every_audience(tmp_path):
    root = tmp_path / "booking"
    shutil.copytree(BOOKING, root)
    code, out = run("explore", str(root), "--today", "2026-11-20")
    onboard = page_data(root / "dashboard.html")["onboard"]
    assert code == 0 and onboard["stage"] == "delivery" and [a["id"] for a in onboard["audiences"]] == list(onboarding.AUDIENCES)
    for audience, path in onboard["paths"].items():
        assert all(k in onboard["modules"] for k in path["modules"]), audience
        assert path["modules"][:5] == ["goal", "approach", "standing", f"fit@{audience}", f"people@{audience}"]
    assert onboard["mine"] is None and onboard["problems"] == [] and set(onboard["depths"]) == {"gist", "normal", "everything"}


def test_an_empty_plan_still_has_a_full_standard_path(tmp_path):
    root = tmp_path / "empty"
    shutil.copytree(REPO / "tests" / "sim" / "snapshots" / "coastal-merger" / "empty", root)
    run("explore", str(root), "--today", TODAY)
    onboard = page_data(root / "dashboard.html")["onboard"]
    assert onboard["stage"] == "discovery" and onboard["paths"]["eng"]["modules"][:5] == ["goal", "approach", "standing", "fit@eng", "people@eng"]
    assert onboard["modules"]["goal"]["notRecorded"]["ask"] == "Solution lead"


def test_two_builds_of_one_plan_write_the_same_bytes_and_a_personal_path_does_not_move_the_shared_page(vault):
    run("explore", str(vault), "--today", TODAY)
    first = (vault / "dashboard.html").read_bytes()
    save_path(vault)
    run("explore", str(vault), "--today", TODAY)
    assert (vault / "dashboard.html").read_bytes() == first, "a person's path changed the shared page"
    assert page_data(vault / "dashboard.html")["onboard"]["mine"] is None


def test_a_page_built_for_one_person_carries_their_path_and_is_written_beside_it_never_over_the_shared_page(vault):
    save_path(vault, depth="gist", diagrams=True)
    code, out = run("explore", str(vault), "--person", "sam", "--today", TODAY)
    assert code == 0 and not (vault / "dashboard.html").exists() and (vault / ".vela" / "onboard" / "sam.html").is_file()
    mine = page_data(vault / ".vela" / "onboard" / "sam.html")["onboard"]["mine"]
    assert mine == {"handle": "sam", "audience": "eng", "modules": ["goal", "contracts"], "depth": "gist", "diagrams": True,
                    "broughtBack": [], "keys": ["goal", "contracts"]}


def test_the_leads_tuning_reaches_the_data_in_order_with_what_was_hidden_and_the_note(vault):
    tune(vault, "## Engineering\n- Stress: Open questions\n- Hide: Apps\n- Note: Read the contract for the pilot first.\n")
    run("explore", str(vault), "--today", TODAY)
    eng = page_data(vault / "dashboard.html")["onboard"]["paths"]["eng"]
    assert eng == {"modules": ["goal", "approach", "standing", "fit@eng", "people@eng", "open-questions", "contracts", "journeys"],
                   "hidden": ["Apps"], "note": "Read the contract for the pilot first."}
    assert page_data(vault / "dashboard.html")["onboard"]["paths"]["exec"]["note"] == ""


def test_every_explore_says_what_is_wrong_on_the_leads_page_and_still_builds(vault):
    tune(vault, "## Engineering\n- Hide: Contrcts\n")
    code, out = run("explore", str(vault), "--today", TODAY)
    assert code == 0 and f"vela explore: {PAGE}2: 'Contrcts' is not a module" in out and (vault / "dashboard.html").is_file()
    assert page_data(vault / "dashboard.html")["onboard"]["problems"][0].startswith(PAGE + "2")


def test_a_leads_page_that_cannot_be_read_stops_the_build_and_says_why(vault):
    (vault / "ONBOARDING.md").write_bytes(b"\xff\xfe not utf-8")
    code, out = run("explore", str(vault), "--today", TODAY)
    assert code == 2 and "the onboarding page can't be read" in out and not (vault / "dashboard.html").exists()


def test_a_path_the_lead_has_since_hidden_is_not_shown_and_the_page_says_why(vault):
    save_path(vault)
    tune(vault, "## Engineering\n- Hide: Contracts\n")
    code, out = run("explore", str(vault), "--person", "sam", "--today", TODAY)
    assert code == 0 and "sam's own path was not used" in out and "the lead hid 'contracts'" in out
    assert page_data(vault / ".vela" / "onboard" / "sam.html")["onboard"]["mine"] is None


def test_a_hidden_module_asked_for_by_name_stays_on_the_path_and_is_recorded(vault):
    save_path(vault)
    tune(vault, "## Engineering\n- Hide: Contracts\n")
    save_path(vault, hidden=("contracts",), bring_back=("contracts",))
    code, out = run("explore", str(vault), "--person", "sam", "--today", TODAY)
    mine = page_data(vault / ".vela" / "onboard" / "sam.html")["onboard"]["mine"]
    assert code == 0 and mine["broughtBack"] == ["contracts"] and mine["keys"] == ["goal", "contracts"]


def test_a_page_for_someone_with_only_a_role_and_no_path_still_builds_and_opens_as_that_role(vault):
    run("whoami", "--vault", str(vault), "--set", "sam")
    run("whoami", "--vault", str(vault), "--role", "qa")
    code, out = run("explore", str(vault), "--person", "sam", "--today", TODAY)
    onboard = page_data(vault / ".vela" / "onboard" / "sam.html")["onboard"]
    assert code == 0 and onboard["mine"] is None and onboard["me"] == {"handle": "sam", "role": "qa"}


def test_the_shared_page_carries_the_leads_roles_but_nobodys_handle_or_choice(vault):
    run("whoami", "--vault", str(vault), "--set", "sam")
    run("whoami", "--vault", str(vault), "--role", "qa")
    config = vault / ".vela.yaml"
    config.write_text(config.read_text(encoding="utf-8").rstrip("\n") + "\nroles:\n  '@ana': Engineer\n  bo: mgr\n", encoding="utf-8")
    run("explore", str(vault), "--today", TODAY)
    onboard = page_data(vault / "dashboard.html")["onboard"]
    assert onboard["roles"] == {"ana": "eng", "bo": "mgr"} and onboard["me"] is None and onboard["problems"] == []
    assert b'"role":"qa"' not in (vault / "dashboard.html").read_bytes().replace(b" ", b"")


def test_a_role_in_the_plans_settings_that_is_not_one_of_the_six_is_said_and_left_out(vault):
    config = vault / ".vela.yaml"
    config.write_text(config.read_text(encoding="utf-8").rstrip("\n") + "\nroles:\n  ana: janitor\n  bo: qa\n", encoding="utf-8")
    code, out = run("explore", str(vault), "--today", TODAY)
    assert code == 0 and "give ana the role 'janitor'" in out
    assert page_data(vault / "dashboard.html")["onboard"]["roles"] == {"bo": "qa"}
    config.write_text(config.read_text(encoding="utf-8").replace("roles:\n  ana: janitor\n  bo: qa\n", "roles: nope\n"), encoding="utf-8")
    code, out = run("explore", str(vault), "--today", TODAY)
    assert "should list a handle and a role for each person" in out and page_data(vault / "dashboard.html")["onboard"]["roles"] == {}


def test_a_saved_path_that_holds_text_is_not_used(vault):
    (vault / ".vela" / "onboard").mkdir(parents=True)
    (vault / ".vela" / "onboard" / "sam.json").write_text(json.dumps({"audience": "eng", "modules": ["goal"], "note": "Booking is late"}), encoding="utf-8")
    code, out = run("explore", str(vault), "--person", "sam", "--today", TODAY)
    assert code == 2 and "'note', which is not a choice" in out and not (vault / ".vela" / "onboard" / "sam.html").exists()


@pytest.mark.parametrize("handle", ["../x", "a/b", "-sam"])
def test_a_handle_that_could_name_another_file_is_refused_before_any_file_is_read(vault, handle):
    code, out = run("explore", str(vault), f"--person={handle}", "--today", TODAY)
    assert code == 2 and "isn't a handle" in out


def test_the_data_is_read_once_from_the_explorers_own_extract_for_the_command_and_the_page(vault):
    tune(vault, "## QA\n- Note: Start with the contract tests.\n")
    data = build.extract(cli.load_vault(vault), vault, TODAY)
    assert data["onboard"]["paths"]["qa"]["note"] == "Start with the contract tests."
    assert onboard_data.read_tuning(vault).for_audience("qa").note == "Start with the contract tests."
