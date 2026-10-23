"""A session is a committed stub and a private notes file (private-sessions Task 4).

The Violation these tests guard is an Infected Core of the plan's history: every word the lead said in a session sat
in a file git would commit, so one `git add` put a conversation on every clone. The stub in `sessions/<id>.md` is
only a header; the notes in `sessions/private/<id>.md` are read and written by every command that used to touch the
record, and no command stages them."""
import json
from conftest import run
from sharing import git, with_remote
from test_session_cli import TODAY, owner, start
from vela import closefinish, privaterecord
from vela.commands import close_stage
import session_files


def started(tmp_path, monkeypatch, topic="consent"):
    vault = owner(tmp_path, monkeypatch)
    assert "sessions/private/" in (vault / ".gitignore").read_text(encoding="utf-8").split(), "as the template's does"
    assert start(vault, "--mode", "dump", "--topic", topic)[0] == 0
    return vault, f"{TODAY}-{topic}"


def test_start_commits_the_stub_and_keeps_the_notes_here(tmp_path, monkeypatch):
    vault, record_id = started(tmp_path, monkeypatch)
    tracked = {p for p in git(vault, "ls-files", "sessions").split() if not p.startswith("sessions/2026-01")}
    assert tracked == {f"sessions/{record_id}.md"}
    assert (vault / "sessions" / "private" / f"{record_id}.md").is_file()
    assert git(vault, "log", "-1", "--format=%s") == f"Open session {record_id}"
    assert "private" not in git(vault, "show", "--name-only", "--format=", "HEAD")
    state = json.loads((vault / ".vela" / "session.json").read_text(encoding="utf-8"))
    assert (state["path"], state["stub"], state["part"]) == (
        f"sessions/private/{record_id}.md", f"sessions/{record_id}.md", 1)


def test_record_add_writes_the_private_file_only(tmp_path, monkeypatch):
    vault, record_id = started(tmp_path, monkeypatch)
    before = session_files.stub_text(vault, record_id)
    code, output = run("record", "add", "--vault", str(vault), "--origin", "claude", "--tag", "idea",
                       "A shared calendar.")
    assert code == 0, output
    assert "A shared calendar." in session_files.record_text(vault, record_id)
    assert "A shared calendar." not in session_files.stub_text(vault, record_id)
    assert session_files.stub_text(vault, record_id) == before


def test_the_loader_never_sees_the_private_file(tmp_path, monkeypatch):
    from vela import cli
    vault, record_id = started(tmp_path, monkeypatch)
    pages = [p.path for p in cli.load_vault(vault).pages]
    assert all(not p.startswith("sessions/private/") for p in pages)
    assert cli.page_kind(f"sessions/private/{record_id}.md") == "ignored"


def test_a_bare_stub_draws_no_finding(mini):
    stub = "2026-01-20-x"
    (mini / "sessions" / f"{stub}.md").write_text(
        privaterecord.new_stub(stub, "Grill: x", "2026-01-20", ["grill"]), encoding="utf-8")
    code, output = run("check", "--vault", str(mini), "--today", "2026-01-21")
    assert stub not in output, output


def test_close_stage_never_stages_the_private_file_without_the_ignore_line(tmp_path, monkeypatch):
    vault, record_id = started(tmp_path, monkeypatch)
    ignore = vault / ".gitignore"
    ignore.write_text(ignore.read_text(encoding="utf-8").replace("sessions/private/\n", ""), encoding="utf-8")
    session_files.edit_record(vault, record_id, "## Captures\n", "## Captures\n\n- [idea] (claude) \"x\" ^c01\n")
    code, output = run("close", "stage", "--vault", str(vault), "--checkpoint", "--json")
    data = json.loads(output)
    assert any(n["rule"] == "session-private" for n in data["never"]), data
    assert not any("private" in p for p in data["staged"])
    assert "private" not in git(vault, "diff", "--cached", "--name-only")


def test_close_finish_closes_the_stub_and_writes_the_summary_privately(tmp_path, monkeypatch):
    vault, record_id = started(tmp_path, monkeypatch)
    with_remote(tmp_path, vault)
    assert run("close", "sync-main", "--vault", str(vault), "--today", TODAY)[0] == 0
    assert run("render", "--vault", str(vault))[0] == 0
    code, output = run("close", "finish", "--vault", str(vault), "--summary", "Filed the stock grill.",
                       "--today", TODAY)
    assert code == 0, output
    stub, private = session_files.stub_text(vault, record_id), session_files.record_text(vault, record_id)
    assert privaterecord.stub_meta(stub)["status"] == "closed" and "summary" not in privaterecord.stub_meta(stub)
    assert privaterecord.summary_of(private) == "Filed the stock grill."
    assert f"sessions/{record_id}.md" in git(vault, "show", "--name-only", "--format=", "HEAD~1")
    assert not any("private" in line for line in git(vault, "ls-files").split("\n"))


def test_open_records_filters_by_branch(tmp_path, monkeypatch):
    vault, record_id = started(tmp_path, monkeypatch)
    other = privaterecord.new_stub("2026-10-14-elsewhere", "Dump: elsewhere", TODAY, ["dump"], branch="session/other")
    (vault / "sessions" / "2026-10-14-elsewhere.md").write_text(other, encoding="utf-8")
    assert close_stage.open_records(vault) == [record_id]


def test_closed_stub_sets_the_status_and_nothing_else():
    stub = privaterecord.new_stub("2026-10-14-x", "Dump: x", TODAY, ["dump"], branch="main")
    closed = closefinish.closed_stub(stub)
    assert privaterecord.stub_meta(closed) == {**privaterecord.stub_meta(stub), "status": "closed"}


def test_a_stub_with_no_notes_here_is_said_not_papered_over(tmp_path, monkeypatch):
    vault, record_id = started(tmp_path, monkeypatch)
    (vault / "sessions" / "private" / f"{record_id}.md").unlink()
    code, output = run("record", "add", "--vault", str(vault), "--origin", "claude", "--tag", "idea", "x")
    assert code != 0 and "notes are not on this machine" in output
    assert not (vault / "sessions" / "private" / f"{record_id}.md").exists()
    code, output = run("close", "gate", "--vault", str(vault), "--today", TODAY)
    assert code != 0 and "notes are not on this machine" in output
