"""`vela onboard`: the standard path for a role, the lead's page checked, and a person's own path set, shown and cleared.

The Violation these guard against is a Leaky Narrative at the skill: it sees names and plain lines, never a module id or
a file format, and a path it sets is the path the page shows (both read `explorer.onboard_data.extract`). The data a page
carries is held by test_onboard_data.py; this file holds the command.
"""
import json
import re
import shutil

import pytest

from conftest import REPO, run
from vela import publish, say
from test_onboard_data import page_data

TODAY = "2026-10-19"
HERON = REPO / "tests" / "sim" / "snapshots" / "heron-desk" / "after-full-1"
BOOKING = REPO / "examples" / "unified-booking"
PAGE = "The onboarding page, line "


@pytest.fixture
def vault(tmp_path):
    root = tmp_path / "vault"
    shutil.copytree(HERON, root)
    (root / ".vela").mkdir(exist_ok=True)
    (root / ".vela" / "handle").write_text("sam\n", encoding="utf-8")
    return root


def onboard(vault, *argv, mode="--json"):
    code, out = run("onboard", *argv, "--vault", str(vault), "--today", TODAY, mode)
    return code, (json.loads(out) if mode == "--json" else out)


def tune(vault, text):
    (vault / "ONBOARDING.md").write_text(text, encoding="utf-8")


def set_path(vault, *extra, mode="--json"):
    return onboard(vault, "path", "set", "--role", "eng", "--modules", "Goal, Contracts, Journeys", *extra, mode=mode)


# ------------------------------------------------------------------ show, modules, check

def test_show_gives_the_standard_path_for_a_role_at_the_projects_stage(vault):
    code, shown = onboard(vault, "show", "--role", "eng")
    assert code == 0 and shown["stage"] == "design" and shown["role"] == "eng"
    assert [m["name"] for m in shown["modules"]] == ["Goal", "Approach", "Where things stand", "Where you fit", "Who to talk to", "Apps", "Contracts", "Journeys", "Open questions"]
    assert shown["minutes"] == sum(m["minutes"] for m in shown["modules"]) and shown["note"] == "" and shown["hidden"] == []


def test_show_says_the_answer_first_and_never_a_code_to_the_lead(vault):
    code, said = onboard(vault, "show", "--role", "exec", mode="--for-lead")
    lines = said.strip().splitlines()
    assert code == 0 and lines[0].startswith("This project is at the design stage. The Exec path is 8 parts, about ")
    assert len(lines) <= 6 and lines[-1].endswith("more; want them?")
    assert say.leak_in(said) is None
    code, everything = onboard(vault, "show", "--role", "exec", "--more", mode="--for-lead")
    assert len(everything.strip().splitlines()) == 9


def test_the_leads_page_orders_hides_and_notes_what_the_command_shows(vault):
    tune(vault, "## Engineering\n- Stress: Open questions\n- Hide: Apps\n- Note: Read the contract for the pilot first.\n")
    code, shown = onboard(vault, "show", "--role", "eng")
    assert [m["name"] for m in shown["modules"]][5:] == ["Open questions", "Contracts", "Journeys"]
    assert shown["hidden"] == ["Apps"] and shown["note"] == "Read the contract for the pilot first."
    code, said = onboard(vault, "show", "--role", "eng", mode="--for-lead")
    assert said.splitlines()[1] == "The lead's note for Engineering: Read the contract for the pilot first."


def test_a_role_said_on_the_command_line_is_understood_the_way_a_person_says_it(vault):
    for said, role in (("engineer", "eng"), ("QA lead", "qa"), ("delivery manager", "mgr")):
        code, shown = onboard(vault, "show", "--role", said)
        assert code == 0 and shown["role"] == role and shown["roleSource"] == "said"


def roles_in_settings(vault, **who):
    text = (vault / ".vela.yaml").read_text(encoding="utf-8")
    (vault / ".vela.yaml").write_text(text.rstrip("\n") + "\nroles:\n" + "".join(f"  '{h}': {r}\n" for h, r in who.items()), encoding="utf-8")


def test_with_no_role_named_the_leads_record_wins_then_the_persons_choice_then_their_path_then_ask(vault):
    code, shown = onboard(vault, "show")
    assert shown["role"] == "exec" and shown["roleSource"] == "none", "nothing is known, so the skill must ask"
    set_path(vault)
    assert onboard(vault, "show")[1]["roleSource"] == "path" and onboard(vault, "show")[1]["role"] == "eng"
    run("whoami", "--vault", str(vault), "--role", "qa")
    assert onboard(vault, "show")[1]["role"] == "qa" and onboard(vault, "show")[1]["roleSource"] == "choice"
    roles_in_settings(vault, **{"@sam": "product"})
    shown = onboard(vault, "show")[1]
    assert shown["role"] == "product" and shown["roleSource"] == "record"
    assert onboard(vault, "show", "--role", "mgr")[1]["role"] == "mgr", "what the person says now is used for this path"


def test_modules_lists_every_name_and_what_it_is_for(vault):
    code, listed = onboard(vault, "modules")
    names = [m["name"] for m in listed["modules"]]
    assert code == 0 and len(names) == 20 and names[:5] == ["Goal", "Approach", "Where things stand", "Where you fit", "Who to talk to"]
    assert all(m["lede"] and m["roles"] for m in listed["modules"])


def test_check_names_each_mistake_on_the_leads_page_and_exits_1(vault):
    tune(vault, "## Engineering\n- Hide: Contrcts\n## Sales\n")
    code, said = onboard(vault, "check", mode="--for-lead")
    assert code == 1 and said.splitlines()[0] == "The onboarding page has 2 things to fix."
    assert f"{PAGE}2: 'Contrcts' is not a module. Did you mean 'Contracts'?" in said and "'Sales' is not a role" in said
    tune(vault, "## Engineering\n- Hide: Apps\n")
    code, said = onboard(vault, "check", mode="--for-lead")
    assert code == 0 and said.strip() == "The onboarding page reads cleanly."


def test_vela_check_never_reads_the_leads_page(vault):
    tune(vault, "not a vault page: no frontmatter, no headings a page needs\n")
    code, out = run("check", "--vault", str(vault), "--today", TODAY)
    assert "ONBOARDING.md" not in out


def test_the_command_and_the_page_read_the_same_path(vault):
    tune(vault, "## QA\n- Note: Start with the contract tests.\n")
    code, shown = onboard(vault, "show", "--role", "qa")
    run("explore", str(vault), "--today", TODAY)
    onboard_data_ = page_data(vault / "dashboard.html")["onboard"]
    keys = onboard_data_["paths"]["qa"]["modules"]
    assert [onboard_data_["modules"][k]["name"] for k in keys] == [m["name"] for m in shown["modules"]]
    assert onboard_data_["stage"] == shown["stage"] and onboard_data_["paths"]["qa"]["note"] == shown["note"] == "Start with the contract tests."


def test_a_plan_with_no_leads_page_gets_the_standard_path(tmp_path):
    root = tmp_path / "booking"
    shutil.copytree(BOOKING, root)
    code, shown = onboard(root, "show", "--role", "mgr")
    assert code == 0 and shown["stage"] == "delivery" and [m["name"] for m in shown["modules"]][5:] == ["Progress", "Slices", "Who is blocking what", "Dates"]


# ------------------------------------------------------------------ a person's own path

def test_setting_a_path_saves_choices_under_the_handle_and_builds_their_page(vault):
    code, done = set_path(vault, "--depth", "gist", "--diagrams", "yes")
    assert code == 0 and done["file"] == ".vela/onboard/sam.html" and done["wrote"] == [".vela/onboard/sam.json", ".vela/onboard/sam.html"]
    saved = json.loads((vault / ".vela" / "onboard" / "sam.json").read_text(encoding="utf-8"))
    assert saved == {"audience": "eng", "broughtBack": [], "depth": "gist", "diagrams": True, "modules": ["goal", "contracts", "journeys"]}
    mine = page_data(vault / ".vela" / "onboard" / "sam.html")["onboard"]["mine"]
    assert mine["keys"] == ["goal", "contracts", "journeys"] and mine["handle"] == "sam" and mine["diagrams"] is True


def test_the_shared_dashboard_is_committed_so_it_carries_nobodys_path(vault):
    set_path(vault)
    code, out = run("explore", str(vault), "--today", TODAY)
    assert code == 0 and page_data(vault / "dashboard.html")["onboard"]["mine"] is None
    before = (vault / "dashboard.html").read_bytes()
    set_path(vault, "--depth", "everything")
    run("explore", str(vault), "--today", TODAY)
    assert (vault / "dashboard.html").read_bytes() == before, "a person's path changed the shared page"


def test_a_personal_path_is_never_published_and_the_leads_page_is():
    assert publish.is_excluded(".vela/onboard/sam.json") and publish.is_excluded(".vela/onboard/sam.html")
    assert not publish.is_excluded("ONBOARDING.md")


def test_setting_again_replaces_and_clearing_goes_back_to_the_standard_path(vault):
    set_path(vault)
    code, again = onboard(vault, "path", "set", "--role", "exec", "--modules", "Risks")
    assert code == 0 and onboard(vault, "path", "show")[1]["path"]["audience"] == "exec"
    code, cleared = onboard(vault, "path", "clear")
    assert code == 0 and cleared["cleared"] and not (vault / ".vela" / "onboard" / "sam.json").exists() and not (vault / ".vela" / "onboard" / "sam.html").exists()
    code, none = onboard(vault, "path", "show", mode="--for-lead")
    assert code == 0 and "no path of your own yet" in none


@pytest.mark.parametrize("argv, rule, said", [
    (["--role", "eng", "--modules", "Goal, Vendors"], "onboard-module", "'Vendors' isn't a module"),
    (["--role", "eng", "--modules", "Contrcts"], "onboard-module", "Did you mean 'Contracts'?"),
    (["--role", "sales", "--modules", "Goal"], "onboard-role", "'sales' isn't a role"),
    (["--role", "eng", "--modules", "Goal", "--depth", "deep"], "onboard-path", "'deep' is not a depth"),
    (["--role", "eng", "--modules", "Goal", "--diagrams", "maybe"], "onboard-diagrams", "isn't yes or no"),
    (["--role", "eng", "--modules", "Goal, Goal"], "onboard-path", "'goal' is listed twice"),
    (["--role", "eng", "--modules", "Goal", "--handle", "../x"], "onboard-handle", "isn't a handle")])
def test_a_choice_that_is_not_in_the_vocabulary_is_refused_and_nothing_is_written(vault, argv, rule, said):
    code, refused = onboard(vault, "path", "set", *argv)
    assert code == 1 and refused["refusals"][0]["rule"] == rule and said in refused["refusals"][0]["plain"]
    assert not (vault / ".vela" / "onboard").exists()


@pytest.mark.parametrize("verb", ["show", "clear", "build"])
def test_no_verb_reads_or_removes_a_file_a_handle_could_point_outside_the_folder(vault, verb):
    args = ("path", verb) if verb != "build" else ("build",)
    code, refused = onboard(vault, *args, "--handle", "../x")
    assert code == 1 and refused["refusals"][0]["rule"] == "onboard-handle"


def test_a_handle_typed_with_the_at_sign_is_the_same_person(vault):
    code, done = set_path(vault, "--handle", "@ana")
    assert code == 0 and (vault / ".vela" / "onboard" / "ana.json").is_file()


def test_a_module_the_lead_hid_is_the_leads_call_to_set_aside_and_is_recorded_when_asked_for(vault):
    tune(vault, "## Engineering\n- Hide: Apps\n")
    code, refused = onboard(vault, "path", "set", "--role", "eng", "--modules", "Goal, Apps")
    assert code == 1 and refused["refusals"][0]["rule"] == "onboard-hidden" and refused["refusals"][0]["audience"] == "lead"
    assert not (vault / ".vela" / "onboard").exists()
    code, done = onboard(vault, "path", "set", "--role", "eng", "--modules", "Goal, Apps", "--bring-back", "Apps")
    assert code == 0 and done["path"]["broughtBack"] == ["apps"]
    code, said = onboard(vault, "path", "show", mode="--for-lead")
    assert "Goal, Apps" in said


def test_a_person_whose_handle_is_unknown_is_asked_once_and_nothing_is_written(tmp_path):
    root = tmp_path / "copy"
    shutil.copytree(HERON, root)
    (root / ".vela").mkdir(exist_ok=True)
    (root / ".vela" / "workspace.json").write_text("{}", encoding="utf-8")  # a reader copy never runs gh, so only the person can say
    code, asked = onboard(root, "path", "set", "--role", "eng", "--modules", "Goal")
    assert code == 3 and asked["needs_lead"][0]["ask"] == "handle" and not (root / ".vela" / "onboard").exists()
    code, _ = run("whoami", "--vault", str(root), "--set", "ana")
    code, done = onboard(root, "path", "set", "--role", "eng", "--modules", "Goal")
    assert code == 0 and (root / ".vela" / "onboard" / "ana.json").is_file()


def test_a_saved_path_that_holds_text_is_reported_not_used(vault):
    (vault / ".vela" / "onboard").mkdir()
    (vault / ".vela" / "onboard" / "sam.json").write_text(json.dumps({"audience": "eng", "modules": ["goal"], "note": "Booking is late"}), encoding="utf-8")
    code, shown = onboard(vault, "path", "show", mode="--for-lead")
    assert code == 2 and "isn't usable" in shown
    code, rebuilt = onboard(vault, "build")
    assert code == 2 and rebuilt["lines"][0].startswith("the path file is not usable")
