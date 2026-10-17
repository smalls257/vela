"""`vela close push` (overhaul Task 12): one confirmation before anything leaves the machine.

Without `--consent` it prints the send notice, notes the record's capture count, and exits 3; with it, the yes must be
a person's, numbered after the notice, and more than an "ok", and the gate must pass, before the branch is pushed. The
push goes to a bare repo in tmp_path standing in for origin."""
import json
import os
import stat

from conftest import run
from sharing import git, make_vault, with_remote
from vela import say

RECORD = "2026-10-20-grill-stock"
BRANCH = f"session/{RECORD}"
TODAY = "2026-10-20"
STOCK = "05-building-blocks/stock-building-blocks.md"
MARK = " → keep: [[stock-building-blocks#CON-002 Stock level|CON-002]] (decided)"
YES_WORDS = "Yes, decide stock level as read."
YES = f'- [thought] (@lead) "{YES_WORDS}" says yes{MARK} ^c01'
YES_ROW = f"| CON-002 | fact | decided | [[{RECORD}#^c01]] |"
DECIDED = f"- **State:** decided\n- **Decision:** [[{RECORD}]]\n- **Tested by:** the stock read test on both sides"
SEND_MARK = "drop: the yes to send this for review"


def record_text(record_id=RECORD, modes="grill", title="Grill: stock", captures=None, rows=None):
    captures = captures if captures is not None else [YES]
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
    (vault / "sessions" / f"{record_id}.md").write_text(record_text(record_id, modes, title), encoding="utf-8")
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
    state = {"id": record_id, "path": f"sessions/{record_id}.md", "branch": branch, "modes": modes.split(", "),
             "started": TODAY, "last_capture": 1}
    (vault / ".vela" / "session.json").write_text(json.dumps(state), encoding="utf-8")
    return vault, bare


def push(vault, *flags):
    return run("close", "push", "--vault", str(vault), "--today", TODAY, *flags)


def add_yes(vault, words="Yes, send it.", origin="@lead", commit=True, record_id=RECORD):
    """The lead's answer to the send notice, captured with `vela record add`, then committed."""
    code, out = run("record", "add", "--vault", str(vault), "--origin", origin, "--tag", "decision", "--mark",
                    SEND_MARK, words)
    assert code == 0, out
    if commit:
        git(vault, "add", "sessions")
        git(vault, "commit", "-q", "-m", f"Checkpoint {record_id}")
    return out.splitlines()[0]  # the number; the topic map's lines follow it


def remote_has(bare, branch):
    return git(bare, "branch", "--list", branch).strip() != ""


def test_push_without_consent_prints_notice_exits_3(tmp_path):
    vault, bare = sent_session(tmp_path)
    head = git(vault, "rev-parse", "HEAD")
    code, out = push(vault)
    assert code == 3, out
    assert f"I'll push `{BRANCH}` and open a pull request for" in out
    assert "stock-team" in out and "mini/shop-team" in out  # the changed app's owner and its contract's consumer
    assert "1 capture" in out and "--consent" in out
    assert git(vault, "rev-parse", "HEAD") == head and not remote_has(bare, BRANCH)
    code, lead = push(vault, "--for-lead")
    assert code == 3 and lead.strip().startswith("I'll send this for review to") and lead.strip().endswith("OK?")
    assert say.leak_in(lead) is None
    code, data = push(vault, "--json")
    assert code == 3 and json.loads(data)["needs_lead"][0]["captures_at_notice"] == 1


def test_consent_before_notice_refused(tmp_path):
    vault, bare = sent_session(tmp_path)
    number = add_yes(vault)  # a yes captured before any notice was printed
    code, out = push(vault)
    assert code == 3, out  # the notice comes now, after the yes
    code, out = push(vault, "--consent", number)
    assert code == 1 and "Before I send anything, I need to tell you what goes and to whom." in out, out
    assert not remote_has(bare, BRANCH)


def test_bare_ok_consent_refused(tmp_path):
    vault, bare = sent_session(tmp_path)
    assert push(vault)[0] == 3
    number = add_yes(vault, words="ok")
    code, out = push(vault, "--consent", number, "--for-lead")
    assert code == 1 and "You said 'ok'. Is that a yes" in out, out
    assert not remote_has(bare, BRANCH)


def test_claude_consent_refused(tmp_path):
    vault, bare = sent_session(tmp_path)
    assert push(vault)[0] == 3
    number = add_yes(vault, words="the lead seemed happy to send", origin="claude")
    code, out = push(vault, "--consent", number)
    assert code == 1 and "That line was mine, not yours." in out
    assert not remote_has(bare, BRANCH)


def test_a_yes_from_anyone_but_the_lead_sends_nothing(tmp_path):
    """The confirm run recorded the send's yes under the operator's account email (S14, S18, S21) and as "Sim Lead"
    (S2); a person's origin was all close push asked for. Only the `vela whoami` handle's yes sends now."""
    vault, bare = sent_session(tmp_path)
    assert push(vault)[0] == 3
    for origin, said in (("someone@example.com", "someone@example.com"), ("Priya", "Priya"),
                         ("@stock-team", "stock team")):
        number = add_yes(vault, origin=origin)
        code, out = push(vault, "--consent", number, "--for-lead")
        assert code == 1, out
        assert f"That yes is written down as coming from {said}, not from you, so I haven't sent anything." in out
        assert not remote_has(bare, BRANCH)
    code, out = push(vault, "--consent", number, "--json")
    refusal = json.loads(out)["refusals"][0]
    assert refusal["rule"] == "consent-not-the-lead" and "--origin @lead" in refusal["fix"], out
    number = add_yes(vault, origin="LEAD")  # the lead's own handle, however it is written
    assert push(vault, "--consent", number)[0] == 0
    assert remote_has(bare, BRANCH)


def test_consent_after_notice_pushes(tmp_path):
    vault, bare = sent_session(tmp_path)
    assert push(vault)[0] == 3
    number = add_yes(vault)
    code, out = push(vault, "--consent", number, "--for-lead")
    assert code == 0, out
    assert remote_has(bare, BRANCH)
    assert git(bare, "rev-parse", BRANCH) == git(vault, "rev-parse", "HEAD")
    assert say.leak_in(out) is None
    pushed = json.loads((vault / ".vela" / "close" / f"{RECORD}.push.json").read_text(encoding="utf-8"))
    assert pushed["branch"] == BRANCH and pushed["consent"] == number.lstrip("^")


def test_uncommitted_yes_refused(tmp_path):
    vault, bare = sent_session(tmp_path)
    assert push(vault)[0] == 3
    number = add_yes(vault, commit=False)
    code, out = push(vault, "--consent", number)
    assert code == 1 and "isn't committed" in out, out
    assert not remote_has(bare, BRANCH)


def test_gate_refusal_stops_the_push(tmp_path):
    vault, bare = sent_session(tmp_path)
    assert push(vault)[0] == 3
    number = add_yes(vault)
    (vault / ".vela" / "close").joinpath(f"{BRANCH.replace('/', '__')}.json").unlink()  # sync-main's record gone
    code, out = push(vault, "--consent", number)
    assert code == 1 and "not ready" in out, out
    assert not remote_has(bare, BRANCH)


def test_no_network_says_the_stance_and_sends_nothing(tmp_path):
    vault, bare = sent_session(tmp_path)
    host = {"python": "3.11.4", "git": "yes", "git_repo": True, "network": "no", "gh": "no"}
    (vault / ".vela" / "host.json").write_text(json.dumps(host), encoding="utf-8")
    code, out = push(vault, "--for-lead")
    assert code == 1, out
    assert "I can file the session here, but I can't send it." in out
    assert not (vault / ".vela" / "close" / f"{RECORD}.push-notice.json").exists()


def test_push_failure_prints_branch_and_retry(tmp_path):
    vault, bare = sent_session(tmp_path)
    assert push(vault)[0] == 3
    number = add_yes(vault)
    hook = bare / "hooks" / "pre-receive"
    hook.write_text("#!/bin/sh\necho 'refused by the test' >&2\nexit 1\n", encoding="utf-8")
    hook.chmod(hook.stat().st_mode | stat.S_IEXEC)
    code, out = push(vault, "--consent", number)
    assert code == 2, out
    assert BRANCH in out and f"git push -u origin {BRANCH}" in out
    code, lead = push(vault, "--consent", number, "--for-lead")
    assert code == 2 and say.leak_in(lead) is None and "Shall I try again?" in lead
    assert BRANCH not in lead  # the branch and git's command stay in the default line


def test_an_unready_session_is_refused_before_the_send_notice(tmp_path):
    """The gate runs first: asking "OK?" for a session that can't go yet asks for a yes that is then refused."""
    vault, bare = sent_session(tmp_path)
    (vault / "notes.txt").write_text("scratch\n", encoding="utf-8")
    code, out = push(vault, "--for-lead")
    assert code == 1, out
    assert out.startswith("I haven't sent anything.") and "OK?" not in out, out
    assert not list((vault / ".vela" / "close").glob("*push-notice*"))  # no notice, so no yes can be taken for it
    assert not remote_has(bare, BRANCH)


def test_reader_copy_sends_nothing(tmp_path):
    vault, bare = sent_session(tmp_path)
    import shutil
    shutil.rmtree(vault / ".git")
    (vault / ".vela" / "workspace.json").write_text('{"author": "Sam"}', encoding="utf-8")
    code, out = push(vault, "--for-lead")
    assert code == 1 and "your copy" in out and os.path.isdir(vault)
