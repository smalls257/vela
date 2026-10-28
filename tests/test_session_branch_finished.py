"""A session run on main and closed by `close finish`: `close push` moves it onto its own branch and sends that, and
`vela session branch` moves it the same way on its own. The finished, never-pushed session on main moves like an open
one (it used to dead-end on "I can't tell which session to move")."""
import json

from conftest import run
from sharing import git, make_vault, with_remote
import session_files
import test_close_push as pushing
from test_session_cli import no_gh
from vela import privaterecord

TODAY = pushing.TODAY
SUMMARY = "Stock level is decided."


def finished_on_main(tmp_path, monkeypatch):
    """A grill started on main, the stock level decided in it, and `close finish` run: nothing pushed."""
    vault = make_vault(tmp_path)
    bare = with_remote(tmp_path, vault)
    no_gh(tmp_path, monkeypatch)
    (vault / ".git" / "info" / "exclude").write_text(".vela/*\n", encoding="utf-8")
    code, out = run("session", "start", "--vault", str(vault), "--today", TODAY, "--mode", "grill", "--topic", "stock",
                    "--json")
    assert code == 0, out
    record_id = json.loads(out)["id"]
    began = git(vault, "rev-parse", "HEAD~1")
    private = privaterecord.split_record(pushing.record_text(record_id)).private
    session_files.write_private(vault, record_id, private)
    assert run("close", "sync-main", "--vault", str(vault), "--today", TODAY)[0] == 0
    page = vault / pushing.STOCK
    page.write_text(page.read_text(encoding="utf-8").replace(
        "- **State:** fact", pushing.DECIDED.replace(pushing.RECORD, record_id), 1), encoding="utf-8")
    assert run("render", "--vault", str(vault))[0] == 0
    (vault / ".vela" / "handle").write_text("lead\n", encoding="utf-8")
    code, out = run("close", "finish", "--vault", str(vault), "--summary", SUMMARY, "--today", TODAY)
    assert code == 0, out
    return vault, bare, record_id, began


def test_close_push_moves_a_finished_session_on_main_to_its_own_branch_and_sends_it(tmp_path, monkeypatch):
    vault, bare, record_id, began = finished_on_main(tmp_path, monkeypatch)
    branch, tip = f"session/{record_id}", git(vault, "rev-parse", "HEAD")
    code, out = run("close", "push", "--vault", str(vault), "--today", TODAY, "--for-lead")
    assert code == 0 and "own branch" in out, out  # moved, brought main in once, then sent
    assert git(vault, "branch", "--show-current") == branch
    assert git(vault, "rev-parse", "main") == began and git(vault, "rev-parse", branch + "~1") == tip
    assert pushing.remote_has(bare, branch) and not git(bare, "rev-parse", "main") == tip


def test_session_branch_moves_a_finished_session_on_main_by_itself(tmp_path, monkeypatch):
    vault, bare, record_id, began = finished_on_main(tmp_path, monkeypatch)
    branch, tip = f"session/{record_id}", git(vault, "rev-parse", "HEAD")
    code, out = run("session", "branch", "--vault", str(vault), "--for-lead")
    assert code == 0, out
    assert git(vault, "branch", "--show-current") == branch and git(vault, "rev-parse", "HEAD~0") != began
    assert git(vault, "rev-parse", "main") == began and git(vault, "rev-parse", branch + "~1") == tip
    assert "can't tell" not in out and "own branch now" in out


def test_two_finished_unpushed_sessions_are_not_guessed_between(tmp_path, monkeypatch):
    vault, _, record_id, _ = finished_on_main(tmp_path, monkeypatch)
    other = "2026-10-20-second"
    first = vault / privaterecord.stub_path(record_id)
    stub = vault / privaterecord.stub_path(other)
    stub.write_text(first.read_text(encoding="utf-8").replace(record_id, other), encoding="utf-8")
    git(vault, "add", "--", str(stub.relative_to(vault)))
    git(vault, "commit", "-q", "-m", "a second finished session")
    code, out = run("session", "branch", "--vault", str(vault), "--for-lead")
    assert code == 1 and "can't tell which session" in out, out
    assert git(vault, "branch", "--show-current") == "main"
