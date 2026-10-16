"""`vela close sync-main` against real repos: a bare origin, the lead's clone on a session branch, and a second clone
that moves main. The first caller is the CLI itself, through conftest's `run`."""
import json
import subprocess

import pytest

from conftest import run
from vela import closestate, say
from vela.edge import mergegit, vaultgit

TODAY = "2026-10-14"
FILLER = [f"Filler line {n}." for n in range(1, 9)]  # keeps edits far enough apart that git merges them separately


def git(cwd, *args):
    done = subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True, timeout=30)
    assert done.returncode == 0, (args, done.stdout, done.stderr)
    return done.stdout.strip()


def block(content, sha="aaaaaaaa", name="summary"):
    return [f"<!-- generated:{name} sha={sha}: do not edit, run vela render -->", *content,
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
    return json.loads((lead / ".vela" / "close" / f"{key}.json").read_text(encoding="utf-8"))


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
    assert out.strip() == ("I couldn't reach main, so I haven't checked for newer changes. "
                           "Try again, or go on without them?")  # voice audit row 127: one name for main


def test_dirty_tracked_files_exit_3_and_change_nothing(repos):
    lead, other = repos
    commit(other, {"notes.md": "notes from main\n"}, "main moves", push=True)
    (lead / "01-goals.md").write_text(page(intro="Unsaved edit."), encoding="utf-8")
    head = git(lead, "rev-parse", "HEAD")
    code, out = sync(lead)
    assert code == 3 and "vela close stage --checkpoint" in out, out
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
    (copy / ".vela").mkdir(parents=True)
    (copy / ".vela" / "workspace.json").write_text("{}", encoding="utf-8")

    def no_git(*args, **kwargs):
        raise AssertionError(f"a read copy ran git: {args}")
    monkeypatch.setattr(vaultgit, "run_git", no_git)
    code, out = run("close", "sync-main", "--vault", str(copy), "--today", TODAY, "--for-lead")
    assert code == 0 and out.strip() == "This is your copy, so there is no main to bring in.", out
    rec = json.loads((copy / ".vela" / "close" / f"{closestate.READER_KEY}.json").read_text(encoding="utf-8"))
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
    assert 'On "Goals", both sides changed the same lines.' in out  # voice audit row 126: no line numbers
    assert out.startswith("Someone changed the same paragraphs on main") and "Want to see both versions?" in out
    assert "a page whose title I couldn't read" in out


def test_a_conflict_with_no_title_in_its_text_is_named_from_the_vault(repos):
    """Voice audit row 126: when the conflicted text gives no title, the page is named the way the vault names it
    (here its first heading), not by the "couldn't read" stand-in."""
    lead, other = repos
    for repo in (lead, other):
        git(repo, "fetch", "-q", "origin")
    commit(other, {"UNK-12-consent.md": "# Consent check\n\nmain's text\n"}, "main", push=True)
    commit(lead, {"UNK-12-consent.md": "# Consent check\n\nour text\n",
                  ".vela.yaml": "initiative: INI-001\ntitle: Heron\n"}, "session")
    code, out = sync(lead, "--for-lead")
    assert code == 1, out
    assert 'On "Consent check", both sides changed the same lines.' in out, out
    assert "couldn't read" not in out


def test_sync_not_run_blocks_in_the_gate_verdict(repos):
    lead, _ = repos
    assert mergegit.sync_verdict(lead).blocks
    assert closestate.verdict({"status": closestate.NOT_COMPARED}).blocks


CACHE = ".vela/flowcheck-cache.json"


def test_the_one_porcelain_parser_keeps_every_letter():
    out = " M dashboard.html\0R  new name.md\0old name.md\0?? .vela/flowcheck-cache.json\0"
    assert vaultgit.parse_porcelain(out) == ["dashboard.html", "new name.md", ".vela/flowcheck-cache.json"]


def commit_cache(repo, text, message):
    (repo / ".vela").mkdir(exist_ok=True)
    (repo / CACHE).write_text(text, encoding="utf-8")
    git(repo, "add", "-f", CACHE)  # the model's own `git add ... .vela/flowcheck-cache.json` (S7 T202)
    git(repo, "commit", "-q", "-m", message)


def test_a_committed_cache_vela_rewrites_does_not_block_sync(repos):
    """The midpoint's S7 then S21: the model committed vela's cache, check-slice rewrote it, main moved, sync-main.
    `close stage` never stages `.vela/`, so asking for a checkpoint commit of it was a deadlock."""
    lead, other = repos
    commit_cache(lead, '{"v": 1}\n', "Settle timeouts and retries")
    commit(lead, {"01-goals.md": page(intro="Our intro.")}, "session edit")
    (lead / CACHE).write_text('{"v": 2, "local": true}\n', encoding="utf-8")  # the next check-slice
    commit(other, {"notes.md": "notes from main\n"}, "main moves", push=True)
    code, out = sync(lead, "--json")
    assert code == 0, out
    result = json.loads(out)
    assert result["status"] == closestate.MERGED, out
    assert "checkpoint" not in out and "Commit them" not in out
    assert (lead / "notes.md").read_text(encoding="utf-8") == "notes from main\n"
    assert (lead / CACHE).read_text(encoding="utf-8") == '{"v": 2, "local": true}\n'  # vela's working copy is kept
    assert result["set_aside"] == [CACHE]


def test_a_rebuilt_dashboard_does_not_block_sync(repos):
    """`close dashboard` with a session open leaves the page for close finish to rebuild and commit; sync-main runs
    first in that close, and stopping on the page asked for a checkpoint close stage won't make."""
    lead, other = repos
    commit(lead, {"dashboard.html": "<p>committed</p>\n"}, "Rebuild dashboard")
    (lead / "dashboard.html").write_text("<p>rebuilt, not committed</p>\n", encoding="utf-8")
    commit(other, {"notes.md": "notes from main\n"}, "main moves", push=True)
    code, out = sync(lead, "--json")
    assert code == 0, out
    result = json.loads(out)
    assert result["status"] == closestate.MERGED and result["set_aside"] == ["dashboard.html"], out
    assert (lead / "dashboard.html").read_text(encoding="utf-8") == "<p>rebuilt, not committed</p>\n"


def test_a_cache_both_sides_committed_never_stops_the_merge(repos):
    """Main got the cache too (the session branch carrying it merged), and both sides then rewrote it."""
    lead, other = repos
    commit_cache(lead, '{"v": 1}\n', "cache on the session")
    commit_cache(other, '{"v": "main"}\n', "cache on main")
    git(other, "push", "-q", "origin", "HEAD:main")
    (lead / CACHE).write_text('{"v": 2}\n', encoding="utf-8")
    code, out = sync(lead)
    assert code == 0, out
    assert git(lead, "rev-parse", "HEAD^2") == git(lead, "rev-parse", "origin/main")
    assert (lead / CACHE).read_text(encoding="utf-8") == '{"v": 2}\n'


def test_check_warns_while_git_tracks_vela_s_cache_and_stops_once_untracked(repos):
    lead, _ = repos
    (lead / ".vela.yaml").write_text("initiative: INI-001\ntitle: Heron\n", encoding="utf-8")
    commit_cache(lead, '{"v": 1}\n', "cache")
    code, out = run("check", "--vault", str(lead), "--today", TODAY)
    assert f"{CACHE}:1: W719" in out and f"git rm --cached -- {CACHE}" in out, out
    git(lead, "rm", "-q", "--cached", CACHE)
    git(lead, "commit", "-q", "-m", "untrack the cache")
    assert "W719" not in run("check", "--vault", str(lead), "--today", TODAY)[1]


def test_the_template_ignores_every_vela_working_file_but_the_shared_layout(tmp_path):
    from conftest import REPO
    git(tmp_path, "init", "-q")
    (tmp_path / ".gitignore").write_bytes((REPO / "template" / ".gitignore").read_bytes())
    for name in ("flowcheck-cache.json", "close/session__x.json", "findings/a.txt", "pr-body.md", "explorer-pins.json"):
        (tmp_path / ".vela" / name).parent.mkdir(parents=True, exist_ok=True)
        (tmp_path / ".vela" / name).write_text("{}\n", encoding="utf-8")
    assert vaultgit.status_paths(tmp_path, "--untracked-files=all", "--", ".vela") == [".vela/explorer-pins.json"]


def test_the_lead_s_files_still_block_and_are_named_whole(repos):
    """A dirty page still needs a checkpoint, the cache beside it is not in the list, and no path loses its first
    letter (porcelain was sliced after the output was stripped)."""
    lead, other = repos
    commit_cache(lead, '{"v": 1}\n', "cache")
    commit(other, {"notes.md": "notes from main\n"}, "main moves", push=True)
    (lead / CACHE).write_text('{"v": 2}\n', encoding="utf-8")
    (lead / "01-goals.md").write_text(page(intro="Unsaved edit."), encoding="utf-8")
    code, out = sync(lead)
    assert code == 3, out
    assert "1 tracked files have uncommitted edits (01-goals.md)" in out, out
    assert "flowcheck-cache" not in out
    assert (lead / CACHE).read_text(encoding="utf-8") == '{"v": 2}\n'
