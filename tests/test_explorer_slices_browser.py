"""The Slices view in a real browser: a link with filters in its hash opens the same filtered view, and the page's own
selftest walks the table, the path, the filters, the hash round trip and an overdue journey in What's waiting."""
import html
import re
import shutil
import subprocess
import sys

from conftest import chrome_profile, run_chrome

import pytest
from test_explorer_browser import REPO, _check_selftest_in_chrome, chrome_path  # noqa: F401  (chrome_path is a fixture)

BOOKING = REPO / "examples" / "unified-booking"


def staged(tmp_path):
    """The example with SLC-002 building and its journey past due, and SLC-004 planned."""
    vault = tmp_path / "vault"
    shutil.copytree(BOOKING, vault)
    for sid, extra in (("SLC-002", "- **Status:** building\n- **Journey due:** 2026-11-19\n"), ("SLC-004", "- **Status:** planned\n")):
        page = next((vault / "slices").glob(f"{sid}-*.md"))
        page.write_text(page.read_text(encoding="utf-8").replace("- **Owner:**", extra + "- **Owner:**", 1), encoding="utf-8")
    return vault


def dom(chrome_path, page, hash_):  # noqa: F811
    cmd = [str(chrome_path), "--headless=new", chrome_profile(), "--disable-gpu", "--no-sandbox", "--window-size=1400,900", "--virtual-time-budget=20000",
           "--dump-dom", f"file://{page}#{hash_}"]
    return run_chrome(cmd, 180)[1]


@pytest.mark.browser
def test_a_link_with_filters_opens_the_same_filtered_slices(tmp_path, chrome_path):  # noqa: F811
    vault = staged(tmp_path)
    cmd = [sys.executable, str(REPO / "plugin" / "scripts" / "vela"), "explore", str(vault), "--today", "2026-11-20"]
    assert subprocess.run(cmd, timeout=120, capture_output=True, text=True).returncode == 0
    page = vault / "dashboard.html"
    out = dom(chrome_path, page, "s=slices&sl-status=building&sl-status=planned&still")
    rows = re.findall(r'class="sl-tr[^"]*"[^>]*data-slice="([^"]+)"', out)
    assert rows == ["SLC-002", "SLC-004"], rows
    pressed = re.findall(r'aria-pressed="true" data-value="([^"]+)"', out)
    assert sorted(pressed) == ["building", "planned"], pressed
    out = dom(chrome_path, page, "s=slices&sl-needs&sl-layout=path&still")
    assert re.findall(r'class="sl-node[^"]*"[^>]*data-slice="([^"]+)"', out) == ["SLC-002"]
    assert "journey due Nov 19" in html.unescape(out)
    out = dom(chrome_path, page, "s=slices&sl-find=no%20such%20words&still")
    assert 'class="sl-empty"' in out and 'No slice matches the words "no such words"' in html.unescape(out) and ">Clear filters<" in out
    out = dom(chrome_path, page, "s=slices&sl-app=APP-gone&still")  # a stale link keeps its value and says why it is empty
    assert 'class="sl-empty"' in out and 'aria-pressed="true" data-value="APP-gone"' in out


@pytest.mark.browser
def test_the_selftest_walks_the_slices_view_with_a_journey_past_due(tmp_path, chrome_path):  # noqa: F811
    vault = staged(tmp_path)
    cmd = [sys.executable, str(REPO / "plugin" / "scripts" / "vela"), "explore", "--selftest", str(vault), "--today", "2026-11-20"]
    assert subprocess.run(cmd, timeout=120, capture_output=True, text=True).returncode == 0
    runs = {viewport: _check_selftest_in_chrome(chrome_path, vault / "dashboard.html", f"booking with slices moving at {viewport}", viewport)
            for viewport in ("1600,1000", "800,600")}
    lines = runs["1600,1000"]  # the wide run's own lines: the same page and window, so no second run of the selftest
    for want in ("ok slices table: Enter opens a row", "ok slices filter: the link", "ok slices: Waiting only shows the 1 ", "ok slices path:"):
        assert any(line.startswith(want) for line in lines), want
