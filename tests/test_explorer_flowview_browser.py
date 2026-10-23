"""The Flows view's pinned lane names, starts, fold and hide in a real browser (flowview.js, flowkit.js, view-flows.js).

The example vault with four flows written in (starts_flows.py): two ways in named by an opening alt, the same two with no
diagram, one way in, and two reports that no step says who sends. The page's own selftest walks everything (the pinned row
under a scroll, a click on a pinned name, each start picked and dimmed, Simplify and the badge and F, hide and show, the
address, the key, the words fitting in every theme and in Plain); these check the page a link opens, in the address's own
words, and that the selftest ran each part at both window sizes."""
import html
import re
import shutil
import subprocess
import sys

import pytest
from conftest import chrome_profile, run_chrome
from starts_flows import add_flows
from test_explorer_browser import REPO, _check_selftest_in_chrome, chrome_path  # noqa: F401  (chrome_path is a fixture)

BOOKING = REPO / "examples" / "unified-booking"


def staged(tmp_path):
    vault = tmp_path / "vault"
    shutil.copytree(BOOKING, vault)
    add_flows(vault)
    cmd = [sys.executable, str(REPO / "plugin" / "scripts" / "vela"), "explore", "--selftest", str(vault), "--today", "2026-11-20"]
    assert subprocess.run(cmd, timeout=120, capture_output=True, text=True).returncode == 0
    return vault / "dashboard.html"


def dom(chrome_path, page, hash_, budget=20000):  # noqa: F811
    cmd = [str(chrome_path), "--headless=new", chrome_profile(), "--disable-gpu", "--no-sandbox", "--window-size=1400,900", f"--virtual-time-budget={budget}",
           "--dump-dom", f"file://{page}#{hash_}"]
    shown = re.sub(r"<(script|style)\b.*?</\1>", "", run_chrome(cmd, 300)[1], flags=re.S)  # the page as drawn, not the code that drew it
    return html.unescape(shown)


def radio(out, label, checked):
    return re.search(rf'<button type="button" role="radio" class="starts-opt" aria-checked="{checked}"[^>]*>(?:<i[^>]*></i>)?{re.escape(label)}</button>', out)


@pytest.mark.browser
def test_a_link_naming_a_start_opens_with_it_picked(tmp_path, chrome_path):  # noqa: F811
    page = staged(tmp_path)
    out = dom(chrome_path, page, "flows&open=FLO-010&start=S2&still")
    assert 'role="radiogroup" aria-label="Where the flow starts" data-starts="FLO-010"' in out
    assert radio(out, "A customer calls in", "true") and radio(out, "Either", "false") and radio(out, "A customer books on the website", "false")
    assert "This flow starts two ways" in out and 'class="starts-guess' not in out  # every arrow on the page says who sends: no guess label
    # one way in: no picker at all, and nothing to simplify that the flow's first step keeps
    one = dom(chrome_path, page, "flows&open=FLO-012&still")
    assert 'role="radiogroup"' not in one and "This flow starts" not in one
    # a guess says it is one
    guessed = dom(chrome_path, page, "flows&open=FLO-013&still")
    assert 'class="starts-guess heuristic"' in guessed and "(A guess: the page doesn't say who sends some of these steps.)" in guessed


@pytest.mark.browser
def test_a_link_naming_folds_and_hides_opens_with_them(tmp_path, chrome_path):  # noqa: F811
    page = staged(tmp_path)
    out = dom(chrome_path, page, "flows&open=FLO-010&fold=APP-booking&hide=APP-notifications&still")
    assert re.search(r'id="simplify-btn"[^>]*aria-pressed="true"', out) and "Simplified · 2 folded" in out
    assert "Not decided yet · 5 steps" in out  # three steps folded into one: seven steps read as five
    # the list gives the same two choices as buttons: Notifications and Pricing fold into Booking, Notifications is hidden
    assert re.search(r'aria-label="Unfold Notifications and Pricing from Booking"', out)
    assert re.search(r'aria-label="Show Notifications"', out)
    # another flow starts clean: the choices belong to the flow the address names
    other = dom(chrome_path, page, "flows&open=FLO-011&still")
    assert re.search(r'id="simplify-btn"[^>]*aria-pressed="false"', other) and "Simplified" not in other


@pytest.mark.browser
def test_the_selftest_walks_the_pinned_row_the_starts_and_the_folds_at_both_sizes(tmp_path, chrome_path):  # noqa: F811
    page = staged(tmp_path)
    for viewport in ("1600,1000", "800,600"):
        lines = _check_selftest_in_chrome(chrome_path, page, f"booking with starts flows at {viewport}", viewport)
        for want in ("ok pin: a short stage makes", "ok pin: a click on a pinned name still opens", "ok pin: a shadow falls under the pinned row", "ok pin: the saved clip draws the flow whole",
                     "ok starts: 4 flows with one way in show no Starts from", 'ok starts, FLO-010: "Starts from" in the header row', "ok starts, FLO-010: picking",
                     "ok starts, FLO-010: Next skips the steps of the start not picked", "ok starts, FLO-010: the arrow keys move between the starts",
                     "ok starts, FLO-010: a click on a Start tag picks that start", "ok starts, FLO-010: a link naming the start opens with it picked",
                     "ok starts, FLO-013: a guess says it is one", "ok fold: on 7 flows Simplify folds every lane", "ok hide: on FLO-001, a lane hides",
                     "ok hide: a link naming a hidden lane", "ok flows: the Starts from picker and Simplify fit the header row in every theme and in Plain"):
            assert any(line.startswith(want) for line in lines), (viewport, want)
