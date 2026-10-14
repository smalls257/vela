"""The Flows view's branch picker in a real browser (design 19, D8): the example vault with one flow drawn in the strict
form, so it has branches, and its contracts lack Can time out, so its check is not fully checked. A link naming a
branch opens it chosen; the page's own selftest walks every branch, its marks, the panel clicks and the text fit in
every theme and in Plain, at a wide and a small window."""
import html
import re
import shutil
import subprocess
import sys

import pytest
from test_explorer_browser import REPO, _check_selftest_in_chrome, chrome_path  # noqa: F401  (chrome_path is a fixture)

BOOKING = REPO / "examples" / "unified-booking"
KIOSK_FLOW = """---
id: FLO-009
type: flow
title: A kiosk holds a seat
state: assumption
owner: "@hl-solution-lead"
authored: authored
---

# A kiosk holds a seat

A traveler at a port kiosk holds a seat, and the kiosk says what happened.

## Steps

1. [[kiosks-building-blocks|Port kiosks]] → [[booking-building-blocks|Booking]]: holds a seat, over [[booking-building-blocks#CON-001 Booking API|Booking API]].

## Checked flow

```mermaid
sequenceDiagram
    participant K as Port kiosks
    participant B as Booking
    K->>B: CON-001 hold a seat
    alt held
        B-->>K: ok held
        Note over K: END held
    else confirming
        Note over K: END confirming
    else refused_ledger_unavailable
        Note over K: END refused
    end
```
"""


def staged(tmp_path):
    vault = tmp_path / "vault"
    shutil.copytree(BOOKING, vault)
    (vault / "06-runtime" / "flows" / "FLO-009-a-kiosk-holds-a-seat.md").write_text(KIOSK_FLOW, encoding="utf-8")
    cmd = [sys.executable, str(REPO / "plugin" / "scripts" / "planner"), "explore", "--selftest", str(vault), "--today", "2026-11-20"]
    assert subprocess.run(cmd, timeout=120, capture_output=True, text=True).returncode == 0
    return vault / "dashboard.html"


def dom(chrome_path, page, hash_, budget=20000):  # noqa: F811
    cmd = [str(chrome_path), "--headless=new", "--disable-gpu", "--no-sandbox", "--window-size=1400,900", f"--virtual-time-budget={budget}",
           "--dump-dom", f"file://{page}#{hash_}"]
    return subprocess.run(cmd, timeout=300, capture_output=True, text=True).stdout


@pytest.mark.browser
def test_a_link_naming_a_branch_opens_it_with_its_marks_in_words(tmp_path, chrome_path):  # noqa: F811
    page = staged(tmp_path)
    out = html.unescape(dom(chrome_path, page, "flows&open=FLO-009&branch=CON-001.confirming&still"))
    assert re.search(r'<option value="CON-001.confirming" selected="">Booking API: Confirming \(not fully checked\)</option>', out), out[:2000]
    assert '<option value="happy">Happy path (not fully checked)</option>' in out
    # with no Can time out written, the check stops at F10 before it judges a missing branch (R0): not drawn, not passed
    assert '<option value="CON-001.refused_dependency_down" disabled="">Booking API: Refused dependency down (not drawn, not fully checked)</option>' in out
    assert ("3 ways this flow can go: the happy path and 2 branches. None has a finding, 5 weren't fully checked, and 2 answers "
            "aren't drawn at all.") in out
    assert re.search(r'<label for="br-pick-FLO-009">Show</label>', out)
    # a flow drawn the old way keeps the played view and one line
    out = html.unescape(dom(chrome_path, page, "flows&open=FLO-001&still"))
    assert "Error cases aren't drawn yet" in out and 'class="br-pick"' not in out


@pytest.mark.browser
def test_the_selftest_walks_every_branch_in_every_theme(tmp_path, chrome_path):  # noqa: F811
    page = staged(tmp_path)
    for viewport in ("1600,1000", "800,600"):
        _check_selftest_in_chrome(chrome_path, page, f"booking with a kiosk flow's branches at {viewport}", viewport)
    out = dom(chrome_path, page, "map&selftest", budget=60000)
    lines = html.unescape(re.search(r'data-selftest="([^"]*)"', out).group(1)).split(" || ")
    for want in ('ok branches, FLO-009: "Show" and one picker', "ok branches, FLO-009: every option says not fully checked",
                 "ok branches, FLO-009: each of 3 branches redraws", "ok branches: a link naming", "ok branches, FLO-001: one line",
                 "ok branches: in Plain, every branch's words fit"):
        assert any(line.startswith(want) for line in lines), want
