"""planner export jira-csv: one row per epic, export only, nothing read back."""
import csv
import io
import shutil

from conftest import REPO, edit, run
from planner import export

FIXTURE = REPO / "examples" / "unified-booking"


def exported(tmp_path, *extra, vault=None):
    if vault is None:
        vault = tmp_path / "ub"
        shutil.copytree(FIXTURE, vault)
    out = tmp_path / "epics.csv"
    code, text = run("export", "jira-csv", "--vault", str(vault), "--out", str(out), *extra)
    rows = list(csv.reader(out.open(encoding="utf-8", newline=""))) if out.exists() else []
    return code, text, rows


def test_one_row_per_epic_with_the_five_columns(tmp_path):
    code, text, rows = exported(tmp_path, "--repo-url", "git@github.com:harbourline/unified-booking.git", "--commit", "3f9c2a1")
    assert code == 0, text
    assert text == f"planner export: wrote 9 epics to {tmp_path / 'epics.csv'}.\n"
    assert rows[0] == ["Summary", "Description", "Epic Name", "Owner team", "Vault link"]
    assert [r[2] for r in rows[1:]] == [f"EPC-0{n}" for n in range(31, 40)]
    summary, description, name, owner, link = rows[1]
    assert (summary, name, owner) == ("Booking holds and confirms crossings", "EPC-031", "'@harbourline/booking-team")
    assert link == "https://github.com/harbourline/unified-booking/blob/3f9c2a1/13-epics/EPC-031-holds-and-confirms.md"
    assert description.startswith("Booking becomes the one place that decides whether a crossing is held")
    assert "FERRYMASTER stays the ledger of record (ADR-0002), so Booking" in description
    assert "\n\nAcceptance criteria:\n1. A channel that asks to hold a seat through CON-001" in description
    assert description.endswith("7. No request or response on CON-001 or CON-007 carries card data. [security] [data]")
    assert "[[" not in description and "**Owning team:**" not in description and "**Decision:**" not in description


def test_without_a_repository_the_link_is_the_vault_path_and_it_says_so(tmp_path):
    code, text, rows = exported(tmp_path)
    assert code == 0
    assert rows[1][4] == "13-epics/EPC-031-holds-and-confirms.md"
    assert "Vault link holds each epic's path in the vault" in text


def test_epics_not_decided_are_exported_and_named(tmp_path):
    vault = tmp_path / "ub"
    shutil.copytree(FIXTURE, vault)
    edit(vault / "13-epics" / "EPC-033-website-to-booking.md", "state: decided", "state: reopened")
    code, text, rows = exported(tmp_path, vault=vault)
    assert code == 0 and len(rows) == 10
    assert "Not decided yet: EPC-033 (reopened)." in text


def test_struck_criteria_and_commas_and_quotes_survive(tmp_path):
    vault = tmp_path / "ub"
    shutil.copytree(FIXTURE, vault)
    path = vault / "13-epics" / "EPC-031-holds-and-confirms.md"
    edit(path, "5. Two channels asking", '5. ~~Dropped, "for now"~~\n6. Two "channels", asking')
    _, _, rows = exported(tmp_path, vault=vault)
    description = rows[1][1]
    assert "Dropped" not in description
    assert '5. Two "channels", asking about the same booking reference' in description


def test_an_empty_vault_writes_the_header_only(tmp_path):
    vault = tmp_path / "vault"
    shutil.copytree(REPO / "template", vault)
    code, text, rows = exported(tmp_path, vault=vault)
    assert code == 0 and rows == [list(export.COLUMNS)]


def test_export_never_writes_into_the_vault(tmp_path):
    vault = tmp_path / "ub"
    shutil.copytree(FIXTURE, vault)
    before = {p: p.read_bytes() for p in vault.rglob("*") if p.is_file()}
    exported(tmp_path, vault=vault)
    assert {p: p.read_bytes() for p in vault.rglob("*") if p.is_file()} == before


def test_remote_urls_become_web_urls():
    assert export.web_url("git@github.com:org/repo.git") == "https://github.com/org/repo"
    assert export.web_url("https://github.com/org/repo.git") == "https://github.com/org/repo"
    assert export.web_url("https://gitlab.example.com/a/b/") == "https://gitlab.example.com/a/b"
    assert export.web_url("") == "" and export.web_url("/local/path") == ""


def test_plain_turns_links_into_labels():
    assert export.plain("see [[ADR-0002-x|ADR-0002]] and [[booking-building-blocks#CON-001 Booking API]]") == \
        "see ADR-0002 and CON-001 Booking API"
    assert export.plain("[[a\\|B]]") == "B"


def test_export_needs_a_format_and_an_out_file(tmp_path):
    assert run("export")[0] == 2
    assert run("export", "jira-csv")[0] == 2


def test_cells_that_start_like_a_formula_are_not_read_as_one():
    table = [(f"{lead}SUM(A1)", f"{lead}x", "EPC-001", "@team", f"{lead}y") for lead in "=+-@\t\r"]
    cells = [c for row in csv.reader(io.StringIO(export.to_csv(table), newline="")) for c in row][5:]
    guarded = [c for i, c in enumerate(cells) if i % 5 != 2]
    assert guarded and all(c.startswith("'") for c in guarded)
    assert [c for c in cells if c in ("EPC-001",)] and "'" not in export.to_csv([("Plain = fine", "a-b", "EPC-001", "", "https://x/y")])


def test_a_formula_shaped_epic_title_is_defused_in_the_file(tmp_path):
    vault = tmp_path / "ub"
    shutil.copytree(FIXTURE, vault)
    edit(vault / "13-epics" / "EPC-031-holds-and-confirms.md", "title: Booking holds and confirms crossings", 'title: "=HYPERLINK(\\"http://evil\\")"')
    _, _, rows = exported(tmp_path, vault=vault)
    assert rows[1][0].startswith("'=HYPERLINK")
