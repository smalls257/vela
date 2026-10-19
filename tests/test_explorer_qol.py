"""The dashboard's quality-of-life changes (the audit's findings 4 to 16), each checked the way a reader meets it.

The checks are the page's own (assets/js/selftest-qol.js) run in headless Chrome with `#only=qol`, so only these
groups run: a narrow window runs the "compact" group, a wide one the rest. A group that quietly did not run would pass
a test that only looked for FAIL, so every test names the lines it needs to see.

    python3 -m pytest -q -m browser tests/test_explorer_qol.py
"""
import html
import pathlib
import re
import shutil
import subprocess
import sys

import pytest
from test_explorer_browser import find_chrome

REPO = pathlib.Path(__file__).resolve().parent.parent
SNAPSHOTS = REPO / "tests" / "sim" / "snapshots"
HERON = SNAPSHOTS / "heron-desk" / "after-design-2"
TRADING = SNAPSHOTS / "trading-coach" / "after-80b"


def build(tmp_path_factory, source, name):
    vault = tmp_path_factory.mktemp(name) / "vault"
    shutil.copytree(source, vault)
    cmd = [sys.executable, str(REPO / "plugin" / "scripts" / "vela"), "explore", "--selftest", str(vault), "--today", "2026-10-10"]
    assert subprocess.run(cmd, timeout=120, capture_output=True, text=True).returncode == 0
    return vault / "dashboard.html"


@pytest.fixture(scope="module")
def heron(tmp_path_factory):
    return build(tmp_path_factory, HERON, "heron")


@pytest.fixture(scope="module")
def chrome():
    return find_chrome()


def selftest(chrome, page, width, hash_="s=apps", height=900):
    """The qol group's lines, as the page wrote them."""
    cmd = [str(chrome), "--headless=new", "--disable-gpu", "--no-sandbox", f"--window-size={width},{height}", "--virtual-time-budget=90000",
           "--dump-dom", f"file://{page}#{hash_}&selftest&only=qol"]
    dom = subprocess.run(cmd, timeout=180, capture_output=True, text=True).stdout
    found = re.search(r'data-selftest="([^"]*)"', dom)
    assert found, "the page wrote no selftest report"
    lines = html.unescape(found.group(1)).split(" || ")
    fails = [x for x in lines if x.startswith("FAIL")]
    assert not fails, "\n".join(fails)
    return lines


def need(lines, *wanted):
    missing = [w for w in wanted if not any(w in line and line.startswith("ok") for line in lines)]
    assert not missing, "checks that did not run or pass: " + "; ".join(missing)


@pytest.mark.browser
def test_narrow_window_gives_the_diagram_the_width(chrome, heron):
    """Finding 6: under 1000 px the menu and the panel are slide-overs, so the diagram has the whole width."""
    lines = selftest(chrome, heron, 800)
    need(lines, "compact, 800 px: the menu and the panel start closed", "the hamburger slides the menu over the diagram",
         "choosing a section closes the menu", "slides the panel over the diagram", "Esc closes the panel", "nothing scrolls sideways")


@pytest.mark.browser
def test_app_click_shows_its_flows_and_neighbors_first(chrome, heron):
    """Finding 4: the panel for an app opens on In these flows and Talks to, each chip a button that goes there."""
    lines = selftest(chrome, heron, 1440)
    need(lines, "app panel: clicking any of", "app panel: the flow chip plays", "app panel: the contract chip opens")


@pytest.mark.browser
@pytest.mark.parametrize("width", [1440, 800])
def test_open_menus_are_above_every_view(chrome, heron, width):
    """The user: on Who uses whom the chart drew over the open View menu. Every menu is the topmost element at its middle
    and corners (document.elementFromPoint), in every section, map view and theme, and stays inside the window."""
    lines = selftest(chrome, heron, width)
    need(lines, "menus on top:")


@pytest.mark.browser
def test_search_is_one_row_per_thing_with_app_pills(chrome, heron):
    """Finding 5: no Claude row on a file, one row per thing, pills for the apps it touches, Enter lights those apps."""
    lines = selftest(chrome, heron, 1440)
    need(lines, 'search "digest":', "search: the", "shows the apps it touches as pills", "search: Enter on")


@pytest.mark.browser
def test_one_need_you_number_and_notes_in_an_i(chrome, heron):
    """Findings 7 and 13: one "N need you" on the bar, the card and the panel (parts on hover); Home's notes are an i."""
    lines = selftest(chrome, heron, 1440)
    need(lines, "need you: one number", "need you: the sidebar's count", "Home: no banner or note lines above the map", "Home: the i opens the notes in place")
