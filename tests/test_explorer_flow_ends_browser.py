"""Flow steps with unknown ends, drawn in headless Chrome (the page's own selftest, assets/js/selftest-branches.js).

    python3 -m pytest -q -m browser tests/test_explorer_flow_ends_browser.py

The fixture flow FLO-009 has a plain-text app, an outside actor the plan doesn't know, a pair with no contract, a step
inside one app and a step that names two apps and records no pair. The selftest must draw the actor on its own dashed
lane marked "not in the plan", mark the pair "no contract named", say "who sends to whom isn't recorded" on the band, and
draw a loop on one app only for a step that names exactly one lane and records no pair. A selftest that skipped these
would pass, so each named line must be present and ok.
"""
import html
import re
import subprocess
import sys

import pytest
from conftest import REPO, chrome_profile, run_chrome
from flow_ends_vault import TODAY, booking_with_flow_ends
from test_explorer_browser import find_chrome

WANTED = [
    "flows: a loop on one app is drawn only for a step that names exactly one lane and records no pair",
    "flows: an end the plan doesn't know (\"Ferry passenger\") has its own lane, labeled \"not in the plan\"",
    "flows: only the lanes a flow's steps touch are drawn, and the columns share the full width",
    "flows: a gap lane opens the panel, which says what to do",
    "flows: a step that names several lanes and records no pair is a band that says who sends to whom isn't recorded",
    "flows: a recorded pair with no contract draws an arrow marked \"no contract named\"",
    "flows: no label on any of",
]


def report(html_path, size):
    dom = run_chrome([str(find_chrome()), "--headless=new", chrome_profile(), "--disable-gpu", "--no-sandbox", f"--window-size={size}", "--virtual-time-budget=90000",
                      "--dump-dom", f"file://{html_path}#selftest"], 300)[1]
    found = re.search(r'data-selftest="([^"]*)"', dom)
    assert found, f"the page produced no selftest report at {size}"
    return html.unescape(found.group(1)).split(" || ")


@pytest.fixture(scope="module")
def page(tmp_path_factory):
    vault = booking_with_flow_ends(tmp_path_factory.mktemp("flowends"))
    cmd = [sys.executable, str(REPO / "plugin" / "scripts" / "vela"), "explore", "--selftest", str(vault), "--today", TODAY, "--no-open"]
    assert subprocess.run(cmd, timeout=180, capture_output=True, text=True).returncode == 0
    return vault / "dashboard.html"


@pytest.mark.browser
@pytest.mark.parametrize("size", ["1440,900", "800,900"])
def test_unknown_ends_are_drawn_and_no_self_arrow_is_invented(page, size):
    lines = report(page, size)
    failing = [x for x in lines if x.startswith("FAIL")]
    assert not failing, "\n".join(failing)
    assert lines[0].startswith("SELFTEST OK"), lines[0]
    ok = [x for x in lines if x.startswith("ok flows:")]
    missing = [w for w in WANTED if not any(w in line for line in ok)]
    assert not missing, "selftest lines missing or not ok: " + "; ".join(missing)
