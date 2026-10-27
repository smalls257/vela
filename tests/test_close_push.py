"""`vela close push`: the lead's word to close is the yes, so it sends once the gate passes, with no second question,
and a session on main moves to its own branch first. The push goes to a bare repo in tmp_path standing in for origin."""
import json
import os
import stat

from conftest import run
from sharing import git, make_vault, with_remote
from vela import say
from vela.edge import saidlog
import session_files

RECORD = "2026-10-20-grill-stock"
BRANCH = f"session/{RECORD}"
TODAY = "2026-10-20"
STOCK = "05-building-blocks/stock-building-blocks.md"
MARK = " → keep: [[stock-building-blocks#CON-002 Stock level|CON-002]] (decided)"
SEND_MARK = "drop: a yes the test captured"
YES_WORDS = "Yes, decide stock level as read."
BACK = f"- [thought] (claude) Read back: stock level is read on both sides{MARK} ^c01"
YES = f'- [thought] (@lead) "{YES_WORDS}" says yes{MARK} ^c02'
YES_ROW = f"| CON-002 | fact | decided | [[{RECORD}#^c02]] |"
DECIDED = f"- **State:** decided\n- **Decision:** [[{RECORD}]]\n- **Tested by:** the stock read test on both sides"


def record_text(record_id=RECORD, modes="grill", title="Grill: stock", captures=None, rows=None):
    captures = captures if captures is not None else [BACK, YES]
    rows = rows if rows is not None else [YES_ROW.replace(RECORD, record_id)]
    lines = ["---", f"id: {record_id}", "type: session", f'title: "{title}"', f"date: {TODAY}", f"modes: [{modes}]",
             "status: open", "summary: Stock level is decided.", "---", "", f"# {TODAY} {title}", "", "## Captures",
             "", *captures, "", "## Changes", "", "| ID | From | To | Source |", "|---|---|---|---|", *rows]
    return "\n".join(lines) + "\n"


def commit_all(vault, message):
    git(vault, "add", "-A", "--", ".", ":!.vela")
    git(vault, "commit", "-q", "-m", message)


def sent_session(tmp_path, stock_owner=None, handle="lead", record_id=RECORD, branch=BRANCH, modes="grill",
                 title="Grill: stock", on_branch=None, stock_meta=""):
    """A session ready to send: the record and the decided stock level committed on the session's branch, main
    brought in, `.vela/session.json` written as `session start` writes it. `on_branch` is an existing branch to open
    the record on (an answer session's challenge branch)."""
    vault = make_vault(tmp_path)
    bare = with_remote(tmp_path, vault)
    if on_branch:
        git(vault, "switch", "-q", "-c", on_branch)
        git(vault, "push", "-q", "-u", "origin", on_branch)
        branch = on_branch
    else:
        git(vault, "switch", "-q", "-c", branch)
    session_files.write_record(vault, record_id, record_text(record_id, modes, title))
    commit_all(vault, f"Open session {record_id}")
    assert run("close", "sync-main", "--vault", str(vault), "--today", TODAY)[0] == 0
    page = vault / STOCK
    text = page.read_text(encoding="utf-8").replace("- **State:** fact", DECIDED.replace(RECORD, record_id), 1)
    if stock_owner:
        text = text.replace('owner: "@stock-team"', f'owner: "{stock_owner}"', 1)
    if stock_meta:
        text = text.replace("authored: authored\n", f"authored: authored\n{stock_meta}\n", 1)
    page.write_text(text, encoding="utf-8")
    assert run("render", "--vault", str(vault))[0] == 0
    commit_all(vault, f"Close session {record_id}")
    (vault / ".vela").mkdir(exist_ok=True)
    if handle:
        (vault / ".vela" / "handle").write_text(handle + "\n", encoding="utf-8")
    state = {"id": record_id, "path": f"sessions/private/{record_id}.md", "stub": f"sessions/{record_id}.md",
             "part": 1, "branch": branch, "modes": modes.split(", "),
             "started": TODAY, "last_capture": 2}
    (vault / ".vela" / "session.json").write_text(json.dumps(state), encoding="utf-8")
    return vault, bare


def push(vault, *flags):
    return run("close", "push", "--vault", str(vault), "--today", TODAY, *flags)


def add_yes(vault, words="Yes, send it.", origin="@lead"):
    """A capture by `vela record add`, typed as the hook logs it, in the private notes (never committed). Close push
    takes no yes; tests that read a lead's capture back (`records show`) use this."""
    saidlog.append(vault, "test-session", "2026-10-14T09:00:00Z", words)
    code, out = run("record", "add", "--vault", str(vault), "--origin", origin, "--tag", "decision", "--mark",
                    SEND_MARK, words)
    assert code == 0, out
    return out.strip()


def remote_has(bare, branch):
    return git(bare, "branch", "--list", branch).strip() != ""


def test_push_sends_with_no_yes_once_the_gate_is_ready(tmp_path):
    vault, bare = sent_session(tmp_path)
    code, out = push(vault, "--for-lead")
    assert code == 0, out
    assert remote_has(bare, BRANCH)
    assert git(bare, "rev-parse", BRANCH) == git(vault, "rev-parse", "HEAD")
    assert out.strip() == "Sent. Now I'll open the review." and say.leak_in(out) is None
    pushed = json.loads((vault / ".vela" / "close" / f"{RECORD}.push.json").read_text(encoding="utf-8"))
    assert pushed["branch"] == BRANCH and "consent" not in pushed and "link" not in pushed
    assert not list((vault / ".vela" / "close").glob("*push-notice*"))


def test_the_consent_flag_is_gone(tmp_path):
    vault, bare = sent_session(tmp_path)
    code, out = push(vault, "--consent", "^c02")
    assert code == 2, out
    assert not remote_has(bare, BRANCH)


def test_push_on_main_moves_the_work_to_its_own_branch_and_never_pushes_main(tmp_path):
    vault, bare = sent_session(tmp_path)
    git(vault, "switch", "-q", "main")
    git(vault, "merge", "-q", "--ff-only", BRANCH)  # the finished session sits on main, unpushed
    git(vault, "branch", "-q", "-D", BRANCH)
    state = json.loads((vault / ".vela" / "session.json").read_text(encoding="utf-8"))
    state["branch"] = "main"
    (vault / ".vela" / "session.json").write_text(json.dumps(state), encoding="utf-8")
    main_on_origin = git(bare, "rev-parse", "main")
    code, out = push(vault, "--for-lead")
    assert code == 0, out
    assert "own branch" in out and remote_has(bare, BRANCH)
    assert git(vault, "branch", "--show-current") == BRANCH
    assert git(bare, "rev-parse", "main") == main_on_origin, "main was never pushed"
    assert git(vault, "rev-parse", "main") != git(vault, "rev-parse", BRANCH), "main no longer holds the session"


def test_an_uncommitted_change_stops_the_push(tmp_path):
    vault, bare = sent_session(tmp_path)
    (vault / STOCK).write_text((vault / STOCK).read_text(encoding="utf-8") + "\nA late edit.\n", encoding="utf-8")
    code, out = push(vault)
    assert code == 1 and "aren't committed yet" in out, out
    assert not remote_has(bare, BRANCH)


def test_gate_refusal_stops_the_push(tmp_path):
    vault, bare = sent_session(tmp_path)
    (vault / ".vela" / "close").joinpath(f"{BRANCH.replace('/', '__')}.json").unlink()  # sync-main's record gone
    code, out = push(vault)
    assert code == 1 and "not ready" in out, out
    assert not remote_has(bare, BRANCH)


def test_no_network_says_the_stance_and_sends_nothing(tmp_path):
    vault, bare = sent_session(tmp_path)
    host = {"python": "3.11.4", "git": "yes", "git_repo": True, "network": "no", "gh": "no"}
    (vault / ".vela" / "host.json").write_text(json.dumps(host), encoding="utf-8")
    code, out = push(vault, "--for-lead")
    assert code == 1, out
    assert "I can file the session here, but I can't send it." in out
    assert not remote_has(bare, BRANCH)


def test_push_failure_prints_branch_and_retry(tmp_path):
    vault, bare = sent_session(tmp_path)
    hook = bare / "hooks" / "pre-receive"
    hook.write_text("#!/bin/sh\necho 'refused by the test' >&2\nexit 1\n", encoding="utf-8")
    hook.chmod(hook.stat().st_mode | stat.S_IEXEC)
    code, out = push(vault)
    assert code == 2, out
    assert BRANCH in out and f"git push -u origin {BRANCH}" in out
    code, lead = push(vault, "--for-lead")
    assert code == 2 and say.leak_in(lead) is None and "Shall I try again?" in lead
    assert BRANCH not in lead  # the branch and git's command stay in the default line


def test_a_stray_file_does_not_stop_the_push(tmp_path):
    vault, bare = sent_session(tmp_path)
    (vault / "notes.txt").write_text("scratch\n", encoding="utf-8")
    code, out = push(vault, "--for-lead")
    assert code == 0, out
    assert remote_has(bare, BRANCH)


def test_reader_copy_sends_nothing(tmp_path):
    vault, bare = sent_session(tmp_path)
    import shutil
    shutil.rmtree(vault / ".git")
    (vault / ".vela" / "workspace.json").write_text('{"author": "Sam"}', encoding="utf-8")
    code, out = push(vault, "--for-lead")
    assert code == 1 and "your copy" in out and os.path.isdir(vault)
