"""Fixtures for the owner/reader tests: a vault in a real git repo, a temp bare remote standing in for origin, and a
reader workspace written directly in the format design session 15 defines (until `open` exists to make one)."""
import json
import pathlib
import shutil
import subprocess

from conftest import MINI

IDENTITY = ["-c", "user.name=Priya Nair", "-c", "user.email=priya@example.com", "-c", "commit.gpgsign=false"]


def git(root, *args):
    done = subprocess.run(["git", "-C", str(root), *IDENTITY, *args], capture_output=True, text=True, timeout=60)
    assert done.returncode == 0, f"git {args} failed: {done.stderr}"
    return done.stdout.strip()


def make_vault(tmp_path, name="vault"):
    """The mini vault committed in its own repo, with an identity set so the user can commit."""
    root = tmp_path / name
    shutil.copytree(MINI, root)
    git(tmp_path, "init", "-q", "-b", "main", str(root))
    git(root, "config", "user.name", "Priya Nair")
    git(root, "config", "user.email", "priya@example.com")
    git(root, "config", "commit.gpgsign", "false")
    git(root, "add", "-A")
    git(root, "commit", "-q", "-m", "first")
    return root


def with_remote(tmp_path, root):
    """A bare repo as origin, with the vault pushed to it. Returns the bare repo's path."""
    bare = tmp_path / "origin.git"
    git(tmp_path, "init", "-q", "--bare", "-b", "main", str(bare))
    git(root, "remote", "add", "origin", str(bare))
    git(root, "push", "-q", "-u", "origin", "main")
    return bare


def advance_remote(tmp_path, bare, text="more\n"):
    """Another clone pushes one commit to origin, the way a teammate would."""
    other = tmp_path / "teammate"
    git(tmp_path, "clone", "-q", str(bare), str(other))
    git(other, "config", "user.name", "Teammate")
    git(other, "config", "user.email", "t@example.com")
    (other / "note.md").write_text(text, encoding="utf-8")
    git(other, "add", "-A")
    git(other, "commit", "-q", "-m", "teammate")
    git(other, "push", "-q", "origin", "main")
    shutil.rmtree(other)


def make_workspace(tmp_path, source, name="workspace"):
    """A reader workspace as design session 15 section 2 lays it out: the published files, a pristine baseline,
    and .planner/workspace.json recording the source it was opened from. Works from a published folder."""
    source = pathlib.Path(source)
    stamp = json.loads((source / ".planner" / "published.json").read_text(encoding="utf-8"))
    root = tmp_path / name
    shutil.copytree(source, root)
    shutil.copytree(source, root / ".planner" / "baseline")
    workspace = {"role": "reader", "source": source.name, "source_path": str(source), "base_commit": stamp["commit"],
                 "base_date": stamp["date"], "opened": "2026-10-12", "author": "Sam Okoye"}
    (root / ".planner" / "workspace.json").write_text(json.dumps(workspace, indent=2), encoding="utf-8")
    return root


SNAPSHOT = pathlib.Path(__file__).resolve().parent / "sim" / "snapshots" / "trading-coach" / "after-capture-boundary"
HOSTILE = "a reader's cap is a <b>must</b> & never a may, </script><img src=x onerror=alert(1)>"


def commit_snapshot(tmp_path, name="src"):
    """The trading-coach snapshot committed in its own repo (it carries .planner.yaml, so it can be published)."""
    root = tmp_path / name
    shutil.copytree(SNAPSHOT, root)
    git(tmp_path, "init", "-q", "-b", "main", str(root))
    git(root, "config", "user.name", "Priya Nair")
    git(root, "config", "user.email", "priya@example.com")
    git(root, "add", "-A")
    git(root, "commit", "-q", "-m", "first")
    return root


def draft_workspace(tmp_path):
    """(source repo, published folder, reader workspace) after the reader edited a page (with markup in the new line),
    added a page and recorded a pending-approval decision on CON-001, which nothing else lights."""
    from conftest import run
    src = commit_snapshot(tmp_path)
    published, workspace = tmp_path / "published", tmp_path / "workspace"
    assert run("publish", "--vault", str(src), "--out", str(published), "--today", "2026-10-11")[0] == 0
    assert run("open", str(published), "--into", str(workspace), "--author", "Sam Okoye", "--today", "2026-10-12")[0] == 0
    page = workspace / "05-building-blocks" / "coach-building-blocks.md"
    text = page.read_text(encoding="utf-8")
    assert "so no real order ever crosses." in text and "#### CON-001 Lessons and track\n\n" in text
    text = text.replace("so no real order ever crosses.", f"so no real order ever crosses, and {HOSTILE}.", 1)
    text = text.replace("#### CON-001 Lessons and track\n\n", "#### CON-001 Lessons and track\n\n- **Pending approval:** @sam, 2026-10-12\n", 1)
    page.write_text(text, encoding="utf-8")
    (workspace / "reader-notes.md").write_text("# Notes\n\nWhat Finance said on Tuesday.\n", encoding="utf-8")
    return src, published, workspace
