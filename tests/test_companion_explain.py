"""vela companion explain: a closed list of views, vela's own numbers, and what the plan doesn't know."""
import json
import re
import shutil

import pytest

from conftest import REPO, run
from companion_vault import run_companion
from vela import companionexplain, companionseen

EXAMPLE = REPO / "examples" / "unified-booking"


@pytest.fixture(scope="module")
def plan(tmp_path_factory):
    root = tmp_path_factory.mktemp("explain") / "plan"
    shutil.copytree(EXAMPLE, root)
    assert run("companion", "prepare", "--vault", str(root), "--today", "2026-10-24")[0] == 0
    return root


def explain(root, *args):
    code, out = run_companion(root, "explain", "--json", *args)
    return code, (json.loads(out) if out.strip().startswith("{") else out)


@pytest.mark.parametrize("view", ["track", "stuck", "left", "who"])
def test_every_view_has_a_headline_and_says_what_isnt_recorded(plan, view):
    code, got = explain(plan, "--view", view)
    assert code == 0 and got["headline"] and got["not_recorded"] == [companionexplain.NOT_RECORDED[view]]


def test_the_example_has_no_release_date_and_says_so(plan):
    assert explain(plan, "--view", "track")[1]["headline"] == ["No release has a date yet."]


def slice_row(key, status, reach=(), overdue=""):
    return {"key": key, "name": f"Slice {key}", "status": status, "journey_due": "", "milestone": "", "milestones": [],
            "overdue": overdue, "reach": list(reach)}


def ask_row(ident, holds, who_key="@hl-director", days=5):
    return {"id": ident, "name": ident, "who": "Director", "who_key": who_key, "state": "open", "ask_by": "", "opened": "",
            "light": "warning", "urgency": 1, "open_days": days, "holds": [], "hold_keys": list(holds)}


def dated_digest():
    """Two dated releases; the first shipped, the second has three slices in three different states and one question
    that reaches only one of its slices; a third question holds up something outside it."""
    slices = [slice_row("SLC-001", "on"), slice_row("SLC-002", "on", ["app-a"]), slice_row("SLC-003", "building", ["app-b"]),
              slice_row("SLC-004", "planned", ["app-c"]), slice_row("SLC-005", "planned", ["app-z"])]
    asks = [ask_row("UNK-001", ["app-b"]), ask_row("UNK-002", ["app-z"], days=40), ask_row("UNK-003", ["app-c", "app-b"])]
    return {"version": 2, "title": "T", "made": {}, "today": "2026-10-24", "names": {}, "asks": asks, "stuck": asks,
            "needs": {"lines": []}, "slices": slices, "progress": [], "flows": [], "pages": [], "apps": [], "app_lights": {},
            "releases": [{"name": "Pilot", "target": "2026-09-01", "state": "decided", "slices": ["SLC-001", "SLC-002"]},
                         {"name": "Rollout", "target": "2026-12-01", "state": "assumption",
                          "slices": ["SLC-003", "SLC-004"]}]}


VIEWER = companionexplain.Viewer("@hl-director", "")


def track(digest, about=""):
    return companionexplain.explain(digest, "track", about, VIEWER, None, "2026-10-24")


def test_track_names_the_first_release_not_shipped_and_counts_only_its_slices():
    got = track(dated_digest())
    assert got["headline"][0] == "Rollout is due December 1, 38 days out."
    assert got["headline"][1] == "Of 2 slices, 1 is building and 1 is only planned."
    assert [i["id"] for i in got["items"]] == ["Rollout", "SLC-003", "SLC-004"]


def test_track_counts_only_the_questions_that_reach_this_releases_slices():
    assert track(dated_digest())["headline"][2] == "2 things could make it late."  # UNK-001 and UNK-003, not UNK-002


def test_a_passed_date_is_late_and_never_sits_beside_nothing_says_its_late():
    digest = dated_digest()
    digest["releases"][1]["target"] = "2026-10-01"
    got = track(digest)
    assert got["headline"][0] == "Rollout is due October 1, 23 days ago."
    assert got["headline"][-1] == "Late: the date passed."
    assert "Nothing in the plan says it's late." not in got["headline"]


def test_about_names_the_release_even_when_it_shipped():
    got = track(dated_digest(), "Pilot")
    assert got["headline"][0].startswith("Pilot is due September 1, 53 days ago.")
    assert got["headline"][1] == "Of 2 slices, 2 are on."


def test_a_release_with_no_stuck_question_reaching_it_has_nothing_recorded_saying_late():
    digest = dated_digest()
    digest["stuck"] = [ask_row("UNK-002", ["app-z"])]
    assert track(digest)["headline"][2] == "Nothing in the plan says it's late."


def test_when_every_dated_release_shipped_it_says_so():
    digest = dated_digest()
    digest["slices"] = [slice_row(k, "on") for k in ("SLC-001", "SLC-002", "SLC-003", "SLC-004")]
    assert track(digest)["headline"] == ["Every dated release has shipped."]


def numbers_in(sentence):
    return [int(n) for n in re.findall(r"\b(\d+)\b", sentence) if int(n) < 1900]


def test_each_number_in_the_stuck_headline_matches_the_field_it_came_from():
    digest = dated_digest()
    got = companionexplain.explain(digest, "stuck", "", VIEWER, None, "2026-10-24")
    things, oldest, mine = got["headline"]
    assert numbers_in(things) == [len(got["items"])] == [3]
    assert numbers_in(oldest) == [max(i["open_days"] for i in got["items"])] == [40]
    assert numbers_in(mine) == [sum(1 for a in digest["stuck"] if a["who_key"] == VIEWER.handle)] == [3]


def test_each_number_in_the_left_headline_matches_the_sums(plan):
    _, got = explain(plan, "--view", "left")
    total = got["items"][0]
    sentence, apps = got["headline"]
    assert numbers_in(sentence) == [sum(i["decided"] for i in got["items"][1:]), sum(i["total"] for i in got["items"][1:])]
    assert numbers_in(sentence) == [total["decided"], total["total"]]
    assert numbers_in(apps) == [sum(1 for i in got["items"][1:] if i["total"] > i["decided"])]


def test_each_number_in_the_who_headline_matches_the_items(plan):
    _, got = explain(plan, "--view", "who")
    sentence = got["headline"][0]
    assert numbers_in(sentence) == [got["items"][0]["open"], len(got["groups"])]
    assert got["items"][0]["open"] == len(got["items"]) - 1


def test_it_never_says_on_track(plan):
    for view in ("track", "stuck", "left", "who", "none"):
        root_files = plan / ".vela" / "companion"
        explain(plan, "--view", view)
        for name in ("explain.json", "explain.md", "explain.html"):
            assert "on track" not in (root_files / name).read_text(encoding="utf-8").lower(), (view, name)


def test_needs_asks_who_you_are_when_it_cant_tell(plan):
    code, out = explain(plan, "--view", "needs")
    assert code == 3 and "Who are you in the plan?" in json.dumps(out)


def test_needs_lists_what_waits_on_the_viewer(plan):
    code, got = explain(plan, "--view", "needs", "--as", "@hl-solution-lead")
    assert code == 0 and any(i["id"] == "UNK-008" for i in got["items"])


def test_a_flow_view_draws_its_steps(plan):
    code, got = explain(plan, "--view", "flow", "--about", "Hold, pay, confirm")
    assert code == 0 and got["headline"] == ["Hold, pay, confirm has 5 steps."] and got["diagram"]["svg"].startswith("<svg")


def test_an_unknown_subject_is_refused_with_close_names(plan):
    code, out = explain(plan, "--view", "flow", "--about", "Hold and pay")
    assert code == 1 and "Hold, pay, confirm" in json.dumps(out)


def test_no_view_says_so_instead_of_keeping_the_last_one(plan):
    explain(plan, "--view", "stuck")
    code, got = explain(plan, "--view", "none")
    assert code == 0 and got["headline"] == [companionexplain.NO_VIEW] and not got["items"]


def test_a_changed_plan_is_prepared_again_and_said(plan, tmp_path):
    root = tmp_path / "plan"
    shutil.copytree(plan, root)
    page = root / "11-unknowns-and-risks.md"
    page.write_text(page.read_text(encoding="utf-8") + "\n", encoding="utf-8")
    code, got = explain(root, "--view", "stuck")
    assert code == 0 and any("Prepared the plan's data again" in w for w in got["warnings"])


def test_since_last_time_compares_two_copies_and_is_silent_on_the_first():
    first = {"made": {"commit": "a", "date": "2026-10-17"}, "date": "2026-10-17",
             "states": {"FLO-001": "assumption", "CON-007": "assumption"}, "open": ["UNK-006"], "late": []}
    second = {"made": {"commit": "b", "date": "2026-10-24"}, "date": "2026-10-24",
              "states": {"FLO-001": "decided", "CON-007": "decided"}, "open": ["UNK-006", "UNK-008"], "late": []}
    seen = companionseen.roll({}, first)
    assert companionseen.since_line(seen.get("previous"), seen["current"]) == ""
    seen = companionseen.roll(seen, second)
    assert companionseen.since_line(seen["previous"], seen["current"]) == \
        "Since October 17: 2 decided, 1 new question, nothing went late."
    assert companionseen.roll(seen, second) == seen   # the same copy again doesn't roll (ruling 16)


def test_the_view_list_is_closed(plan):
    code, _ = explain(plan, "--view", "everything")
    assert code == 2


@pytest.mark.parametrize("view", ["track", "stuck", "left", "who", "none"])
def test_explain_text_holds_no_ids_paths_or_iso_dates(plan, view):
    from vela import say
    explain(plan, "--view", view, "--as", "@hl-solution-lead")
    folder = plan / ".vela" / "companion"
    assert say.leak_in((folder / "explain.md").read_text(encoding="utf-8")) is None
    page = re.sub(r"<style.*?</style>|<svg.*?</svg>|<[^>]+>", " ", (folder / "explain.html").read_text(encoding="utf-8"), flags=re.S)
    assert say.leak_in(page) is None, say.leak_in(page)


def test_a_question_vela_wrote_with_its_session_word_still_shows_its_age(plan):
    """vela writes "Opened: 2026-10-07 Grill"; reading only a bare date left every age blank."""
    _, got = explain(plan, "--view", "stuck")
    unk6 = [i for i in got["items"] if i["id"] == "UNK-006"][0]
    assert unk6["open_days"] == 17 and "The oldest has waited" in " ".join(got["headline"])


def test_the_session_panel_and_the_explorer_read_the_same_opened_date(plan):
    from vela import cli, pageindex
    from vela.explorer import asks_data
    vault = cli.load_vault(plan)
    asked = {a["id"]: a["opened"] for a in asks_data.asks(vault, None, "2026-10-24")}
    path = "11-unknowns-and-risks.md"
    entry = pageindex.entries(path, (plan / path).read_text(encoding="utf-8"))
    assert asked["UNK-006"] == "2026-10-07" == entry["items"]["UNK-006"]["opened"]


@pytest.mark.parametrize("kind,opening", [("question", "An answer on"), ("proposal", "Your review of"),
                                          ("handed", "Your take on"), ("grill", "A grill on")])
def test_each_kind_of_need_is_asked_for_in_its_own_words(kind, opening):
    digest = dated_digest()
    digest["names"] = {"X": {"name": "Booking events"}}
    digest["needs"] = {"lines": [{"key": "X", "name": "Booking events", "kind": kind, "for": ["@hl-director"], "date": "",
                                  "days": None, "standing": ""}]}
    got = companionexplain.explain(digest, "needs", "", VIEWER, None, "2026-10-24")
    assert got["headline"][1] == f"{opening} Booking events."


def test_nothing_waiting_still_gives_the_next_date():
    digest = dated_digest()
    got = companionexplain.explain(digest, "needs", "", VIEWER, None, "2026-10-24")
    assert got["headline"] == ["Nothing right now. The plan's next date is Rollout, December 1."]
