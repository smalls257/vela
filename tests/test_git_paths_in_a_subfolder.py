"""A plan kept in a subfolder of its repo (`projects/heron/`) reads its own pages back from HEAD.

`git -C <vault> show HEAD:<path>` reads <path> from the repo's top folder, not the vault, so close, voice settle and
the team read found none of the plan's pages there; a bug report hit it closing a session. `vaultgit.at` adds `./`,
which makes git read the path from the vault. Each reader here is run with the vault one folder down."""
import subprocess

import pytest

from vela.commands import team
from vela.edge import settlegit, vaultgit, voicegit

PAGE = "sessions/S-001.md"


def git(root, *args):
    return subprocess.run(["git", "-C", str(root), *args], check=True, capture_output=True, text=True).stdout.strip()


@pytest.fixture
def vault(tmp_path, monkeypatch):
    monkeypatch.setenv("GIT_CONFIG_GLOBAL", str(tmp_path / "gitconfig"))
    monkeypatch.setenv("GIT_CONFIG_NOSYSTEM", "1")
    (tmp_path / "gitconfig").write_text("[user]\n\tname = Test Lead\n\temail = lead@example.com\n", encoding="utf-8")
    repo = tmp_path / "docs"
    folder = repo / "projects" / "heron"
    (folder / "sessions").mkdir(parents=True)
    git(repo, "init", "-q", "-b", "main")
    (folder / PAGE).write_text("committed\n", encoding="utf-8")
    git(repo, "add", ".")
    git(repo, "commit", "-q", "-m", "plan")
    return folder


def test_at_reads_the_path_from_the_vault_folder():
    assert vaultgit.at("HEAD", PAGE) == f"HEAD:./{PAGE}"


def test_settle_reads_heads_copy_of_a_page(vault):
    assert settlegit.head_text(vault, PAGE) == "committed\n"
    assert settlegit.head_blob(vault, PAGE)
    assert settlegit.head_text(vault, "sessions/new.md") is None


def test_team_reads_heads_copy_of_a_page(vault):
    assert team.head_text(vault, PAGE) == "committed"
    assert team.head_text(vault, "sessions/new.md") == ""


def test_voice_reads_a_page_at_a_commit(vault):
    assert voicegit.show(vault, "HEAD", PAGE) == "committed\n"
    assert voicegit.show(vault, "HEAD", "sessions/new.md") is None
