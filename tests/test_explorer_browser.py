"""Browser smoke test for the explorer page. Runs the #selftest in headless Chrome.

    python3 -m pytest -q -m browser tests/test_explorer_browser.py

Requires Chrome or Chromium. Set env var CHROME to override the default search paths.
If Chrome is not found and CI env var is set, the test fails instead of skipping.
"""
import functools
import html
import http.server
import os
import pathlib
import re
import shutil
import signal
import subprocess
import sys
import threading

import pytest
from sharing import draft_workspace, git, make_vault

REPO = pathlib.Path(__file__).resolve().parent.parent
CHECKS_FLOOR = 80  # the emptiest snapshot ran 92 when this was set; a drop below means checks went missing

# Vault snapshots to test: map of (name, path) for snapshots that exist.
SNAPSHOT_BASE = REPO / "tests" / "sim" / "snapshots"
SNAPSHOTS = {
    "coastal-merger/empty": SNAPSHOT_BASE / "coastal-merger" / "empty",
    "coastal-merger/after-boundary-s2": SNAPSHOT_BASE / "coastal-merger" / "after-boundary-s2",
    "trading-coach/after-handoff-2": SNAPSHOT_BASE / "trading-coach" / "after-handoff-2",
    "trading-coach/after-80b": SNAPSHOT_BASE / "trading-coach" / "after-80b",
    # Written by real sessions (requirements, allocate, releases, boundary): domains, senders, a release, allocation.
    "trading-coach/after-capture-boundary": SNAPSHOT_BASE / "trading-coach" / "after-capture-boundary",
    "holdout-hospitals/after-discover": SNAPSHOT_BASE / "holdout-hospitals" / "after-discover",
    # Contracts whose providers are written as prose, not linked: three outside boxes on one row under one app, and
    # three lamps meeting at it. The ungrouped map, the line map and the minimap once drew these on top of each other.
    "heron-desk/after-full-1": SNAPSHOT_BASE / "heron-desk" / "after-full-1",
    # Two contracts join one pair of apps (consent: check and record), a design challenges an acceptance criterion and a
    # constraint that have no page of their own, and the line map has an outside party under the zone label (E14).
    "heron-desk/after-design-2": SNAPSHOT_BASE / "heron-desk" / "after-design-2",
}


@pytest.mark.browser
def test_plain_names_and_trace_rows_pass_the_selftest(tmp_path, chrome_path):
    """The heron vault with its calendar epic rewritten in plain words: Trace lines under each criterion, subheadings
    over them. The page's own selftest finds the folded chip rows and the bare IDs that now read as names."""
    vault = tmp_path / "vault"
    shutil.copytree(SNAPSHOTS["heron-desk/after-full-1"], vault)
    shutil.copy(REPO / "tests" / "fixtures" / "readable" / "EPC-001-calendar.md", vault / "13-epics" / "EPC-001-calendar.md")
    cmd = [sys.executable, str(REPO / "plugin" / "scripts" / "planner"), "explore", "--selftest", str(vault), "--today", "2026-10-10"]
    assert subprocess.run(cmd, timeout=120, capture_output=True, text=True).returncode == 0
    html_path = vault / "dashboard.html"
    _check_selftest_in_chrome(chrome_path, html_path, "heron-desk/readable")
    dom = subprocess.run([str(chrome_path), "--headless=new", "--disable-gpu", "--no-sandbox", "--window-size=1600,1000",
                          "--virtual-time-budget=60000", "--dump-dom", f"file://{html_path}#map&selftest&trace"],
                         timeout=180, capture_output=True, text=True).stdout
    selftest = html.unescape(re.search(r'data-selftest="([^"]*)"', dom).group(1))
    assert "ok trace rows:" in selftest and "ok plain names:" in selftest, selftest


@pytest.mark.browser
def test_fourteen_flows_are_grouped_in_the_picker_and_pass_the_selftest(tmp_path, chrome_path):
    """The synthetic stress vault has 14 flows, past the ten the picker lists flat: grouped, filtered and driven by key."""
    sys.path.insert(0, str(REPO / "prototypes" / "explorer"))
    import make_stress_vault
    vault = tmp_path / "stress"
    make_stress_vault.main(vault)
    cmd = [sys.executable, str(REPO / "plugin" / "scripts" / "planner"), "explore", "--selftest", str(vault), "--today", "2026-10-10"]
    assert subprocess.run(cmd, timeout=180, capture_output=True, text=True).returncode == 0
    _check_selftest_in_chrome(chrome_path, vault / "dashboard.html", "stress/14 flows")


def find_chrome():
    """Find Chrome binary. Returns path or None. Raises RuntimeError if CI and not found."""
    # Try env var CHROME first
    if "CHROME" in os.environ:
        path = pathlib.Path(os.environ["CHROME"])
        if path.exists():
            return path
        # A CHROME that names nothing is a broken setup, not a missing browser: skipping would pass CI silently.
        raise RuntimeError(f"CHROME is set to {path}, which does not exist")

    # Try default macOS path
    mac_default = pathlib.Path("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome")
    if mac_default.exists():
        return mac_default

    # Try shutil.which with common names
    for name in ["google-chrome", "google-chrome-stable", "chromium", "chromium-browser"]:
        found = shutil.which(name)
        if found:
            return pathlib.Path(found)

    # Not found: skip unless CI
    if os.environ.get("CI"):
        raise RuntimeError("no Chrome/Chromium found; set CHROME env var or install chrome")
    pytest.skip("no Chrome/Chromium found; set CHROME")


@pytest.fixture(scope="module")
def chrome_path():
    """Find Chrome once per test session."""
    return find_chrome()


@pytest.mark.browser
@pytest.mark.parametrize(
    "vault_name,vault_path",
    [(name, path) for name, path in SNAPSHOTS.items() if path.exists()],
    ids=lambda x: x[0] if isinstance(x, tuple) else None,
)
def test_explorer_selftest(tmp_path, chrome_path, vault_name, vault_path):
    """Build explorer for a vault and check #selftest in headless Chrome."""
    if chrome_path is None:
        pytest.skip("Chrome not available")

    # Copy vault to tmp
    vault_copy = tmp_path / "vault"
    shutil.copytree(vault_path, vault_copy)

    # Run planner explore
    cmd = [
        sys.executable,
        str(REPO / "plugin" / "scripts" / "planner"),
        "explore",
        "--selftest",
        str(vault_copy),
        "--today",
        "2026-10-10",
    ]
    result = subprocess.run(cmd, timeout=120, capture_output=True, text=True)
    assert result.returncode == 0, f"planner explore failed: {result.stderr}"

    # Run Chrome to extract selftest
    html_path = vault_copy / "dashboard.html"
    assert html_path.exists(), f"dashboard.html not found at {html_path}"

    # Extract and check selftest
    _check_selftest_in_chrome(chrome_path, html_path, vault_name)

    # Check that the page doesn't contain home path
    page_text = html_path.read_text(encoding="utf-8")
    assert str(pathlib.Path.home()) not in page_text, (
        f"page contains home path {pathlib.Path.home()}"
    )


@pytest.mark.browser
def test_explorer_selftest_800x600(tmp_path, chrome_path):
    """Test explorer at small viewport (800x600)."""
    if chrome_path is None:
        pytest.skip("Chrome not available")

    vault_name = "trading-coach/after-80b"
    vault_path = SNAPSHOT_BASE / "trading-coach" / "after-80b"
    if not vault_path.exists():
        pytest.skip(f"{vault_name} not found")

    # Copy vault to tmp
    vault_copy = tmp_path / "vault"
    shutil.copytree(vault_path, vault_copy)

    # Run planner explore
    cmd = [
        sys.executable,
        str(REPO / "plugin" / "scripts" / "planner"),
        "explore",
        "--selftest",
        str(vault_copy),
        "--today",
        "2026-10-10",
    ]
    result = subprocess.run(cmd, timeout=120, capture_output=True, text=True)
    assert result.returncode == 0, f"planner explore failed: {result.stderr}"

    # Run Chrome at small viewport
    html_path = vault_copy / "dashboard.html"
    assert html_path.exists()
    _check_selftest_in_chrome(chrome_path, html_path, vault_name, viewport="800,600")


@pytest.mark.browser
def test_the_heron_design_vault_passes_the_selftest_at_800x600(tmp_path, chrome_path):
    vault = tmp_path / "vault"
    shutil.copytree(SNAPSHOTS["heron-desk/after-design-2"], vault)
    cmd = [sys.executable, str(REPO / "plugin" / "scripts" / "planner"), "explore", "--selftest", str(vault), "--today", "2026-10-10"]
    assert subprocess.run(cmd, timeout=120, capture_output=True, text=True).returncode == 0
    _check_selftest_in_chrome(chrome_path, vault / "dashboard.html", "heron-desk/after-design-2", viewport="800,600")


def _check_selftest_in_chrome(chrome_path, html_path, vault_name, viewport="1600,1000"):
    """Run Chrome headless and check #selftest output."""
    cmd = [
        str(chrome_path),
        "--headless=new",
        "--disable-gpu",
        "--no-sandbox",
        f"--window-size={viewport}",
        "--virtual-time-budget=60000",
        "--dump-dom",
        f"file://{html_path}#map&selftest",
    ]

    result = subprocess.run(cmd, timeout=180, capture_output=True, text=True)

    # Extract selftest data from DOM
    match = re.search(r'data-selftest="([^"]*)"', result.stdout)
    assert match, f"data-selftest not found in Chrome output for {vault_name}"

    selftest_text = html.unescape(match.group(1))

    # Extract FAIL lines if any
    fail_lines = [line for line in selftest_text.split(" || ") if line.startswith("FAIL")]

    assert selftest_text.startswith(
        "SELFTEST OK"
    ), f"{vault_name} selftest failed:\n" + "\n".join(fail_lines)
    # a selftest that quietly skipped most of its checks still says OK, so a floor on how many ran guards it (E32)
    ran = int(re.match(r"SELFTEST OK: (\d+) checks passed", selftest_text).group(1))
    assert ran >= CHECKS_FLOOR, f"{vault_name}: only {ran} selftest checks ran, wanted at least {CHECKS_FLOOR}"


@pytest.mark.browser
def test_a_served_page_finds_its_helper(tmp_path, chrome_path):
    """`planner explore --serve` with a fake claude on PATH: the page loaded over loopback fetches /health, flags itself
    served, and its own #selftest (which then plays the Ask checks against a fake fetch) passes."""
    vault = tmp_path / "vault"
    shutil.copytree(SNAPSHOT_BASE / "trading-coach" / "after-capture-boundary", vault)
    env = {**os.environ, "PATH": f"{REPO / 'tests' / 'explorer_stub'}:{os.environ['PATH']}"}
    server = subprocess.Popen([sys.executable, str(REPO / "plugin" / "scripts" / "planner"), "explore", "--selftest", str(vault), "--today", "2026-10-10",
                               "--serve", "--no-open", "--port", "0"], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, env=env)
    watchdog = threading.Timer(120, server.kill)  # a server that never says where it is must not hang the suite
    watchdog.start()
    try:
        url = None
        for line in server.stdout:
            found = re.search(r"serving (http://\S+?/\?k=\S+) ", line)  # the printed link carries the helper's key
            if found:
                url = found.group(1)
                break
        assert url, "planner explore --serve never printed its address"
        assert url.startswith("http://127.0.0.1:")
        cmd = [str(chrome_path), "--headless=new", "--disable-gpu", "--no-sandbox", "--window-size=1600,1000", "--virtual-time-budget=60000",
               "--dump-dom", f"{url}#home&selftest"]
        dom = subprocess.run(cmd, timeout=180, capture_output=True, text=True).stdout
        assert 'data-ask="served"' in dom, "the page did not detect the helper"
        selftest = html.unescape(re.search(r'data-selftest="([^"]*)"', dom).group(1))
        assert selftest.startswith("SELFTEST OK"), [line for line in selftest.split(" || ") if line.startswith("FAIL")]
        assert "ask when served: the page found its helper with one /health request" in selftest
        assert re.search(r"ok served: \d+ Open the file links? each reach their file through the helper", selftest), "E17: served file links were not followed"
    finally:
        watchdog.cancel()
        server.send_signal(signal.SIGINT)
        try:
            server.wait(timeout=15)
        except subprocess.TimeoutExpired:
            server.kill()
            server.wait()


def _selftest_lines(dom):
    return html.unescape(re.search(r'data-selftest="([^"]*)"', dom).group(1)).split(" || ")


@pytest.mark.browser
def test_a_reader_workspace_shows_its_draft_and_its_pending_decision(tmp_path, chrome_path):
    """publish a snapshot, open it, edit a page and record a pending-approval decision, explore: the page's own #selftest
    passes with the draft badge, the Drafts view, the pending badge and the stamped freshness all drawn."""
    _, _, workspace = draft_workspace(tmp_path)
    result = subprocess.run([sys.executable, str(REPO / "plugin" / "scripts" / "planner"), "explore", "--selftest", str(workspace), "--today", "2026-10-12"],
                            timeout=120, capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    page = workspace / "dashboard.html"
    dom = subprocess.run([str(chrome_path), "--headless=new", "--disable-gpu", "--no-sandbox", "--window-size=1600,1000", "--virtual-time-budget=60000",
                          "--dump-dom", f"file://{page}#home&selftest"], timeout=180, capture_output=True, text=True).stdout
    lines = _selftest_lines(dom)
    assert lines[0].startswith("SELFTEST OK"), [line for line in lines if line.startswith("FAIL")]
    assert 'ok draft badge: "Draft: 2 pages changed" in the top bar of this reader\'s page' in lines
    assert any(line.startswith("ok drafts view: #drafts lists 2 changed pages") for line in lines)
    assert any(line.startswith("ok drafts view: a hint names /planner:propose") for line in lines)
    assert any(line.startswith('ok pending approval: CON-001 (@sam, 2026-10-12) is lit "pending"') for line in lines)
    assert "ok freshness on a file: no request at load, none when asked to poll" in lines
    assert str(pathlib.Path.home()) not in page.read_text(encoding="utf-8")


@pytest.mark.browser
def test_a_served_reader_page_asks_freshness_once_on_load(tmp_path, chrome_path):
    """The same workspace served: the page polls /freshness (the helper's answer is `planner freshness --json`) and its self-test passes."""
    _, _, workspace = draft_workspace(tmp_path)
    env = {**os.environ, "PATH": f"{REPO / 'tests' / 'explorer_stub'}:{os.environ['PATH']}"}
    server = subprocess.Popen([sys.executable, str(REPO / "plugin" / "scripts" / "planner"), "explore", "--selftest", str(workspace), "--today", "2026-10-12",
                               "--serve", "--no-open", "--port", "0"], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, env=env)
    watchdog = threading.Timer(120, server.kill)
    watchdog.start()
    try:
        url = None
        for line in server.stdout:
            found = re.search(r"serving (http://\S+?/\?k=\S+) ", line)
            if found:
                url = found.group(1)
                break
        assert url, "planner explore --serve never printed its address"
        dom = subprocess.run([str(chrome_path), "--headless=new", "--disable-gpu", "--no-sandbox", "--window-size=1600,1000", "--virtual-time-budget=60000",
                              "--dump-dom", f"{url}#home&selftest"], timeout=180, capture_output=True, text=True).stdout
        lines = _selftest_lines(dom)
        assert lines[0].startswith("SELFTEST OK"), [line for line in lines if line.startswith("FAIL")]
        assert "ok freshness when served: at most one /freshness request at load" in lines
        assert "ok freshness when served: a poll asks /freshness once and shows the banner from the answer" in lines
    finally:
        watchdog.cancel()
        server.send_signal(signal.SIGINT)
        try:
            server.wait(timeout=15)
        except subprocess.TimeoutExpired:
            server.kill()
            server.wait()


@pytest.mark.browser
def test_a_replayed_workspace_lists_its_conflicts_first_and_the_badge_counts_them(tmp_path, chrome_path):
    """re-open a newer copy onto drafts that clash: the page's own #selftest passes with the Conflict badge drawn in every
    theme, the conflicts listed before the changed pages, and the draft badge counting them."""
    from test_replay import conflicted_workspace
    workspace = conflicted_workspace(tmp_path)
    page = workspace / "dashboard.html"
    rebuilt = subprocess.run([sys.executable, str(REPO / "plugin" / "scripts" / "planner"), "explore", "--selftest", str(workspace), "--today", "2026-10-12"],
                             timeout=120, capture_output=True, text=True)
    assert rebuilt.returncode == 0, rebuilt.stderr  # re-open writes the page without its checks; this test needs them
    dom = subprocess.run([str(chrome_path), "--headless=new", "--disable-gpu", "--no-sandbox", "--window-size=1600,1000", "--virtual-time-budget=60000",
                          "--dump-dom", f"file://{page}#home&selftest"], timeout=180, capture_output=True, text=True).stdout
    lines = _selftest_lines(dom)
    assert lines[0].startswith("SELFTEST OK"), [line for line in lines if line.startswith("FAIL")]
    assert any(line.startswith("ok drafts view: the Conflict badge shows its word, ink and ring in every theme") for line in lines)
    assert any(line.startswith("ok drafts view: 4 conflicts listed before every other change, and the draft badge counts them") for line in lines)


@pytest.mark.browser
@pytest.mark.parametrize("page,said", [("maps/cockpit.html", '[maps] assets from provider "comfyui"'),
                                       ("flows/played.html", '[flows] assets from provider "comfyui"')])
def test_gallery_pages_load_the_plugins_art(chrome_path, page, said):
    """The gallery has no copy of the resolver, slots or builtin art; its pages must still load them from the plugin
    (with the ComfyUI provider from the gallery's own folder) and fall back to nothing."""
    handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(REPO))
    handler.log_message = lambda *args: None
    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        result = subprocess.run(
            [str(chrome_path), "--headless=new", "--disable-gpu", "--no-sandbox", "--virtual-time-budget=8000",
             "--enable-logging=stderr", "--v=0", "--dump-dom",
             f"http://127.0.0.1:{server.server_address[1]}/prototypes/gallery/{page}"],
            timeout=120, capture_output=True, text=True)
    finally:
        server.shutdown()
        server.server_close()
    console = [line for line in result.stderr.splitlines() if "CONSOLE" in line]
    assert any(said in line for line in console), "\n".join(console) or result.stderr[-500:]
    assert not [line for line in console if "fell back" in line or "[assets]" in line], "\n".join(console)


@pytest.mark.browser
@pytest.mark.parametrize("viewport", ["1600,1000", "1280,720"])
def test_explorer_selftest_with_three_designs_loaded(tmp_path, chrome_path, viewport):
    """The demo vault with its three team designs: Inside this app draws components and the data model, which the
    snapshot vaults above have no design for. Run at a wide and at a laptop window."""
    demo = tmp_path / "booking-demo"
    made = subprocess.run([sys.executable, str(REPO / "prototypes/explorer/make_demo_vault.py"), str(demo)], timeout=120, capture_output=True, text=True)
    assert made.returncode == 0, made.stderr
    designs = REPO / "prototypes/explorer/demo_designs"
    page = tmp_path / "booking-demo.html"
    built = subprocess.run([sys.executable, str(REPO / "prototypes/explorer/build.py"), str(demo), str(page), "--today", "2026-11-20", "--selftest",
                            "--pins", str(REPO / "prototypes/explorer/pins/unified-booking.json"),
                            *[f"--design=APP-{name}={designs / name / 'docs/tech-design' / (name + '.md')}" for name in ("booking", "pricing", "notifications")]],
                           timeout=120, capture_output=True, text=True)
    assert built.returncode == 0, built.stderr
    _check_selftest_in_chrome(chrome_path, page, "booking-demo with designs", viewport=viewport)


@pytest.mark.browser
def test_the_built_line_shows_at_the_top_with_the_commit(tmp_path, chrome_path):
    if chrome_path is None:
        pytest.skip("Chrome not available")
    vault = make_vault(tmp_path, "shown")
    subprocess.run([sys.executable, str(REPO / "plugin" / "scripts" / "planner"), "explore", "--selftest", str(vault), "--today", "2026-10-10"], timeout=120, check=True, capture_output=True)
    short = git(vault, "rev-parse", "--short", "HEAD")
    dom = subprocess.run([str(chrome_path), "--headless=new", "--disable-gpu", "--no-sandbox", "--virtual-time-budget=20000", "--dump-dom",
                          f"file://{vault / 'dashboard.html'}#home"], timeout=180, capture_output=True, text=True).stdout
    line = html.unescape(re.search(r'<div class="built" id="built"[^>]*>(.*?)</div>', dom, re.S).group(1))
    assert f"from commit {short}" in line and "hidden" not in re.search(r'<div class="built" id="built"[^>]*>', dom).group(0)


def _explore_and_dump(chrome_path, source, tmp_path, today, route, viewport="1600,1000"):
    """Build `source` as a vault copy and return the page's DOM after loading `route`."""
    vault = tmp_path / "vault"
    shutil.copytree(source, vault)
    subprocess.run([sys.executable, str(REPO / "plugin" / "scripts" / "planner"), "explore", "--selftest", str(vault), "--today", today], timeout=120, check=True, capture_output=True)
    return subprocess.run([str(chrome_path), "--headless=new", "--disable-gpu", "--no-sandbox", f"--window-size={viewport}", "--virtual-time-budget=20000", "--dump-dom",
                           f"file://{vault / 'dashboard.html'}#{route}"], timeout=180, capture_output=True, text=True).stdout


@pytest.mark.browser
@pytest.mark.parametrize("viewport", ["1600,1000", "800,600"])
def test_the_home_page_lists_a_short_queue_not_a_strip_of_chips(tmp_path, chrome_path, viewport):
    """The heron vault holds 34 question-and-thing pairs above the map. Home shows at most five rows of the queue, in
    plain words, with no strip of chips, at a wide and at a small window."""
    dom = _explore_and_dump(chrome_path, SNAPSHOTS["heron-desk/after-full-1"], tmp_path, "2026-10-10", "home&still", viewport)
    assert 'class="q-card' in dom and 'class="above"' not in dom and "Held above the map" not in dom
    rows = re.findall(r'<button class="q-row[^"]*" data-ref="([^"]+)"', dom)
    assert 1 <= len(rows) <= 5 and len(set(rows)) == len(rows), rows
    assert not re.search(r'class="q-title">[A-Z]+-\d', dom), "a queue row leads with an ID"


@pytest.mark.browser
def test_the_old_garden_route_opens_the_decision_log_at_the_decision(tmp_path, chrome_path):
    """#garden&open=ADR-0002 still lands on the decision, now drawn as a log row and a decision record."""
    dom = _explore_and_dump(chrome_path, REPO / "examples" / "unified-booking", tmp_path, "2026-11-20", "garden&open=ADR-0002&still")
    assert 'data-view="decisions"' in dom and "dl-detail" in dom and "FERRYMASTER stays the ledger of record" in dom
    assert 'class="sheet' not in dom and "garden" not in re.sub(r"#garden", "", re.search(r"<main.*?</main>", dom, re.S).group(0))
