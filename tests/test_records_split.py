"""`vela records split`: moving a plan that holds whole session records over to stubs and private notes.

The Violation these tests guard is a Silent Fallback in the migration: a split that moves the files but leaves a
person's words on a committed page (a Dissent, a quoted receipt, an answered quote) reports success and leaves the
plan sharing what the rule says it never shares. Each strip is listed, so the lead sees what the split took out."""
import dataclasses
import json
import pathlib

import pytest

from conftest import run
from sharing import git, make_vault
from vela import cli, handoff, privaterecord, recordsplit
from vela.cli import ToolError
import session_files

SHOP = "05-building-blocks/shop-building-blocks.md"
UNKNOWNS = "11-unknowns-and-risks.md"
RECORD = "2026-01-10-shop-api"
ANSWER = "One till should sell everything."
ASKED_ROW = f"| Q-FIN-02@INI-900 | asked | capture: [[{RECORD}#^c01]] | @mini-lead | 2026-01-10 |"
ANSWERED_ROW = (f'| Q-DAT-03@INI-900 | answered | item: [[shop-building-blocks#CON-001 Sale API\\|CON-001]]; '
                f'source: "{ANSWER}" in [[{RECORD}]]; answer: one till | @mini-lead | 2026-01-10 |')


def tree_bytes(root):
    return {p.relative_to(root).as_posix(): p.read_bytes() for p in sorted(pathlib.Path(root).rglob("*"))
            if p.is_file() and ".git" not in p.relative_to(root).parts}


def full_records_vault(tmp_path):
    """The mini vault in git: whole records, a Dissent with words on CON-001, an asked and an answered ledger row."""
    vault = make_vault(tmp_path)
    page = vault / SHOP
    page.write_text(page.read_text(encoding="utf-8").replace(
        "- **Why:** The till needs one place to ask for a sale.\n\n| Case",
        "- **Why:** The till needs one place to ask for a sale.\n- **Dissent:** @raj, 2026-01-10: too slow\n\n| Case"),
        encoding="utf-8")
    ledger = vault / UNKNOWNS
    ledger.write_text(ledger.read_text(encoding="utf-8").rstrip("\n") + f"\n{ASKED_ROW}\n{ANSWERED_ROW}\n",
                      encoding="utf-8")
    (vault / ".vela").mkdir(exist_ok=True)
    (vault / ".vela" / "handle").write_text("mini-lead\n", encoding="utf-8")
    git(vault, "add", "-A")
    git(vault, "commit", "-q", "-m", "full records")
    return vault


def test_dry_run_changes_nothing_and_lists_what_it_strips(tmp_path):
    vault = full_records_vault(tmp_path)
    before = tree_bytes(vault)
    code, out = run("records", "split", "--vault", str(vault), "--today", "2026-10-22", "--json")
    data = json.loads(out)
    assert code == 3 and tree_bytes(vault) == before
    assert {s["what"] for s in data["stripped"]} == {"dissent", "answered quote"}
    assert data["records"] == ["2026-01-05-till-needs", RECORD]
    assert data["links"] == 1 and data["sources_added"] == ["SRC-002"] and data["split_date"] == "2026-10-22"
    assert {s["path"] for s in data["stripped"]} == {SHOP, UNKNOWNS}
    assert data["needs_lead"][0]["answer_with"] == "--apply"
    assert git(vault, "branch", "--show-current") == "main"


def test_apply_commits_stubs_and_rewritten_links_only(tmp_path):
    vault = full_records_vault(tmp_path)
    assert run("records", "split", "--apply", "--vault", str(vault), "--today", "2026-10-22")[0] == 0
    assert git(vault, "branch", "--show-current") == "records-split"
    shown = git(vault, "show", "--stat", "--format=", "HEAD")
    assert "sessions/private" not in shown and "sessions/2026-01-10-shop-api.md" in shown
    assert git(vault, "log", "-1", "--format=%s") == "Split session records: the notes stay on this machine"
    ledger = (vault / UNKNOWNS).read_text(encoding="utf-8")
    assert "#^c" not in ledger and f"capture: [[{RECORD}]] c01" in ledger
    page_text = (vault / SHOP).read_text(encoding="utf-8")
    assert "**Dissent:** @raj, 2026-01-10" in page_text and "too slow" not in page_text
    assert "records_split: 2026-10-22" in (vault / ".vela.yaml").read_text(encoding="utf-8")
    assert git(vault, "status", "--porcelain") == ""


def test_apply_moves_the_words_to_the_private_file_and_leaves_a_stub(tmp_path):
    vault = full_records_vault(tmp_path)
    whole = (vault / "sessions" / f"{RECORD}.md").read_text(encoding="utf-8")
    assert run("records", "split", "--apply", "--vault", str(vault), "--today", "2026-10-22")[0] == 0
    notes = session_files.record_text(vault, RECORD)
    assert ANSWER in notes and notes.endswith(whole.split("---\n", 2)[2])
    stub = session_files.stub_text(vault, RECORD)
    assert ANSWER not in stub
    meta = privaterecord.stub_meta(stub)
    assert privaterecord.parts(meta) == {1: privaterecord.fingerprint(notes)}
    assert run("records", "verify", RECORD, "--vault", str(vault))[0] == 0
    assert "sessions/private/" in (vault / ".gitignore").read_text(encoding="utf-8").split("\n")
    assert git(vault, "ls-files", "sessions/private") == ""


def test_apply_refuses_a_dirty_tree(tmp_path):
    vault = full_records_vault(tmp_path)
    (vault / "01-goals.md").write_text((vault / "01-goals.md").read_text(encoding="utf-8") + "\nedit\n",
                                       encoding="utf-8")
    code, out = run("records", "split", "--apply", "--vault", str(vault))
    assert code == 1 and "changes that aren't committed" in out
    assert git(vault, "branch", "--show-current") == "main"


def test_apply_says_what_history_still_holds(tmp_path):
    vault = full_records_vault(tmp_path)
    code, out = run("records", "split", "--apply", "--vault", str(vault), "--today", "2026-10-22")
    assert code == 0 and recordsplit.HISTORY_TELL in out
    assert "Once it's merged, I'll republish the read copy." in out


def test_the_for_lead_lines_hold_no_id_and_still_tell_the_history(tmp_path):
    vault = full_records_vault(tmp_path)
    code, out = run("records", "split", "--vault", str(vault), "--for-lead")
    assert code == 3 and "W720" not in out and "@raj" not in out
    code, out = run("records", "split", "--apply", "--vault", str(vault), "--today", "2026-10-22", "--for-lead")
    assert code == 0 and "still in this repository's history" in out and "W720" not in out


def test_a_second_split_has_nothing_to_do(tmp_path):
    vault = full_records_vault(tmp_path)
    assert run("records", "split", "--apply", "--vault", str(vault), "--today", "2026-10-22")[0] == 0
    code, out = run("records", "split", "--vault", str(vault), "--today", "2026-10-23", "--json")
    assert code == 0 and json.loads(out)["records"] == []


def test_split_date_covers_records_dated_ahead():
    assert recordsplit.split_date(["2026-11-19", "2026-08-12"], "2026-10-22") == "2026-11-20"
    assert recordsplit.split_date(["2026-08-12"], "2026-10-22") == "2026-10-22"
    assert recordsplit.split_date([], "2026-10-22") == "2026-10-22"


def test_answered_quote_points_at_a_first_hand_row(tmp_path):
    vault = full_records_vault(tmp_path)
    assert run("records", "split", "--apply", "--vault", str(vault), "--today", "2026-10-22")[0] == 0
    ledger_row = next(line for line in (vault / UNKNOWNS).read_text(encoding="utf-8").split("\n")
                      if line.startswith("| Q-DAT-03"))
    sources = (vault / "sources.md").read_text(encoding="utf-8")
    assert "source: SRC-002" in ledger_row and f"in [[{RECORD}]]" not in ledger_row and ANSWER not in ledger_row
    assert "answered" in ledger_row and "answer: one till" in ledger_row
    row = next(line for line in sources.split("\n") if line.startswith("| SRC-002"))
    assert "@mini-lead" in row and "exists" in row and row.rstrip().endswith("first-hand: @mini-lead |")


def test_a_first_hand_row_that_exists_is_reused():
    files = whole_files()
    files["sources.md"] += "| SRC-07 | Lead's own knowledge | @mini-lead | 2026-01-01 | exists | first-hand: @mini-lead |\n"
    report = recordsplit.plan(files, "@mini-lead", "2026-10-22")
    assert report.sources_added == []
    assert "source: SRC-07" in report.writes[UNKNOWNS]


def test_an_answered_quote_with_no_by_stops_the_split():
    files = whole_files()
    files[UNKNOWNS] = files[UNKNOWNS].replace(f"answer: one till | @mini-lead | 2026-01-10 |",
                                              "answer: one till |  | 2026-01-10 |")
    with pytest.raises(ValueError, match="Q-DAT-03"):
        recordsplit.plan(files, "@mini-lead", "2026-10-22")


def whole_files():
    """The pure planner's input: every committed text of the full-records vault, by path."""
    from conftest import MINI
    files = {p.relative_to(MINI).as_posix(): p.read_text(encoding="utf-8") for p in sorted(MINI.rglob("*"))
             if p.is_file() and p.suffix in (".md", ".yaml") or p.name == ".gitignore"}
    files[SHOP] = files[SHOP].replace("- **Why:** The till needs one place to ask for a sale.\n\n| Case",
                                      "- **Why:** The till needs one place to ask for a sale.\n"
                                      "- **Dissent:** @raj, 2026-01-10: too slow\n\n| Case")
    files[UNKNOWNS] = files[UNKNOWNS].rstrip("\n") + f"\n{ASKED_ROW}\n{ANSWERED_ROW}\n"
    return files


def test_a_receipt_with_someone_elses_words_loses_the_words_and_keeps_the_name():
    files = whole_files()
    files[SHOP] = files[SHOP].replace(
        "- **State:** decided\n- **Decision:** [[2026-01-10-shop-api]]",
        '- **State:** decided\n- **Decision:** [[2026-01-10-shop-api]] c01, @cto-ana: "Yes, ship it."')
    report = recordsplit.plan(files, "@mini-lead", "2026-10-22")
    kept = report.writes[SHOP]
    assert "- **Decision:** [[2026-01-10-shop-api]] c01, @cto-ana\n" in kept and "ship it" not in kept
    receipt = [s for s in report.stripped if s.what == "receipt"]
    assert [(s.path, s.words) for s in receipt] == [(SHOP, "Yes, ship it.")]
    assert files[SHOP].split("\n")[receipt[0].line - 1].startswith("- **Decision:**")


def test_the_leads_own_receipt_words_stay():
    files = whole_files()
    files[SHOP] = files[SHOP].replace(
        "- **State:** decided\n- **Decision:** [[2026-01-10-shop-api]]",
        '- **State:** decided\n- **Decision:** [[2026-01-10-shop-api]] c01, @mini-lead: "Yes."')
    report = recordsplit.plan(files, "mini-lead", "2026-10-22")
    assert '@mini-lead: "Yes."' in report.writes[SHOP]
    assert not [s for s in report.stripped if s.what == "receipt"]


def test_an_unknown_lead_strips_every_receipt_words():
    files = whole_files()
    files[SHOP] = files[SHOP].replace(
        "- **State:** decided\n- **Decision:** [[2026-01-10-shop-api]]",
        '- **State:** decided\n- **Decision:** [[2026-01-10-shop-api]] c01, @mini-lead: "Yes."')
    report = recordsplit.plan(files, "", "2026-10-22")
    assert '"Yes."' not in report.writes[SHOP]


def test_the_leads_own_dissent_words_stay_and_a_dissent_without_words_is_untouched():
    files = whole_files()
    files[SHOP] = files[SHOP].replace("@raj, 2026-01-10: too slow", "@mini-lead, 2026-01-10: too slow")
    report = recordsplit.plan(files, "@mini-lead", "2026-10-22")
    assert SHOP not in report.writes  # nothing on the page was anyone else's words
    files[SHOP] = files[SHOP].replace("@mini-lead, 2026-01-10: too slow", "@raj, 2026-01-10")
    assert [s.what for s in recordsplit.plan(files, "@mini-lead", "2026-10-22").stripped] == ["answered quote"]


def test_plan_writes_a_stub_and_private_file_per_record_and_counts_links():
    report = recordsplit.plan(whole_files(), "@mini-lead", "2026-10-22")
    assert report.records == ["2026-01-05-till-needs", RECORD]
    for record_id in report.records:
        assert privaterecord.stub_meta(report.writes[privaterecord.stub_path(record_id)])["status"] == "closed"
        assert report.writes[privaterecord.private_path(record_id)].startswith("---\n")
    assert report.links == 1 and report.split_date == "2026-10-22"
    assert ".gitignore" not in report.writes  # the fixture's already holds the line
    assert set(report.writes) - {privaterecord.private_path(r) for r in report.records} >= {
        UNKNOWNS, SHOP, "sources.md", ".vela.yaml"}
    files = whole_files()
    files[".gitignore"] = "*.tmp\n"
    assert recordsplit.plan(files, "@mini-lead", "2026-10-22").writes[".gitignore"] == "*.tmp\nsessions/private/\n"


def test_plan_refuses_a_record_whose_notes_already_exist():
    files = whole_files()
    files[privaterecord.private_path(RECORD)] = "---\nid: x\npart: 1\n---\n"
    with pytest.raises(ValueError, match=RECORD):
        recordsplit.plan(files, "@mini-lead", "2026-10-22")


def test_with_records_split_adds_or_replaces_one_line_and_keeps_comments():
    text = "initiative: INI-900  # the id\ntitle: Mini\n# a note\n"
    added = recordsplit.with_records_split(text, "2026-10-22")
    assert added == text + "records_split: 2026-10-22\n"
    assert recordsplit.with_records_split(added, "2026-11-01") == text + "records_split: 2026-11-01\n"
    assert recordsplit.with_records_split("title: x", "2026-10-22") == "title: x\nrecords_split: 2026-10-22\n"


def test_with_ignore_line_adds_once():
    assert recordsplit.with_ignore_line("") == "sessions/private/\n"
    assert recordsplit.with_ignore_line("a\n") == "a\nsessions/private/\n"
    assert recordsplit.with_ignore_line("a") == "a\nsessions/private/\n"
    assert recordsplit.with_ignore_line("sessions/private/\n") == "sessions/private/\n"


MANIFEST = ("| ID | Kind | Page | State | Hash |\n|---|---|---|---|---|\n"
            "| APP-shop | app | p.md | decided | aaaaaaaaaaaa |\n| CON-001 | provides | p.md | decided | bbbbbbbbbbbb |\n"
            "| CON-002 | provides | p.md | decided | cccccccccccc |\n")


def test_updated_manifest_moves_a_hash_only_when_the_split_was_the_only_change():
    before = {"APP-shop": "aaaaaaaaaaaa", "CON-001": "bbbbbbbbbbbb", "CON-002": "111111111111"}
    after = {"APP-shop": "aaaaaaaaaaaa", "CON-001": "dddddddddddd", "CON-002": "222222222222"}
    moved, ids = recordsplit.updated_manifest(MANIFEST, before, after)
    assert ids == ["CON-001"]
    assert "| CON-001 | provides | p.md | decided | dddddddddddd |" in moved
    assert "| APP-shop | app | p.md | decided | aaaaaaaaaaaa |" in moved
    assert "| CON-002 | provides | p.md | decided | cccccccccccc |" in moved  # changed by someone since: left to verify
    assert moved.count("\n") == MANIFEST.count("\n")


def test_handoff_hash_moves_only_when_the_split_was_the_only_change(tmp_path):
    vault = full_records_vault(tmp_path)
    loaded = cli.load_vault(vault)
    app = loaded.by_id["APP-shop"][0]
    entries = handoff.handoff_list(loaded, app)
    assert any(e.id == "CON-001" for e in entries)
    # every row but CON-001 is made to differ from the vault, as if changed since the senior accepted it
    rows = [e if e.id == "CON-001" else dataclasses.replace(e, hash="0" * 12) for e in entries]
    manifest = vault / "handoffs" / "APP-shop.md"
    manifest.parent.mkdir()
    manifest.write_text(handoff.write("APP-shop", rows, "abc1234", "2026-01-20", title="Shop"), encoding="utf-8")
    git(vault, "add", "-A")
    git(vault, "commit", "-q", "-m", "handoff")
    code, out = run("records", "split", "--apply", "--vault", str(vault), "--today", "2026-10-22", "--json")
    assert code == 0 and json.loads(out)["handoff_rows"] == ["handoffs/APP-shop.md: CON-001"]
    _, new_rows = handoff.read(manifest.read_text(encoding="utf-8"))
    old_hash = {e.id: e.hash for e in entries}
    after = cli.load_vault(vault)
    now = {e.id: e.hash for e in handoff.handoff_list(after, after.by_id["APP-shop"][0])}
    got = {e.id: e.hash for e in new_rows}
    assert got["CON-001"] == now["CON-001"] != old_hash["CON-001"]
    assert all(got[i] == "0" * 12 for i in got if i != "CON-001")
    assert "handoffs/APP-shop.md" in git(vault, "show", "--name-only", "--format=", "HEAD")


def test_load_config_reads_a_real_records_split_date(tmp_path):
    root = tmp_path / "v"
    root.mkdir()
    for value, good in (("2026-10-22", True), ('"2026-10-22"', True), ("soon", False), ("2026-13-40", False)):
        (root / ".vela.yaml").write_text(f"initiative: INI-900\ntitle: T\nrecords_split: {value}\n", encoding="utf-8")
        if good:
            assert cli.load_config(root)["records_split"] == "2026-10-22"
        else:
            with pytest.raises(ToolError, match="records_split.*such as 2026-10-22"):
                cli.load_config(root)
    (root / ".vela.yaml").write_text("initiative: INI-900\ntitle: T\n", encoding="utf-8")
    assert "records_split" not in cli.load_config(root)


def test_the_guard_names_the_split_as_the_fix_for_a_missing_ignore_line():
    from vela import guard
    assert "vela records split" in guard.SESSION_PRIVATE.fix


def test_the_first_hand_row_lands_on_sources_text_the_page_loop_already_changed():
    files = whole_files()
    files["sources.md"] += f"\nSee [[{RECORD}#^c07]] for how it came up.\n"
    report = recordsplit.plan(files, "@mini-lead", "2026-10-22")
    text = report.writes["sources.md"]
    assert f"[[{RECORD}]] c07" in text and "#^c07" not in text
    assert "| SRC-002 |" in text and report.links == 2


def test_a_line_the_split_cannot_read_is_listed_without_its_words_and_stops_apply(tmp_path):
    vault = full_records_vault(tmp_path)
    page = vault / SHOP
    page.write_text(page.read_text(encoding="utf-8").replace(
        "- **Dissent:** @raj, 2026-01-10: too slow", "- **Dissent:** Raj thinks it is slow"), encoding="utf-8")
    git(vault, "commit", "-qam", "odd dissent")
    code, out = run("records", "split", "--vault", str(vault), "--today", "2026-10-22", "--json")
    data = json.loads(out)
    assert code == 1 and [(i["path"], i["what"]) for i in data["left"]] == [(SHOP, "dissent")]
    assert "thinks" not in out
    before = tree_bytes(vault)
    code, out = run("records", "split", "--apply", "--vault", str(vault), "--today", "2026-10-22")
    assert code == 1 and "Fix them by hand" in out and "thinks" not in out
    assert git(vault, "branch", "--show-current") == "main" and tree_bytes(vault) == before


def test_a_failure_after_the_branch_is_made_puts_everything_back(tmp_path, monkeypatch):
    vault = full_records_vault(tmp_path)

    def explode(root):
        raise ToolError("the vault would not load")
    monkeypatch.setattr(cli, "load_vault", explode)
    (vault / "handoffs").mkdir()
    (vault / "handoffs" / "APP-shop.md").write_text(
        handoff.write("APP-shop", [handoff.Entry("APP-shop", "app", SHOP, "decided", "0" * 12)], "abc", "2026-01-20"),
        encoding="utf-8")
    git(vault, "add", "-A")
    git(vault, "commit", "-q", "-m", "handoff")
    before = tree_bytes(vault)
    code, out = run("records", "split", "--apply", "--vault", str(vault), "--today", "2026-10-22")
    assert code == 2 and "would not load" in out and "put the plan back" in out
    assert git(vault, "branch", "--show-current") == "main" and "records-split" not in git(vault, "branch")
    assert tree_bytes(vault) == before and git(vault, "status", "--porcelain") == ""
    assert not (vault / "sessions" / "private").exists()


def test_the_dry_run_never_asks_gh_or_writes_the_handle(tmp_path, monkeypatch):
    from vela.edge import sessiongit
    vault = full_records_vault(tmp_path)
    (vault / ".vela" / "handle").unlink()

    def no_gh(*args, **kwargs):
        raise AssertionError("the dry run called gh")
    monkeypatch.setattr(sessiongit, "gh", no_gh)
    code, out = run("records", "split", "--vault", str(vault), "--today", "2026-10-22", "--json")
    assert code == 3 and not (vault / ".vela" / "handle").exists()
    assert any("handle" in line for line in json.loads(out)["lines"])


def test_apply_refuses_when_no_handle_is_cached_so_the_leads_words_are_kept(tmp_path):
    vault = full_records_vault(tmp_path)
    (vault / ".vela" / "handle").unlink()
    git(vault, "commit", "-qam", "no cached handle")
    before = tree_bytes(vault)
    code, out = run("records", "split", "--apply", "--vault", str(vault), "--today", "2026-10-22")
    assert code == 1 and "Run vela whoami first, so I keep your own words" in out
    assert git(vault, "branch", "--show-current") == "main" and tree_bytes(vault) == before
    code, out = run("records", "split", "--apply", "--vault", str(vault), "--today", "2026-10-22", "--for-lead")
    assert code == 1 and "whoami" not in out and "find out first" in out
