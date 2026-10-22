"""The capability views (cards, focus, matrix) in headless Chrome (assets/js/selftest-capview.js, capview.js).

    python3 -m pytest -q -m browser tests/test_explorer_capview_browser.py

The page's own selftest checks each view; these tests make sure it checked the things that matter and did not quietly skip
them. The booking demo has few capabilities and no pair that needs each other, so a second page is built from it with
fourteen more capabilities and flows that put nine capabilities on one side, a pair that needs each other, and a capability
no flow mentions. A page whose flows record no capabilities shows the empty state, and says how many flows it leaves out.
"""
import html
import re
import subprocess
import sys

import pytest
from conftest import REPO, built_once
from test_explorer_browser import chrome_dom, find_chrome

pytestmark = pytest.mark.browser
VELA = REPO / "plugin" / "scripts" / "vela"
TODAY = "2026-11-20"


@pytest.fixture(scope="module")
def chrome_path():
    return find_chrome()


def run(args, what):
    done = subprocess.run([sys.executable, *map(str, args)], timeout=180, capture_output=True, text=True)
    assert done.returncode == 0, f"{what} failed: {done.stderr}"


def demo_vault(folder):
    run([REPO / "tests/fixtures/explorer/make_demo_vault.py", folder], "make_demo_vault")
    return folder


def clone(text, old_id, new_id, old_title, new_title):
    return text.replace(old_id, new_id).replace(old_title, new_title)


def scaled_vault(folder):
    """The booking demo plus fourteen capabilities (CAP-101 to CAP-114) and flows that make dependencies of every shape."""
    vault = demo_vault(folder)
    cap_text = (vault / "capabilities" / "CAP-012-quote-a-fare.md").read_text(encoding="utf-8")
    flow_text = next((vault / "06-runtime" / "flows").glob("FLO-001-*.md")).read_text(encoding="utf-8")
    for n in range(101, 115):
        page = clone(cap_text, "CAP-012", f"CAP-{n}", "Quote a fare", f"Capability number {n}")
        (vault / "capabilities" / f"CAP-{n}-capability-number-{n}.md").write_text(page, encoding="utf-8")
    flows = {101: [101, *range(102, 111)],      # one capability that needs nine others: past seven on its right
             102: [102, 101],                   # and 101 needs 102 back: both ways
             103: [111, 101], 104: [112, 101], 105: [113, 101], 106: [114, 101]}
    for n, caps in flows.items():
        page = clone(flow_text, "FLO-001", f"FLO-{n}", "Hold, pay, confirm", f"Scaled journey {n}")
        page = re.sub(r"^capabilities:.*$", "capabilities: [" + ", ".join(f"CAP-{c}" for c in caps) + "]", page, flags=re.M)
        assert f"CAP-{caps[0]}" in page, "the demo's flow page must carry a capabilities line to replace"
        (vault / "06-runtime" / "flows" / f"FLO-{n}-scaled-journey-{n}.md").write_text(page, encoding="utf-8")
    return vault


def bare_flows_vault(folder):
    """The booking demo with the capabilities line taken off every flow: nothing makes a dependency."""
    vault = demo_vault(folder)
    for path in (vault / "06-runtime" / "flows").glob("FLO-*.md"):
        path.write_text(re.sub(r"^capabilities:.*\n", "", path.read_text(encoding="utf-8"), flags=re.M), encoding="utf-8")
    return vault


def built_page(key, make_vault, selftest=True):
    def build(folder):
        vault = make_vault(folder / "vault")
        run([VELA, "explore", *(["--selftest"] if selftest else []), vault, "-o", folder / "page.html", "--no-open", "--today", TODAY], "vela explore")
    return built_once(None, key, build) / "page.html"


def selftest_lines(chrome_path, page, route="map&selftest"):
    dom = chrome_dom(chrome_path, page, route=route)
    return html.unescape(re.search(r'data-selftest="([^"]*)"', dom).group(1)).split(" || ")


def said(lines, *fragments):
    return [x for x in lines if x.startswith("ok") and all(f in x for f in fragments)]


def must_say(lines, fragments):
    missing = [f for f in fragments if not any(f in x and x.startswith("ok") for x in lines)]
    assert not missing, "missing or failing selftest lines: " + "; ".join(missing) + "\n" + "\n".join(x for x in lines if x.startswith("FAIL"))
    ours = [x for x in lines if x.startswith("FAIL") and re.search(r"capabilit|JS ERRORS", x)]  # the scaled page has no pinned layout, so the map's own checks may fail there
    assert not ours, ours


COMMON = ["capability dependencies:", "capability cards: one keyboard-reachable button", "capability cards: each card's Needs and Needed by counts",
          "capability cards: colored by state", "capability cards: colored by open", "capability cards: colored by ready",
          "capability cards: picking a card opens its focus view and its details in the panel",
          "capability focus view: every arrow has a chip", "capability focus view: no label is cut", "capability focus view: it has the shared zoom bar",
          "capability focus view: the + key zooms the drawing", "capability focus view: a chip lists the flows that make the dependency",
          "capability focus view: Enter on another box refocuses on it", "capability matrix: each cell is a button with the number of flows",
          "capability matrix: the capability picked before is still the picked one", "capability matrix: a cell lists its flows and contracts in the panel",
          "capability views: back on the cards, the capability picked in the matrix is still marked", "capability views: Focus opens the same capability"]


def test_the_booking_demo_draws_every_view_from_the_flows_alone(chrome_path):
    """Cards, focus view and matrix on the demo, with the selection carried between them and the keyboard reaching every
    card, box, chip and cell. Its capabilities are few, so the matrix is one click away and not pushed."""
    from test_explorer_browser import built_booking_demo_page
    lines = selftest_lines(chrome_path, built_booking_demo_page())
    must_say(lines, COMMON)
    assert said(lines, "the matrix is one click away in the toggle and not pushed")


def test_a_wide_plan_folds_past_seven_marks_both_ways_and_offers_the_matrix(chrome_path):
    """Twenty-two capabilities: nine on one side fold into +N more and expand, a pair that needs each other is marked on the
    box, the cards offer the matrix, and the matrix has a both-ways mark. None of these is skipped on this page."""
    page = built_page("capview-scaled", scaled_vault)
    lines = selftest_lines(chrome_path, page)
    must_say(lines, COMMON + ["capability cards: 22 capabilities, so the matrix is offered", "capability focus view: the rest fold into +N more",
                              "capability focus view: +N more shows the rest", "capability focus view: a pair that needs each other is marked on the box",
                              "capability focus view: a capability no flow ties to another says so"])
    assert not [x for x in lines if x.startswith("ok skip capability focus view")], [x for x in lines if "skip" in x and "capability" in x]


def test_a_vault_whose_flows_record_no_capabilities_says_so_and_points_at_the_session(chrome_path):
    """No flow lists a capability, so no capability depends on another: the cards still draw, with a plain note, not an
    invented dependency. The dashboard names the session that writes the field."""
    page = built_page("capview-bare", bare_flows_vault)
    lines = selftest_lines(chrome_path, page)
    must_say(lines, ["capability dependencies: 0 edges", "capability cards: no flow records capabilities, and the page says so and points at /vela:shape"])
    dom = chrome_dom(chrome_path, page, route="s=capabilities")
    assert "No flow lists its capabilities yet, so no capability depends on another." in dom and "the shape session" in dom


def test_a_link_to_a_capability_opens_the_focus_view_and_the_sidebar_says_so(chrome_path):
    """The owner's rule: capability focus elsewhere (a sidebar entry, a chip, a link) lands on the focus view."""
    page = built_page("capview-scaled", scaled_vault)
    dom = chrome_dom(chrome_path, page, route="s=capabilities&open=CAP-101")
    assert 'id="cv-board"' in dom and 'data-where="side"' in dom and 'class="cv-node sel' in dom
    matrix = chrome_dom(chrome_path, page, route="s=capabilities&v=capmatrix")
    assert 'class="cv-mx"' in matrix and 'class="cv-cell d both"' in matrix
