"""`planner close sync-main` against real repos: a bare origin, the lead's clone on a session branch, and a second clone
that moves main. The first caller is the CLI itself, through conftest's `run`."""
import json
import subprocess

import pytest

from conftest import run
from planner import closestate, say
from planner.edge import mergegit, vaultgit

TODAY = "2026-10-14"
FILLER = [f"Filler line {n}." for n in range(1, 9)]  # keeps edits far enough apart that git merges them separately


def git(cwd, *args):
    done = subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True, timeout=30)
    assert done.returncode == 0, (args, done.stdout, done.stderr)
    return done.stdout.strip()


def block(content, sha="aaaaaaaa", name="summary"):
    return [f"<!-- generated:{name} sha={sha}: do not edit, run planner render -->", *content,
            f"<!-- /generated:{name} -->"]


def page(intro="Intro paragraph.", summary=("- line one",), sha="aaaaaaaa", outro="Closing paragraph.",
         title="Goals"):
    lines = ["---", "id: goals", "type: goals", f"title: {title}", "---", "", "# Goals", "", intro, "", *FILLER, "",
             *block(list(summary), sha), "", *FILLER, "", outro]
    return "\n".join(lines) + "\n"


@pytest.fixture
def repos(tmp_path, monkeypatch):
    """(lead, other): the lead's clone on session/x, and a clone that pushes to main."""
    for who in ("AUTHOR", "COMMITTER"):
        monkeypatch.setenv(f"GIT_{who}_NAME", "Test Lead")
        monkeypatch.setenv(f"GIT_{who}_EMAIL", "lead@example.com")
    origin, seed = tmp_path / "origin.git", tmp_path / "seed"
    git(tmp_path, "init", "--bare", "-b", "main", str(origin))
    git(tmp_path, "init", "-b", "main", str(seed))
    (seed / "01-goals.md").write_text(page(), encoding="utf-8")
    (seed / "notes.md").write_text("notes\n", encoding="utf-8")
    git(seed, "add", "01-goals.md", "notes.md")
    git(seed, "commit", "-m", "start")
    git(seed, "remote", "add", "origin", str(origin))
    git(seed, "push", "-q", "origin", "main")
    lead, other = tmp_path / "lead", tmp_path / "other"
    git(tmp_path, "clone", "-q", str(origin), str(lead))
    git(tmp_path, "clone", "-q", str(origin), str(other))
    git(lead, "checkout", "-q", "-b", "session/x")
    return lead, other


def commit(repo, files, message, push=False):
    for name, content in files.items():
        (repo / name).write_text(content, encoding="utf-8")
    git(repo, "add", *files)
    git(repo, "commit", "-q", "-m", message)
    if push:
        git(repo, "push", "-q", "origin", "HEAD:main")


def sync(lead, *flags):
    return run("close", "sync-main", "--vault", str(lead), "--today", TODAY, *flags)


def state(lead, key="session__x"):
    return json.loads((lead / ".planner" / "close" / f"{key}.json").read_text(encoding="utf-8"))


def test_up_to_date(repos):
    lead, _ = repos
    code, out = sync(lead)
    assert code == 0 and "up to date" in out, out
    rec = state(lead)
    assert rec["status"] == closestate.UP_TO_DATE and rec["date"] == TODAY
    assert rec["main"] == git(lead, "rev-parse", "origin/main") == rec["head"]


def test_clean_merge(repos):
    lead, other = repos
    commit(other, {"notes.md": "notes from main\n"}, "main moves", push=True)
    commit(lead, {"01-goals.md": page(intro="Our intro.")}, "session edit")
    code, out = sync(lead, "--json")
    assert code == 0, out
    result = json.loads(out)
    assert result["status"] == closestate.MERGED and "notes.md" in result["wrote"]
    assert (lead / "notes.md").read_text(encoding="utf-8") == "notes from main\n"
    assert state(lead)["head"] == git(lead, "rev-parse", "HEAD")
    assert git(lead, "status", "--porcelain", "--untracked-files=no") == ""


def test_conflicts_only_in_generated_blocks_keep_both_clean_edits(repos):
    """Both sides re-rendered the block (so even the sha line differs), and each side also edited writing outside it.
    -X ours settles only the block; both clean edits survive."""
    lead, other = repos
    commit(other, {"01-goals.md": page(summary=["- theirs"], sha="22222222", outro="Main's closing.")}, "main", push=True)
    commit(lead, {"01-goals.md": page(summary=["- ours"], sha="11111111", intro="Our intro.")}, "session")
    code, out = sync(lead)
    assert code == 0, out
    merged = (lead / "01-goals.md").read_text(encoding="utf-8")
    assert "Our intro." in merged and "Main's closing." in merged
    assert "- ours" in merged and "<<<<<<<" not in merged
    rec = state(lead)
    assert rec["status"] == closestate.MERGED_GENERATED and rec["files"][0]["path"] == "01-goals.md"
    assert git(lead, "rev-parse", "HEAD^2") == git(lead, "rev-parse", "origin/main")  # a real merge, not a checkout


def test_conflict_outside_generated_aborts_and_lists_lines(repos):
    lead, other = repos
    commit(other, {"01-goals.md": page(intro="Main's intro.")}, "main", push=True)
    commit(lead, {"01-goals.md": page(intro="Our intro.")}, "session")
    head = git(lead, "rev-parse", "HEAD")
    code, out = sync(lead)
    assert code == 1, out
    assert "01-goals.md: 9 outside a generated block" in out, out
    assert git(lead, "rev-parse", "HEAD") == head and not mergegit.merging(lead)
    assert "Our intro." in (lead / "01-goals.md").read_text(encoding="utf-8")
    rec = state(lead)
    assert rec["status"] == closestate.CONFLICT and rec["files"] == [{"path": "01-goals.md", "title": "Goals",
                                                                      "lines": ["9"]}]


def test_hunk_straddling_a_generated_marker_counts_as_outside(repos):
    """Main moved the block's closing marker past the closing paragraph while the session edited both: one hunk that
    holds the marker and hand-written text. It is outside, so the merge stops."""
    lead, other = repos
    straddled = page().replace("- line one\n<!-- /generated:summary -->", "- main's line")
    straddled = straddled.replace("Closing paragraph.", "Closing paragraph.\n<!-- /generated:summary -->")
    commit(other, {"01-goals.md": straddled}, "main", push=True)
    commit(lead, {"01-goals.md": page(summary=["- ours"], outro="Our closing.")}, "session")
    head = git(lead, "rev-parse", "HEAD")
    code, out = sync(lead)
    assert code == 1, out
    assert git(lead, "rev-parse", "HEAD") == head and not mergegit.merging(lead)
    rec = state(lead)
    assert rec["status"] == closestate.CONFLICT
    # Lines 21-22 are our "- ours" and the closing marker: the hunk that starts inside the block and leaves it.
    assert "21-22" in rec["files"][0]["lines"], rec


def test_fetch_failure_exits_3_not_compared(repos, tmp_path):
    lead, _ = repos
    git(lead, "remote", "set-url", "origin", str(tmp_path / "nowhere.git"))
    head = git(lead, "rev-parse", "HEAD")
    code, out = sync(lead, "--json")
    assert code == 3, out
    result = json.loads(out)
    assert {c["choice"] for c in result["needs_lead"]} == {"retry", "go-on"} and result["wrote"] == []
    assert state(lead)["status"] == closestate.NOT_COMPARED and state(lead)["reason"] == closestate.FETCH_FAILED
    assert git(lead, "rev-parse", "HEAD") == head
    code, out = sync(lead, "--for-lead")
    assert out.strip() == ("I couldn't reach the shared copy, so this branch isn't compared with main yet. "
                           "Go on without it, or try again?")


def test_dirty_tracked_files_exit_3_and_change_nothing(repos):
    lead, other = repos
    commit(other, {"notes.md": "notes from main\n"}, "main moves", push=True)
    (lead / "01-goals.md").write_text(page(intro="Unsaved edit."), encoding="utf-8")
    head = git(lead, "rev-parse", "HEAD")
    code, out = sync(lead)
    assert code == 3 and "planner close stage --checkpoint" in out, out
    assert git(lead, "rev-parse", "HEAD") == head and not mergegit.merging(lead)
    assert "Unsaved edit." in (lead / "01-goals.md").read_text(encoding="utf-8")
    assert (lead / "notes.md").read_text(encoding="utf-8") == "notes\n"
    assert state(lead)["reason"] == closestate.UNCOMMITTED


def test_accept_not_compared_is_recorded(repos, tmp_path):
    lead, _ = repos
    git(lead, "remote", "set-url", "origin", str(tmp_path / "nowhere.git"))
    assert sync(lead)[0] == 3
    code, out = sync(lead, "--accept-not-compared")
    assert code == 0, out
    verdict = mergegit.sync_verdict(lead)
    assert state(lead)["status"] == closestate.ACCEPTED and not verdict.blocks and verdict.listed


def test_reader_copy_runs_no_git(tmp_path, monkeypatch):
    copy = tmp_path / "copy"
    (copy / ".planner").mkdir(parents=True)
    (copy / ".planner" / "workspace.json").write_text("{}", encoding="utf-8")

    def no_git(*args, **kwargs):
        raise AssertionError(f"a read copy ran git: {args}")
    monkeypatch.setattr(vaultgit, "run_git", no_git)
    code, out = run("close", "sync-main", "--vault", str(copy), "--today", TODAY, "--for-lead")
    assert code == 0 and out.strip() == "This is a read copy, so there is no main to bring in.", out
    rec = json.loads((copy / ".planner" / "close" / f"{closestate.READER_KEY}.json").read_text(encoding="utf-8"))
    assert rec["status"] == closestate.READER
    assert not mergegit.sync_verdict(copy).blocks


def test_for_lead_lines_pass_the_leak_check(repos):
    """A page with no title whose file name holds an ID is named by a stand-in, never by the ID."""
    lead, other = repos
    for repo in (lead, other):
        git(repo, "fetch", "-q", "origin")
    commit(other, {"UNK-12-consent.md": "main's text\n"}, "main", push=True)
    commit(lead, {"UNK-12-consent.md": "our text\n", "01-goals.md": page(intro="Our intro.")}, "session")
    commit(other, {"01-goals.md": page(intro="Main's intro.")}, "main 2", push=True)
    code, out = sync(lead, "--for-lead")
    assert code == 1, out
    for line in out.splitlines():
        assert say.leak_in(line) is None, line
    assert 'Main changed "Goals" while we worked on it, so I stopped the merge.' in out
    assert "a page whose title I couldn't read" in out


def test_sync_not_run_blocks_in_the_gate_verdict(repos):
    lead, _ = repos
    assert mergegit.sync_verdict(lead).blocks
    assert closestate.verdict({"status": closestate.NOT_COMPARED}).blocks
