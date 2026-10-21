"""The Library view, driven in headless Chrome (assets/js/selftest-library.js).

    python3 -m pytest -q -m browser tests/test_explorer_library_browser.py

The page's own selftest groups the items, runs every filter and the search, opens a row in the right-hand panel, follows a
relates-to chip to the thing it names, finds the item listed back on that thing, and walks the rows with the keyboard. A
selftest that quietly skipped them would pass, so each named behavior must be present and ok, at a wide window and at
800 px. A vault whose register has no rows has no Library section, and the heron desk (no rows) proves the checks stop there.
"""
import html
import re
import shutil
import subprocess
import sys

from conftest import MINI, chrome_profile, run_chrome

import pytest
from test_explorer_browser import REPO, find_chrome
from test_explorer_library import ROWS, TEN, booking_with

HERON = REPO / "tests" / "sim" / "snapshots" / "heron-desk" / "after-design-2"

WANTED = [
    "library: 8 items group by what they are",
    "library: the group headings are",
    "library: every row has a type icon, a title, a meta line and a tag",
    "library: the tags say newer version out",
    "library: the meta line says the date in words",
    "library: the list says names, never register codes",
    "library: In the vault, Links and Cited by the plan each show exactly their items",
    "library: searching",
    "library: a search that matches nothing says so",
    "library: Clear filters brings every item back",
    "library: clicking",
    "library: the panel says where it is stored",
    "library: Open the file links to",
    "library: Open the original opens a web address",
    "library: what cites it lists",
    "library: Show what cites it brings the list into view",
    "library: the relates-to chip names",
    "library: the chip opens",
    "library: Tidepay",  # the thing it names lists the item back (named by title)
    "library: a Library entry on that panel opens the item again",
    "library: the down arrow moves from one row to the next",
    "library: every row is a button the keyboard reaches",
    "library: Escape returns the panel to the summary",
    "library: the top search finds",
    "library: the top search finds an item by its code",
]


def report(chrome, html_path, size):
    dom = run_chrome([str(chrome), "--headless=new", chrome_profile(), "--disable-gpu", "--no-sandbox", f"--window-size={size}", "--virtual-time-budget=90000", "--dump-dom",
                      f"file://{html_path}#selftest"], 300)[1]
    found = re.search(r'data-selftest="([^"]*)"', dom)
    assert found, f"the page produced no selftest report at {size}"
    return html.unescape(found.group(1)).split(" || ")


def build(tmp_path_factory, vault):
    cmd = [sys.executable, str(REPO / "plugin" / "scripts" / "vela"), "explore", "--selftest", str(vault), "--today", "2026-10-21", "--no-open"]
    assert subprocess.run(cmd, timeout=180, capture_output=True, text=True).returncode == 0
    return vault / "dashboard.html"


@pytest.fixture(scope="module")
def booking(tmp_path_factory):
    vault = booking_with(tmp_path_factory.mktemp("library"), ROWS)
    for name, text in (("specs/tidepay.openapi.yaml", "openapi: 3.0.3\ninfo:\n  version: v2.3\n"), ("specs/events.asyncapi.yaml", "asyncapi: 2.6.0\n"),
                       ("designs/screens.pdf", "%PDF-1.4 demo\n"), ("documents/survey.docx", "demo")):
        (vault / "library" / name).parent.mkdir(parents=True, exist_ok=True)
        (vault / "library" / name).write_text(text, encoding="utf-8")
    return build(tmp_path_factory, vault)


@pytest.fixture(scope="module")
def heron(tmp_path_factory):
    """The heron desk: a six-column register written before Type and Relates to existed, every row a document."""
    vault = tmp_path_factory.mktemp("heron") / "vault"
    shutil.copytree(HERON, vault)
    return build(tmp_path_factory, vault)


@pytest.fixture(scope="module")
def empty(tmp_path_factory):
    vault = tmp_path_factory.mktemp("empty") / "vault"
    shutil.copytree(MINI, vault)
    (vault / "sources.md").write_text("---\nid: sources\ntype: sources\ntitle: Library\nauthored: authored\n---\n\n# Library\n\n" + TEN, encoding="utf-8")
    return build(tmp_path_factory, vault)


def check(lines):
    failing = [x for x in lines if x.startswith("FAIL")]
    assert not failing, "\n".join(failing)
    assert lines[0].startswith("SELFTEST OK"), lines[0]
    mine = [x for x in lines if x.startswith("ok library:")]
    missing = [w for w in WANTED if not any(w in line for line in mine)]
    assert not missing, "selftest lines missing or not ok: " + "; ".join(missing)


@pytest.mark.browser
@pytest.mark.parametrize("size", ["1440,900", "800,900"])
def test_the_library_view_passes_its_selftest(booking, size):
    check(report(find_chrome(), booking, size))


@pytest.mark.browser
def test_a_register_written_before_the_new_columns_still_shows_as_documents(heron):
    lines = report(find_chrome(), heron, "1440,900")
    assert not [x for x in lines if x.startswith("FAIL")], "\n".join(x for x in lines if x.startswith("FAIL"))
    assert any(re.match(r"ok library: \d+ items group by what they are \(Documents \d+\)", x) for x in lines), "every row of the old register is a document"


@pytest.mark.browser
def test_a_vault_with_an_empty_register_has_no_library_section(empty):
    lines = report(find_chrome(), empty, "1440,900")  # the mini vault has no flows, so the other checks fail there; only the library's own are read
    assert not [x for x in lines if x.startswith("FAIL") and "library" in x.lower()], "\n".join(x for x in lines if "library" in x.lower())
    assert any(x.startswith("ok library: a register with no rows has no Library section") for x in lines)
