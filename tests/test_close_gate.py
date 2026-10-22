"""`vela close gate` (overhaul Tasks 10a and 10) against a real vault repo: a decision since the branch point needs the
lead's quoted yes in the record, main must have been brought in, and `--consent-block` quotes the lead verbatim. Task 10
adds the rest of the one list: unmarked captures, check errors, ledger rows or overrides removed since the branch point,
stray files, a stale render, the flow check per affected slice, and whether hooks ran."""
import json
import shutil
import subprocess

from conftest import REPO, run
from vela import closegate, say
from sharing import git, make_vault, with_remote
import session_files

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
    session_files.write_record(vault, RECORD, record_text())
    git(vault, "add", "sessions")
    git(vault, "commit", "-q", "-m", f"Open session {RECORD}")
    if sync:
        assert run("close", "sync-main", "--vault", str(vault), "--today", "2026-10-20")[0] == 0
    return vault


# A decided contract check has nothing to say about: the session it was decided in, and who tests it.
DECIDED = f"- **State:** decided\n- **Decision:** [[{RECORD}]]\n- **Tested by:** the stock read test on both sides"
MARK = " → keep: [[stock-building-blocks#CON-002 Stock level|CON-002]] (decided)"
YES = f'- [thought] (@priya) "Yes, decide stock level as read." says yes{MARK} ^c01'
YES_ROW = f"| CON-002 | fact | decided | [[{RECORD}#^c01]] |"


def decide_stock(vault, captures=(), rows=(), extra=""):
    page = vault / STOCK
    page.write_text(page.read_text(encoding="utf-8").replace("- **State:** fact", DECIDED + extra, 1), encoding="utf-8")
    session_files.write_record(vault, RECORD, record_text(captures, rows))
    assert run("render", "--vault", str(vault))[0] == 0


def on_main(vault, path, old, new):
    """A change on main before the session branched, pushed, so it sits at the branch point."""
    target = vault / path
    text = target.read_text(encoding="utf-8")
    assert old in text
    target.write_text(text.replace(old, new, 1), encoding="utf-8")
    git(vault, "commit", "-qam", "on main")
    git(vault, "push", "-q", "origin", "main")


def gate(vault, *flags):
    return run("close", "gate", "--vault", str(vault), *flags)


def test_hand_set_decided_with_no_changes_row_refused(tmp_path):
    vault = session(tmp_path)
    decide_stock(vault)
    code, out = gate(vault, "--for-lead")
    assert code == 1, out
    assert out.startswith("One thing before I can finish: one decision needs your yes."), out  # the answer first
    assert "You haven't said yes to deciding Stock level yet." in out
    assert "Changes row" not in out and "the lead" not in out  # the model's bookkeeping stays in the model's line
    assert say.leak_in(out) is None


def test_changes_row_citing_claude_capture_refused(tmp_path):
    vault = session(tmp_path)
    decide_stock(vault, ["- [thought] (claude) decide stock level now ^c01"],
                 [f"| CON-002 | fact | decided | [[{RECORD}#^c01]] |"])
    code, out = gate(vault)
    assert code == 1 and "was my suggestion, not your yes" in out and "origin 'claude'" in out


def test_claude_from_summary_is_not_a_quote(tmp_path):
    vault = session(tmp_path)
    decide_stock(vault, ["- [thought] (claude, from @priya) Priya is happy with it ^c01"],
                 [f"| CON-002 | fact | decided | [[{RECORD}#^c01]] |"])
    assert gate(vault)[0] == 1


def test_bare_ok_is_not_a_yes(tmp_path):
    vault = session(tmp_path)
    decide_stock(vault, ['- [thought] (@priya) "ok" ^c01'], [f"| CON-002 | fact | decided | [[{RECORD}#^c01]] |"])
    code, out = gate(vault)
    assert code == 1 and "You said 'ok' on Stock level. Was that a yes to deciding Stock level?" in out


def test_a_quoted_yes_is_ready_and_the_consent_block_quotes_it(tmp_path):
    vault = session(tmp_path)
    decide_stock(vault, [YES], [YES_ROW])
    code, out = gate(vault, "--for-lead")
    assert code == 0 and "ready to finish" in out, out
    code, out = gate(vault, "--consent-block")
    assert code == 0
    assert f'- Stock level (CON-002), fact to decided: "Yes, decide stock level as read." [[{RECORD}#^c01]]' in out


def test_consent_block_quotes_the_lead_verbatim(tmp_path):
    words = 'Yes | with "care", and decide it'
    vault = session(tmp_path)
    decide_stock(vault, [f"- [thought] (@priya) {words}{MARK} ^c01"], [YES_ROW])
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
    assert code == 1 and "a step of my own" in out, out  # sync-main is Claude's step: counted, never asked about
    assert "Main hasn't been brought into this branch yet." in gate(vault)[1]


def test_reader_copy_checks_every_changes_row(tmp_path):
    vault = session(tmp_path)
    decide_stock(vault, ["- [thought] (claude) decide it ^c01"], [f"| CON-002 | fact | decided | [[{RECORD}#^c01]] |"])
    shutil.rmtree(vault / ".git")
    (vault / ".vela").mkdir(exist_ok=True)
    (vault / ".vela" / "workspace.json").write_text('{"author": "Sam"}', encoding="utf-8")
    code, out = gate(vault)
    assert code == 1 and "was my suggestion" in out


def test_no_open_session_exits_1(tmp_path):
    vault = make_vault(tmp_path)
    code, out = gate(vault)
    assert code == 1 and "No session is open" in out


# Task 10: the rest of the list.

def session_with(tmp_path, before_branch):
    """`session`, after a change on main that the session's branch point then holds."""
    vault = make_vault(tmp_path)
    with_remote(tmp_path, vault)
    on_main(vault, *before_branch)
    git(vault, "switch", "-q", "-c", f"session/{RECORD}")
    session_files.write_record(vault, RECORD, record_text())
    git(vault, "add", "sessions")
    git(vault, "commit", "-q", "-m", f"Open session {RECORD}")
    assert run("close", "sync-main", "--vault", str(vault), "--today", "2026-10-20")[0] == 0
    return vault


def hooks_ran(vault):
    (vault / ".vela").mkdir(exist_ok=True)
    (vault / ".vela" / "hooks-active").write_text(json.dumps({"session_id": "s1"}) + "\n", encoding="utf-8")


def test_clean_session_passes(tmp_path):
    vault = session(tmp_path)
    decide_stock(vault, [YES], [YES_ROW])
    hooks_ran(vault)
    code, out = gate(vault, "--for-lead", "--today", "2026-10-20")
    assert code == 0, out
    assert out.startswith("The session is ready to finish.") and "Hooks did not run" not in out
    assert say.leak_in(out) is None


def test_unmarked_capture_blocks(tmp_path):
    vault = session(tmp_path)
    decide_stock(vault, [YES, "- [idea] (claude) ask the till team about returns ^c02"], [YES_ROW])
    code, out = gate(vault, "--for-lead")
    assert code == 1, out
    assert "One thing you said isn't sorted yet: keep it, set it aside for later, or drop it?" in out
    assert say.leak_in(out) is None


def test_an_error_with_no_recorded_choice_blocks(tmp_path):
    vault = session(tmp_path)
    decide_stock(vault, [YES], [YES_ROW])
    page = vault / STOCK
    page.write_text(page.read_text(encoding="utf-8").replace("- **Tested by:** the stock read test on both sides\n", ""),
                    encoding="utf-8")
    code, out = gate(vault, "--for-lead", "--today", "2026-10-20")
    assert code == 1 and "Stock: Stock level is decided but says nothing about who tests it." in out, out


OVERRIDE = "- **Override:** E318 by @priya on 2026-10-01: the vendor tests the stock read"


def test_override_removed_since_branch_point_blocks(tmp_path):
    vault = session_with(tmp_path, (STOCK, "- **Source:** SRC-01", "- **Source:** SRC-01\n" + OVERRIDE))
    page = vault / STOCK
    page.write_text(page.read_text(encoding="utf-8").replace(OVERRIDE + "\n", ""), encoding="utf-8")
    code, out = gate(vault, "--for-lead")
    assert code == 1, out
    assert "The exception on Stock level was taken out this session" in out and "the vendor tests the stock read" in out
    assert say.leak_in(out) is None


def test_ledger_row_removed_since_branch_point_blocks(tmp_path):
    vault = session(tmp_path)
    page = vault / "11-unknowns-and-risks.md"
    text = page.read_text(encoding="utf-8")
    row = next(line for line in text.split("\n") if line.startswith("| Q-FIN-01@INI-900 "))
    page.write_text(text.replace(row + "\n", ""), encoding="utf-8")
    code, out = gate(vault, "--for-lead")
    assert code == 1, out
    assert "A question was taken off" in out and "Was that on purpose?" in out and say.leak_in(out) is None
    _, default = gate(vault)
    assert "Q-FIN-01@INI-900" in default


def test_hooks_marker_missing_is_said_plainly(tmp_path):
    vault = session(tmp_path)
    assert run("render", "--vault", str(vault))[0] == 0  # the new record's own line in a generated table
    code, out = gate(vault, "--for-lead")
    assert code == 0, out
    assert "Hooks did not run" not in out  # housekeeping is not news to the lead (conversation voice)
    assert "Hooks did not run in this session" in gate(vault)[1]


def test_render_stale_blocks(tmp_path):
    vault = session(tmp_path)
    page = vault / STOCK
    page.write_text(page.read_text(encoding="utf-8").replace("### CON-002 Stock level", "### CON-002 Stock count"),
                    encoding="utf-8")
    code, out = gate(vault, "--for-lead")
    assert code == 1 and "generated tables" not in out, out  # Claude runs render itself; the lead isn't asked
    assert "generated tables are out of date" in gate(vault)[1]


def test_tree_not_clean_blocks(tmp_path):
    vault = session(tmp_path)
    (vault / "notes.txt").write_text("scratch\n", encoding="utf-8")
    code, out = gate(vault, "--for-lead")
    assert code == 1 and "notes.txt" in out, out


def test_flowcheck_line_per_affected_slice(tmp_path):
    """The flow-check fixture's three slices: a session that changes one contract hears one line, for the slice it
    reaches, and none for the two it doesn't. The line never changes the exit code by itself."""
    vault = tmp_path / "vault"
    shutil.copytree(REPO / "tests" / "fixtures" / "flowcheck" / "30-impact-walk", vault)
    (vault / "sessions").mkdir()
    git(tmp_path, "init", "-q", "-b", "main", str(vault))
    for key, value in (("user.name", "Priya Nair"), ("user.email", "priya@example.com"), ("commit.gpgsign", "false")):
        git(vault, "config", key, value)
    git(vault, "add", "-A")
    git(vault, "commit", "-q", "-m", "the plan")
    git(vault, "switch", "-q", "-c", f"session/{RECORD}")
    session_files.write_record(vault, RECORD, record_text())
    billing = vault / "05-building-blocks" / "billing-building-blocks.md"
    billing.write_text(billing.read_text(encoding="utf-8").replace("| declined |  | 402 |", "| declined |  | 403 |", 1),
                       encoding="utf-8")
    _, out = gate(vault, "--today", "2026-10-20")
    flow = [line for line in out.split("\n") if "SLC-" in line]
    assert len(flow) == 1 and "SLC-002 Pay for it" in flow[0], out
    _, lead = gate(vault, "--for-lead", "--more", "--today", "2026-10-20")
    assert "Pay for it" in lead and say.leak_in(lead) is None


def test_reader_copy_checks_without_git(tmp_path, monkeypatch):
    vault = session(tmp_path)
    decide_stock(vault, ['- [thought] (@priya) "Yes, decide stock level as read." ^c01'], [YES_ROW])
    shutil.rmtree(vault / ".git")
    (vault / ".vela").mkdir(exist_ok=True)
    (vault / ".vela" / "workspace.json").write_text('{"author": "Sam"}', encoding="utf-8")
    assert run("close", "sync-main", "--vault", str(vault), "--today", "2026-10-20")[0] == 0

    def no_programs(*args, **kwargs):
        raise AssertionError(f"a reader copy ran a program: {args[0] if args else kwargs}")
    monkeypatch.setattr(subprocess, "Popen", no_programs)
    monkeypatch.setattr(subprocess, "run", no_programs)
    code, out = gate(vault, "--for-lead")
    assert code == 1 and "isn't sorted yet" in out, out


def test_close_offers_only_ready_steps():
    """`close finish` and `close push` exist as stub modules (Tasks 11 and 12 fill them), so the two can land in
    parallel without both editing close.py; a stub adds no parser until its task lands."""
    import argparse
    import importlib
    from vela.commands import close
    assert {"close_finish", "close_push"} <= set(close.STEPS)
    parser = argparse.ArgumentParser()
    close.register(parser.add_subparsers())
    top = next(a for a in parser._actions if isinstance(a, argparse._SubParsersAction))
    steps = next(a for a in top.choices["close"]._actions if isinstance(a, argparse._SubParsersAction)).choices
    names = {"close_sync": "sync-main", "close_stage": "stage", "close_gate": "gate", "close_drafts": "drafts",
             "close_finish": "finish", "close_push": "push"}
    for name in close.STEPS:
        module = importlib.import_module(f"vela.commands.{name}")
        assert (names[name] in steps) == (module.register_close is not None), name
