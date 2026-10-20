"""The Details panel on Flows, the Apps map, Who to ask and Decisions, driven in headless Chrome (assets/js/selftest-details.js).

    python3 -m pytest -q -m browser tests/test_explorer_details_browser.py

The page's own selftest picks a step, a contract, an outside service, a waiting question and a person, follows links, presses
Escape and clicks empty space; this test builds two vaults (the heron desk, whose contracts have no case table, and the
booking example, whose contracts do), runs it at a wide window and at 800 px, and requires each named behavior to be present
and ok. A selftest that quietly skipped them would pass, so the lines are listed, not just the verdict. It also requires the
check that a jump inside the side panel leaves the window and the main column where they were.
"""
import html
import re
import shutil
import subprocess
import sys

from conftest import chrome_profile

import pytest
from test_explorer_browser import REPO, find_chrome

HERON = REPO / "tests" / "sim" / "snapshots" / "heron-desk" / "after-design-2"
BOOKING = REPO / "examples" / "unified-booking"

WANTED = [
    "(flows): nothing picked shows the flow's own summary, not its step list",
    "(flows): picking step",                              # who sends, contract, answers, error branch, waiting
    "(flows): the contract link opens",                   # the trail and an Open button
    "(flows): ← back returns to the step",
    "(flows): the crumb that names the flow returns to its summary",
    "(flows): the first click only shows; Open is the second click",
    "(flows): Escape returns to the flow's summary",
    "(flows): the waiting item",                          # lights what it holds up
    "(flows): say names, never codes",
    "(map): nothing picked shows the page summary",
    "(map): a contract label opens its own details",
    "(map): an app keeps In these flows and Talks to at the top",
    "(map): Open goes inside the app",
    "(map): Escape returns to the summary",
    "(map): a click on empty space returns to the summary",
    "(map): the waiting item",
    "(asks): nothing picked says",
    "(asks): a person shows their",
    "(asks): picking a question shows it",
    "(asks): the waiting tab lists all",
    "(asks): Escape returns to the summary",
    "(asks): empty space returns to the summary",
    "(decisions): nothing picked shows",
    "(decisions): picking",
    "(decisions): following a link stacks the trail",
    "(decisions): ← back returns to the decision",
    "(decisions): Escape returns to the summary and closes the record",
    "panel jump:",                                        # a jump in the panel moves the panel only
]


def report(chrome, html_path, size):
    dom = subprocess.run([str(chrome), "--headless=new", chrome_profile(), "--disable-gpu", "--no-sandbox", f"--window-size={size}", "--virtual-time-budget=90000", "--dump-dom",
                          f"file://{html_path}#selftest"], timeout=300, capture_output=True, text=True).stdout
    found = re.search(r'data-selftest="([^"]*)"', dom)
    assert found, f"the page produced no selftest report at {size}"
    return html.unescape(found.group(1)).split(" || ")


def build(tmp_path_factory, source, today, *extra):
    vault = tmp_path_factory.mktemp("details") / "vault"
    shutil.copytree(source, vault)
    cmd = [sys.executable, str(REPO / "plugin" / "scripts" / "vela"), "explore", "--selftest", str(vault), "--today", today, *extra]
    assert subprocess.run(cmd, timeout=180, capture_output=True, text=True).returncode == 0
    return vault / "dashboard.html"


@pytest.fixture(scope="module")
def heron(tmp_path_factory):
    design = HERON / "docs" / "tech-design" / "desktop-agent.md"
    page = build(tmp_path_factory, HERON, "2026-10-12", "--design", f"APP-desktop-agent={design}")
    return page


@pytest.fixture(scope="module")
def booking(tmp_path_factory):
    return build(tmp_path_factory, BOOKING, "2026-11-20")


def check(lines, except_for=()):
    failing = [x for x in lines if x.startswith("FAIL")]
    assert not failing, "\n".join(failing)
    mine = [x for x in lines if x.startswith("ok details panel (") or x.startswith("ok panel jump:")]
    missing = [w for w in WANTED if w not in except_for and not any(w in line for line in mine)]
    assert not missing, "selftest lines missing or not ok: " + "; ".join(missing)


@pytest.mark.browser
@pytest.mark.parametrize("size", ["1440,900", "800,900"])
def test_the_details_panel_on_the_four_pages_passes_its_selftest_on_the_heron_desk(heron, size):
    check(report(find_chrome(), heron, size))


@pytest.mark.browser
def test_a_contract_lists_every_way_it_answers_where_the_vault_records_them(booking):
    lines = report(find_chrome(), booking, "1440,900")
    check(lines, except_for=("(flows): the waiting item", "(map): the waiting item"))  # the booking vault has no question that holds up a flow step
    assert any("ways Booking API can answer are listed, the errors marked" in x for x in lines), "the booking contract's case table shows in the panel"
