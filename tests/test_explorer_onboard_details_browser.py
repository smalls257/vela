"""Clicking an item in Get up to speed opens that thing's real Details in the right-hand panel, in a real browser.

    python3 -m pytest -q -m browser tests/test_explorer_onboard_details_browser.py

The Violation these guard against is a Leaky Narrative of the wrong sort: a click that lands on a generic summary (a code, a
flat list) where the same thing picked in What's waiting or on its own page gives the real Details. The page's selftest
(selftest-onboard.js, itemKinds) clicks one item of every kind on every role's path and requires the shared Details panel
(trail, tabs) and the sections each kind owns: a question has its plain words, who to ask and what it holds up; a decision
its record; a person their waiting questions; a release what it ships. Here the line must name every kind the plan has.
"""
import shutil
import subprocess
import sys

import pytest
from test_explorer_browser import REPO, SNAPSHOTS, _check_selftest_in_chrome, chrome_path  # noqa: F401  (chrome_path is a fixture)

VELA = [sys.executable, str(REPO / "plugin" / "scripts" / "vela")]
LINE = "ok onboarding: clicking an item opens its real Details ("


def kinds_clicked(chrome_path, source, today, tmp_path):  # noqa: F811
    vault = tmp_path / "vault"
    shutil.copytree(source, vault)
    done = subprocess.run([*VELA, "explore", "--selftest", str(vault), "--today", today], timeout=180, capture_output=True, text=True)
    assert done.returncode == 0, done.stdout + done.stderr
    lines = _check_selftest_in_chrome(chrome_path, vault / "dashboard.html", "details")
    line = next((x for x in lines if x.startswith(LINE)), None)
    assert line, [x for x in lines if "clicking an item" in x]
    return set(line[len(LINE):].split(")")[0].split(", "))


@pytest.mark.browser
def test_every_kind_of_item_on_the_booking_plan_opens_its_real_details(tmp_path, chrome_path):  # noqa: F811
    got = kinds_clicked(chrome_path, REPO / "examples" / "unified-booking", "2026-11-20", tmp_path)
    assert {"unknown", "decision", "app", "contract", "flow", "slice", "owner"} <= got


@pytest.mark.browser
def test_a_release_and_a_question_on_the_heron_design_plan_open_their_real_details(tmp_path, chrome_path):  # noqa: F811
    got = kinds_clicked(chrome_path, SNAPSHOTS["heron-desk/after-design-2"], "2026-10-19", tmp_path)
    assert {"unknown", "decision", "release", "owner", "app"} <= got
