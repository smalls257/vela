"""The Details panel inside an app, driven in headless Chrome (assets/js/selftest-inside.js).

    python3 -m pytest -q -m browser tests/test_explorer_panel_browser.py

The page's own selftest picks components, follows links, presses Escape and so on; this test builds the heron vault with
its team design, runs the selftest at a wide window and at 800 px, and requires each named behavior to be present and
passing. A selftest that quietly skipped them would pass, so the lines are listed, not just the verdict.
"""
import html
import pathlib
import re
import shutil
import subprocess
import sys

from conftest import chrome_profile, run_chrome

import pytest
from test_explorer_browser import find_chrome

REPO = pathlib.Path(__file__).resolve().parent.parent
HERON = REPO / "tests" / "sim" / "snapshots" / "heron-desk" / "after-design-2"

WANTED = [
    "the header says",                                   # one chip: the design's state and what was not read
    "nothing picked shows the design at a glance",       # the summary, two tabs, no column of design tabs
    "the summary cards are",                             # each card with a way into its section
    "a card opens its whole section, with ← back to the summary",
    "picking",                                           # scope switching: only that component
    "are lit",                                           # the pick and its neighbors, the rest dimmed
    "are only the ones the design ties to it",           # only real links
    "reads",                                             # the trail, ← back to the component
    "Escape returns to the summary",
    "opens that contract",                               # a contract label on a line
    "says who provides it",
    "the waiting item",                                  # a waiting item lights the parts it holds up
    "a click on empty space in the drawing returns to the summary",
    "hovering",                                          # hover lights neighbors, the panel stays
    "takes Tab, Enter picks it and Escape clears it",
    "shows its details first, with an Open button",      # the first click shows, Open jumps
    "Open goes inside",
    "say names, never codes",
    "the diagram bar carries Show, Highlight, the Key, full screen and more",
    "Highlight \"What's waiting\"",
    "full screen hides the panel and Escape leaves it",
    "says Not recorded",
    "the page does not scroll sideways",
    "uses the same panel, tabs and diagram bar",
]


def selftest_lines(chrome, html_path, size):
    dom = run_chrome([str(chrome), "--headless=new", chrome_profile(), "--disable-gpu", "--no-sandbox", f"--window-size={size}", "--virtual-time-budget=90000", "--dump-dom",
                          f"file://{html_path}#inside&selftest"], 300)[1]
    found = re.search(r'data-selftest="([^"]*)"', dom)
    assert found, f"the page produced no selftest report at {size}"
    return html.unescape(found.group(1)).split(" || ")


@pytest.fixture(scope="module")
def built(tmp_path_factory):
    vault = tmp_path_factory.mktemp("panel") / "vault"
    shutil.copytree(HERON, vault)
    design = vault / "docs" / "tech-design" / "desktop-agent.md"
    cmd = [sys.executable, str(REPO / "plugin" / "scripts" / "vela"), "explore", "--selftest", str(vault), "--today", "2026-10-12", "--design", f"APP-desktop-agent={design}"]
    assert subprocess.run(cmd, timeout=180, capture_output=True, text=True).returncode == 0
    return vault / "dashboard.html"


@pytest.mark.browser
@pytest.mark.parametrize("size", ["1440,900", "800,900"])
def test_the_details_panel_passes_its_selftest(built, size):
    chrome = find_chrome()
    lines = selftest_lines(chrome, built, size)
    mine = [x for x in lines if "details panel" in x]
    failing = [x for x in lines if x.startswith("FAIL")]
    assert not failing, "\n".join(failing)
    missing = [w for w in WANTED if not any(w in line and line.startswith("ok details panel") for line in mine)]
    assert not missing, "selftest lines missing or not ok: " + "; ".join(missing)
