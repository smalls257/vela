"""The onboarding mode in a real browser, as a person meets it: the route, the lead's tuning, a person's own path, and who
the page takes the reader to be. (The page's own selftest, which walks every link and item, is in
test_explorer_onboard_selftest.py.)

    python3 -m pytest -q -m browser tests/test_explorer_onboard_browser.py

The Violation these guard against is a Distributed Monolith between the shared page and one person's page, and a Leaky
Narrative in the lead's note: the shared page carries nobody's path, and the note is shown as written, never as markup.
"""
import html
import re
import shutil
import subprocess
import sys

from conftest import chrome_profile, run_chrome

import pytest
from test_explorer_browser import REPO, chrome_path  # noqa: F401  (chrome_path is a fixture)

BOOKING = REPO / "examples" / "unified-booking"
VELA = [sys.executable, str(REPO / "plugin" / "scripts" / "vela")]
TODAY = "2026-11-20"
MODULES = re.compile(r'class="onb-mod[^"]*" data-module="([^"]+)"')
HEADING = re.compile(r'<aside class="onb-path"[^>]*><h2>([^<]+)</h2>')


def vela(*argv):
    done = subprocess.run([*VELA, *argv], timeout=180, capture_output=True, text=True)
    assert done.returncode == 0, done.stdout + done.stderr


def dom(chrome_path, page, hash_):  # noqa: F811
    cmd = [str(chrome_path), "--headless=new", chrome_profile(), "--disable-gpu", "--no-sandbox", "--window-size=1600,1000", "--virtual-time-budget=20000", "--dump-dom", f"file://{page}#{hash_}"]
    return run_chrome(cmd, 180)[1]


@pytest.fixture
def vault(tmp_path):
    root = tmp_path / "vault"
    shutil.copytree(BOOKING, root)
    (root / ".vela").mkdir(exist_ok=True)
    (root / ".vela" / "handle").write_text("ana\n", encoding="utf-8")
    return root


@pytest.mark.browser
def test_the_route_opens_the_path_at_the_named_part_and_the_sidebar_has_the_door(vault, chrome_path):  # noqa: F811
    vela("explore", str(vault), "--today", TODAY)
    out = dom(chrome_path, vault / "dashboard.html", "onboard=eng&m=contracts&still")
    assert 'data-role="eng"' in out and re.search(r'class="onb-mod on" data-module="contracts"', out) and 'aria-current="step"' in out
    assert MODULES.findall(out) == ["goal", "approach", "standing", "fit@eng", "people@eng", "handoff", "contracts", "journeys", "blocked"]
    assert "Get up to speed" in out and 'side-onboard' in out and 'Viewing as' in out


@pytest.mark.browser
def test_the_lead_tunes_the_path_and_the_note_is_shown_as_written_never_as_markup(vault, chrome_path):  # noqa: F811
    (vault / "ONBOARDING.md").write_text("## Engineering\n- Stress: Journeys\n- Play down: Handoff\n- Hide: Contracts\n- Note: Read <b>the contract</b> & the pilot plan first.\n", encoding="utf-8")
    vela("explore", str(vault), "--today", TODAY)
    out = dom(chrome_path, vault / "dashboard.html", "onboard=eng&still")
    assert MODULES.findall(out)[5:] == ["journeys", "blocked", "handoff"]
    assert "From the lead: " in out and "Read &lt;b&gt;the contract&lt;/b&gt; &amp; the pilot plan first." in out
    assert "<b>the contract</b>" not in out


@pytest.mark.browser
def test_a_persons_own_path_is_what_their_page_shows_and_the_shared_page_does_not(vault, chrome_path):  # noqa: F811
    vela("onboard", "path", "set", "--vault", str(vault), "--today", TODAY, "--role", "product", "--modules", "Goal, Slices, Journeys", "--diagrams", "yes", "--depth", "gist")
    vela("explore", str(vault), "--today", TODAY)
    shared = dom(chrome_path, vault / "dashboard.html", "onboard=product&still")
    assert HEADING.search(shared).group(1) == "The standard path" and '"mine":null' in shared and '"me":null' in shared
    assert '"handle":"ana"' not in shared and '"me":{' not in shared, "the shared page carries nobody's handle, not even the builder's (D.me exists only on a --person page)"
    own = dom(chrome_path, vault / ".vela" / "onboard" / "ana.html", "onboard=product&still")
    assert MODULES.findall(own) == ["goal", "slices", "journeys"] and HEADING.search(own).group(1) == "Your path"


@pytest.mark.browser
def test_the_door_opens_as_the_readers_role_the_leads_record_first_then_their_choice_then_the_door_they_picked(vault, chrome_path):  # noqa: F811
    vela("whoami", "--vault", str(vault), "--role", "qa")
    vela("explore", str(vault), "--person", "ana", "--today", TODAY)
    page = vault / ".vela" / "onboard" / "ana.html"
    assert 'data-role="qa"' in dom(chrome_path, page, "onboard&still"), "their own choice"
    config = vault / ".vela.yaml"
    config.write_text(config.read_text(encoding="utf-8").rstrip("\n") + "\nroles:\n  '@ana': mgr\n", encoding="utf-8")
    vela("explore", str(vault), "--person", "ana", "--today", TODAY)
    assert 'data-role="mgr"' in dom(chrome_path, page, "onboard&still"), "the lead's record wins over their choice"
    vela("explore", str(vault), "--today", TODAY)
    vela("explore", str(vault), "--today", TODAY)
    shared = dom(chrome_path, vault / "dashboard.html", "onboard&still")
    assert 'data-role="exec"' in shared, "a reader with no handle and no door picked gets exec; the door's own order is held by the selftest"


def needs_you(out):
    """The text of the Needs you block on a role overview, or None when the page has none."""
    found = re.search(r'<section class="needs-you[^"]*" id="needs-you"[^>]*>(.*?)</section>', out, re.S)
    return re.sub(r"<[^>]+>", "", found.group(1)) if found else None


@pytest.mark.browser
def test_needs_you_on_the_shared_page_comes_from_the_role_door_and_survives_a_reload(vault, chrome_path, tmp_path):  # noqa: F811
    """Before any choice nobody is viewing, so the overview cannot say what needs them; opening #onboard=qa makes the QA door
    the viewer, and a later visit to the overview in the same browser profile is the QA door's and says what needs it (the role is
    remembered). The lines themselves are held by the page's own selftest."""
    vela("explore", str(vault), "--today", TODAY)
    page, profile = vault / "dashboard.html", tmp_path / "profile"

    def load(hash_):
        cmd = [str(chrome_path), "--headless=new", "--disable-gpu", "--no-sandbox", f"--user-data-dir={profile}", "--window-size=1600,1000", "--virtual-time-budget=20000", "--dump-dom", f"file://{page}#{hash_}"]
        return run_chrome(cmd, 180)[1]
    before = needs_you(load("overview&still"))
    assert before and "Nothing in the plan says who the lead is" in before, "no handle and no door picked: the block does not pretend to know who is viewing"
    load("onboard=qa&still")  # choosing the QA door by its route
    after = load("overview&still")
    assert 'data-role="qa"' in after, "after choosing QA, in a new load of the page, the overview is QA's"
    assert needs_you(after) and "Nothing in the plan says who" not in needs_you(after) and "Pick who is viewing" not in needs_you(after), "and the block knows who is viewing"
    assert 'data-role="qa"' in load("overview&still"), "and it stays"


@pytest.mark.browser
def test_a_persons_page_opens_on_their_paths_role_and_depth_saved_on_the_shared_page_does_not_override_it(vault, chrome_path, tmp_path):  # noqa: F811
    """The Violation is a Distributed Monolith between the shared copy and one person's page: both are in the same browser, and
    a depth or diagram choice saved on the shared copy must not change the path the person's own page was built with. Their
    recorded role (qa) also differs from their path's role (product): the page opens on the path."""
    vela("whoami", "--vault", str(vault), "--role", "qa")
    vela("onboard", "path", "set", "--vault", str(vault), "--today", TODAY, "--role", "product", "--modules", "Goal, Slices, Journeys", "--diagrams", "yes", "--depth", "gist")
    vela("explore", str(vault), "--today", TODAY)
    vault_id = re.search(r'"vaultId":\s*"([^"]+)"', (vault / "dashboard.html").read_text(encoding="utf-8")).group(1)
    profile = tmp_path / "profile"
    seed = tmp_path / "seed.html"
    seed.write_text(f"<script>localStorage.setItem('onboard:{vault_id}:reader:depth','everything');localStorage.setItem('onboard:{vault_id}:reader:shape','cards');</script>", encoding="utf-8")

    def load(page, hash_):
        cmd = [str(chrome_path), "--headless=new", "--disable-gpu", "--no-sandbox", f"--user-data-dir={profile}", "--window-size=1600,1000", "--virtual-time-budget=20000", "--dump-dom", f"file://{page}#{hash_}"]
        return run_chrome(cmd, 180)[1]
    load(seed, "")
    own = load(vault / ".vela" / "onboard" / "ana.html", "onboard&still")
    assert 'data-role="product"' in own, "their path's role, not the role they recorded"
    assert re.search(r'aria-checked="true"[^>]*>Just the gist<', own), "the path's depth wins over the depth saved on the shared copy"
    assert "ob-board" in own, "and its diagrams"


@pytest.mark.browser
def test_an_arrow_that_only_opens_a_section_is_named_for_the_section_not_for_the_item(vault, chrome_path):  # noqa: F811
    vela("explore", str(vault), "--today", TODAY)
    out = dom(chrome_path, vault / "dashboard.html", "onboard=eng&m=people%40eng&still")
    links = re.findall(r'<a class="ob-open" href="([^"]+)"[^>]*aria-label="([^"]+)"', out)
    assert links, "the people part lists people, each with an arrow"
    assert ("#asks", "Open Who to ask") in links
    for href, label in links:
        assert label.endswith(" in its own view") == ("open=" in href), (href, label)


@pytest.mark.browser
@pytest.mark.parametrize("route,section,viewing", [("role=qa&still", "qa", "QA"), ("onboard=eng&still", "eng", "Engineering")])
def test_both_routes_set_the_one_viewing_as_role_and_the_links_follow_it(vault, chrome_path, route, section, viewing):  # noqa: F811
    """The role door and the onboarding route are one setting: the sidebar's Viewing as menu shows it, and its two links name it."""
    vela("explore", str(vault), "--today", TODAY)
    out = dom(chrome_path, vault / "dashboard.html", route)
    assert re.search(r'data-dmenu="viewing-as".*?<small>Viewing as</small><b>' + viewing + "</b>", out, re.S)
    assert f"Overview for {viewing} ›" in out
    assert f"Get up to speed as {viewing} ›" in out
