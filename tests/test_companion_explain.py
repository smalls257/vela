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


@pytest.mark.parametrize("view", ["track", "stuck", "left", "who"])
def test_every_number_in_the_headline_is_in_the_items(plan, view):
    _, got = explain(plan, "--view", view)
    numbers = {int(n) for n in re.findall(r"\b(\d+)\b", " ".join(got["headline"])) if int(n) < 1900}
    shown = json.dumps(got["items"]) + json.dumps(got["groups"])
    for n in numbers:
        assert str(n) in shown or n == len(got["items"]) or n == sum(len(g["items"]) for g in got["groups"]), (n, got)


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
