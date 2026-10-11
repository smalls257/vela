"""A vault that lives in a subfolder of a bigger git repo (a team monorepo) must publish, report its role and
freshness, and take a proposal review exactly as a vault that is the repo root does. Phase 2 found publish returned
zero files here: `git archive HEAD:<prefix>` was run from inside the prefix, so git applied the prefix twice."""
import json
import shutil

import pytest
from conftest import run
from sharing import SNAPSHOT, git, with_remote

PAGE = "05-building-blocks/coach-building-blocks.md"


@pytest.fixture
def monorepo(tmp_path):
    """(repo root, vault folder inside it): the trading-coach snapshot under teams/coach/, beside unrelated files."""
    repo = tmp_path / "monorepo"
    vault = repo / "teams" / "coach"
    shutil.copytree(SNAPSHOT, vault)
    (repo / "ROOT-ONLY.md").write_text("not part of the vault\n", encoding="utf-8")
    (repo / "teams" / "other.md").write_text("a sibling\n", encoding="utf-8")
    git(tmp_path, "init", "-q", "-b", "main", str(repo))
    git(repo, "config", "user.name", "Priya Nair")
    git(repo, "config", "user.email", "priya@example.com")
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "-m", "first")
    return repo, vault


def test_publish_carries_the_vault_and_nothing_from_the_rest_of_the_repo(monorepo, tmp_path):
    repo, vault = monorepo
    out = tmp_path / "copy"
    code, text = run("publish", "--vault", str(vault), "--out", str(out), "--today", "2026-10-11")
    assert code == 0, text
    names = sorted(p.relative_to(out).as_posix() for p in out.rglob("*") if p.is_file())
    assert ".planner.yaml" in names and PAGE in names and ".planner/published.json" in names
    assert not [n for n in names if n.startswith("teams/") or n == "ROOT-ONLY.md"]
    stamp = json.loads((out / ".planner" / "published.json").read_text(encoding="utf-8"))
    assert stamp["commit"] == git(repo, "rev-parse", "HEAD") and f"({len(names)} files)" in text


def test_a_zip_of_a_subfolder_vault_equals_one_of_the_same_vault_as_a_repo_root(monorepo, tmp_path):
    from sharing import commit_snapshot
    _, vault = monorepo
    alone = commit_snapshot(tmp_path, "alone")
    for source, name in ((vault, "a.zip"), (alone, "b.zip")):
        assert run("publish", "--vault", str(source), "--out", str(tmp_path / name), "--today", "2026-10-11")[0] == 0
    import zipfile
    names = [sorted(n.split("/", 1)[1] for n in zipfile.ZipFile(tmp_path / z).namelist()) for z in ("a.zip", "b.zip")]
    assert names[0] == names[1] != []


def test_role_is_owner_in_a_subfolder(monorepo):
    _, vault = monorepo
    code, text = run("role", "--vault", str(vault), "--json")
    assert code == 0 and json.loads(text)["role"] == "owner"


def test_freshness_counts_only_this_vaults_uncommitted_files(monorepo, tmp_path):
    repo, vault = monorepo
    with_remote(tmp_path, repo)
    (repo / "ROOT-ONLY.md").write_text("edited outside the vault\n", encoding="utf-8")
    (vault / PAGE).write_text((vault / PAGE).read_text(encoding="utf-8") + "\nmore\n", encoding="utf-8")
    code, text = run("freshness", "--vault", str(vault), "--json")
    report = json.loads(text)
    assert code == 0 and report["role"] == "owner" and report["state"] == "current"
    assert report["uncommitted"] == 1 and report["have"]["commit"] == git(repo, "rev-parse", "--short", "HEAD")


def test_publish_says_how_many_uncommitted_pages_of_this_vault_are_left_out(monorepo, tmp_path):
    repo, vault = monorepo
    (repo / "ROOT-ONLY.md").write_text("edited outside the vault\n", encoding="utf-8")
    (vault / PAGE).write_text((vault / PAGE).read_text(encoding="utf-8") + "\nmore\n", encoding="utf-8")
    code, text = run("publish", "--vault", str(vault), "--out", str(tmp_path / "copy"), "--today", "2026-10-11")
    assert code == 0 and "your 1 uncommitted file is not in it" in text


def test_a_proposal_from_a_reader_is_reviewed_in_a_worktree_of_the_subfolder(monorepo, tmp_path):
    repo, vault = monorepo
    published, workspace = tmp_path / "published", tmp_path / "workspace"
    assert run("publish", "--vault", str(vault), "--out", str(published), "--today", "2026-10-11")[0] == 0
    assert run("open", str(published), "--into", str(workspace), "--author", "Sam Okoye", "--today", "2026-10-12")[0] == 0
    page = workspace / PAGE
    text = page.read_text(encoding="utf-8").replace("so no real order ever crosses.", "so no real order ever crosses, and a cap is a must.", 1)
    page.write_text(text.replace("#### CON-001 Lessons and track\n\n", "#### CON-001 Lessons and track\n\n- **Pending approval:** @sam, 2026-10-18\n", 1), encoding="utf-8")
    code, text = run("propose", "--vault", str(workspace), "--title", "Cap rule", "--today", "2026-10-18", "--whys", _whys(tmp_path))
    assert code == 0, text
    code, text = run("proposals", "review", str(tmp_path / "proposals" / "2026-10-18-cap-rule"), "--vault", str(vault), "--today", "2026-10-18")
    assert code == 0, text
    worktree = repo.parent / "monorepo-proposal-cap-rule"
    assert "a cap is a must" in (worktree / "teams" / "coach" / PAGE).read_text(encoding="utf-8")
    assert git(repo, "rev-parse", "--abbrev-ref", "HEAD") == "main"
    code, text = run("proposals", "accept", "--vault", str(worktree / "teams" / "coach"), "--item", "CON-001", "--by", "@priya")
    assert code == 0 and "committed" in text, text


def _whys(tmp_path):
    path = tmp_path / "whys.json"
    path.write_text(json.dumps({"CON-001": "Finance said so.", "CON-002": "Clearer for builders."}), encoding="utf-8")
    return str(path)
