"""The page's own selftest walks onboarding in a real browser: every role's path, every link, every item, progress, depth,
the key, the text fit and who the reader is, on plans at each stage, with the lead's page and a person's own path in play,
in a narrow window and on a large plan.

    python3 -m pytest -q -m browser tests/test_explorer_onboard_selftest.py

The Violation these guard against is a dead link or a link to the wrong item: the selftest follows each route the modules
carry and checks where it lands and what the panel shows.
"""
import shutil
import subprocess
import sys

import pytest
from test_explorer_browser import REPO, SNAPSHOTS, _check_selftest_in_chrome, chrome_path  # noqa: F401  (chrome_path is a fixture)

sys.path.insert(0, str(REPO / "prototypes" / "explorer"))
BOOKING = REPO / "examples" / "unified-booking"
VELA = [sys.executable, str(REPO / "plugin" / "scripts" / "vela")]
WANT = ("onboarding: each of the 6 roles lists its path", "onboarding: all ", "onboarding: the first items of every module open the panel",
        "onboarding: Next ticks a part", "onboarding: in the diagram, every look drawn is in the key", "onboarding: in cards and in the diagram, every label fits",
        "onboarding: a kept term is defined on its first use", "onboarding: a progress value that is not JSON", "onboarding: who the reader is comes from the plan's record first")


def build(vault, *extra):
    done = subprocess.run([*VELA, "explore", "--selftest", str(vault), "--today", "2026-11-20", *extra], timeout=180, capture_output=True, text=True)
    assert done.returncode == 0, done.stdout + done.stderr


def check(chrome_path, page, name, viewport="1600,1000"):  # noqa: F811
    lines = _check_selftest_in_chrome(chrome_path, page, name, viewport)
    for want in WANT:
        assert any(line.startswith("ok " + want) for line in lines), f"{name}: no passing line for {want!r}"
    return lines


@pytest.mark.browser
@pytest.mark.parametrize("name", ["heron-desk/after-full-1", "trading-coach/after-80b", "coastal-merger/empty"])
def test_the_selftest_walks_onboarding_on_a_plan_at_each_stage(tmp_path, chrome_path, name):  # noqa: F811
    vault = tmp_path / "vault"
    shutil.copytree(SNAPSHOTS[name], vault)
    build(vault)
    check(chrome_path, vault / "dashboard.html", name)


@pytest.mark.browser
def test_with_the_leads_page_and_roles_in_play_the_selftest_still_passes(tmp_path, chrome_path):  # noqa: F811
    vault = tmp_path / "vault"
    shutil.copytree(BOOKING, vault)
    (vault / "ONBOARDING.md").write_text("## Engineering\n- Stress: Journeys\n- Hide: Contracts\n- Note: Read the contract for the pilot first.\n", encoding="utf-8")
    config = vault / ".vela.yaml"
    config.write_text(config.read_text(encoding="utf-8").rstrip("\n") + "\nroles:\n  '@ana': qa\n", encoding="utf-8")
    build(vault)
    check(chrome_path, vault / "dashboard.html", "booking, tuned")


@pytest.mark.browser
def test_a_persons_own_page_passes_the_selftest_with_their_path_shown(tmp_path, chrome_path):  # noqa: F811
    vault = tmp_path / "vault"
    shutil.copytree(BOOKING, vault)
    (vault / ".vela").mkdir(exist_ok=True)
    (vault / ".vela" / "handle").write_text("ana\n", encoding="utf-8")
    done = subprocess.run([*VELA, "onboard", "path", "set", "--vault", str(vault), "--today", "2026-11-20", "--role", "product", "--modules", "Goal, Slices, Journeys",
                           "--diagrams", "yes", "--depth", "gist"], timeout=180, capture_output=True, text=True)
    assert done.returncode == 0, done.stdout + done.stderr
    build(vault, "--person", "ana")
    lines = check(chrome_path, vault / ".vela" / "onboard" / "ana.html", "booking, ana's path")
    assert any(line.startswith("ok onboarding: ana's own path is what the product role shows") for line in lines)


@pytest.mark.browser
def test_the_layout_stacks_in_a_narrow_window_with_nothing_cut_or_sideways(tmp_path, chrome_path):  # noqa: F811
    vault = tmp_path / "vault"
    shutil.copytree(SNAPSHOTS["trading-coach/after-80b"], vault)
    build(vault)
    for viewport in ("1100,700", "800,600"):
        check(chrome_path, vault / "dashboard.html", f"trading, {viewport}", viewport)


@pytest.mark.browser
def test_a_large_plan_keeps_every_check_passing(tmp_path, chrome_path):  # noqa: F811
    """The synthetic stress vault: 24 apps, 60 contracts, 250 unknowns. The lists are long, so the depth cap and the layout earn their keep."""
    import make_stress_vault
    vault = tmp_path / "stress"
    make_stress_vault.main(vault)
    build(vault)
    check(chrome_path, vault / "dashboard.html", "stress/24 apps")
