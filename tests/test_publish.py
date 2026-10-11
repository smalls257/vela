"""planner publish: a read copy of the committed files at HEAD, stamped, with no .git and nothing local to the owner."""
import json
import os
import zipfile

import pytest

from conftest import run
from sharing import git, make_vault, make_workspace

from planner import publish

TODAY = "2026-10-11"


@pytest.fixture
def vault(tmp_path):
    root = make_vault(tmp_path)
    # Things a read copy must not carry, committed on purpose (force-added past the ignore rules).
    for name in (".claude/skills/planner/scripts/planner", "voice/local/mine.md", ".planner/explorer.html"):
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("owner only\n", encoding="utf-8")
        git(root, "add", "-f", name)
    git(root, "commit", "-q", "-m", "owner-only files")
    return root


def publish_to(vault, out, *extra):
    return run("publish", "--vault", str(vault), "--out", str(out), "--today", TODAY, *extra)


def folder_files(folder):
    return sorted(p.relative_to(folder).as_posix() for p in folder.rglob("*") if p.is_file())


def zip_names(path):
    with zipfile.ZipFile(path) as archive:
        return archive.namelist()


def test_a_folder_copy_has_no_git_no_vendored_plugin_and_no_local_voice(vault, tmp_path):
    out = tmp_path / "copy"
    code, text = publish_to(vault, out)
    assert code == 0, text
    names = folder_files(out)
    assert ".planner.yaml" in names and "01-goals.md" in names
    assert not [n for n in names if n.startswith((".git/", ".claude/skills/planner/", "voice/local/"))]
    assert not (out / ".git").exists()
    assert [n for n in names if n.startswith(".planner/")] == [".planner/published.json"]


def test_the_stamp_is_complete_and_names_the_head_commit(vault, tmp_path):
    out = tmp_path / "copy"
    publish_to(vault, out)
    stamp = json.loads((out / ".planner" / "published.json").read_text(encoding="utf-8"))
    head = git(vault, "rev-parse", "HEAD")
    assert stamp["format"] == 1 and stamp["initiative"] == "INI-900" and stamp["title"] == "Mini shop"
    assert stamp["commit"] == head and stamp["short"] == head[:7]
    assert stamp["date"] == TODAY and stamp["dirty"] is False
    assert stamp["owner"] == {"name": "Priya Nair", "contact": "priya@example.com"}
    assert stamp["check"]["errors"] == 0 and isinstance(stamp["check"]["warnings"], int)


def test_tree_hash_is_the_hash_of_the_sorted_files_without_the_stamp(vault, tmp_path):
    out = tmp_path / "copy"
    publish_to(vault, out)
    stamp = json.loads((out / ".planner" / "published.json").read_text(encoding="utf-8"))
    files = {n: (out / n).read_bytes() for n in folder_files(out) if n != ".planner/published.json"}
    assert stamp["tree_hash"] == publish.tree_hash(files)
    (out / "01-goals.md").write_text("tampered\n", encoding="utf-8")
    files["01-goals.md"] = b"tampered\n"
    assert stamp["tree_hash"] != publish.tree_hash(files)


def test_owner_contact_from_planner_yaml_beats_git_config(vault, tmp_path):
    text = (vault / ".planner.yaml").read_text(encoding="utf-8")
    (vault / ".planner.yaml").write_text(text + "owner_contact: priya@corp.example\n", encoding="utf-8")
    git(vault, "commit", "-q", "-am", "contact")
    publish_to(vault, tmp_path / "copy")
    stamp = json.loads((tmp_path / "copy" / ".planner" / "published.json").read_text(encoding="utf-8"))
    assert stamp["owner"]["contact"] == "priya@corp.example" and stamp["owner"]["name"] == "Priya Nair"


def test_the_copy_is_built_from_head_so_a_dirty_vault_is_stamped_and_not_published(vault, tmp_path):
    (vault / "01-goals.md").write_text("an edit nobody committed\n", encoding="utf-8")
    (vault / "draft.md").write_text("a new page\n", encoding="utf-8")
    code, text = publish_to(vault, tmp_path / "copy")
    assert code == 0
    assert f"Published HEAD {git(vault, 'rev-parse', '--short', 'HEAD')}; your 2 uncommitted files are not in it." in text
    stamp = json.loads((tmp_path / "copy" / ".planner" / "published.json").read_text(encoding="utf-8"))
    assert stamp["dirty"] is True
    assert "an edit nobody committed" not in (tmp_path / "copy" / "01-goals.md").read_text(encoding="utf-8")
    assert not (tmp_path / "copy" / "draft.md").exists()


def test_a_zip_has_one_top_folder_forward_slashes_and_no_absolute_paths(vault, tmp_path):
    out = tmp_path / "out" / "copy.zip"
    code, text = publish_to(vault, out)
    assert code == 0, text
    names = zip_names(out)
    short = git(vault, "rev-parse", "--short", "HEAD")
    assert {n.split("/")[0] for n in names} == {f"mini-shop-{short}"}
    assert not [n for n in names if n.startswith("/") or "\\" in n or ".." in n.split("/")]
    assert f"mini-shop-{short}/.planner/published.json" in names
    assert not [n for n in names if "/.git/" in n or "voice/local" in n or ".claude/skills/planner" in n]


def test_two_zips_of_the_same_commit_are_byte_identical(vault, tmp_path):
    publish_to(vault, tmp_path / "one.zip")
    publish_to(vault, tmp_path / "two.zip")
    assert (tmp_path / "one.zip").read_bytes() == (tmp_path / "two.zip").read_bytes()


def test_zip_entries_have_fixed_timestamps(vault, tmp_path):
    publish_to(vault, tmp_path / "one.zip")
    with zipfile.ZipFile(tmp_path / "one.zip") as archive:
        assert {i.date_time for i in archive.infolist()} == {(1980, 1, 1, 0, 0, 0)}


def test_no_path_of_this_machine_leaks_into_the_copy(vault, tmp_path):
    publish_to(vault, tmp_path / "copy")
    publish_to(vault, tmp_path / "copy.zip")
    forbidden = [str(tmp_path).encode(), os.path.expanduser("~").encode()]
    blobs = [(tmp_path / "copy" / n).read_bytes() for n in folder_files(tmp_path / "copy")]
    blobs.append((tmp_path / "copy.zip").read_bytes())
    with zipfile.ZipFile(tmp_path / "copy.zip") as archive:
        blobs += [archive.read(n) for n in archive.namelist()]
    for blob in blobs:
        assert not [f for f in forbidden if f in blob]


def test_a_folder_that_is_not_empty_is_refused(vault, tmp_path):
    (tmp_path / "copy").mkdir()
    (tmp_path / "copy" / "keep.txt").write_text("mine\n", encoding="utf-8")
    code, text = publish_to(vault, tmp_path / "copy")
    assert code == 2 and "not empty" in text
    assert (tmp_path / "copy" / "keep.txt").read_text(encoding="utf-8") == "mine\n"


def test_publishing_into_the_vault_itself_is_refused(vault):
    code, text = publish_to(vault, vault / "out")
    assert code == 2 and "inside the vault" in text


def test_check_errors_are_counted_and_do_not_stop_publish(vault, tmp_path):
    (vault / "bad.md").write_text("no frontmatter at all\n", encoding="utf-8")
    git(vault, "add", "-A")
    git(vault, "commit", "-q", "-m", "a broken page")
    code, text = publish_to(vault, tmp_path / "copy")
    stamp = json.loads((tmp_path / "copy" / ".planner" / "published.json").read_text(encoding="utf-8"))
    assert code == 0 and stamp["check"]["errors"] >= 1
    assert f"{stamp['check']['errors']} errors" in text


def test_a_reader_cannot_publish_and_is_told_whose_call_it_is(vault, tmp_path):
    publish_to(vault, tmp_path / "copy")
    workspace = make_workspace(tmp_path, tmp_path / "copy")
    code, text = publish_to(workspace, tmp_path / "again")
    assert code == 2
    assert "Priya Nair's call" in text and "Send a proposal" in text
    assert not (tmp_path / "again").exists()


def test_a_folder_that_is_not_a_vault_cannot_publish(tmp_path):
    (tmp_path / "plain").mkdir()
    code, text = publish_to(tmp_path / "plain", tmp_path / "copy")
    assert code == 2 and "neither a vault repo nor a published copy" in text


def test_a_repo_with_no_commit_says_so(tmp_path):
    root = tmp_path / "empty"
    git(tmp_path, "init", "-q", "-b", "main", str(root))
    git(root, "config", "user.name", "P")
    git(root, "config", "user.email", "p@x.org")
    code, text = publish_to(root, tmp_path / "copy")
    assert code == 2 and "commit" in text


def test_no_owner_to_write_to_is_an_error_not_an_empty_contact():
    with pytest.raises(publish.PublishError, match="who a reader should write to"):
        publish.owner_contact({"initiative": "INI-1"}, "", "")


def test_names_that_climb_out_are_refused():
    for bad in ("../x", "/abs", "a\\b", "C:/x"):
        with pytest.raises(publish.PublishError):
            publish.check_name(bad)


def test_the_same_content_hashes_the_same_whatever_the_order():
    one = {"a": b"1", "b": b"2"}
    assert publish.tree_hash(one) == publish.tree_hash({"b": b"2", "a": b"1"})
    assert publish.tree_hash(one) != publish.tree_hash({"a": b"1", "b": b"3"})
