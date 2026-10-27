"""vela export jira-csv: one row per epic, export only, nothing read back."""
import csv
import io
import shutil

from conftest import REPO, edit, run
from vela import export

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
    code, text, rows = exported(tmp_path, "--repo-url", "git@github.com:harborline/unified-booking.git", "--commit", "3f9c2a1")
    assert code == 0, text
    assert text == f"vela export: wrote 9 epics to {tmp_path / 'epics.csv'}.\n"
    assert rows[0] == ["Summary", "Description", "Epic Name", "Owner team", "Vault link"]
    assert [r[2] for r in rows[1:]] == [f"EPC-0{n}" for n in range(31, 40)]
    summary, description, name, owner, link = rows[1]
    assert (summary, name, owner) == ("Booking holds and confirms crossings", "EPC-031", "harborline/booking-team")
    assert link == "https://github.com/harborline/unified-booking/blob/3f9c2a1/13-epics/EPC-031-holds-and-confirms.md"
    assert description.startswith("Booking becomes the one place that decides whether a crossing is held")
    assert "FERRYMASTER stays the ledger of record (the ledger-of-record decision), so Booking" in description  # under "Who this is for"
    assert "Still open: nothing." in description
    assert "\n\nAcceptance criteria:\nAC1. A hold keeps the seat for ten minutes: A channel that asks to hold a seat through the Booking API" in description
    assert description.endswith("AC7. No card data on the API: No request or response on the Booking API or on Tidepay's payment outcome carries card data.")
    assert "Trace:" not in description  # the IDs stay in the vault; a tracker reader gets the plain sentence
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
    assert "(EPC-033) (reopened)." in text and "Not decided yet: " in text


def test_struck_criteria_and_commas_and_quotes_survive(tmp_path):
    vault = tmp_path / "ub"
    shutil.copytree(FIXTURE, vault)
    path = vault / "13-epics" / "EPC-031-holds-and-confirms.md"
    edit(path, "### Two channels see the same state\n\nTwo channels asking", '### ~~Dropped, "for now"~~\n\nOld.\n\n- Trace: AC9\n\n### Two "channels" see the same state\n\nTwo "channels", asking')
    _, _, rows = exported(tmp_path, vault=vault)
    description = rows[1][1]
    assert "Dropped" not in description and "AC9" not in description
    assert 'AC5. Two "channels" see the same state: Two "channels", asking about the same booking reference' in description


def test_an_empty_vault_writes_the_header_only(tmp_path):
    vault = tmp_path / "vault"
    shutil.copytree(REPO / "plugin" / "template", vault)
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


def test_owner_loses_its_at_sign_and_is_still_guarded(tmp_path):
    vault = tmp_path / "ub"
    shutil.copytree(FIXTURE, vault)
    edit(vault / "13-epics" / "EPC-031-holds-and-confirms.md", "owner: \"@harborline/booking-team\"", 'owner: "@=x"')
    _, _, rows = exported(tmp_path, vault=vault)
    assert rows[1][3] == "'=x"


def test_an_unwritable_out_is_a_tool_failure_not_a_traceback(tmp_path):
    for bad in (tmp_path, tmp_path / "missing" / "epics.csv", ""):
        code, text = run("export", "jira-csv", "--vault", str(FIXTURE), "--out", str(bad))
        assert code == 2 and "Cannot write" in text and "Traceback" not in text, text


def test_an_epic_that_does_not_parse_is_named_and_the_rest_still_export(tmp_path):
    vault = tmp_path / "ub"
    shutil.copytree(FIXTURE, vault)
    broken = vault / "13-epics" / "EPC-032-ledger-adapter.md"
    edit(broken, "id: EPC-032\n", "id: [EPC-032\n")
    code, text, rows = exported(tmp_path, vault=vault)
    assert code == 1 and len(rows) == 9
    assert "Not exported (fix with vela check): 13-epics/EPC-032-ledger-adapter.md" in text


def test_credentials_in_a_remote_never_reach_the_file(tmp_path):
    assert export.web_url("https://user:s3cr3tpw@github.com/o/r.git") == "https://github.com/o/r"
    _, _, rows = exported(tmp_path, "--repo-url", "https://user:s3cr3tpw@github.com/o/r.git", "--commit", "abc")
    assert rows[1][4].startswith("https://github.com/o/r/blob/abc/")
    assert "s3cr3tpw" not in (tmp_path / "epics.csv").read_text(encoding="utf-8")


def test_every_handle_in_a_multi_owner_field_loses_its_at():
    assert export.handles("@org/a, @org/b") == "org/a, org/b"
    assert export.handles(["@org/a", "@org/b"]) == "org/a, org/b"
    assert export.handles(None) == "" and export.handles(7) == ""


def test_an_epic_with_no_id_shows_its_path(tmp_path):
    vault = tmp_path / "ub"
    shutil.copytree(FIXTURE, vault)
    edit(vault / "13-epics" / "EPC-033-website-to-booking.md", "id: EPC-033\n", "id: \"\"\n")
    edit(vault / "13-epics" / "EPC-033-website-to-booking.md", "state: decided", "state: reopened")
    code, text, rows = exported(tmp_path, vault=vault)
    assert "13-epics/EPC-033-website-to-booking.md" in [r[2] for r in rows]
    assert "Not decided yet: 13-epics/EPC-033-website-to-booking.md (reopened)." in text


def test_ssh_remotes_and_remotes_with_whitespace(tmp_path):
    assert export.web_url("ssh://git@github.com/o/r.git") == "https://github.com/o/r"
    assert export.web_url("ssh://git@host.example:2222/o/r") == "https://host.example/o/r"
    assert export.web_url("https://host.example:8443/o/r.git") == "https://host.example:8443/o/r"
    assert export.web_url("https://github.com/o/my repo") == ""
    code, text, rows = exported(tmp_path, "--repo-url", "https://github.com/o/my repo", "--commit", "abc")
    assert rows[1][4] == "13-epics/EPC-031-holds-and-confirms.md"
    assert "couldn't make web links from this repository's address" in text


def test_link_paths_are_encoded(tmp_path):
    vault = tmp_path / "ub"
    shutil.copytree(FIXTURE, vault)
    (vault / "13-epics" / "EPC-031-holds-and-confirms.md").rename(vault / "13-epics" / "EPC-031 holds #1.md")
    _, _, rows = exported(tmp_path, "--repo-url", "https://github.com/o/r", "--commit", "abc", vault=vault)
    assert rows[1][4] == "https://github.com/o/r/blob/abc/13-epics/EPC-031%20holds%20%231.md"


def test_uncommitted_vault_warns_that_links_point_at_head(tmp_path):
    import subprocess
    vault = tmp_path / "ub"
    shutil.copytree(FIXTURE, vault)
    git = lambda *a: subprocess.run(["git", "-C", str(vault), "-c", "user.name=t", "-c", "user.email=t@t",
                                      "-c", "commit.gpgsign=false", *a], check=True, capture_output=True)
    git("init", "-q"); git("add", "-A"); git("commit", "-qm", "x")
    _, clean, _ = exported(tmp_path, "--repo-url", "https://github.com/o/r", vault=vault)
    assert "uncommitted changes" not in clean
    edit(vault / "13-epics" / "EPC-031-holds-and-confirms.md", "state: decided", "state: reopened")
    _, dirty, _ = exported(tmp_path, "--repo-url", "https://github.com/o/r", vault=vault)
    assert "uncommitted changes, so Vault links point at HEAD" in dirty
    _, pinned, _ = exported(tmp_path, "--repo-url", "https://github.com/o/r", "--commit", "abc", vault=vault)
    assert "uncommitted changes" not in pinned


def test_a_query_string_or_fragment_in_a_remote_never_reaches_a_link(tmp_path):
    assert export.web_url("https://github.com/o/r?token=abc") == "https://github.com/o/r"
    assert export.web_url("https://github.com/o/r.git#frag") == "https://github.com/o/r"
    _, _, rows = exported(tmp_path, "--repo-url", "https://github.com/o/r?token=sEcr3tq", "--commit", "abc")
    assert rows[1][4].startswith("https://github.com/o/r/blob/abc/")
    assert "sEcr3tq" not in (tmp_path / "epics.csv").read_text(encoding="utf-8")


def test_a_password_holding_an_at_sign_gives_no_link_and_no_leak(tmp_path):
    assert export.web_url("https://user:p@ss@github.com/o/r") == ""
    code, text, rows = exported(tmp_path, "--repo-url", "https://user:p@ssw0rdX@github.com/o/r", "--commit", "abc")
    assert rows[1][4] == "13-epics/EPC-031-holds-and-confirms.md"
    assert "couldn't make web links from this repository's address" in text
    assert "ssw0rdX" not in (tmp_path / "epics.csv").read_text(encoding="utf-8") + text


def test_a_null_byte_in_out_is_a_tool_failure(tmp_path):
    code, text = run("export", "jira-csv", "--vault", str(FIXTURE), "--out", str(tmp_path / "a\0b.csv"))
    assert code == 2 and "Cannot write" in text and "Traceback" not in text


def after_title(path, bullets):
    """Put page-level bullets straight under the page's # title."""
    lines = path.read_text(encoding="utf-8").split("\n")
    at = next(i for i, line in enumerate(lines) if line.startswith("# "))
    path.write_text("\n".join(lines[:at + 1] + ["", *bullets.rstrip("\n").split("\n")] + lines[at + 1:]), encoding="utf-8")


def test_an_epic_that_carries_an_override_and_an_unconfirmed_decision_says_so_at_the_end_of_its_description(tmp_path):
    vault = tmp_path / "ub"
    shutil.copytree(FIXTURE, vault)
    epic = vault / "13-epics" / "EPC-031-holds-and-confirms.md"
    after_title(epic, "- **Override:** E316, GATE-5 by @hl-solution-lead on 2026-11-20: the ask can wait\n"
                "- **Decided by:** @hl-solution-lead, on behalf of @harborline/booking-team\n")
    _, _, rows = exported(tmp_path, vault=vault)
    description = rows[1][1]
    assert description.endswith("\n\nOverride: E316, GATE-5 by @hl-solution-lead on 2026-11-20: the ask can wait\n"
                                "Decided by @hl-solution-lead on behalf of @harborline/booking-team")
    assert "Acceptance criteria:\nAC1." in description and description.index("Acceptance criteria") < description.index("Override:")
    assert "Override:" not in rows[2][1], "an epic without overrides is unchanged"


def test_a_confirmed_on_behalf_decision_names_the_confirmation_not_a_pending_one(tmp_path):
    vault = tmp_path / "ub"
    shutil.copytree(FIXTURE, vault)
    after_title(vault / "13-epics" / "EPC-031-holds-and-confirms.md",
                "- **Decided by:** @a, on behalf of @b\n- **Confirmed by:** @b on 2026-11-21\n")
    _, _, rows = exported(tmp_path, vault=vault)
    assert rows[1][1].endswith("Decided by @a on behalf of @b (confirmed by @b on 2026-11-21)")


def test_an_override_reason_that_looks_like_a_formula_is_still_guarded(tmp_path):
    vault = tmp_path / "ub"
    shutil.copytree(FIXTURE, vault)
    after_title(vault / "13-epics" / "EPC-031-holds-and-confirms.md", '- **Override:** E303 by @a on 2026-11-20: =HYPERLINK("http://evil")\n')
    _, _, rows = exported(tmp_path, vault=vault)
    assert rows[1][1].endswith('Override: E303 by @a on 2026-11-20: =HYPERLINK("http://evil")')
    guarded = export.to_csv([("s", "=cmd|x\nOverride: grill", "EPC-001", "", "l")])
    assert "'=cmd|x" in guarded
