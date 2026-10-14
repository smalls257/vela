"""`planner close gate` (overhaul Task 10a) against a real vault repo: a decision since the branch point needs the
lead's quoted yes in the record, main must have been brought in, and `--consent-block` quotes the lead verbatim."""
import shutil

from conftest import run
from vela import closegate, say
from sharing import git, make_vault, with_remote

RECORD = "2026-10-20-grill-stock"
STOCK = "05-building-blocks/stock-building-blocks.md"


def record_text(captures=(), rows=()):
    lines = ["---", f"id: {RECORD}", "type: session", "date: 2026-10-20", "modes: [grill]", "status: open",
             "summary: In progress.", "---", "", "# 2026-10-20 Stock grill", "", "## Captures", "", *captures, "",
             "## Changes", "", "| ID | From | To | Source |", "|---|---|---|---|", *rows]
    return "\n".join(lines) + "\n"


def session(tmp_path, sync=True):
    vault = make_vault(tmp_path)
    with_remote(tmp_path, vault)
    git(vault, "switch", "-q", "-c", f"session/{RECORD}")
    (vault / "sessions" / f"{RECORD}.md").write_text(record_text(), encoding="utf-8")
    git(vault, "add", "sessions")
    git(vault, "commit", "-q", "-m", f"Open session {RECORD}")
    if sync:
        assert run("close", "sync-main", "--vault", str(vault), "--today", "2026-10-20")[0] == 0
    return vault


def decide_stock(vault, captures=(), rows=(), extra=""):
    page = vault / STOCK
    page.write_text(page.read_text(encoding="utf-8").replace("- **State:** fact", "- **State:** decided" + extra, 1),
                    encoding="utf-8")
    (vault / "sessions" / f"{RECORD}.md").write_text(record_text(captures, rows), encoding="utf-8")


def gate(vault, *flags):
    return run("close", "gate", "--vault", str(vault), *flags)


def test_hand_set_decided_with_no_changes_row_refused(tmp_path):
    vault = session(tmp_path)
    decide_stock(vault)
    code, out = gate(vault, "--for-lead")
    assert code == 1, out
    assert "Stock level was made decided with nothing on record saying the lead agreed." in out
    assert say.leak_in(out) is None


def test_changes_row_citing_claude_capture_refused(tmp_path):
    vault = session(tmp_path)
    decide_stock(vault, ["- [thought] (claude) decide stock level now ^c01"],
                 [f"| CON-002 | fact | decided | [[{RECORD}#^c01]] |"])
    code, out = gate(vault)
    assert code == 1 and "on my suggestion" in out and "origin 'claude'" in out


def test_claude_from_summary_is_not_a_quote(tmp_path):
    vault = session(tmp_path)
    decide_stock(vault, ["- [thought] (claude, from @priya) Priya is happy with it ^c01"],
                 [f"| CON-002 | fact | decided | [[{RECORD}#^c01]] |"])
    assert gate(vault)[0] == 1


def test_bare_ok_is_not_a_yes(tmp_path):
    vault = session(tmp_path)
    decide_stock(vault, ['- [thought] (@priya) "ok" ^c01'], [f"| CON-002 | fact | decided | [[{RECORD}#^c01]] |"])
    code, out = gate(vault)
    assert code == 1 and "isn't a yes" in out


def test_a_quoted_yes_is_ready_and_the_consent_block_quotes_it(tmp_path):
    vault = session(tmp_path)
    decide_stock(vault, ['- [thought] (@priya) "Yes, decide stock level as read." says yes ^c01'],
                 [f"| CON-002 | fact | decided | [[{RECORD}#^c01]] |"])
    code, out = gate(vault, "--for-lead")
    assert code == 0 and "ready to finish" in out, out
    code, out = gate(vault, "--consent-block")
    assert code == 0
    assert f'- Stock level (CON-002), fact to decided: "Yes, decide stock level as read." [[{RECORD}#^c01]]' in out


def test_consent_block_quotes_the_lead_verbatim(tmp_path):
    words = 'Yes | with "care", and decide it'
    vault = session(tmp_path)
    decide_stock(vault, [f"- [thought] (@priya) {words} ^c01"], [f"| CON-002 | fact | decided | [[{RECORD}#^c01]] |"])
    _, out = gate(vault, "--consent-block")
    assert "care" in out and "**Consent**" in out


def test_override_bullet_lets_it_through_and_is_listed(tmp_path):
    vault = session(tmp_path)
    bullet = f"\n- **Override:** {closegate.QUOTED_YES_RULE} by @priya on 2026-10-20: the owner said yes on the phone"
    decide_stock(vault, extra=bullet)
    code, out = gate(vault)
    assert code == 0, out
    _, block = gate(vault, "--consent-block")
    assert "by override" in block and "on the phone" in block


def test_sync_not_run_blocks(tmp_path):
    vault = session(tmp_path, sync=False)
    code, out = gate(vault, "--for-lead")
    assert code == 1 and "Main hasn't been brought into this branch yet." in out


def test_reader_copy_checks_every_changes_row(tmp_path):
    vault = session(tmp_path)
    decide_stock(vault, ["- [thought] (claude) decide it ^c01"], [f"| CON-002 | fact | decided | [[{RECORD}#^c01]] |"])
    shutil.rmtree(vault / ".git")
    (vault / ".planner").mkdir(exist_ok=True)
    (vault / ".planner" / "workspace.json").write_text('{"author": "Sam"}', encoding="utf-8")
    code, out = gate(vault)
    assert code == 1 and "on my suggestion" in out


def test_no_open_session_exits_1(tmp_path):
    vault = make_vault(tmp_path)
    code, out = gate(vault)
    assert code == 1 and "No session is open" in out
