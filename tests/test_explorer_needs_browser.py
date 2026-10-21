"""Needs you on every role overview, driven in headless Chrome (assets/js/selftest-needs.js).

    python3 -m pytest -q -m browser tests/test_explorer_needs_browser.py

The page's own selftest opens every role overview and finds the block under its heading, cuts seven lines to five behind
"2 more", checks the "N for you" badge, the block, Grills waiting and the question filter give one answer for each of the
people the vault names (they all ask one Viewer), draws a late question in red with its date, says "Nothing needs you right
now." with no badge when there is nothing, names the next date, never says "you" with nobody viewing, jumps from the badge
to the block, and finds no What's waiting page, sidebar entry or "waiting" badge. A selftest that quietly skipped them would
pass, so each named behavior must be present and ok, at a wide window and at 800 px.
"""
import html
import re
import subprocess
import sys

import pytest
from conftest import REPO, chrome_profile, run_chrome
from grills_vault import booking_grills
from test_explorer_browser import find_chrome

WANTED = [
    "needs you: all 6 role overviews open with Needs you, right under their heading",
    "needs you: seven lines show five, \"2 more\" is behind a link and the badge says 7",
    "needs you: \"2 more\" opens the other two, and the link folds them back",
    "needs you: Show the first 5 folds them back",
    "needs you: a line opens ",
    "needs you: the \"7 for you\" badge, clicked from another page, lands on the viewer's overview with Needs you focused",
    "needs you: a late question says \"due\" and its date in red, shows the question itself and says you were asked",
    "the block, the badge, Grills waiting and the viewer give the same answer",
    "needs you: with nothing for the viewer it is one line, \"Nothing needs you right now.\", and there is no badge",
    "needs you: with a date on their side the empty line names it",
    "needs you: with nobody viewing the block says how to pick someone and does not say \"you\"",
    "needs you: no What's waiting in the sidebar, no queue card on the map, no \"waiting\" badge in the top bar",
]


def report(chrome, html_path, size):
    dom = run_chrome([str(chrome), "--headless=new", chrome_profile(), "--disable-gpu", "--no-sandbox", f"--window-size={size}", "--virtual-time-budget=90000", "--dump-dom",
                      f"file://{html_path}#selftest"], 300)[1]
    found = re.search(r'data-selftest="([^"]*)"', dom)
    assert found, f"the page produced no selftest report at {size}"
    return html.unescape(found.group(1)).split(" || ")


@pytest.fixture(scope="module")
def booking(tmp_path_factory):
    vault = booking_grills(tmp_path_factory.mktemp("needs"))
    cmd = [sys.executable, str(REPO / "plugin" / "scripts" / "vela"), "explore", "--selftest", str(vault), "--today", "2026-10-21", "--no-open"]
    assert subprocess.run(cmd, timeout=180, capture_output=True, text=True).returncode == 0
    return vault / "dashboard.html"


@pytest.mark.browser
@pytest.mark.parametrize("size", ["1440,900", "800,900"])
def test_needs_you_passes_its_selftest(booking, size):
    lines = report(find_chrome(), booking, size)
    failing = [x for x in lines if x.startswith("FAIL")]
    assert not failing, "\n".join(failing)
    assert lines[0].startswith("SELFTEST OK"), lines[0]
    mine = [x for x in lines if x.startswith("ok needs you:") or x.startswith("ok grills:")]
    missing = [w for w in WANTED if not any(w in line for line in mine)]
    assert not missing, "selftest lines missing or not ok: " + "; ".join(missing)
