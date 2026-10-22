"""The data the dashboard's Library view draws (explorer/library_data.py), and that a read copy carries the files.

    python3 -m pytest -q tests/test_explorer_library.py

The Violation these guard against is a Leaky Narrative on the page: the rules about the register (what a Figma address
is, what `v1.0 (latest v1.1)` means, what counts as cited) live in library_data.py, so they are tested here against
vaults, not discovered in script. The browser side is test_explorer_library_browser.py.
"""
import io
import json
import shutil
import zipfile

import pytest
from conftest import MINI, REPO, edit, run
from sharing import git, make_vault

from vela import cli, publish
from vela.explorer import build, library_data
from vela.explorer.record import Keys
import session_files

BOOKING = REPO / "examples" / "unified-booking"
TEN = "| ID | Title | Owner | Date | Kind | Type | Relates to | Version | Stored | Location |\n|---|---|---|---|---|---|---|---|---|---|\n"
ROWS = [
    "| SRC-01 | Tidepay webhook API | @hl-booking-senior | 2026-07-28 | exists | spec | PTY-01 CON-007 | v2.3 (latest v2.4) | library/specs/tidepay.openapi.yaml | https://developers.example.com/tidepay/openapi.yaml |",
    "| SRC-02 | Booking events | @hl-booking-senior | 2026-11-03 | intends | spec | CON-002 | v0.4 | library/specs/events.asyncapi.yaml | |",
    "| SRC-03 | Booking screens | @hl-booking-senior | 2026-10-09 | exists | design | APP-booking | | library/designs/screens.pdf | https://www.figma.com/file/abc/screens |",
    "| SRC-04 | Opt-in flow | @hl-booking-senior | 2026-10-12 | exists | design | | | | https://www.figma.com/file/def/opt-in |",
    "| SRC-05 | Marine wiki | @hl-solution-lead | 2026-07-09 | exists | wiki | SRC-03 | | | https://acme.atlassian.net/wiki/spaces/M/pages/1 |",
    "| SRC-06 | Delivery board | @hl-solution-lead | 2026-07-09 | exists | tracker | | | | https://acme.atlassian.net/browse/HL |",
    "| SRC-07 | Procurement summary | @hl-solution-lead | 2026-07-09 | exists | document | PTY-02 | | | Procurement, local only |",
    "| SRC-08 | Staff survey | @hl-solution-lead | 2026-07-09 | exists | document | | | library/documents/survey.docx | |",
]


def booking_with(tmp_path, rows):
    """The booking example with its register replaced by `rows` (ten columns), and the files the rows keep."""
    vault = tmp_path / "booking"
    shutil.copytree(BOOKING, vault)
    page = (vault / "sources.md").read_text(encoding="utf-8")
    head, _ = page.split("| ID |", 1)
    (vault / "sources.md").write_text(head + TEN + "\n".join(rows) + "\n", encoding="utf-8")
    return vault


def extract(vault):
    loaded = cli.load_vault(vault)
    return library_data.extract(loaded, Keys(loaded))["rows"]


def by_id(rows):
    return {r["id"]: r for r in rows}


@pytest.fixture(scope="module")
def booking_rows(tmp_path_factory):
    return by_id(extract(booking_with(tmp_path_factory.mktemp("lib"), ROWS)))


def test_the_row_says_what_it_is_in_a_word_a_person_knows(booking_rows):
    got = {i: r["format"] for i, r in booking_rows.items()}
    assert got == {"SRC-01": "OpenAPI", "SRC-02": "AsyncAPI", "SRC-03": "Figma", "SRC-04": "Figma", "SRC-05": "Confluence",
                   "SRC-06": "Jira", "SRC-07": "Document", "SRC-08": "Word"}


def test_where_an_item_is_kept_decides_its_tag(booking_rows):
    got = {i: r["where"] for i, r in booking_rows.items()}
    assert got == {"SRC-01": "newer", "SRC-02": "vault", "SRC-03": "both", "SRC-04": "link", "SRC-05": "link", "SRC-06": "link",
                   "SRC-07": "listed", "SRC-08": "vault"}
    assert booking_rows["SRC-03"]["ext"] == "PDF" and booking_rows["SRC-08"]["ext"] == "Word"
    assert booking_rows["SRC-04"]["web"] and not booking_rows["SRC-07"]["web"]


def test_a_newer_version_is_told_not_fetched(booking_rows):
    spec = booking_rows["SRC-01"]
    assert (spec["version"], spec["newer"]) == ("v2.3", "v2.4")
    assert booking_rows["SRC-02"]["newer"] == ""


def test_relates_to_names_any_item_a_page_or_another_library_row(booking_rows):
    assert booking_rows["SRC-01"]["relates"] == ["PTY-01", "CON-007"]  # an outside party and a contract, by item key
    assert booking_rows["SRC-03"]["relates"] == ["APP-booking"]  # a page, by its key
    assert booking_rows["SRC-05"]["relates"] == ["lib:SRC-03"]  # another Library row
    assert booking_rows["SRC-04"]["relates"] == []


def test_a_relates_to_that_names_nothing_is_left_out_not_invented(tmp_path):
    rows = extract(booking_with(tmp_path, ["| SRC-01 | X | @a | 2026-07-28 | exists | link | NOPE-9 CON-001 | | | https://x.example.com |"]))
    assert rows[0]["relates"] == ["CON-001"]


def test_cited_by_is_counted_from_the_pages_never_typed(tmp_path):
    rows = by_id(extract(booking_with(tmp_path, [
        "| SRC-02 | Vendor contract | @a | 2026-07-09 | exists | document | | | | Procurement |",
        "| SRC-99 | Nobody cites this | @a | 2026-07-09 | exists | document | | | | Somewhere |"])))
    cited = rows["SRC-02"]["citedBy"]
    assert cited and len(cited) == len(set(cited))
    assert rows["SRC-99"]["citedBy"] == []
    text = (BOOKING / "03-context-and-scope.md").read_text(encoding="utf-8")
    assert "SRC-02" in text and "PTY-02" in cited  # the mention sits inside the PTY-02 section, so the item is named, not the page


def test_sessions_and_the_register_itself_do_not_count_as_citing(tmp_path):
    vault = booking_with(tmp_path, ["| SRC-02 | Vendor contract | @a | 2026-07-09 | exists | document | | | | Procurement |"])
    session_files.write_record(vault, "2026-11-20-mentions", "---\nid: x\ntype: session\ntitle: x\n---\n\nTouched SRC-02.\n")
    assert "page:2026-11-20-mentions" not in extract(vault)[0]["citedBy"]
    assert "sources" not in extract(vault)[0]["citedBy"]


def test_a_register_written_before_the_new_columns_reads_as_documents(tmp_path):
    vault = tmp_path / "mini"
    shutil.copytree(MINI, vault)
    rows = extract(vault)
    assert [(r["id"], r["type"], r["format"], r["where"], r["stored"]) for r in rows] == [("SRC-01", "document", "Document", "listed", "")]
    assert rows[0]["citedBy"]  # the stock app cites it


def test_the_library_section_is_listed_only_when_the_register_has_rows(tmp_path):
    full = build.extract(cli.load_vault(booking_with(tmp_path, ROWS)), BOOKING, "2026-10-21", pins_path=None)
    ids = [s["id"] for s in full["sections"]]
    assert ids[-1] == "library" and full["sections"][-1]["label"] == "Library"
    empty = tmp_path / "empty"
    shutil.copytree(MINI, empty)
    (empty / "sources.md").write_text("---\nid: sources\ntype: sources\ntitle: Library\nauthored: authored\n---\n\n# Library\n\n" + TEN, encoding="utf-8")
    data = build.extract(cli.load_vault(empty), empty, "2026-10-21", pins_path=None)
    assert data["library"]["rows"] == [] and "library" not in [s["id"] for s in data["sections"]]


def test_the_page_data_carries_the_rows_in_register_order(tmp_path):
    data = build.extract(cli.load_vault(booking_with(tmp_path, ROWS)), BOOKING, "2026-10-21", pins_path=None)
    assert [r["id"] for r in data["library"]["rows"]] == [f"SRC-0{n}" for n in range(1, 9)]
    json.dumps(data["library"])  # plain data the page can embed


# ------------------------------------------------------------------ a read copy carries the library's files

def test_a_read_copy_keeps_library_files_and_skips_none_of_them():
    files = {"sources.md": b"x", "library/specs/a.openapi.yaml": b"openapi: 3.0.0", "library/designs/b.pdf": b"%PDF\x00", ".vela/x": b"y"}
    assert set(publish.selected(files)) == {"sources.md", "library/specs/a.openapi.yaml", "library/designs/b.pdf"}


def library_vault(tmp_path, extra=None):
    vault = make_vault(tmp_path)
    (vault / "library" / "specs").mkdir(parents=True)
    (vault / "library" / "designs").mkdir()
    (vault / "library" / "specs" / "stock.openapi.yaml").write_text("openapi: 3.0.3\ninfo:\n  title: demo\n  version: v1.0\npaths: {}\n", encoding="utf-8")
    (vault / "library" / "designs" / "screens.pdf").write_bytes(b"%PDF-1.4\x00demo material\n")
    edit(vault / "sources.md", "| ID | Title | Owner | Date | Kind | Location |\n|---|---|---|---|---|---|\n| SRC-01 | Stock read API documentation | @stock-team | 2026-01-02 | exists | local only |",
         TEN + "| SRC-01 | Stock read API | @stock-team | 2026-01-02 | exists | spec | | v1.0 | library/specs/stock.openapi.yaml | |\n"
         "| SRC-02 | Screens | @stock-team | 2026-01-02 | exists | design | | | library/designs/screens.pdf | https://www.figma.com/file/a/b |")
    for name, text in (extra or {}).items():
        (vault / name).write_text(text, encoding="utf-8")
    git(vault, "add", "-A")
    git(vault, "commit", "-q", "-m", "library")
    return vault


def test_publish_copies_library_files_and_its_dashboard_opens_them(tmp_path):
    vault = library_vault(tmp_path)
    code, text = run("publish", "--vault", str(vault), "--out", str(tmp_path / "out.zip"), "--today", "2026-10-21")
    assert code == 0, text
    with zipfile.ZipFile(tmp_path / "out.zip") as z:
        names = {n.split("/", 1)[1] for n in z.namelist()}
        assert {"library/specs/stock.openapi.yaml", "library/designs/screens.pdf", "dashboard.html"} <= names
        top = z.namelist()[0].split("/")[0]
        page = z.read(f"{top}/dashboard.html").decode("utf-8")
    data = json.loads(page.split('id="data">', 1)[1].split("</script>", 1)[0])
    assert [r["stored"] for r in data["library"]["rows"]] == ["library/specs/stock.openapi.yaml", "library/designs/screens.pdf"]
    assert data["vault"] == "."  # the dashboard sits beside library/, so "Open the file" is the stored path as written


def test_secretscan_still_reads_a_text_library_file_and_leaves_a_binary_one(tmp_path):
    key = "AKIA" + "ABCDEFGHIJKLMNOP"
    vault = library_vault(tmp_path, {"library/specs/stock.openapi.yaml": f"openapi: 3.0.3\ninfo:\n  version: v1.0\nx-key: {key}\n"})
    code, text = run("publish", "--vault", str(vault), "--out", str(tmp_path / "out.zip"), "--today", "2026-10-21")
    assert code == 2 and "library/specs/stock.openapi.yaml" in text and key not in text
    (tmp_path / "clean").mkdir()
    ok = library_vault(tmp_path / "clean")
    assert run("publish", "--vault", str(ok), "--out", str(tmp_path / "clean.zip"), "--today", "2026-10-21")[0] == 0  # the PDF's bytes are not scanned as text
