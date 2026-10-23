"""`vela session start`, `vela session brief` and `vela whoami` (overhaul Task 6b), in real repos in tmp_path with a
bare origin, and `gh` (and, for a reader copy, `git`) replaced by shims on PATH."""
import datetime
import json
import os
import shutil
import sys

from conftest import MINI, run
from sharing import advance_remote, git, make_vault, with_remote
import session_files
from vela.privaterecord import stub_meta

TODAY = "2026-10-14"
NO_SEND = ("I can file the session here, but I can't send it. Open Claude Code in this folder and type /vela:close "
           "to send it.")


def shim(tmp_path, monkeypatch, name, replies=None, fail=None):
    """Put a fake `name` first on PATH. `replies` maps the first few arguments, joined by spaces, to (exit, stdout);
    anything else exits 1 with `fail` (or a note) on stderr. Every call is logged to `<name>-calls`."""
    shims = tmp_path / "shims"
    shims.mkdir(exist_ok=True)
    log = tmp_path / f"{name}-calls"
    script = shims / name
    script.write_text(f"""#!{sys.executable}
import json, sys
args = sys.argv[1:]
with open({str(log)!r}, "a") as out:
    out.write(" ".join(args) + "\\n")
replies = {json.dumps(replies or {})!r}
for key, (code, text) in json.loads(replies).items():
    if " ".join(args).startswith(key):
        print(text)
        sys.exit(code)
print({(fail or f"{name} shim: not expected")!r}, file=sys.stderr)
sys.exit(1)
""", encoding="utf-8")
    script.chmod(0o755)
    monkeypatch.setenv("PATH", f"{shims}{os.pathsep}{os.environ['PATH']}")
    return log


def no_gh(tmp_path, monkeypatch):
    return shim(tmp_path, monkeypatch, "gh", fail="gh: not signed in (HTTP 401)")


def owner(tmp_path, monkeypatch, title=None):
    vault = make_vault(tmp_path)
    if title is not None:
        path = vault / ".vela.yaml"
        path.write_text(path.read_text(encoding="utf-8").replace("title: Mini shop", f"title: {title}"),
                        encoding="utf-8")
        git(vault, "commit", "-q", "-am", "placeholder title")
    no_gh(tmp_path, monkeypatch)
    return vault


def start(vault, *args):
    return run("session", "start", "--vault", str(vault), "--today", TODAY, *args)


def head(vault):
    return git(vault, "rev-parse", "HEAD"), git(vault, "rev-parse", "--abbrev-ref", "HEAD")


def test_start_on_main_stays_on_main_notes_it_and_says_a_review_needs_a_branch(tmp_path, monkeypatch):
    vault = owner(tmp_path, monkeypatch)
    with_remote(tmp_path, vault)
    began = git(vault, "rev-parse", "HEAD")
    code, output = start(vault, "--mode", "grill", "--topic", "desk agent calendar", "--for-lead")
    assert code == 0, output
    assert output.count("needs its own branch") == 1 and "make it" in output
    record_id = f"{TODAY}-desk-agent-calendar"
    assert head(vault)[1] == "main"
    assert git(vault, "log", "-1", "--format=%s") == f"Open session {record_id}"
    assert git(vault, "rev-parse", "HEAD~1") == began
    record = session_files.stub_text(vault, record_id)
    assert 'title: "Grill: desk agent calendar"' in record and "modes: [grill]" in record
    assert (stub_meta(record)["branch"], stub_meta(record)["start_commit"]) == ("main", began)
    state = json.loads((vault / ".vela" / "session.json").read_text(encoding="utf-8"))
    assert (state["id"], state["branch"]) == (record_id, "main")
    code, output = start(vault, "--mode", "grill", "--topic", "desk agent calendar", "--for-lead")
    assert code == 3  # the first one is open now


def test_start_on_a_feature_branch_stays_on_it_and_records_it(tmp_path, monkeypatch):
    vault = owner(tmp_path, monkeypatch)
    with_remote(tmp_path, vault)
    git(vault, "switch", "-q", "-c", "waiting-for-review")
    began = git(vault, "rev-parse", "HEAD")
    code, output = start(vault, "--mode", "grill", "--topic", "consent", "--for-lead")
    assert code == 0, output
    assert "needs its own branch" not in output  # said only on the default branch
    assert head(vault)[1] == "waiting-for-review"
    record = session_files.stub_text(vault, f"{TODAY}-consent")
    assert (stub_meta(record)["branch"], stub_meta(record)["start_commit"]) == ("waiting-for-review", began)
    assert git(vault, "rev-parse", "main") == began  # no pull, no switch, nothing committed to main


def test_new_branch_makes_a_session_branch_from_the_current_one(tmp_path, monkeypatch):
    vault = owner(tmp_path, monkeypatch)
    git(vault, "switch", "-q", "-c", "waiting-for-review")
    began = git(vault, "rev-parse", "HEAD")
    code, output = start(vault, "--mode", "grill", "--topic", "consent", "--new-branch", "--for-lead")
    assert code == 0, output
    assert "needs its own branch" not in output
    assert head(vault)[1] == f"session/{TODAY}-consent"
    assert git(vault, "rev-parse", "HEAD~1") == began
    record = session_files.stub_text(vault, f"{TODAY}-consent")
    assert (stub_meta(record)["branch"], stub_meta(record)["start_commit"]) == (f"session/{TODAY}-consent", began)


def test_open_sessions_exit_3_and_list(tmp_path, monkeypatch):
    vault = owner(tmp_path, monkeypatch)
    assert start(vault, "--mode", "shape", "--topic", "till options", "--new-branch")[0] == 0
    git(vault, "switch", "-q", "main")
    before = head(vault)
    code, output = start(vault, "--mode", "grill", "--topic", "consent", "--json")
    assert code == 3, output
    found = json.loads(output)
    assert [n["id"] for n in found["needs_lead"] if n["ask"] == "open session"] == [f"{TODAY}-till-options"]
    assert found["wrote"] == [] and head(vault) == before
    code, output = start(vault, "--mode", "grill", "--topic", "consent", "--for-lead")
    assert code == 3
    assert "Shape: till options" in output and "^c" not in output
    code, output = start(vault, "--mode", "grill", "--topic", "consent", "--new")
    assert code == 0, output
    assert head(vault)[1] == "main" and (vault / "sessions" / f"{TODAY}-consent.md").is_file()


def test_resume_switches_to_the_open_one(tmp_path, monkeypatch):
    vault = owner(tmp_path, monkeypatch)
    assert start(vault, "--mode", "shape", "--topic", "till options", "--new-branch")[0] == 0
    git(vault, "switch", "-q", "main")
    code, output = start(vault, "--resume", f"{TODAY}-till-options")
    assert code == 0, output
    assert head(vault)[1] == f"session/{TODAY}-till-options"


def test_a_dirty_tree_never_stops_a_start_that_pulls_nothing(tmp_path, monkeypatch):
    vault = owner(tmp_path, monkeypatch)
    bare = with_remote(tmp_path, vault)
    advance_remote(tmp_path, bare, text="from the teammate\n")  # adds note.md on origin's main
    (vault / "note.md").write_text("mine, not committed\n", encoding="utf-8")
    (vault / "01-goals.md").write_text((vault / "01-goals.md").read_text(encoding="utf-8") + "\nmine\n",
                                       encoding="utf-8")
    code, output = start(vault, "--mode", "grill", "--topic", "consent")
    assert code == 0, output
    assert "01-goals.md" in output  # carried into the session, unstaged, and said
    assert (vault / "note.md").read_text(encoding="utf-8") == "mine, not committed\n"  # nothing was pulled over it


def test_w718_exits_3_with_the_naming_question(tmp_path, monkeypatch):
    vault = owner(tmp_path, monkeypatch, title="New initiative")
    before = head(vault)
    code, output = start(vault, "--mode", "dump", "--topic", "kickoff", "--for-lead")
    assert code == 3, output
    assert "What short name should this initiative go by? A few words, as you would say it to a colleague." in output
    assert head(vault) == before
    code, output = start(vault, "--mode", "dump", "--topic", "kickoff", "--unnamed", "--for-lead")
    assert code == 0, output
    assert 'The dashboard will read "New initiative" until you give it a name.' in output


def test_title_written_and_committed(tmp_path, monkeypatch):
    vault = owner(tmp_path, monkeypatch, title="New initiative")
    code, output = start(vault, "--mode", "dump", "--topic", "kickoff", "--title", "Heron desk agent")
    assert code == 0, output
    assert git(vault, "log", "-2", "--format=%s").splitlines() == ["Name the initiative",
                                                                    f"Open session {TODAY}-kickoff"]
    assert 'title: "Heron desk agent"' in (vault / ".vela.yaml").read_text(encoding="utf-8")
    assert git(vault, "status", "--short", "--", ".vela.yaml") == ""


def test_no_network_in_host_json_said_at_start(tmp_path, monkeypatch):
    vault = owner(tmp_path, monkeypatch)
    with_remote(tmp_path, vault)
    (vault / ".vela").mkdir(exist_ok=True)
    (vault / ".vela" / "host.json").write_text(json.dumps(
        {"git": "yes", "network": "no", "gh": "no", "python": "3.12.1", "git_repo": True, "reader": False}),
        encoding="utf-8")
    code, output = start(vault, "--mode", "grill", "--topic", "consent", "--for-lead")
    assert code == 0, output
    assert output.splitlines()[0] == NO_SEND


def test_git_broken_in_host_json_refuses_with_the_reader_path(tmp_path, monkeypatch):
    vault = owner(tmp_path, monkeypatch)
    (vault / ".vela").mkdir(exist_ok=True)
    (vault / ".vela" / "host.json").write_text(json.dumps(
        {"git": "no", "network": "couldn't tell", "gh": "no", "python": "3.12.1", "git_repo": True}), encoding="utf-8")
    before = head(vault)
    code, output = start(vault, "--mode", "grill", "--topic", "consent", "--for-lead")
    assert code == 1, output
    assert "git doesn't run here" in output and "read, ask, find, explore and draft" in output
    assert head(vault) == before


def reader_copy(tmp_path):
    copy = tmp_path / "copy"
    shutil.copytree(MINI, copy)
    (copy / ".vela").mkdir()
    (copy / ".vela" / "workspace.json").write_text('{"role": "reader"}', encoding="utf-8")
    return copy


def test_reader_copy_uses_no_git(tmp_path, monkeypatch):
    copy = reader_copy(tmp_path)
    git_log = shim(tmp_path, monkeypatch, "git")
    gh_log = no_gh(tmp_path, monkeypatch)
    code, output = start(copy, "--mode", "challenge", "--topic", "pushback")
    assert code == 1, output  # a challenge is the owner's: it opens a pull request
    code, output = start(copy, "--mode", "discover", "--topic", "reading the sources")
    assert code == 0, output
    assert (copy / "sessions" / f"{TODAY}-reading-the-sources.md").is_file()
    code, output = run("session", "brief", "--vault", str(copy), "--today", TODAY, "--for-lead")
    assert code == 0, output
    assert "Review comments aren't checked in your copy." in output
    assert not git_log.exists(), "a reader copy ran git"
    assert not gh_log.exists(), "a reader copy ran gh"


def challenge_branch(vault, branch, record_id):
    git(vault, "switch", "-q", "-c", branch)
    session_files.write_record(vault, record_id,
        f"---\nid: {record_id}\ntype: session\ntitle: \"Challenge: CON-001\"\ndate: 2026-10-10\nmodes: [challenge]\n"
        "status: closed\nsummary: s.\n---\n\n# x\n\n## Captures\n\n## Changes\n")
    git(vault, "add", "sessions")
    git(vault, "commit", "-q", "-m", f"Open session {record_id}")
    git(vault, "push", "-q", "origin", branch)
    git(vault, "switch", "-q", "main")


def test_answer_pr_title_must_end_with_exact_id(tmp_path, monkeypatch):
    vault = make_vault(tmp_path)
    with_remote(tmp_path, vault)
    branch = "session/2026-10-10-challenge-con-001"
    challenge_branch(vault, branch, "2026-10-10-challenge-con-001")
    prs = [{"number": 7, "headRefName": "session/2026-10-09-challenge-con-0010", "title": "2026-10-09 Challenge: CON-0010"},
           {"number": 8, "headRefName": branch, "title": "2026-10-10 Challenge: CON-001"}]
    shim(tmp_path, monkeypatch, "gh", {"pr list": (0, json.dumps(prs))})
    code, output = start(vault, "--answer", "CON-001", "--json")
    assert code == 0, output
    record_id = f"{TODAY}-answer-con-001"
    assert head(vault)[1] == branch  # on the challenge's branch, no new one
    assert git(vault, "log", "-1", "--format=%s") == f"Open session {record_id}"
    record = session_files.stub_text(vault, record_id)
    assert "modes: [answer]" in record and 'title: "Answer: CON-001"' in record


def test_answer_none_or_several_exits_1_with_gh_output(tmp_path, monkeypatch):
    vault = make_vault(tmp_path)
    with_remote(tmp_path, vault)
    several = [{"number": 8, "headRefName": "session/a", "title": "2026-10-10 Challenge: CON-001"},
               {"number": 9, "headRefName": "session/b", "title": "2026-10-11 Challenge: CON-001"}]
    shim(tmp_path, monkeypatch, "gh", {"pr list": (0, json.dumps(several))})
    before = head(vault)
    code, output = start(vault, "--answer", "CON-001")
    assert code == 1, output
    assert "session/a" in output and "session/b" in output and head(vault) == before
    shutil.rmtree(tmp_path / "shims")
    only_longer = [{"number": 7, "headRefName": "session/c", "title": "2026-10-09 Challenge: CON-0010"}]
    shim(tmp_path, monkeypatch, "gh", {"pr list": (0, json.dumps(only_longer))})
    code, output = start(vault, "--answer", "CON-001")
    assert code == 1, output
    assert "CON-0010" in output and head(vault) == before  # what gh returned is shown, never a guessed branch


def test_brief_gh_failure_is_a_line_not_silence(tmp_path, monkeypatch):
    vault = make_vault(tmp_path)
    no_gh(tmp_path, monkeypatch)
    code, output = run("session", "brief", "--vault", str(vault), "--today", TODAY, "--json")
    assert code == 2, output
    found = json.loads(output)
    assert found["review_comments"] is None  # not [], which would read as "no comments"
    assert any("gh could not list merged PRs (gh: not signed in (HTTP 401))" in line for line in found["lines"])
    assert found["next"], "the rest of the brief still runs"
    code, output = run("session", "brief", "--vault", str(vault), "--today", TODAY, "--for-lead")
    assert code == 2 and "I couldn't reach GitHub, so I haven't checked for review comments" in output


def test_brief_offers_review_comments_as_candidate_captures(tmp_path, monkeypatch):
    vault = make_vault(tmp_path)
    shim(tmp_path, monkeypatch, "gh", {
        "pr list": (0, json.dumps([{"number": 4, "title": "Close session x", "url": "https://x/4"}])),
        "pr view 4": (0, json.dumps({"comments": [{"author": {"login": "sam"}, "body": "Is the till offline-first?"}],
                                     "reviews": [{"author": {"login": "kai"}, "body": "", "state": "APPROVED"}]})),
        "api repos/{owner}/{repo}/pulls/4/comments": (0, json.dumps([{"user": {"login": "kai"},
                                                                       "body": "Name the queue."}]))})
    code, output = run("session", "brief", "--vault", str(vault), "--today", TODAY, "--json")
    assert code == 0, output
    comments = json.loads(output)["review_comments"]
    assert [(c["author"], c["body"]) for c in comments] == [("sam", "Is the till offline-first?"),
                                                             ("kai", "Name the queue.")]


def test_brief_names_overdue_unknowns_by_name_for_the_lead(tmp_path, monkeypatch):
    vault = make_vault(tmp_path)
    no_gh(tmp_path, monkeypatch)
    code, output = run("session", "brief", "--vault", str(vault), "--today", "2030-01-01", "--json")
    overdue = json.loads(output)["overdue"]
    assert overdue and all(u["ask_by"] < "2030-01-01" for u in overdue)
    code, output = run("session", "brief", "--vault", str(vault), "--today", "2030-01-01", "--for-lead")
    assert overdue[0]["id"] not in output and overdue[0]["name"] in output


def test_whoami_cached_and_exit_3_when_unknown(tmp_path, monkeypatch):
    vault = make_vault(tmp_path)
    shim(tmp_path, monkeypatch, "gh", {"api user": (0, "priya-n")})
    code, output = run("whoami", "--vault", str(vault))
    assert (code, output) == (0, "priya-n\n")
    assert (vault / ".vela" / "handle").read_text(encoding="utf-8") == "priya-n\n"
    shutil.rmtree(tmp_path / "shims")
    (tmp_path / "gh-calls").unlink()
    log = no_gh(tmp_path, monkeypatch)
    assert run("whoami", "--vault", str(vault)) == (0, "priya-n\n")  # cached: gh isn't asked again
    assert not log.exists()
    (vault / ".vela" / "handle").unlink()
    code, output = run("whoami", "--vault", str(vault), "--json")
    assert code == 3, output
    assert json.loads(output)["needs_lead"][0]["ask"] == "handle"
    assert run("whoami", "--vault", str(vault), "--set", "@Priya-N")[0] == 0
    assert run("whoami", "--vault", str(vault)) == (0, "Priya-N\n")
    assert run("whoami", "--vault", str(vault), "--set", "not a handle")[0] == 1


def test_vela_capture_counts_still_parse(tmp_path):
    """`tests/sim/run.py` reads `vela capture --json`; `record add` must never have taken its name."""
    code, output = run("capture", "--vault", str(MINI), "--json")
    assert code == 0, output
    counts = json.loads(output)["counts"]
    assert {"apps", "unknowns", "asks", "releases"} <= set(counts)


def test_today_is_the_default_date(tmp_path, monkeypatch):
    vault = owner(tmp_path, monkeypatch)
    code, output = run("session", "start", "--vault", str(vault), "--mode", "grill", "--topic", "x", "--json")
    assert code == 0, output
    assert json.loads(output)["id"] == f"{datetime.date.today().isoformat()}-x"


def dashboard_on_main_and_changed_on_origin(tmp_path, vault):
    """The confirm run's sequence: main has a committed dashboard, a merged session rebuilt it on origin, and a
    no-session close rebuilt it here and left it uncommitted."""
    bare = with_remote(tmp_path, vault)
    (vault / "dashboard.html").write_text("<p>first build</p>\n", encoding="utf-8")
    git(vault, "add", "dashboard.html")
    git(vault, "commit", "-q", "-m", "Rebuild dashboard")
    git(vault, "push", "-q", "origin", "main")
    other = tmp_path / "teammate"
    git(tmp_path, "clone", "-q", str(bare), str(other))
    git(other, "config", "user.name", "Teammate")
    git(other, "config", "user.email", "t@example.com")
    (other / "dashboard.html").write_text("<p>a merged session's build</p>\n", encoding="utf-8")
    git(other, "commit", "-q", "-am", "Rebuild dashboard")
    git(other, "push", "-q", "origin", "main")
    code, output = run("close", "dashboard", "--vault", str(vault), "--today", TODAY, "--json")
    assert code == 3, output  # the branch offer; the page is left changed until the lead answers
    assert "dashboard.html" in git(vault, "status", "--short")


def test_a_dashboard_left_by_a_no_session_close_never_stops_the_next_start(tmp_path, monkeypatch):
    vault = owner(tmp_path, monkeypatch)
    dashboard_on_main_and_changed_on_origin(tmp_path, vault)
    left = (vault / "dashboard.html").read_bytes()
    code, output = start(vault, "--mode", "grill", "--topic", "consent", "--json")
    assert code == 0, output
    found = json.loads(output)
    assert not [n for n in found["needs_lead"] if n.get("ask") == "uncommitted changes"]
    assert head(vault)[1] == "main"
    assert (vault / "dashboard.html").read_bytes() == left  # set aside and written back, not dropped
    code, output = start(vault, "--resume", f"{TODAY}-consent", "--for-lead")
    assert code == 0 and "dashboard" not in output, output  # the lead never hears about vela's own page


def test_turning_the_dashboard_branch_down_leaves_main_clean(tmp_path, monkeypatch):
    vault = owner(tmp_path, monkeypatch)
    dashboard_on_main_and_changed_on_origin(tmp_path, vault)
    code, output = run("close", "dashboard", "--vault", str(vault), "--today", TODAY, "--put-back", "--for-lead")
    assert code == 0, output
    assert "I've left the dashboard as it was" in output
    assert git(vault, "status", "--short", "--untracked-files=no") == "" and head(vault)[1] == "main"
    assert (vault / "dashboard.html").read_text(encoding="utf-8") == "<p>first build</p>\n"
    code, output = start(vault, "--mode", "grill", "--topic", "consent")
    assert code == 0, output
    assert (vault / "dashboard.html").read_text(encoding="utf-8") == "<p>first build</p>\n"  # a start pulls nothing
