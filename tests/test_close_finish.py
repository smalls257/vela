"""`vela close finish` and `vela close dashboard` (overhaul Task 11) against a real vault repo: the close commit, then
each handoff manifest alone, then the dashboard alone, in that order; a replaced manifest needs `--replace` and the
app's team's own yes, or nothing is written; a dashboard that fails never undoes the close; with no session the
dashboard is never committed to main; a read copy commits nothing."""
import shutil
import subprocess

from conftest import run
from vela import closefinish, closegate, handoff, parse, privaterecord, say
from sharing import git, make_vault, with_remote
import session_files

RECORD = "2026-10-20-grill-stock"
STOCK = "05-building-blocks/stock-building-blocks.md"
TODAY = "2026-10-20"
SUMMARY = "Handed stock to its team: colon: and all."


def record_text(captures=()):
    lines = ["---", f"id: {RECORD}", "type: session", "date: 2026-10-20", "modes: [grill]", "status: open",
             "summary: In progress.", "---", "", "# 2026-10-20 Stock grill", "", "## Captures", "", *captures, "",
             "## Changes", "", "| ID | From | To | Source |", "|---|---|---|---|"]
    return "\n".join(lines) + "\n"


def hand_off(vault, value, pr="pending"):
    page = vault / STOCK
    text = page.read_text(encoding="utf-8")
    meta_end = text.index("\n---", 3)
    head, rest = text[:meta_end], text[meta_end:]
    head = "\n".join(line for line in head.split("\n") if not line.startswith("handed_off"))
    page.write_text(f'{head}\nhanded_off: "{value}"\nhanded_off_pr: {pr}{rest}', encoding="utf-8")


def session(tmp_path, sync=True, handed=None, captures=(), on_main=None):
    vault = make_vault(tmp_path)
    with_remote(tmp_path, vault)
    with open(vault / ".git" / "info" / "exclude", "a", encoding="utf-8") as ignore:
        ignore.write(".vela/*\n")  # as a real vault's .gitignore does: tool state never shows as a change
    if on_main:
        on_main(vault)
    git(vault, "switch", "-q", "-c", f"session/{RECORD}")
    session_files.write_record(vault, RECORD, record_text())
    git(vault, "add", "sessions")
    git(vault, "commit", "-q", "-m", f"Open session {RECORD}")
    if sync:
        assert run("close", "sync-main", "--vault", str(vault), "--today", TODAY)[0] == 0
    if handed:
        hand_off(vault, handed)
    session_files.write_record(vault, RECORD, record_text(captures))
    assert run("render", "--vault", str(vault))[0] == 0
    return vault


def finish(vault, *flags):
    return run("close", "finish", "--vault", str(vault), "--summary", SUMMARY, "--today", TODAY, *flags)


def subjects(vault, n):
    return git(vault, "log", f"-{n}", "--format=%s").split("\n")


def files_in(vault, ref):
    return git(vault, "show", "--name-only", "--format=", ref).split("\n")


def record_meta(vault):
    """The committed stub's header with the private notes' own keys (the summary) laid over it."""
    notes = parse.split_frontmatter(session_files.record_text(vault, RECORD))[0]
    return {**privaterecord.stub_meta(session_files.stub_text(vault, RECORD)), **notes}


def manifest_already_accepted(vault):
    """On main, before the session: stock was handed off and its team accepted the manifest."""
    hand_off(vault, "@stock-team, 2026-10-01", pr="7")
    assert run("render", "--vault", str(vault))[0] == 0
    git(vault, "add", "-A")
    git(vault, "commit", "-q", "-m", "hand off stock")
    assert run("handoff", "APP-stock", "--vault", str(vault), "--today", "2026-10-01")[0] == 0
    git(vault, "add", "handoffs")
    git(vault, "commit", "-q", "-m", "Handoff manifest for APP-stock")
    git(vault, "push", "-q", "origin", "main")


TEAM_YES = '- [decision] (@stock-team) "Yes, we take the changes to stock." → park ^c01'


def test_commit_order_close_then_manifest_then_dashboard(tmp_path):
    vault = session(tmp_path, handed="@stock-team, 2026-10-20")
    code, out = finish(vault)
    assert code == 0, out
    assert subjects(vault, 3) == ["Rebuild dashboard", "Handoff manifest for APP-stock", f"Close session {RECORD}"]
    assert files_in(vault, "HEAD") == ["dashboard.html"]
    assert files_in(vault, "HEAD~1") == ["handoffs/APP-stock.md"]
    close = files_in(vault, "HEAD~2")
    assert f"sessions/{RECORD}.md" in close and STOCK in close and "dashboard.html" not in close
    assert record_meta(vault)["status"] == "closed" and record_meta(vault)["summary"] == SUMMARY
    assert not git(vault, "status", "--porcelain", "--", "sessions", "handoffs", "dashboard.html")


def test_manifest_written_after_close_commit_and_names_it(tmp_path):
    vault = session(tmp_path, handed="@stock-team, 2026-10-20")
    code, out = finish(vault, "--for-lead")
    assert code == 0, out
    close_sha = git(vault, "rev-parse", "--short", "HEAD~2")
    facts, _ = handoff.read((vault / "handoffs" / "APP-stock.md").read_text(encoding="utf-8"))
    assert facts["Commit"] == close_sha, facts
    assert closefinish.DASHBOARD_DONE in out and say.leak_in(out) is None, out


def test_the_lead_hears_what_is_not_settled_at_handoff(tmp_path):
    def assumed(vault):
        page = vault / STOCK
        page.write_text(page.read_text(encoding="utf-8").replace("- **State:** fact", "- **State:** assumption", 1),
                        encoding="utf-8")
        git(vault, "commit", "-qam", "stock level is only assumed")
        git(vault, "push", "-q", "origin", "main")
    vault = session(tmp_path, handed="@stock-team, 2026-10-20", on_main=assumed)
    code, out = finish(vault, "--for-lead", "--more")
    assert code == 0, out
    assert closefinish.NOT_SETTLED_HEAD.format(app="Stock") in out
    assert "Nobody has said yes to Stock level yet." in out and say.leak_in(out) is None  # grouped, row 155


def test_replace_without_team_yes_exits_3(tmp_path):
    vault = session(tmp_path, handed="@stock-team, 2026-10-20", on_main=manifest_already_accepted)
    head = git(vault, "rev-parse", "HEAD")
    for flags in ((), ("--replace",)):
        code, out = finish(vault, "--json", *flags)
        assert code == 3, out
        assert git(vault, "rev-parse", "HEAD") == head and record_meta(vault)["status"] == "open"
        assert git(vault, "show", "HEAD:handoffs/APP-stock.md") == (vault / "handoffs" / "APP-stock.md").read_text(
            encoding="utf-8").rstrip("\n")
    session_files.write_record(vault, RECORD, record_text([TEAM_YES]))
    code, out = finish(vault, "--replace")
    assert code == 0, out
    assert subjects(vault, 3) == ["Rebuild dashboard", "Handoff manifest for APP-stock", f"Close session {RECORD}"]


def test_a_bare_ok_from_the_team_is_not_a_yes():
    meta = {"owner": "@stock-team", "handed_off": "Sam Lee, 2026-10-20", "handed_off_pr": "pending"}
    assert closefinish.team_yes(record_text(['- [decision] (@stock-team) "ok" → park ^c01']), meta) is None
    assert closefinish.team_yes(record_text(['- [decision] (claude, from @stock-team) yes → park ^c01']), meta) is None
    assert closefinish.team_yes(record_text(['- [decision] (@someone-else) "Yes, go." → park ^c01']), meta) is None
    found = closefinish.team_yes(record_text(['- [decision] (Sam Lee) "Yes, go." → park ^c01']), meta)
    assert isinstance(found, closegate.Capture) and found.n == "01"


def test_gate_not_ready_exits_1(tmp_path):
    vault = session(tmp_path, sync=False)
    head = git(vault, "rev-parse", "HEAD")
    code, out = finish(vault, "--for-lead")
    assert code == 1, out
    assert "before I can finish" in out and say.leak_in(out) is None
    _, default = finish(vault)
    assert "vela close gate" in default
    assert git(vault, "rev-parse", "HEAD") == head and record_meta(vault)["status"] == "open"


def test_dashboard_failure_never_undoes_close(tmp_path, monkeypatch):
    from vela.explorer import build
    vault = session(tmp_path)

    def broken(*args, **kwargs):
        raise build.ExplorerError("the page template is missing")
    monkeypatch.setattr(build, "generate", broken)
    code, out = finish(vault, "--for-lead")
    assert code == 0, out
    assert "The dashboard couldn't be updated: the page template is missing. Everything else is filed." in out
    assert closefinish.DASHBOARD_DONE not in out
    assert subjects(vault, 1) == [f"Close session {RECORD}"] and record_meta(vault)["status"] == "closed"


def test_no_session_path_does_not_commit_to_main(tmp_path):
    vault = make_vault(tmp_path)
    with_remote(tmp_path, vault)
    head = git(vault, "rev-parse", "HEAD")
    code, out = run("close", "dashboard", "--vault", str(vault), "--today", TODAY, "--for-lead")
    assert code == 3, out
    assert closefinish.NO_SESSION_DASHBOARD in out and say.leak_in(out) is None
    assert (vault / "dashboard.html").is_file()
    assert git(vault, "rev-parse", "HEAD") == head and git(vault, "branch", "--show-current") == "main"
    code, out = run("close", "dashboard", "--vault", str(vault), "--today", TODAY, "--branch")
    assert code == 0, out
    assert git(vault, "branch", "--show-current") == f"dashboard/{TODAY}"
    assert files_in(vault, "HEAD") == ["dashboard.html"] and subjects(vault, 1) == ["Rebuild dashboard"]
    assert git(vault, "rev-parse", "main") == head


def test_dashboard_with_a_session_open_leaves_it_for_the_close(tmp_path):
    vault = session(tmp_path)
    head = git(vault, "rev-parse", "HEAD")
    code, out = run("close", "dashboard", "--vault", str(vault), "--today", TODAY, "--for-lead")
    assert code == 0 and "when you finish this session" in out, out
    assert git(vault, "rev-parse", "HEAD") == head


def test_reader_finish_stages_nothing(tmp_path, monkeypatch):
    vault = session(tmp_path)
    shutil.rmtree(vault / ".git")
    (vault / ".vela").mkdir(exist_ok=True)
    (vault / ".vela" / "workspace.json").write_text('{"author": "Sam"}', encoding="utf-8")
    assert run("close", "sync-main", "--vault", str(vault), "--today", TODAY)[0] == 0

    def no_programs(*args, **kwargs):
        raise AssertionError(f"a reader copy ran a program: {args[0] if args else kwargs}")
    monkeypatch.setattr(subprocess, "Popen", no_programs)
    monkeypatch.setattr(subprocess, "run", no_programs)
    code, out = finish(vault, "--for-lead")
    assert code == 0, out
    assert closefinish.READER_NOTHING_COMMITTED in out and say.leak_in(out) is None
    assert record_meta(vault)["status"] == "closed"


def test_summary_must_be_one_line(tmp_path):
    vault = session(tmp_path)
    code, out = run("close", "finish", "--vault", str(vault), "--summary", "two\nlines", "--today", TODAY)
    assert code == 2 and "one line" in out, out
    assert record_meta(vault)["status"] == "open"


def test_the_steps_run_in_one_order():
    due = closefinish.Handoff("APP-stock", "Stock", exists=False)
    steps = [s for s, _ in closefinish.plan(False, (due,), False).steps]
    assert steps == [closefinish.RECORD, closefinish.CLOSE_COMMIT, closefinish.MANIFEST, closefinish.DASHBOARD_BUILD,
                     closefinish.DASHBOARD_COMMIT]
    assert [s for s, _ in closefinish.plan(True, (due,), False).steps] == [closefinish.RECORD,
                                                                           closefinish.DASHBOARD_BUILD]


def test_closing_sets_the_stub_status_and_quotes_the_summary_in_the_notes():
    split = privaterecord.split_record(record_text())
    stub = closefinish.closed_stub(split.stub)
    assert privaterecord.stub_meta(stub)["status"] == "closed" and "summary" not in privaterecord.stub_meta(stub)
    notes = privaterecord.with_summary(split.private, 'Said "yes": to stock')
    assert parse.split_frontmatter(notes)[0]["summary"] == 'Said "yes": to stock'
    assert notes.split("---", 2)[2] == split.private.split("---", 2)[2]


def test_close_tells_the_lead_which_yeses_wait_for_a_short_grill(tmp_path):
    """E81: a yes in a session that can't decide is listed for the next grill; close says so, in words and no IDs."""
    vault = session(tmp_path)
    page = vault / STOCK
    page.write_text(page.read_text(encoding="utf-8").replace("- **State:** fact", "- **State:** assumption", 1),
                    encoding="utf-8")
    session_files.edit_record(
        vault, RECORD, "## Captures",
        f"## Ready to decide\n\n- CON-002: the lead said yes in {RECORD} (^c01)\n\n## Captures")
    stub = vault / "sessions" / f"{RECORD}.md"
    stub.write_text(privaterecord.synced_stub(stub.read_text(encoding="utf-8"),
                                              session_files.record_text(vault, RECORD)), encoding="utf-8")
    assert run("render", "--vault", str(vault))[0] == 0
    code, out = finish(vault, "--for-lead")
    assert code == 0, out
    assert "One item you said yes to is ready for a short grill: Stock level." in out
    assert "CON-002" not in out
