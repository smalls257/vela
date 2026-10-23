"""A session runs on the branch the lead is on (the owner: "just have a session be on current branch"). A second
session on one branch owes only its own paragraphs, and a session left on the default branch is moved to its own
branch, by the lead's yes, before anything is sent for review."""
import json

from conftest import run
from sharing import git, make_vault, with_remote
from test_close_drafts import STOCK, decide_stock, drafts_json, resolve_till_rig
from test_session_cli import TODAY, no_gh, start
import session_files
from vela import privaterecord


def commit_all(vault, message):
    git(vault, "add", "-A")
    git(vault, "commit", "-q", "-m", message)


def close_record(vault, record_id):
    session_files.edit_stub(vault, record_id, "status: open", "status: closed")
    commit_all(vault, f"Close session {record_id}")


def pages_owed(vault):
    return {p["page"] for p in drafts_json(vault)["paragraphs"]}


def test_a_second_session_on_a_branch_owes_only_its_own_paragraphs(tmp_path, monkeypatch):
    vault = make_vault(tmp_path)
    no_gh(tmp_path, monkeypatch)
    git(vault, "switch", "-q", "-c", "waiting-for-review")
    assert start(vault, "--mode", "grill", "--topic", "stock")[0] == 0
    decide_stock(vault)
    commit_all(vault, "Decide the stock level")
    assert pages_owed(vault), "the first session changed a page and owes paragraphs"
    close_record(vault, f"{TODAY}-stock")
    code, out = start(vault, "--mode", "grill", "--topic", "till")
    assert code == 0, out
    assert git(vault, "branch", "--show-current") == "waiting-for-review"
    assert drafts_json(vault)["paragraphs"] == []  # the stock level was the first session's
    resolve_till_rig(vault)
    owed = pages_owed(vault)
    assert owed and STOCK not in owed and "05-building-blocks/stock-building-blocks.md" not in owed


def test_close_push_on_the_default_branch_offers_a_branch_and_session_branch_moves_the_work(tmp_path, monkeypatch):
    vault = make_vault(tmp_path)
    bare = with_remote(tmp_path, vault)
    no_gh(tmp_path, monkeypatch)
    began = git(vault, "rev-parse", "HEAD")
    assert start(vault, "--mode", "grill", "--topic", "stock")[0] == 0
    decide_stock(vault)
    commit_all(vault, "Decide the stock level")
    code, out = run("close", "push", "--vault", str(vault), "--today", TODAY, "--for-lead")
    assert code == 1, out
    assert "needs its own branch" in out and "move today's work onto a new branch" in out
    assert git(bare, "rev-parse", "main") == began  # nothing was pushed
    code, out = run("session", "branch", "--vault", str(vault), "--json")
    assert code == 0, out
    branch = f"session/{TODAY}-stock"
    assert git(vault, "branch", "--show-current") == branch
    assert git(vault, "rev-parse", "main") == began  # main holds nothing of the session
    assert git(vault, "log", "--format=%s", began + ".." + branch).split("\n")[0] == f"Move session {TODAY}-stock to {branch}"
    assert privaterecord.stub_meta(session_files.stub_text(vault, f"{TODAY}-stock"))["branch"] == branch
    code, out = run("session", "open", "--vault", str(vault), "--json")
    assert code == 0 and json.loads(out)["open"][0]["branch"] == branch
    code, out = run("session", "branch", "--vault", str(vault))
    assert code == 1  # already on its own branch: nothing to move
