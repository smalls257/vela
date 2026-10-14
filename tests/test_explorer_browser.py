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
def test_maps_move_free_form_and_pan_by_dragging_the_background(tmp_path, chrome_path):
    """The user, on the dashboard map: movement should be free-form, not snap to a grid, and a drag on the background
    should pan. The selftest's own lines must be there and passing: a box dropped between cells stays there, the
    rule's cases agree with pins.check_move, a background drag pans the cockpit and a drawing inside an app, a box
    drag still moves the box, and every map drawing is pannable. A selftest that quietly skipped them would pass."""
    vault = tmp_path / "vault"
    shutil.copytree(SNAPSHOTS["heron-desk/after-design-2"], vault)
    cmd = [sys.executable, str(REPO / "plugin" / "scripts" / "planner"), "explore", "--selftest", str(vault), "--today", "2026-10-10"]
    assert subprocess.run(cmd, timeout=120, capture_output=True, text=True).returncode == 0
    dom = subprocess.run([str(chrome_path), "--headless=new", "--disable-gpu", "--no-sandbox", "--window-size=1600,1000",
                          "--virtual-time-budget=60000", "--dump-dom", f"file://{vault / 'dashboard.html'}#map&selftest"],
                         timeout=180, capture_output=True, text=True).stdout
    lines = html.unescape(re.search(r'data-selftest="([^"]*)"', dom).group(1)).split(" || ")
    wanted = ["ok the page's overlap rule gives pins.check_move's answer", "it stays exactly there, between cells",
              "it lands clear of it on the line it was dragged along",
              "ok Shift and an arrow key move the box a whole cell", "ok drag to pan: a drag on the cockpit's background",
              "ok drag to pan: a click on the background, a touch drag and a drag on a box do not pan",
              "ok drag to pan: where a drawing scrolls in its holder", "the drawing can be panned by dragging its background"]
    missing = [w for w in wanted if not any(w in line and line.startswith("ok") for line in lines)]
    assert not missing, "missing or failing selftest lines: " + "; ".join(missing) + "\n" + "\n".join(x for x in lines if x.startswith("FAIL"))


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


def _text_fit_lines(chrome_path, html_path, viewport):
    cmd = [str(chrome_path), "--headless=new", "--disable-gpu", "--no-sandbox", f"--window-size={viewport}", "--virtual-time-budget=60000", "--dump-dom", f"file://{html_path}#map&selftest"]
    match = re.search(r'data-selftest="([^"]*)"', subprocess.run(cmd, timeout=180, capture_output=True, text=True).stdout)
    assert match, "data-selftest not found in Chrome output"
    return html.unescape(match.group(1)).split(" || ")


@pytest.mark.browser
@pytest.mark.parametrize("viewport", ["720,800", "900,700"])
def test_no_label_runs_past_its_box_in_a_narrow_window(tmp_path, chrome_path, viewport):
    """The selftest's text-fit sweep alone, at windows narrower than the layout is built for (the other checks assume the
    three columns at 800 or wider): no pill, chip, badge, button, tab or heading in any view, theme or Plain runs out of
    its box. A failure names the view, the label's words and its class. The Heron design vault and the demo with three
    designs, so the sweep is not tuned to one vault."""
    heron = tmp_path / "heron"
    shutil.copytree(SNAPSHOTS["heron-desk/after-design-2"], heron)
    assert subprocess.run([sys.executable, str(REPO / "plugin" / "scripts" / "planner"), "explore", "--selftest", str(heron), "--today", "2026-10-10"], timeout=120, capture_output=True, text=True).returncode == 0
    demo = tmp_path / "booking-demo"
    assert subprocess.run([sys.executable, str(REPO / "prototypes/explorer/make_demo_vault.py"), str(demo)], timeout=120, capture_output=True, text=True).returncode == 0
    designs = REPO / "prototypes/explorer/demo_designs"
    page = tmp_path / "booking-demo.html"
    built = subprocess.run([sys.executable, str(REPO / "prototypes/explorer/build.py"), str(demo), str(page), "--today", "2026-11-20", "--selftest",
                            "--pins", str(REPO / "prototypes/explorer/pins/unified-booking.json"),
                            *[f"--design=APP-{name}={designs / name / 'docs/tech-design' / (name + '.md')}" for name in ("booking", "pricing", "notifications")]],
                           timeout=120, capture_output=True, text=True)
    assert built.returncode == 0, built.stderr
    for name, path in (("heron-desk/after-design-2", heron / "dashboard.html"), ("booking-demo with designs", page)):
        fit = [line for line in _text_fit_lines(chrome_path, path, viewport) if "text fits" in line]
        failed = [line for line in fit if line.startswith("FAIL")]
        assert len(fit) >= 5 and not failed, f"{name} at {viewport}: {len(fit)} text-fit checks ran\n" + "\n".join(failed)


@pytest.mark.browser
def test_names_not_codes_whole_prose_and_one_needs_you_count_pass_the_selftest(tmp_path, chrome_path):
    """The Fix-first findings, each as a line of the page's own selftest: the sensors that flag prose cut mid-sentence and
    titles that are codes see planted defects, the sweep finds none in any view or theme, and the header badge, the side
    door, the waiting card and the panel's opening line give one "needs you" number. Run against the old page these
    lines are absent or FAIL (the sweep found the door cards, the map's CON-nnn lamps and a 20-against-16 count)."""
    vault = tmp_path / "vault"
    shutil.copytree(SNAPSHOTS["heron-desk/after-full-1"], vault)
    cmd = [sys.executable, str(REPO / "plugin" / "scripts" / "planner"), "explore", "--selftest", str(vault), "--today", "2026-10-10"]
    assert subprocess.run(cmd, timeout=120, capture_output=True, text=True).returncode == 0
    lines = _text_fit_lines(chrome_path, vault / "dashboard.html", "1600,1000")
    ok = [line for line in lines if line.startswith("ok ")]
    assert any(line.startswith("ok needs you: one count") for line in ok), "the needs-you agreement check did not run or failed"
    assert any("the sensor flags prose cut with no ellipsis" in line for line in ok)
    assert any("the sensor flags a title that is a code" in line for line in ok)
    swept = [line for line in ok if "no prose is cut off without a Show more, no title is a bare ID" in line]
    assert len(swept) >= 5, "the sweep must pass in every theme and in Plain"
    assert not [line for line in lines if line.startswith("FAIL")], "\n".join(line for line in lines if line.startswith("FAIL"))


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
@pytest.mark.parametrize("viewport", ["1600,1000", "1280,720", "800,600"])
def test_explorer_selftest_with_three_designs_loaded(tmp_path, chrome_path, viewport):
    """The demo vault with its three team designs: Inside this app draws components and the data model, which the
    snapshot vaults above have no design for. Run at a wide, a laptop and a small window."""
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
    tag = re.search(r'<div class="built" id="built"[^>]*>(.*?)</div>', dom, re.S)
    line, opening = html.unescape(tag.group(1)), html.unescape(tag.group(0).split(">", 1)[0])
    # The sentence is for every reader (a date, no hash); the commit is for whoever maintains the plan, in a data
    # attribute, never in a tooltip a reader reads (E56: no commit hashes in reader text).
    assert line.startswith("Built ") and "commit" not in line and short not in line
    assert f'data-commit="{short}' in opening and "title=" not in opening and "hidden" not in opening


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


@pytest.mark.browser
def test_every_diagram_node_opens_the_panel_on_heron_and_the_booking_demo(tmp_path, chrome_path):
    """E44: the selftest clicks every node of every diagram and presses Enter on it, and fails on an empty panel. This holds
    it to the diagrams that were inert: the data model's entities, the sequence steps, the line map, the releases corridors,
    the due-by-week bars, the cluster mini-lamps, and the flows canvas (through its list), on a vault with designs and plans
    (Heron) and on the demo, so the fix is in the builder and not tuned to one vault."""
    heron = tmp_path / "heron"
    shutil.copytree(SNAPSHOTS["heron-desk/after-design-2"], heron)
    assert subprocess.run([sys.executable, str(REPO / "plugin" / "scripts" / "planner"), "explore", "--selftest", str(heron), "--today", "2026-10-10"], timeout=120, capture_output=True, text=True).returncode == 0
    demo = tmp_path / "booking-demo"
    assert subprocess.run([sys.executable, str(REPO / "prototypes/explorer/make_demo_vault.py"), str(demo)], timeout=120, capture_output=True, text=True).returncode == 0
    designs = REPO / "prototypes/explorer/demo_designs"
    page = tmp_path / "booking-demo.html"
    built = subprocess.run([sys.executable, str(REPO / "prototypes/explorer/build.py"), str(demo), str(page), "--today", "2026-11-20", "--selftest",
                            "--pins", str(REPO / "prototypes/explorer/pins/unified-booking.json"),
                            *[f"--design=APP-{name}={designs / name / 'docs/tech-design' / (name + '.md')}" for name in ("booking", "pricing", "notifications")]],
                           timeout=120, capture_output=True, text=True)
    assert built.returncode == 0, built.stderr
    must = ["map, cockpit", "map, line map", "map, grouped by domain, clusters closed", "releases", "progress, open questions by week", "the minimap",
            ", context", ", containers", ", components", ", data model", ", key flows", "flow FLO-"]
    for name, path in (("heron-desk/after-design-2", heron / "dashboard.html"), ("booking-demo with designs", page)):
        lines = _text_fit_lines(chrome_path, path, "1600,1000")
        sweep = [line for line in lines if "node sweep" in line]
        failed = [line for line in sweep if line.startswith("FAIL")]
        assert not failed, f"{name}: " + "\n".join(failed)
        for part in must:
            assert any(part in line and line.startswith("ok") and "each opens the panel" in line for line in sweep), f"{name}: no node sweep ran on {part!r}"
        if "booking" in name:  # the Heron snapshot carries no work breakdown; the demo does
            assert any(", build plan" in line and line.startswith("ok") and "each opens the panel" in line for line in sweep)
            assert any("dependency view: fits the width" in line for line in lines), f"{name}: the dependency view's width check did not run"
        assert any("the helper refuses a node" in line for line in sweep)
