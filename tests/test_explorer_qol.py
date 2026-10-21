"""The dashboard's quality-of-life changes (the audit's findings 4 to 16), each checked the way a reader meets it.

The checks are the page's own (assets/js/selftest-qol.js) run in headless Chrome with `#only=qol`, so only these
groups run: a narrow window runs the "compact" group, a wide one the rest. A group that quietly did not run would pass
a test that only looked for FAIL, so every test names the lines it needs to see.

    python3 -m pytest -q -m browser tests/test_explorer_qol.py
"""
import html
import json
import pathlib
import re
import shutil
import subprocess
import sys

from conftest import chrome_profile, run_chrome

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
def booking(tmp_path_factory):
    return build(tmp_path_factory, REPO / "examples" / "unified-booking", "booking")


@pytest.fixture(scope="module")
def chrome():
    return find_chrome()


def selftest(chrome, page, width, hash_="s=apps", height=900):
    """The qol group's lines, as the page wrote them."""
    cmd = [str(chrome), "--headless=new", chrome_profile(), "--disable-gpu", "--no-sandbox", f"--window-size={width},{height}", "--virtual-time-budget=90000",
           "--dump-dom", f"file://{page}#{hash_}&selftest&only=qol"]
    dom = run_chrome(cmd, 180)[1]
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
def test_one_waiting_number_and_notes_in_an_i(chrome, heron):
    """Findings 7 and 13: no plan-wide "N waiting" in the top bar, the panel or the Progress card (the person's count is "N for you"); the map's notes are an i."""
    lines = selftest(chrome, heron, 1440)
    need(lines, "waiting: no \"N waiting\"", "waiting: the sidebar's count", "Home: no banner or note lines above the map", "Home: the i opens the notes in place")


@pytest.mark.browser
def test_buttons_appear_once_and_the_percent_is_gone(chrome, heron):
    """Findings 8, 9 and 14: one Read full page, the doors only in the sidebar, no done-sounding percent, one timeline."""
    lines = selftest(chrome, heron, 1440)
    need(lines, "one Read full page:", "role doors:", "no percent that reads as done")


@pytest.mark.browser
def test_theme_is_one_gear_at_the_far_right(chrome, heron):
    """Finding 10: the Theme select and the Animation switch leave the top bar for one gear menu."""
    lines = selftest(chrome, heron, 1440)
    need(lines, "top bar: one gear at the far right", "gear: opens", "gear: choosing")


@pytest.mark.browser
def test_left_menu_names_and_a_folded_read_group(chrome, heron):
    """Finding 11: flow names drop what they share; the text-first pages fold under Read."""
    lines = selftest(chrome, heron, 1440)
    need(lines, "menu: ", "menu: Constraints, Context, Strategy and Glossary sit under one Read heading", "menu: Read opens", "menu: Read stays open",
         "menu: the expand triangle is ", "menu: the triangle alone folds")


@pytest.mark.browser
def test_a_few_slices_open_without_filter_rows(chrome, booking):
    """Finding 12: four slices open with no search or filters (the ... menu brings them), the Key is a ?, and Comes after
    says "the first slice"."""
    lines = selftest(chrome, booking, 1440, "s=slices")
    need(lines, "slices: 4 slices open with no search or filter rows", "Comes after says", "slices: the ? opens the key")


@pytest.mark.browser
def test_overview_map_only_where_the_map_is_the_subject_and_labels_say_what_they_show(chrome, heron, booking):
    """Findings 15 and 16. The booking example records a first slice, so its flows carry the tag."""
    lines = selftest(chrome, heron, 1440)
    need(lines, "overview map: shown on Home, Apps, Capabilities, Flows and inside an app", "labels: the View menu says Contracts only, Dependencies and Moving markers")
    need(selftest(chrome, booking, 1440), "labels: a flow in the first slice says so")


@pytest.mark.browser
def test_the_viewing_as_pick_is_the_one_viewer(chrome, heron):
    """The dashboard does not know who is reading until a handle is built in or a role is picked under Viewing as; that pick is
    the one viewer Needs you reads (the old Waiting on you filter is gone)."""
    lines = selftest(chrome, heron, 1440)
    need(lines, "viewing as: the sidebar menu sets the one role")


def test_only_a_page_built_for_one_person_carries_a_handle(tmp_path):
    """The shared page is committed and read by colleagues, so it has no data.me even when .vela/handle is set; a page built with
    `vela explore --person` carries that person's handle, and only that page can say "you" by handle."""
    vault = tmp_path / "v"
    shutil.copytree(HERON, vault)
    (vault / ".vela").mkdir(exist_ok=True)
    (vault / ".vela" / "handle").write_text("@product-owner\n", encoding="utf-8")
    vela = [sys.executable, str(REPO / "plugin" / "scripts" / "vela"), "explore", str(vault), "--today", "2026-10-10", "--no-open"]

    def built(*more):
        out = vault / "d.html"
        assert subprocess.run([*vela, "-o", str(out), *more], timeout=120, capture_output=True, text=True).returncode == 0
        return out.read_text(encoding="utf-8")
    pattern = r'<script type="application/json" id="data">(.*?)</script>'
    shared = built()
    assert "me" not in json.loads(re.search(pattern, shared, re.S).group(1))  # a boolean: the page is large and a failed `in` on it would diff it
    mine = json.loads(re.search(pattern, built("--person", "product-owner"), re.S).group(1))
    assert mine["me"] == {"handle": "product-owner"}


@pytest.mark.browser
@pytest.mark.parametrize("width,height", [(1440, 600), (1440, 700), (1280, 600), (800, 600)])
def test_everything_under_the_flow_diagram_is_reachable_in_a_short_window(chrome, heron, width, height):
    """The list, the step line and the player bar exist, show, and scroll into the window when it is not tall; the diagram never takes all the room."""
    lines = selftest(chrome, heron, width, hash_="s=flows", height=height)
    need(lines, "short window, ")
