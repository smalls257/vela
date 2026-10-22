"""The release branch holds only what an install needs, one commit per release, and its push check says why it refuses."""
import json
import os
import subprocess
import sys

import pytest

from conftest import REPO

sys.path.insert(0, str(REPO / "tools"))
import build_release_branch as rb  # noqa: E402

HOOK = REPO / ".githooks" / "pre-push"
TOOL = REPO / "tools" / "build_release_branch.py"
ENV = {**os.environ, "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t", "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@t"}


def git(repo, *args, stdin=None):
    done = subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True, env=ENV, input=stdin)
    assert done.returncode == 0, done.stderr
    return done.stdout.strip()


def write(root, rel, content):
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)


def release_source(root, version):
    write(root, ".claude-plugin/marketplace.json",
          json.dumps({"name": "vela", "plugins": [{"name": "vela", "source": "./plugin"}]}))
    write(root, "plugin/.claude-plugin/plugin.json", json.dumps({"name": "vela", "version": version}))
    write(root, "plugin/bin/vela", "#!/bin/sh\n")
    write(root, "plugin/lib/mod.py", "x = 1\n")
    write(root, "plugin/lib/__pycache__/mod.cpython-311.pyc", "\0")
    write(root, "LICENSE", "MIT\n")
    write(root, "tests/test_big.py", "assert True\n")
    write(root, "docs/GUIDE.md", "docs\n")
    git(root, "add", "-f", ".")
    git(root, "commit", "-m", f"source {version}")
    return git(root, "rev-parse", "HEAD")


@pytest.fixture
def repo(tmp_path):
    root = tmp_path / "clone"
    git(tmp_path, "init", "-b", "main", str(root))
    return root


def tree(repo, commit):
    return git(repo, "ls-tree", "-r", "--name-only", commit).splitlines()


def test_tree_holds_only_the_install(repo):
    source = release_source(repo, "1.0.0")
    commit, version = rb.build(repo, source)
    assert version == "1.0.0"
    assert tree(repo, commit) == [".claude-plugin/marketplace.json", "LICENSE", "README.md", "plugin/.claude-plugin/plugin.json",
                                  "plugin/bin/vela", "plugin/lib/mod.py"]
    readme = git(repo, "show", f"{commit}:README.md")
    assert "smalls257/vela#release" in readme and "`main`" in readme
    assert git(repo, "status", "--porcelain") == "" and git(repo, "symbolic-ref", "--short", "HEAD") == "main"


def test_one_commit_per_release_on_top_of_the_last(repo):
    first, _ = rb.build(repo, release_source(repo, "1.0.0"))
    write(repo, "plugin/lib/mod.py", "x = 2\n")
    git(repo, "commit", "-am", "more")
    second_source = git(repo, "rev-parse", "HEAD")
    write(repo, "plugin/.claude-plugin/plugin.json", json.dumps({"name": "vela", "version": "1.1.0"}))
    git(repo, "commit", "-am", "bump")
    second, version = rb.build(repo, "HEAD")
    assert git(repo, "rev-list", "--count", "release") == "2"
    assert git(repo, "rev-parse", "release~1") == first
    message = git(repo, "log", "-1", "--format=%s", second)
    assert "1.1.0" in message and git(repo, "rev-parse", "--short=9", "HEAD") in message
    assert second_source != git(repo, "rev-parse", "HEAD")


def test_refuses_same_version_uncommitted_ref_and_older(repo):
    source = release_source(repo, "1.0.0")
    rb.build(repo, source)
    with pytest.raises(rb.ReleaseError, match="already at vela 1.0.0"):
        rb.build(repo, source)
    with pytest.raises(rb.ReleaseError, match="not a committed ref"):
        rb.build(repo, "deadbeef")
    write(repo, "plugin/.claude-plugin/plugin.json", json.dumps({"name": "vela", "version": "0.9.0"}))
    git(repo, "commit", "-am", "older")
    with pytest.raises(rb.ReleaseError, match="backwards"):
        rb.build(repo, "HEAD")


def push_check(repo, commit):
    line = f"refs/heads/release {commit} refs/heads/release {'0' * 40}\n"
    return subprocess.run(["bash", str(HOOK)], cwd=repo, input=line, capture_output=True, text=True, env=ENV)


def test_pre_push_accepts_the_built_branch_and_rejects_an_extra_path(repo):
    commit, _ = rb.build(repo, release_source(repo, "1.0.0"))
    done = push_check(repo, commit)
    assert done.returncode == 0, done.stdout + done.stderr
    assert "release check" in done.stdout

    index = repo / "scratch-index"
    env = {**ENV, "GIT_INDEX_FILE": str(index)}
    subprocess.run(["git", "-C", str(repo), "read-tree", commit], env=env, check=True)
    blob = git(repo, "hash-object", "-w", "--stdin", stdin="x")
    subprocess.run(["git", "-C", str(repo), "update-index", "--add", "--cacheinfo", f"100644,{blob},tests/extra.py"], env=env, check=True)
    tree_id = subprocess.run(["git", "-C", str(repo), "write-tree"], env=env, capture_output=True, text=True, check=True).stdout.strip()
    bad = git(repo, "commit-tree", tree_id, "-p", commit, "-m", "extra")
    done = push_check(repo, bad)
    assert done.returncode != 0 and "tests/extra.py is not allowed" in done.stderr


def test_check_rejects_a_version_that_did_not_rise_and_a_big_file(repo, monkeypatch):
    commit, _ = rb.build(repo, release_source(repo, "1.0.0"))
    tree_id = git(repo, "rev-parse", f"{commit}^{{tree}}")
    same = git(repo, "commit-tree", tree_id, "-p", commit, "-m", "again")
    with pytest.raises(rb.ReleaseError, match="not greater"):
        rb.check_release_tree(repo, same)
    monkeypatch.setattr(rb, "MAX_FILE_BYTES", 3)
    with pytest.raises(rb.ReleaseError, match="per-file limit"):
        rb.check_release_tree(repo, commit)
