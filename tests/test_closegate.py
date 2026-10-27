"""The close gate's yes rule: a change into `decided` passes on this part's Changes row or on a Decision receipt that
names a person, wherever that yes was given. A bare state edit with neither still stops the close."""
import json

from conftest import run
from vela import privaterecord
from sharing import git, make_vault, with_remote
import session_files

RID = "2026-10-20-grill-stock"
STOCK = "05-building-blocks/stock-building-blocks.md"
OTHER_DECISION = f'- **Decision:** [[{RID}]] c01, @priya: "Yes, one till API for the web and the kiosks."'
DECIDED = "- **State:** decided\n{decision}\n- **Tested by:** the stock read test on both sides"


def receipt_only_session(tmp_path, decision_line=OTHER_DECISION, reopen=False):
    """Part 2 of a session: the notes hold no Changes row for CON-002. With `reopen`, the page was already decided at
    the branch point and the working tree sets it back to an assumption."""
    vault = make_vault(tmp_path)
    page = vault / STOCK
    decided = DECIDED.format(decision=decision_line or "- **Note:** none").replace("- **Note:** none\n", "")
    if reopen:
        page.write_text(page.read_text(encoding="utf-8").replace("- **State:** fact", decided, 1), encoding="utf-8")
        git(vault, "add", STOCK)
        git(vault, "commit", "-q", "-m", "Decided before the session")
    with_remote(tmp_path, vault)
    git(vault, "switch", "-q", "-c", f"session/{RID}")
    stub = privaterecord.render_stub({
        "id": RID, "type": "session", "title": "Stock grill", "date": "2026-10-20", "modes": ["grill"],
        "status": "open", "captures_sha256": {1: "a" * 64, 2: privaterecord.PENDING}})
    (vault / "sessions").mkdir(exist_ok=True)
    (vault / privaterecord.stub_path(RID)).write_text(stub, encoding="utf-8")
    session_files.ignore_private(vault)
    notes = privaterecord.new_private(RID, "Stock grill", "2026-10-20", 2)
    session_files.write_private(vault, RID, notes)
    git(vault, "add", "sessions", ".gitignore")
    git(vault, "commit", "-q", "-m", f"Open session {RID}")
    assert run("close", "sync-main", "--vault", str(vault), "--today", "2026-10-20")[0] == 0
    (vault / ".vela").mkdir(exist_ok=True)
    (vault / ".vela" / "handle").write_text("priya\n", encoding="utf-8")
    text = page.read_text(encoding="utf-8")
    if reopen:
        text = text.replace("- **State:** decided", "- **State:** assumption", 1)
    else:
        text = text.replace("- **State:** fact", decided, 1)
    page.write_text(text, encoding="utf-8")
    assert run("render", "--vault", str(vault))[0] == 0
    return vault


def gate(vault):
    code, out = run("close", "gate", "--vault", str(vault), "--json", "--today", "2026-10-20")
    return json.loads(out)["problems"]


def test_a_decision_with_its_receipt_and_no_changes_row_here_passes(tmp_path):
    vault = receipt_only_session(tmp_path)
    kinds = [p["kind"] for p in gate(vault)]
    assert "consent" not in kinds and "elsewhere" not in kinds


def test_a_hand_set_decided_with_no_receipt_is_still_asked(tmp_path):
    vault = receipt_only_session(tmp_path, decision_line="")
    found = [p for p in gate(vault) if p["kind"] == "consent"]
    assert len(found) == 1 and "haven't said yes" in found[0]["plain"]


def test_a_receipt_naming_claude_is_not_a_yes(tmp_path):
    vault = receipt_only_session(tmp_path, decision_line=f'- **Decision:** [[{RID}]] c01, claude: "Yes."')
    assert [p for p in gate(vault) if p["kind"] == "consent"]


def test_reopening_with_no_changes_row_here_is_not_asked(tmp_path):
    vault = receipt_only_session(tmp_path, reopen=True)
    assert not [p for p in gate(vault) if p["kind"] == "consent"]


def test_close_reconfirm_is_gone(capsys):
    from vela.commands import close
    assert "close_reconfirm" not in close.STEPS
    code, _ = run("close", "reconfirm", "--readback", "^c01", "--yes", "^c02", "CON-002")
    assert code == 2  # argparse: not a command
    assert "invalid choice" in capsys.readouterr().err
