"""Browser smoke test for the explorer page. Runs the #selftest in headless Chrome.

    python3 -m pytest -q -m browser tests/test_explorer_browser.py

Requires Chrome or Chromium. Set env var CHROME to override the default search paths.
If Chrome is not found and CI env var is set, the test fails instead of skipping.
"""
import html
import os
import pathlib
import re
import shutil
import signal
import subprocess
import sys
import threading

import pytest
from sharing import draft_workspace

REPO = pathlib.Path(__file__).resolve().parent.parent

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
}


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
        str(vault_copy),
        "--today",
        "2026-10-10",
    ]
    result = subprocess.run(cmd, timeout=120, capture_output=True, text=True)
    assert result.returncode == 0, f"planner explore failed: {result.stderr}"

    # Run Chrome to extract selftest
    html_path = vault_copy / ".planner" / "explorer.html"
    assert html_path.exists(), f"explorer.html not found at {html_path}"

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
        str(vault_copy),
        "--today",
        "2026-10-10",
    ]
    result = subprocess.run(cmd, timeout=120, capture_output=True, text=True)
    assert result.returncode == 0, f"planner explore failed: {result.stderr}"

    # Run Chrome at small viewport
    html_path = vault_copy / ".planner" / "explorer.html"
    assert html_path.exists()
    _check_selftest_in_chrome(chrome_path, html_path, vault_name, viewport="800,600")


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


@pytest.mark.browser
def test_a_served_page_finds_its_helper(tmp_path, chrome_path):
    """`planner explore --serve` with a fake claude on PATH: the page loaded over loopback fetches /health, flags itself
    served, and its own #selftest (which then plays the Ask checks against a fake fetch) passes."""
    vault = tmp_path / "vault"
    shutil.copytree(SNAPSHOT_BASE / "trading-coach" / "after-capture-boundary", vault)
    env = {**os.environ, "PATH": f"{REPO / 'tests' / 'explorer_stub'}:{os.environ['PATH']}"}
    server = subprocess.Popen([sys.executable, str(REPO / "plugin" / "scripts" / "planner"), "explore", str(vault), "--today", "2026-10-10",
                               "--serve", "--no-open", "--port", "0"], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, env=env)
    watchdog = threading.Timer(120, server.kill)  # a server that never says where it is must not hang the suite
    watchdog.start()
    try:
        url = None
        for line in server.stdout:
            found = re.search(r"serving (http://\S+?/) ", line)
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
    result = subprocess.run([sys.executable, str(REPO / "plugin" / "scripts" / "planner"), "explore", str(workspace), "--today", "2026-10-12"],
                            timeout=120, capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    page = workspace / ".planner" / "explorer.html"
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
    server = subprocess.Popen([sys.executable, str(REPO / "plugin" / "scripts" / "planner"), "explore", str(workspace), "--today", "2026-10-12",
                               "--serve", "--no-open", "--port", "0"], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, env=env)
    watchdog = threading.Timer(120, server.kill)
    watchdog.start()
    try:
        url = None
        for line in server.stdout:
            found = re.search(r"serving (http://\S+?/) ", line)
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
