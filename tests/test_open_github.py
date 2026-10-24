"""vela open <GitHub link>: fetch, run the publish code on what was committed, open a private read copy; stop with
a plain message when there is no git, no access or no network, and never fall back to an older copy."""
import json
import subprocess

import pytest

from conftest import run
from sharing import make_vault
from vela import githubsource
from vela.edge import githubcopy


def git(root, *args):
    subprocess.run(["git", "-C", str(root), "-c", "user.name=t", "-c", "user.email=t@t", *args], check=True, capture_output=True)


@pytest.fixture
def github(tmp_path, monkeypatch):
    """A bare repo at <base>/harborline/booking-plan.git holding a committed vault; CLONE_BASE points there.
    Returns (the owner's vault, the bare repo)."""
    vault = make_vault(tmp_path)
    base = tmp_path / "github"
    (base / "harborline").mkdir(parents=True)
    bare = base / "harborline" / "booking-plan.git"
    git(tmp_path, "clone", "-q", "--bare", str(vault), str(bare))
    monkeypatch.setattr(githubcopy, "CLONE_BASE", base.as_uri())
    monkeypatch.setattr(githubcopy, "gh_signed_in", lambda: False)
    return vault, bare


@pytest.mark.parametrize("link, label", [
    ("https://github.com/harborline/booking-plan", "harborline/booking-plan"),
    ("https://github.com/harborline/booking-plan.git", "harborline/booking-plan"),
    ("https://github.com/harborline/booking-plan/tree/main/", "harborline/booking-plan"),
    ("git@github.com:harborline/booking-plan.git", "harborline/booking-plan"),
    ("github.com/harborline/booking-plan", "harborline/booking-plan")])
def test_a_github_link_is_read_in_each_shape(link, label):
    assert githubsource.parse(link).label == label


@pytest.mark.parametrize("text", ["/Users/dana/plan.zip", "https://gitlab.com/a/b", "plan", "https://github.com/a"])
def test_anything_else_is_not_a_github_link(text):
    assert githubsource.parse(text) is None


def test_a_link_opens_a_private_read_copy_stamped_from_github(tmp_path, github):
    code, text = run("open", "https://github.com/harborline/booking-plan", "--into", str(tmp_path / "ws"),
                     "--author", "Dana", "--today", "2026-10-24")
    assert code == 0, text
    workspace = json.loads((tmp_path / "ws" / ".vela" / "workspace.json").read_text(encoding="utf-8"))
    assert workspace["source"] == "https://github.com/harborline/booking-plan" and workspace["role"] == "reader"
    assert "from GitHub harborline/booking-plan" in text
    assert not (tmp_path / "ws" / ".git").exists() and (tmp_path / "ws" / "dashboard.html").is_file()
    assert (tmp_path / "ws" / ".vela" / "companion" / "plan.json").is_file()   # prepared once per open (Task 8)


def test_the_copy_leaves_out_what_a_publish_leaves_out(tmp_path, github):
    run("open", "https://github.com/harborline/booking-plan", "--into", str(tmp_path / "ws"), "--author", "Dana",
        "--today", "2026-10-24")
    assert not (tmp_path / "ws" / "sessions" / "private").exists()


def test_no_git_is_said_plainly(tmp_path, github, monkeypatch):
    monkeypatch.setattr(githubcopy, "has_git", lambda: False)
    code, text = run("open", "https://github.com/harborline/booking-plan", "--into", str(tmp_path / "ws"))
    assert code == 1 and "doesn't have git" in text and "send the plan as a file" in text
    assert not (tmp_path / "ws").exists()


def test_no_access_is_said_plainly_and_nothing_older_opens(tmp_path, github):
    code, text = run("open", "https://github.com/harborline/someone-elses-plan", "--into", str(tmp_path / "ws"))
    assert code == 1 and "GitHub didn't let this computer read the plan." in text
    assert "fatal:" not in text and not (tmp_path / "ws").exists()


def test_the_same_link_again_brings_in_the_newer_plan(tmp_path, github):
    vault, bare = github
    link = "https://github.com/harborline/booking-plan"
    run("open", link, "--into", str(tmp_path / "ws"), "--author", "Dana", "--today", "2026-10-24")
    page = next(p for p in sorted(vault.glob("*.md")) if p.name != "CONVENTIONS.md")
    page.write_text(page.read_text(encoding="utf-8") + "\nOne more line.\n", encoding="utf-8")
    git(vault, "commit", "-qam", "more")
    branch = subprocess.run(["git", "-C", str(vault), "rev-parse", "--abbrev-ref", "HEAD"], capture_output=True,
                            text=True).stdout.strip()
    git(vault, "push", "-q", str(bare), f"HEAD:refs/heads/{branch}")
    code, text = run("open", link, "--into", str(tmp_path / "ws"), "--author", "Dana", "--today", "2026-10-31")
    assert code == 0, text
    assert "One more line." in (tmp_path / "ws" / page.name).read_text(encoding="utf-8")


def test_freshness_asks_github_and_says_a_newer_plan_is_there(tmp_path, github, monkeypatch):
    run("open", "https://github.com/harborline/booking-plan", "--into", str(tmp_path / "ws"), "--author", "Dana",
        "--today", "2026-10-24")
    monkeypatch.setattr(githubcopy, "remote_head", lambda repo, timeout: "f" * 40)
    code, text = run("freshness", "--vault", str(tmp_path / "ws"), "--for-lead")
    assert "newer plan on GitHub" in text and "get the newer plan" in text
