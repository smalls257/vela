"""Closing the second part of a session (Task 12): what the other machine decided is asked about once, "Still yes?",
and the lead's yes in this part re-points the receipt here. The other machine's notes are not on this one, so this
part's Changes table holds no row for them."""
import json

from conftest import run
from vela import closegate, privaterecord
from sharing import git, make_vault, with_remote
import session_files

RID = "2026-10-20-grill-stock"
STOCK = "05-building-blocks/stock-building-blocks.md"
LEDGER_ROW = "| Q-DAT-01@APP-stock | not-applicable | reason: no personal data | @priya | 2026-10-01 |"
LEDGER = f"\n## Question ledger\n\n| Copy | State | Evidence | By | Date |\n|---|---|---|---|---|\n{LEDGER_ROW}\n"
OTHER_DECISION = f'- **Decision:** [[{RID}]] c01, @priya: "Yes, one till API for the web and the kiosks."'
THIS_YES = '- [thought] (@priya) "Yes, still one till API for everything." says yes → park ^c03'
BARE_OK = '- [thought] (@priya) "ok" → park ^c04'
SUMMARY = "In progress."


def part_two_notes(captures):
    lines = ["", "## Captures", "", *captures, ""]
    return privaterecord.new_private(RID, "Stock grill", "2026-10-20", 2).replace("\n## Captures\n", "\n".join(lines), 1)


def two_machine_session(tmp_path, captures=(THIS_YES,), ledger=False):
    """Part 1's notes (and the Changes row for the decision) stayed on the other machine; this is part 2."""
    vault = make_vault(tmp_path)
    if ledger:
        page = vault / STOCK
        page.write_text(page.read_text(encoding="utf-8").rstrip("\n") + "\n" + LEDGER, encoding="utf-8")
        git(vault, "add", STOCK)
        git(vault, "commit", "-q", "-m", "A ledger row")
    with_remote(tmp_path, vault)
    git(vault, "switch", "-q", "-c", f"session/{RID}")
    stub = privaterecord.render_stub({
        "id": RID, "type": "session", "title": "Stock grill", "date": "2026-10-20", "modes": ["grill"],
        "status": "open", "captures_sha256": {1: "a" * 64, 2: privaterecord.PENDING}})
    (vault / "sessions").mkdir(exist_ok=True)
    (vault / privaterecord.stub_path(RID)).write_text(stub, encoding="utf-8")
    session_files.ignore_private(vault)
    session_files.write_private(vault, RID, part_two_notes(captures))
    git(vault, "add", "sessions", ".gitignore")
    git(vault, "commit", "-q", "-m", f"Open session {RID}")
    assert run("close", "sync-main", "--vault", str(vault), "--today", "2026-10-20")[0] == 0
    (vault / ".vela").mkdir(exist_ok=True)
    (vault / ".vela" / "handle").write_text("priya\n", encoding="utf-8")
    page = vault / STOCK
    decided = f"- **State:** decided\n{OTHER_DECISION}\n- **Tested by:** the stock read test on both sides"
    page.write_text(page.read_text(encoding="utf-8").replace("- **State:** fact", decided, 1), encoding="utf-8")
    assert run("render", "--vault", str(vault))[0] == 0
    return vault


def gate(vault):
    code, out = run("close", "gate", "--vault", str(vault), "--json", "--today", "2026-10-20")
    return json.loads(out)["problems"]


def elsewhere(vault):
    return [p for p in gate(vault) if p["kind"] == closegate.ELSEWHERE]


def reconfirm(vault, *args):
    return run("close", "reconfirm", *args, "--vault", str(vault))


def text_of(vault, rel):
    return (vault / rel).read_text(encoding="utf-8")


def test_part_two_asks_once_about_the_other_machines_decisions(tmp_path):
    vault = two_machine_session(tmp_path)
    found = elsewhere(vault)
    assert len(found) == 1
    assert "decided on the other machine" in found[0]["plain"] and "Still yes?" in found[0]["plain"]
    assert "CON-" not in found[0]["plain"] and "CON-002" in found[0]["detail"]
    assert not [p for p in gate(vault) if p["kind"] == closegate.CONSENT]  # one question, not two


def test_part_one_never_asks(tmp_path):
    vault = two_machine_session(tmp_path)
    notes = (vault / privaterecord.private_path(RID))
    notes.write_text(notes.read_text(encoding="utf-8").replace("part: 2", "part: 1"), encoding="utf-8")
    assert not elsewhere(vault)
    assert [p for p in gate(vault) if p["kind"] == closegate.CONSENT]  # today's wording: no Changes row


def test_reconfirm_repoints_the_receipt_to_part_two(tmp_path):
    vault = two_machine_session(tmp_path)
    code, out = reconfirm(vault, "--yes", "^c03", "CON-002")
    assert code == 0, out
    assert f'[[{RID}]] 2.c03, @priya: "Yes, still one till API for everything."' in text_of(vault, STOCK)
    assert f"| CON-002 | fact | decided | [[{RID}#^c03]] |" in text_of(vault, privaterecord.private_path(RID))
    assert not elsewhere(vault)
    assert not [p for p in gate(vault) if p["kind"] in (closegate.CONSENT, closegate.RECEIPT)]


def test_a_no_changes_nothing_and_the_gate_keeps_asking(tmp_path):
    vault = two_machine_session(tmp_path, captures=(THIS_YES, BARE_OK))
    before = text_of(vault, STOCK)
    code, out = reconfirm(vault, "--yes", "^c04", "CON-002")
    assert code == 1 and text_of(vault, STOCK) == before
    assert len(elsewhere(vault)) == 1


def test_the_yes_must_be_the_leads_own(tmp_path):
    other = '- [thought] (@cto-ana) "Yes, keep it." → park ^c05'
    vault = two_machine_session(tmp_path, captures=(THIS_YES, other))
    code, out = reconfirm(vault, "--yes", "^c05", "CON-002")
    assert code == 1 and "2.c05" not in text_of(vault, STOCK)


def test_an_id_the_gate_did_not_ask_about_is_refused_and_nothing_is_written(tmp_path):
    vault = two_machine_session(tmp_path)
    before = text_of(vault, STOCK), text_of(vault, privaterecord.private_path(RID))
    code, out = reconfirm(vault, "--yes", "^c03", "CON-002", "CON-999")
    assert code == 1
    assert (text_of(vault, STOCK), text_of(vault, privaterecord.private_path(RID))) == before


def test_a_ledger_row_taken_off_on_the_other_machine_is_asked_about_and_reconfirmed_as_removed(tmp_path):
    vault = two_machine_session(tmp_path, ledger=True)
    copy = LEDGER_ROW.strip("|").split("|")[0].strip()
    page = vault / STOCK
    page.write_text(page.read_text(encoding="utf-8").replace(LEDGER_ROW + "\n", "", 1), encoding="utf-8")
    found = elsewhere(vault)
    assert len(found) == 1 and "a question taken off" in found[0]["plain"] and copy in found[0]["detail"]
    assert not [p for p in gate(vault) if p["kind"] == closegate.REMOVED_ROW]
    code, out = reconfirm(vault, "--yes", "^c03", "CON-002", copy)
    assert code == 0, out
    assert f"| {copy} | ledger row | removed | [[{RID}#^c03]] |" in text_of(vault, privaterecord.private_path(RID))
    assert not elsewhere(vault)
    assert not [p for p in gate(vault) if p["kind"] == closegate.REMOVED_ROW]


def test_reconfirm_after_a_finished_read_back_says_it_reopens_it(tmp_path):
    vault = two_machine_session(tmp_path)
    assert run("close", "readback", "--done", "--vault", str(vault))[0] == 0
    assert closegate.READBACK not in {p["kind"] for p in gate(vault)}
    code, out = reconfirm(vault, "--yes", "^c03", "CON-002", "--for-lead")
    assert code == 0, out
    assert "I've changed a line you already read back, so read it back again." in out
    assert closegate.READBACK in {p["kind"] for p in gate(vault)}


def test_part_one_closing_last_is_asked_about_what_part_two_decided(tmp_path):
    """The other machine's part 2 decided it, so part 1 hits no dead end: it gets the same one question."""
    vault = two_machine_session(tmp_path)
    notes = vault / privaterecord.private_path(RID)
    notes.write_text(notes.read_text(encoding="utf-8").replace("part: 2", "part: 1"), encoding="utf-8")
    page = vault / STOCK
    page.write_text(text_of(vault, STOCK).replace(f"[[{RID}]] c01", f"[[{RID}]] 2.c01"), encoding="utf-8")
    assert len(elsewhere(vault)) == 1
    code, out = reconfirm(vault, "--yes", "^c03", "CON-002")
    assert code == 0, out
    assert f"[[{RID}]] c03, @priya" in text_of(vault, STOCK)
    assert not elsewhere(vault)
