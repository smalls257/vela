"""The Grills waiting view, driven in headless Chrome (assets/js/selftest-grills.js).

    python3 -m pytest -q -m browser tests/test_explorer_grills_browser.py

The page's own selftest lists the three groups, switches who is viewing and checks that the chips, the
sidebar count and the ready ones in Needs you give the same number for each person, runs every filter, opens a card in the right-hand
panel, checks the prompt and its Copy button, builds a batch in the order that unblocks the most, finds the "Ready for a
grill" line on an item's own details, and walks the cards with the keyboard. A selftest that quietly skipped them would pass,
so each named behavior must be present and ok, at a wide window and at 800 px. A vault with nothing waiting has no entry,
and the decided example proves the checks stop there.
"""
import html
import re
import shutil
import subprocess
import sys

import pytest
from conftest import REPO, chrome_profile, run_chrome
from grills_vault import booking_grills
from test_explorer_browser import find_chrome

WANTED = [
    "grills: with nobody viewing, all 4 grills show once, in the groups said-yes, ready, one-away",
    "grills: the group headings say You already said yes, Ready to decide and One thing away",
    "grills: with nobody viewing there is no Mine chip, the sidebar counts every grill waiting, and the top bar has no grills badge",
    "grills: for each of 3 people the Mine, I'm asked to join and Everyone's chips, the sidebar count and the ready grills in Needs you agree",
    "grills: \"3 more grills belong to other owners. Show everyone's\" and the hidden tile say 3",
    "grills: Show everyone's brings the other owners' grills in",
    "grills: with no role picked and no page built for one person, nobody is viewing and everyone's grills show",
    "grills: choosing Engineering in Viewing as makes Mine follow the people the plan records for it (Booking senior)",
    "grills: Owner, App and Holds up each narrow the list to exactly their grills, and Ready only drops the group one thing away (exercised: owner, app, holds up)",
    "grills: each filter starts at any",
    "grills: each card has an owner line; a said-yes card shows no words, a one-away card says what it waits on and by when",
    "grills: clicking",
    "grills: the panel gives what it settles, where it stands, what it holds up, the owner, who is asked to join and the prompt, in that order",
    "grills: the prompt starts /vela:grill with the item's name and is plain words, no IDs or handles",
    "grills: Copy prompt copies exactly the prompt shown",
    "grills: the panel has \"Open the contract\" to go to the item itself",
    "grills: a said-yes panel shows the date as a link and none of the words",
    "grills: the You said yes link opens the item itself",
    "grills: what it holds up lists",
    "grills: Enter on the chip",
    "grills: the chip \"holds up:",
    "grills: a batch of 3 lists them by what they unblock (12, 12, 0 things held up) and builds one prompt",
    "grills: the batch prompt starts /vela:grill with every name and numbers the grills in order, in plain words",
    "grills: Copy batch prompt copies exactly the batch shown",
    "grills: Remove takes one grill out of the batch",
    "grills: Clear the batch empties it",
    "own details carry a Ready for a grill line with Copy prompt",
    "grills: that Copy prompt copies the same prompt",
    "one thing away, has no Ready for a grill line",
    "grills: every card, chip and filter is a keyboard stop",
    "grills: the down arrow moves from one card to the next",
    "grills: after picking a card, focus stays on it",
    "grills: Escape returns the panel to the summary and unmarks the card",
    "grills: the sidebar has a Grills waiting button",
]


def report(chrome, html_path, size):
    dom = run_chrome([str(chrome), "--headless=new", chrome_profile(), "--disable-gpu", "--no-sandbox", f"--window-size={size}", "--virtual-time-budget=90000", "--dump-dom",
                      f"file://{html_path}#selftest"], 300)[1]
    found = re.search(r'data-selftest="([^"]*)"', dom)
    assert found, f"the page produced no selftest report at {size}"
    return html.unescape(found.group(1)).split(" || ")


def build(vault):
    cmd = [sys.executable, str(REPO / "plugin" / "scripts" / "vela"), "explore", "--selftest", str(vault), "--today", "2026-10-21", "--no-open"]
    assert subprocess.run(cmd, timeout=180, capture_output=True, text=True).returncode == 0
    return vault / "dashboard.html"


@pytest.fixture(scope="module")
def booking(tmp_path_factory):
    return build(booking_grills(tmp_path_factory.mktemp("grills")))


@pytest.fixture(scope="module")
def decided(tmp_path_factory):
    vault = tmp_path_factory.mktemp("decided") / "booking"
    shutil.copytree(REPO / "examples" / "unified-booking", vault)
    return build(vault)


def check(lines):
    failing = [x for x in lines if x.startswith("FAIL")]
    assert not failing, "\n".join(failing)
    assert lines[0].startswith("SELFTEST OK"), lines[0]
    mine = [x for x in lines if x.startswith("ok grills:")]
    missing = [w for w in WANTED if not any(w in line for line in mine)]
    assert not missing, "selftest lines missing or not ok: " + "; ".join(missing)


@pytest.mark.browser
@pytest.mark.parametrize("size", ["1440,900", "800,900"])
def test_the_grills_view_passes_its_selftest(booking, size):
    check(report(find_chrome(), booking, size))


@pytest.mark.browser
def test_a_vault_with_nothing_waiting_has_no_grills_entry(decided):
    lines = report(find_chrome(), decided, "1440,900")
    assert not [x for x in lines if x.startswith("FAIL")], "\n".join(x for x in lines if x.startswith("FAIL"))
    assert any(x.startswith("ok grills: a vault with nothing waiting has no Grills waiting entry and no badge") for x in lines)
