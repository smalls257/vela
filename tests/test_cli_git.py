"""A git that cannot answer is never an empty answer (Silent Fallback): view, export and handoff say so."""
import pytest

from conftest import run
from vela import cli
from vela.edge import vaultgit


def git_down(monkeypatch, why="git status did not finish in 10 s"):
    def fail(*args, **kwargs):
        raise vaultgit.GitUnavailable(why)
    monkeypatch.setattr(vaultgit, "run_git", fail)


def test_a_folder_that_is_not_a_repository_is_an_uncommitted_copy_not_an_error(mini):
    assert cli.commit_stamp(mini) == "an uncommitted copy"


def test_a_git_that_times_out_is_not_an_answer(mini, monkeypatch):
    git_down(monkeypatch)
    with pytest.raises(vaultgit.GitUnavailable):
        cli.git(mini, "status", "--porcelain")


def test_a_git_that_fails_for_another_reason_is_not_an_answer(mini, monkeypatch):
    monkeypatch.setattr(vaultgit, "run_git", lambda *a, **k: (128, "", "fatal: detected dubious ownership in repository"))
    with pytest.raises(vaultgit.GitUnavailable, match="dubious ownership"):
        cli.git(mini, "rev-parse", "HEAD")


def test_view_says_the_commit_is_unknown_when_git_did_not_answer(mini, tmp_path, monkeypatch):
    git_down(monkeypatch)
    out_file = tmp_path / "view.html"
    code, out = run("view", "--vault", str(mini), "--out", str(out_file), "--date", "2026-01-15")
    assert code == 0, out
    assert "unknown, git did not answer" in out
    assert "an uncommitted copy" not in out


def test_handoff_refuses_to_stamp_a_commit_git_did_not_give(mini, monkeypatch):
    git_down(monkeypatch)
    code, out = run("handoff", "APP-till", "--vault", str(mini), "--today", "2026-01-15")
    assert code == 2 and "cannot record the commit" in out and "--commit" in out, out
    assert not (mini / "handoffs").exists()


def test_export_says_when_git_did_not_answer(mini, tmp_path, monkeypatch):
    git_down(monkeypatch)
    code, out = run("export", "jira-csv", "--vault", str(mini), "--out", str(tmp_path / "e.csv"))
    assert "Git did not answer" in out, out
