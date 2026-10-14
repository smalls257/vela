"""planner open: a published copy becomes a private reader workspace with a pristine baseline, and the source is
never written. Also the refusals: a synced location, a tampered copy, a name that climbs out, a re-open."""
import hashlib
import json
import pathlib
import zipfile

import pytest
from conftest import run
from sharing import make_vault

from vela import cli, opening


def digest(path):
    h = hashlib.sha256()
    for item in sorted(p for p in path.rglob("*") if p.is_file()) if path.is_dir() else [path]:
        h.update(item.name.encode() + item.read_bytes())
    return h.hexdigest()


@pytest.fixture
def published(tmp_path):
    vault = make_vault(tmp_path)
    folder, archive = tmp_path / "copy", tmp_path / "copy.zip"
    for target in (folder, archive):
        code, text = run("publish", "--vault", str(vault), "--out", str(target), "--today", "2026-10-11")
        assert code == 0, text
    return folder, archive


def open_copy(source, into, *extra):
    return run("open", str(source), "--into", str(into), "--author", "Sam Okoye", "--today", "2026-10-12", *extra)


def tree(root):
    return {p.relative_to(root).as_posix(): p.read_bytes() for p in root.rglob("*")
            if p.is_file() and ".planner" not in p.relative_to(root).parts}


def test_folder_and_zip_give_the_same_workspace(tmp_path, published):
    folder, archive = published
    for source, name in ((folder, "from-folder"), (archive, "from-zip")):
        code, text = open_copy(source, tmp_path / "ws" / name)
        assert code == 0, text
    assert tree(tmp_path / "ws" / "from-folder") == tree(tmp_path / "ws" / "from-zip") != {}


def test_open_writes_baseline_workspace_json_and_the_explorer(tmp_path, published):
    folder, _ = published
    stamp = json.loads((folder / ".planner" / "published.json").read_text(encoding="utf-8"))
    code, text = open_copy(folder, tmp_path / "ws")
    assert code == 0, text
    ws = tmp_path / "ws"
    without_dashboard = lambda files: {name: data for name, data in files.items() if name != "dashboard.html"}  # rebuilt here, so it differs from the published one
    assert without_dashboard(tree(ws / ".planner" / "baseline")) == without_dashboard(tree(ws)) != {}
    record = json.loads((ws / ".planner" / "workspace.json").read_text(encoding="utf-8"))
    assert record["role"] == "reader" and record["base_commit"] == stamp["commit"] and record["base_date"] == "2026-10-11"
    assert record["source_path"] == str(folder) and record["author"] == "Sam Okoye" and record["opened"] == "2026-10-12"
    assert record["base_tree_hash"] == stamp["tree_hash"] and record["planner_path"].endswith("scripts/planner")
    assert not (ws / ".git").exists() and (ws / "dashboard.html").is_file()
    assert f"Opened {stamp['title']} at {stamp['short']}, published 2026-10-11 by Priya Nair" in text
    assert "Your copy is the latest published" in text


def test_the_new_workspace_is_a_reader(tmp_path, published):
    open_copy(published[0], tmp_path / "ws")
    code, text = run("role", "--vault", str(tmp_path / "ws"))
    assert code == 0 and text.startswith("planner role: reader")


def test_the_source_is_never_written(tmp_path, published):
    folder, archive = published
    before = (digest(folder), digest(archive))
    assert open_copy(folder, tmp_path / "a")[0] == 0 and open_copy(archive, tmp_path / "b")[0] == 0
    assert (digest(folder), digest(archive)) == before
    assert sorted(p.name for p in folder.parent.iterdir() if p.name.startswith(".")) == []


def test_a_workspace_inside_onedrive_is_refused_and_nothing_is_written(tmp_path, published):
    for place in ("OneDrive - Acme/ws", "Documents/SharePoint/ws"):
        code, text = open_copy(published[0], tmp_path / place)
        assert code == 2 and "synced folder" in text and "--into" in text
        assert not (tmp_path / place).exists()


def test_the_default_location_and_the_env_override(tmp_path, published, monkeypatch):
    monkeypatch.setenv("PLANNER_WORKSPACES", str(tmp_path / "mine"))
    code, text = run("open", str(published[0]), "--author", "Sam Okoye")
    assert code == 0, text
    assert [p.name for p in (tmp_path / "mine").iterdir()] == ["trading-coach" if False else p.name for p in (tmp_path / "mine").iterdir()]
    assert len(list((tmp_path / "mine").iterdir())) == 1


def test_where_the_workspace_goes_by_rule(tmp_path, monkeypatch):
    slug = "paper-orders"
    monkeypatch.setattr(pathlib.Path, "home", classmethod(lambda cls: tmp_path / "home"))
    monkeypatch.chdir(tmp_path)
    assert cli.workspace_folder(slug, None, {}, False) == tmp_path / "home" / "PlannerWorkspaces" / slug
    assert cli.workspace_folder(slug, None, {}, True) == tmp_path.resolve() / "planner-workspaces" / slug
    assert cli.workspace_folder(slug, None, {"PLANNER_WORKSPACES": str(tmp_path / "w")}, True) == tmp_path / "w" / slug
    assert cli.workspace_folder(slug, str(tmp_path / "x"), {"PLANNER_WORKSPACES": "/w"}, True) == tmp_path / "x"
    monkeypatch.setattr(pathlib.Path, "home", classmethod(lambda cls: tmp_path / "OneDrive - Acme"))
    with pytest.raises(opening.OpenError, match="synced folder"):
        cli.workspace_folder(slug, None, {}, False)


def test_reopening_the_same_publish_changes_nothing_and_keeps_drafts(tmp_path, published):
    folder, _ = published
    ws = tmp_path / "ws"
    assert open_copy(folder, ws)[0] == 0
    page = next(p for p in sorted(ws.glob("*.md")) if p.name != "CONVENTIONS.md")
    page.write_text(page.read_text(encoding="utf-8") + "\nmy draft\n", encoding="utf-8")
    before = digest(ws)
    code, text = open_copy(folder, ws)
    assert code == 0 and "already on" in text and "nothing to replay" in text
    assert digest(ws) == before


def test_reopening_into_a_workspace_of_another_initiative_says_so(tmp_path, published):
    folder, _ = published
    ws = tmp_path / "ws"
    assert open_copy(folder, ws)[0] == 0
    record_path = ws / ".planner" / "workspace.json"
    record = json.loads(record_path.read_text(encoding="utf-8"))
    record["initiative"] = "INI-999"
    record_path.write_text(json.dumps(record), encoding="utf-8")
    code, text = open_copy(folder, ws)
    assert code == 2 and "INI-999" in text


def test_a_non_empty_folder_that_is_not_a_workspace_is_refused(tmp_path, published):
    ws = tmp_path / "ws"
    ws.mkdir()
    (ws / "mine.txt").write_text("keep", encoding="utf-8")
    code, text = open_copy(published[0], ws)
    assert code == 2 and "not empty" in text and (ws / "mine.txt").read_text(encoding="utf-8") == "keep"


def test_a_copy_edited_after_publishing_is_refused(tmp_path, published):
    folder, _ = published
    page = next(p for p in sorted(folder.glob("*.md")))
    page.write_text(page.read_text(encoding="utf-8") + "sneaky\n", encoding="utf-8")
    code, text = open_copy(folder, tmp_path / "ws")
    assert code == 2 and "tree_hash" in text and not (tmp_path / "ws").exists()


def test_os_junk_in_a_synced_folder_does_not_look_like_tampering(tmp_path, published):
    folder, _ = published
    (folder / ".DS_Store").write_bytes(b"junk")
    code, text = open_copy(folder, tmp_path / "ws")
    assert code == 0, text
    assert not (tmp_path / "ws" / ".DS_Store").exists()


def test_a_zip_name_that_climbs_out_is_refused(tmp_path, published):
    _, archive = published
    evil = tmp_path / "evil.zip"
    with zipfile.ZipFile(archive) as src, zipfile.ZipFile(evil, "w") as dst:
        for info in src.infolist():
            dst.writestr(info, src.read(info))
        dst.writestr("../x", b"escaped")
    code, text = open_copy(evil, tmp_path / "ws")
    assert code == 2 and "outside" in text and not (tmp_path / "ws").exists() and not (tmp_path / "x").exists()


def test_a_folder_that_is_not_a_published_copy_is_refused(tmp_path):
    (tmp_path / "plain").mkdir()
    code, text = open_copy(tmp_path / "plain", tmp_path / "ws")
    assert code == 2 and "not a published copy" in text
    code, text = open_copy(tmp_path / "missing", tmp_path / "ws")
    assert code == 2 and "does not exist" in text


def test_a_stamp_without_a_hash_cannot_vouch_for_the_files():
    with pytest.raises(opening.OpenError, match="no tree_hash"):
        opening.verify_tree({"a.md": b"x"}, {})
