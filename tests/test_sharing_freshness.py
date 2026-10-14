"""vela freshness: an owner's bounded git fetch and a reader's comparison with the source they opened from.
It reports; it never pulls, updates or fails because a source is out of reach."""
import hashlib
import json
import re
import shutil
import subprocess

import pytest

from conftest import run
from sharing import advance_remote, git, make_vault, make_workspace, with_remote

from vela import freshness
from vela.edge import vaultgit


def fresh(root, *extra):
    code, out = run("freshness", "--vault", str(root), "--json", *extra)
    assert code == 0, out
    return json.loads(out)


def publish_to(vault, out, today):
    code, text = run("publish", "--vault", str(vault), "--out", str(out), "--today", today)
    assert code == 0, text


def tree_digest(root):
    digest = hashlib.sha256()
    for path in sorted(p for p in root.rglob("*") if p.is_file()):
        digest.update(path.relative_to(root).as_posix().encode() + path.read_bytes())
    return digest.hexdigest()


# ---- owner


@pytest.fixture
def owner(tmp_path):
    root = make_vault(tmp_path)
    return root, with_remote(tmp_path, root)


def test_an_owner_level_with_origin_is_current(owner):
    root, _ = owner
    report = fresh(root)
    assert report["role"] == "owner" and report["state"] == "current"
    assert (report["behind"], report["ahead"], report["uncommitted"]) == (0, 0, 0)
    assert report["have"]["commit"] == git(root, "rev-parse", "--short", "HEAD")


def test_one_commit_on_origin_is_behind_1_and_nothing_is_pulled(tmp_path, owner):
    root, bare = owner
    before = git(root, "rev-parse", "HEAD")
    advance_remote(tmp_path, bare)
    report = fresh(root)
    assert report["state"] == "newer" and report["behind"] == 1 and report["ahead"] == 0
    assert report["latest"]["commit"] != report["have"]["commit"]
    assert "I have not pulled" in report["message"]
    assert git(root, "rev-parse", "HEAD") == before
    assert not (root / "note.md").exists()


def test_a_local_edit_is_counted_as_uncommitted(tmp_path, owner):
    root, bare = owner
    advance_remote(tmp_path, bare)
    (root / "01-goals.md").write_text((root / "01-goals.md").read_text(encoding="utf-8") + "\nmore\n", encoding="utf-8")
    report = fresh(root)
    assert report["uncommitted"] == 1 and report["behind"] == 1


def test_a_local_commit_is_ahead(owner):
    root, _ = owner
    (root / "x.md").write_text("x\n", encoding="utf-8")
    git(root, "add", "-A")
    git(root, "commit", "-q", "-m", "local")
    report = fresh(root)
    assert report["ahead"] == 1 and report["behind"] == 0 and report["state"] == "current"


def test_origin_gone_says_so_and_still_shows_local_state(tmp_path, owner):
    root, bare = owner
    shutil.rmtree(bare)
    (root / "x.md").write_text("x\n", encoding="utf-8")
    code, text = run("freshness", "--vault", str(root))
    assert code == 0
    assert "I could not reach origin; showing local state" in text and "1 uncommitted file" in text
    report = fresh(root)
    assert report["state"] == "unreachable" and report["uncommitted"] == 1 and report["behind"] == 0


def test_no_origin_is_unknown_and_says_why(tmp_path):
    root = make_vault(tmp_path)
    report = fresh(root)
    assert report["state"] == "unknown" and "no remote called origin" in report["message"]


def test_the_fetch_is_given_the_timeout_and_never_prompts(monkeypatch, owner):
    root, _ = owner
    seen = []
    real = subprocess.run

    def spy(command, **kwargs):
        if "fetch" in command:
            seen.append((kwargs.get("timeout"), kwargs["env"].get("GIT_TERMINAL_PROMPT")))
        return real(command, **kwargs)

    monkeypatch.setattr(subprocess, "run", spy)
    fresh(root, "--timeout", "3")
    assert seen == [(3, "0")]


def test_a_fetch_that_does_not_finish_reads_as_unreachable_not_a_hang(monkeypatch, owner):
    root, _ = owner
    real = subprocess.run

    def slow(command, **kwargs):
        if "fetch" in command:
            raise subprocess.TimeoutExpired(command, kwargs["timeout"])
        return real(command, **kwargs)

    monkeypatch.setattr(subprocess, "run", slow)
    report = fresh(root, "--timeout", "1")
    assert report["state"] == "unreachable" and "did not finish in 1 s" in report["message"]


def test_every_git_call_has_a_timeout(monkeypatch, owner):
    root, _ = owner
    real = subprocess.run
    timeouts = []

    def spy(command, **kwargs):
        timeouts.append(kwargs.get("timeout"))
        return real(command, **kwargs)

    monkeypatch.setattr(subprocess, "run", spy)
    fresh(root)
    assert timeouts and None not in timeouts


def test_git_missing_is_a_named_failure_not_an_empty_answer(monkeypatch, tmp_path):
    def missing(command, **kwargs):
        raise FileNotFoundError("git")

    monkeypatch.setattr(subprocess, "run", missing)
    with pytest.raises(vaultgit.GitUnavailable, match="not installed"):
        vaultgit.run_git(tmp_path, "status")


def test_a_folder_that_is_neither_cannot_be_checked(tmp_path):
    (tmp_path / "plain").mkdir()
    code, text = run("freshness", "--vault", str(tmp_path / "plain"))
    assert code == 2 and "neither a vault repo nor a published copy" in text


# ---- reader


def test_a_reader_on_the_latest_publish_is_current(tmp_path):
    vault = make_vault(tmp_path)
    publish_to(vault, tmp_path / "source", "2026-10-11")
    workspace = make_workspace(tmp_path, tmp_path / "source")
    report = fresh(workspace)
    assert report["role"] == "reader" and report["state"] == "current"
    code, text = run("freshness", "--vault", str(workspace))
    assert f"Your copy is the latest published ({report['have']['commit']}, 2026-10-11)." in text


def test_a_republish_to_the_same_source_is_newer_and_the_workspace_is_untouched(tmp_path):
    vault = make_vault(tmp_path)
    publish_to(vault, tmp_path / "source", "2026-10-11")
    workspace = make_workspace(tmp_path, tmp_path / "source")
    (workspace / "01-goals.md").write_text("my draft\n", encoding="utf-8")
    (vault / "02-new.md").write_text("new\n", encoding="utf-8")
    git(vault, "add", "-A")
    git(vault, "commit", "-q", "-m", "v2")
    shutil.rmtree(tmp_path / "source")
    publish_to(vault, tmp_path / "source", "2026-10-20")
    before = tree_digest(workspace)
    report = fresh(workspace)
    assert report["state"] == "newer"
    assert report["latest"] == {"commit": git(vault, "rev-parse", "--short", "HEAD"), "date": "2026-10-20"}
    assert report["have"]["date"] == "2026-10-11"
    assert "A newer copy was published 2026-10-20" in report["message"] and "/vela:open" in report["message"]
    assert "Your drafts are kept" in report["message"]
    assert tree_digest(workspace) == before


def test_a_zip_source_is_read_from_its_stamp_only(tmp_path):
    vault = make_vault(tmp_path)
    publish_to(vault, tmp_path / "source", "2026-10-11")
    workspace = make_workspace(tmp_path, tmp_path / "source")
    (vault / "02-new.md").write_text("new\n", encoding="utf-8")
    git(vault, "add", "-A")
    git(vault, "commit", "-q", "-m", "v2")
    publish_to(vault, tmp_path / "later.zip", "2026-10-20")
    workspace_json = workspace / ".vela" / "workspace.json"
    data = json.loads(workspace_json.read_text(encoding="utf-8"))
    data["source_path"] = str(tmp_path / "later.zip")
    workspace_json.write_text(json.dumps(data), encoding="utf-8")
    assert fresh(workspace)["state"] == "newer"


def test_a_source_that_is_gone_is_unreachable_and_exits_0(tmp_path):
    vault = make_vault(tmp_path)
    publish_to(vault, tmp_path / "source", "2026-10-11")
    workspace = make_workspace(tmp_path, tmp_path / "source")
    shutil.rmtree(tmp_path / "source")
    code, text = run("freshness", "--vault", str(workspace))
    assert code == 0
    assert "I cannot reach the folder you opened this from (OneDrive offline?). Your copy is as of 2026-10-11." in text
    report = fresh(workspace)
    assert report["state"] == "unreachable" and report["latest"] is None


def test_a_source_that_is_not_a_published_copy_is_unknown_and_says_why(tmp_path):
    vault = make_vault(tmp_path)
    publish_to(vault, tmp_path / "source", "2026-10-11")
    workspace = make_workspace(tmp_path, tmp_path / "source")
    shutil.rmtree(tmp_path / "source")
    (tmp_path / "source").mkdir()
    report = fresh(workspace)
    assert report["state"] == "unknown" and "not a published copy" in report["message"]


def test_a_workspace_with_no_recorded_commit_is_unknown(tmp_path):
    vault = make_vault(tmp_path)
    publish_to(vault, tmp_path / "source", "2026-10-11")
    workspace = make_workspace(tmp_path, tmp_path / "source")
    path = workspace / ".vela" / "workspace.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    del data["base_commit"]
    path.write_text(json.dumps(data), encoding="utf-8")
    assert fresh(workspace)["state"] == "unknown"


def test_a_republish_at_the_same_commit_with_other_contents_is_newer():
    workspace = {"base_commit": "9f3c2ab41d7e", "base_date": "2026-10-11", "base_tree_hash": "aaa"}
    stamp = {"commit": "9f3c2ab41d7e", "date": "2026-10-12", "tree_hash": "bbb"}
    report = freshness.reader_report(workspace, stamp, "", "", "2026-10-12T09:00:00")
    assert report.state == freshness.NEWER and "same commit" in report.message


def test_short_and_full_commits_compare_equal_and_too_short_ones_do_not():
    assert freshness.same_commit("9f3c2ab", "9f3c2ab41d7e0000")
    assert not freshness.same_commit("9f3", "9f3c2ab41d7e")
    assert not freshness.same_commit("", "")


def test_the_json_carries_the_documented_keys(tmp_path):
    root = make_vault(tmp_path)
    report = fresh(root)
    assert set(report) == {"role", "state", "checked_at", "have", "latest", "behind", "ahead", "uncommitted", "message"}


# ---- the explorer's own write is not an uncommitted change

def page_freshness_of(root):
    page = (root / "dashboard.html").read_text(encoding="utf-8")
    return json.loads(re.search(r'<script type="application/json" id="data">(.*?)</script>', page, re.S).group(1))["freshness"]


def test_a_dashboard_built_by_close_does_not_count_its_own_write_as_uncommitted(tmp_path, owner):
    root, _ = owner
    for _ in range(2):  # the first build creates dashboard.html and the pins; the second rewrites them
        code, out = run("explore", str(root), "--today", "2026-10-12")
        assert code == 0, out
        assert page_freshness_of(root)["uncommitted"] == 0
    assert "dashboard.html" in git(root, "status", "--short")  # git sees it, and the page does not count it
    (root / "01-goals.md").write_text((root / "01-goals.md").read_text(encoding="utf-8") + "\nmore\n", encoding="utf-8")
    code, out = run("explore", str(root), "--today", "2026-10-12")
    assert code == 0, out
    assert page_freshness_of(root)["uncommitted"] == 1
