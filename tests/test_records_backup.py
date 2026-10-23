"""`vela records backup --to <folder or .zip>`: the one sanctioned way the notes leave the machine as a copy.

The Violation this exists to prevent is a Silent Fallback at the other end of the privacy rule: notes that never leave
the machine are lost with it, so the lead needs a way to keep them, and a way that can't quietly put them back into
the plan. A target inside the plan or its git repo is refused before anything is written (the copy would be committed);
an existing name is never overwritten; and an empty result says so instead of writing an empty folder."""
import json
import zipfile

import shutil

import pytest

from conftest import run
from sharing import git
from test_session_cli import TODAY, owner, start
import session_files

OTHER = "2026-10-12-till-options"
NOTES = "---\nid: 2026-10-12-till-options\npart: 1\n---\n\n## Captures\n\n- [idea] (@lead) The till rounds up. ^c01\n"


@pytest.fixture
def started(tmp_path, monkeypatch):
    vault = owner(tmp_path, monkeypatch)
    shutil.rmtree(vault / "sessions" / "private")  # the mini fixture's own notes: these tests count their own
    assert start(vault, "--mode", "dump", "--topic", "consent")[0] == 0
    session_files.write_private(vault, OTHER, NOTES)
    return vault


def backup(vault, to, *extra):
    return run("records", "backup", "--to", str(to), "--vault", str(vault), "--today", TODAY, *extra)


def private_files(vault):
    return sorted(p.name for p in (vault / "sessions" / "private").glob("*.md"))


def test_backup_inside_the_repo_is_refused(started):
    code, text = backup(started, started / "backup")
    assert code == 1
    assert "That folder is inside the plan, so the copy would be committed. Pick a folder outside it." in text
    assert not (started / "backup").exists()


def test_backup_inside_the_git_top_level_but_outside_the_plan_is_refused(tmp_path, started):
    plan = started / "plans" / "a"
    plan.mkdir(parents=True)
    for name in (".vela.yaml",):
        (plan / name).write_text((started / name).read_text(encoding="utf-8"), encoding="utf-8")
    (plan / "sessions" / "private").mkdir(parents=True)
    (plan / "sessions" / "private" / f"{OTHER}.md").write_text(NOTES, encoding="utf-8")
    code, text = backup(plan, started / "elsewhere-in-the-repo")
    assert code == 1 and "inside the plan" in text
    assert not (started / "elsewhere-in-the-repo").exists()


def test_backup_to_a_folder_copies_every_private_file_and_says_how_many(started, tmp_path):
    out = tmp_path / "keep"
    code, text = backup(started, out)
    assert code == 0, text
    made = sorted(out.iterdir())
    assert len(made) == 1
    assert made[0].name.startswith("vela-sessions-") and made[0].name.endswith(f"-{TODAY}")
    assert sorted(p.name for p in made[0].iterdir()) == private_files(started)
    for copy in made[0].iterdir():
        assert copy.read_bytes() == (started / "sessions" / "private" / copy.name).read_bytes()
    assert "2 session notes" in text and str(made[0]) in text


def test_backup_to_a_zip_holds_every_private_file(started, tmp_path):
    code, text = backup(started, tmp_path / "out.zip")
    assert code == 0, text
    archive = zipfile.ZipFile(tmp_path / "out.zip")
    top = archive.namelist()[0].split("/")[0]
    assert top.startswith("vela-sessions-") and top.endswith(f"-{TODAY}")
    assert sorted(archive.namelist()) == [f"{top}/{name}" for name in private_files(started)]
    assert archive.read(f"{top}/{OTHER}.md").decode("utf-8") == NOTES


def test_a_second_backup_never_overwrites(started, tmp_path):
    out = tmp_path / "keep"
    assert backup(started, out)[0] == 0
    (first,) = list(out.iterdir())
    marker = first / "marker.txt"
    marker.write_text("first backup", encoding="utf-8")
    code, text = backup(started, out)
    assert code == 0, text
    assert sorted(p.name for p in out.iterdir()) == [first.name, f"{first.name}-2"]
    assert marker.read_text(encoding="utf-8") == "first backup" and not (out / f"{first.name}-2" / "marker.txt").exists()
    assert backup(started, out)[0] == 0
    assert (out / f"{first.name}-3").is_dir()
    zipped = tmp_path / "keep.zip"
    assert backup(started, zipped)[0] == 0
    before = zipped.read_bytes()
    assert backup(started, zipped)[0] == 0
    assert zipped.read_bytes() == before and (tmp_path / "keep-2.zip").is_file()


def test_with_no_private_notes_it_says_so_and_writes_nothing(tmp_path, monkeypatch):
    vault = owner(tmp_path, monkeypatch)
    shutil.rmtree(vault / "sessions" / "private")
    code, text = backup(vault, tmp_path / "keep")
    assert code == 1 and "There are no session notes here to back up." in text
    assert not (tmp_path / "keep").exists()
    code, _ = backup(vault, tmp_path / "keep.zip")
    assert code == 1 and not (tmp_path / "keep.zip").exists()


def test_backup_changes_nothing_in_the_plan(started, tmp_path):
    before = git(started, "status", "--porcelain"), private_files(started)
    assert backup(started, tmp_path / "keep")[0] == 0
    assert (git(started, "status", "--porcelain"), private_files(started)) == before


def test_json_names_the_count_and_the_place(started, tmp_path):
    code, text = backup(started, tmp_path / "keep", "--json")
    data = json.loads(text)
    assert code == 0 and data["count"] == 2 and data["to"].startswith(str(tmp_path / "keep"))
