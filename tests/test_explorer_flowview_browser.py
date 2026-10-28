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
    assert re.search(r'id="simplify-btn"[^>]*aria-pressed="true"', out) and "Simplified · 1 folded" in out
    assert "Not decided yet · 6 steps shown of 7" in out  # two steps folded into one: seven steps read as six
    # the list gives the same two choices as buttons: Pricing folds into Booking (it answers; Notifications only receives, so it stays), Notifications is hidden
    assert re.search(r'aria-label="Unfold Pricing from Booking"', out)
    assert re.search(r'aria-label="Show Notifications"', out)
    # Notifications only receives, so Simplify leaves it alone
    assert 'aria-label="Fold Notifications' not in out
    # a link naming what the flow doesn't have says so
    gone = dom(chrome_path, page, "flows&open=FLO-010&start=S9&fold=APP-notifications&still")
    assert 'data-ignored-link' in gone and "a start (S9), folding Notifications" in gone
    # another flow starts clean: the choices belong to the flow the address names
    other = dom(chrome_path, page, "flows&open=FLO-011&still")
    assert re.search(r'id="simplify-btn"[^>]*aria-pressed="false"', other) and "Simplified" not in other


@pytest.mark.browser
def test_a_flow_whose_page_writes_boxes_opens_grouped_and_a_link_can_ungroup_it(tmp_path, chrome_path):  # noqa: F811
    page = staged(tmp_path)
    out = dom(chrome_path, page, "flows&open=FLO-001&still")
    assert re.search(r'id="group-btn"[^>]*aria-pressed="true"[^>]*aria-label="Grouped, 2 groups"', out) and "Grouped · 2" in out
    # the list under the diagram is the keyboard path: a row for each group, its members under it, Ungroup and Hide beside it
    assert "Channels, group of 3" in out and "Lookups, group of 3" in out and 'aria-label="Ungroup Channels"' in out and 'aria-label="Hide Channels"' in out
    # a member is not hidden alone while it is grouped
    assert 'aria-label="Hide Public website"' not in out
    # a link names what the reader did: ungroup rides in the address, and rides on a present link too
    one = dom(chrome_path, page, "flows&open=FLO-001&apart=Channels&still")
    assert "Grouped · 1" in one and 'aria-label="Ungroup Lookups"' in one and 'aria-label="Ungroup Channels"' not in one and 'aria-label="Hide Public website"' in one
    none = dom(chrome_path, page, "flows&open=FLO-001&apart=Channels,Lookups&still")
    assert "Grouped" not in none and re.search(r'id="group-btn"[^>]*aria-pressed="false"[^>]*aria-label="Group lanes"', none)
    present = dom(chrome_path, page, "present=FLO-001&step=2&apart=Channels&still")
    assert 'data-step="2"' in present  # (the groups on a present screen are canvas pixels: the selftest reads what it draws, and that the address carries them)
    # a link's own lanes= wins over the page's, and what it cannot honor is said
    link = dom(chrome_path, page, "flows&open=FLO-001&lanes=Ferry:APP-booking,APP-nowhere&still")
    assert "which isn't in this flow" in link and "Ferry has fewer than two lanes" in link and "Channels, group of 3" not in link
    # the Apps map's own group= is the map's alone: a stray value (here a flows-style one) neither draws groups nor breaks the map's Group menu
    stray = dom(chrome_path, page, "s=apps&group=Channels:APP-website,APP-call-center&still")
    assert 'data-dmenu="group"' in stray, "the map's Group menu did not draw"
    assert 'data-dmenu="group"' in dom(chrome_path, page, "s=apps&still")  # (and it draws on the same page with no stray value: the check can tell)


@pytest.mark.browser
def test_the_selftest_walks_the_pinned_row_the_starts_and_the_folds_at_both_sizes(tmp_path, chrome_path):  # noqa: F811
    page = staged(tmp_path)
    for viewport in ("1600,1000", "800,600"):
        lines = _check_selftest_in_chrome(chrome_path, page, f"booking with starts flows at {viewport}", viewport)
        for want in ("ok steps: a flow of 12 steps scrolls in a box", "ok steps: the box is a keyboard-reachable region", "ok steps: the box ends at the bottom of the fifth step", "ok steps: the fade shows while", "ok steps: the fade goes at the bottom",
                     "ok steps: the current step is marked", "ok steps: every step is still a button", "ok steps: a flow of 3 steps stays a plain list", "ok pin: a short stage makes", "ok pin: a click on a pinned name still opens", "ok pin: a shadow falls under the pinned row", "ok pin: the saved clip draws the flow whole",
                     "ok starts: 3 flows with one way in show no Starts from", 'ok starts, FLO-010: "Starts from" in the header row', "ok starts, FLO-010: picking",
                     "ok starts, FLO-010: Next skips the steps of the start not picked", "ok starts, FLO-010: the arrow keys move between the starts",
                     "ok starts, FLO-010: a click on a Start tag picks that start", "ok starts, FLO-010: pressing the picked start again goes back to Either", "ok starts, FLO-010: a link naming the start opens with it picked",
                     "ok starts, FLO-013: a guess says it is one", "ok starts, FLO-001: picking", "ok fold: on ", "ok hide: on FLO-001, a lane hides",
                     "ok hide: a link naming a hidden lane", "ok flows: the Starts from picker and Simplify fit the header row in every theme and in Plain",
                     "ok groups: FLO-001 opens with its page's Channels and Lookups", "ok groups: ungroup rides in the address", "ok groups: a name with , : ; and % round-trips through the real address", "ok groups: renaming to another group's name is refused", "ok groups: a group can host a fold", "ok groups: G opens the picker",
                     "ok groups: a click on a group's pill opens its panel", "ok groups: present mode draws the groups", "ok groups: traffic inside a group is one card",
                     "ok groups: with both groups on, the lane names do not overlap", "ok groups: the Group button, Starts from and Simplify fit the header row", "ok arrows: across "):
            assert any(line.startswith(want) for line in lines), (viewport, want)
