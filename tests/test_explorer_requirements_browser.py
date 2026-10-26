"""The Requirements section's list and focus in headless Chrome (assets/js/selftest-reqview.js, reqview.js).

    python3 -m pytest -q -m browser tests/test_explorer_requirements_browser.py

The page's own selftest checks the drawing; these tests make sure it checked the things that matter and did not quietly skip
them, on the Heron test plan (nine requirements, one app with a tech design). The data itself is pinned in
test_explorer_requirements.py.
"""
import html
import re
import shutil
import subprocess
import sys

import pytest
from conftest import REPO, built_once
from test_explorer_browser import chrome_dom, find_chrome

pytestmark = pytest.mark.browser
VELA = REPO / "plugin" / "scripts" / "vela"
HERON = REPO / "tests" / "fixtures" / "team-skills" / "heron-plan"


@pytest.fixture(scope="module")
def chrome_path():
    return find_chrome()


def heron_page():
    def build(folder):
        shutil.copytree(HERON, folder / "vault")
        done = subprocess.run([sys.executable, str(VELA), "explore", "--selftest", str(folder / "vault"), "-o", str(folder / "page.html"), "--no-open", "--today", "2026-10-26"],
                              timeout=180, capture_output=True, text=True)
        assert done.returncode == 0, done.stderr
    return built_once(None, "requirements-heron", build) / "page.html"


def selftest_lines(chrome_path):
    dom = chrome_dom(chrome_path, heron_page(), route="map&selftest")
    return html.unescape(re.search(r'data-selftest="([^"]*)"', dom).group(1)).split(" || ")


EXPECTED = ["requirements: 9 rows, six checks each in order", "requirements: the page says what the plan cannot know", "requirements: the sidebar has a Requirements entry",
            "requirements list: one keyboard-reachable row for each of the 9 requirements", "requirements list: each row says its five checks in words",
            "requirements list: the all filter shows 9", "requirements list: the gap filter shows 8", "requirements list: the held filter shows 6", "requirements list: the design filter shows 8",
            "requirements list: grouped by release", "requirements list: grouped by app", "requirements list: grouped by none", "requirements list: grouped by capability",
            "requirements focus: Enter on", "requirements focus: the panel opens the requirement with the six checks and Decided", "requirements focus: the hero says how many of six checks are met",
            "requirements focus: 2 red dashed boxes", "requirements focus: all ", "requirements focus: clicking", "requirements focus: the picked box is marked",
            "requirements focus: it lists what is missing", "requirements focus: List returns to the list"]


def test_the_list_and_the_focus_pass_the_selftest_with_nothing_skipped(chrome_path):
    lines = selftest_lines(chrome_path)
    missing = [f for f in EXPECTED if not any(f in x and x.startswith("ok") for x in lines)]
    assert not missing, "missing or failing selftest lines: " + "; ".join(missing) + "\n" + "\n".join(x for x in lines if x.startswith("FAIL"))
    assert not [x for x in lines if x.startswith("FAIL")], [x for x in lines if x.startswith("FAIL")]
    assert not [x for x in lines if x.startswith("ok skip requirements")]


def test_a_link_to_a_requirement_opens_its_focus_and_the_list_is_the_section_default(chrome_path):
    page = heron_page()
    focus = chrome_dom(chrome_path, page, route="s=requirements&open=CAP-003.FR1")
    assert 'class="rv-hero"' in focus and focus.count('class="rv-col"') == 6 and "Write each person" in focus
    plain = chrome_dom(chrome_path, page, route="s=requirements")
    assert plain.count('class="rv-row"') + plain.count('class="rv-row picked"') == 9 and "Built and tested: not something the plan knows" in plain
