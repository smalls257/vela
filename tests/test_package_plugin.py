"""The claude.ai package is built from committed files and never carries bin/."""
import subprocess
import sys
import zipfile

import pytest

from conftest import REPO

sys.path.insert(0, str(REPO / "tools"))
import package_plugin  # noqa: E402


def git(repo, *args):
    subprocess.run(["git", "-C", str(repo), "-c", "user.name=t", "-c", "user.email=t@t", *args],
                   check=True, capture_output=True)


@pytest.fixture
def repo(tmp_path):
    root = tmp_path / "repo"
    (root / "plugin" / ".claude-plugin").mkdir(parents=True)
    (root / "plugin" / "bin").mkdir()
    (root / "plugin" / "scripts").mkdir()
    (root / "plugin" / "lib" / "__pycache__").mkdir(parents=True)
    (root / "plugin" / ".claude-plugin" / "plugin.json").write_text('{"name": "planner"}')
    (root / "plugin" / "bin" / "planner").write_text("#!/bin/sh\n")
    (root / "plugin" / "scripts" / "planner").write_text("#!/usr/bin/env python3\n")
    (root / "plugin" / "lib" / "mod.py").write_text("x = 1\n")
    (root / "plugin" / "lib" / "__pycache__" / "mod.cpython-311.pyc").write_bytes(b"\0")
    git(root.parent, "init", str(root))
    git(root, "add", "-f", ".")
    git(root, "commit", "-m", "plugin")
    return root


def names(path):
    with zipfile.ZipFile(path) as archive:
        return sorted(archive.namelist())


def test_zip_has_manifest_at_root_and_no_bin_or_caches(repo, tmp_path):
    out = tmp_path / "p.zip"
    count = package_plugin.package(out, repo=repo, say=lambda _: None)
    assert names(out) == [".claude-plugin/plugin.json", "lib/mod.py", "scripts/planner"]
    assert count == 3


def test_uncommitted_edits_do_not_ship(repo, tmp_path):
    (repo / "plugin" / "lib" / "mod.py").write_text("x = 2\n")
    (repo / "plugin" / "lib" / "new.py").write_text("y = 1\n")
    out = tmp_path / "p.zip"
    package_plugin.package(out, repo=repo, say=lambda _: None)
    with zipfile.ZipFile(out) as archive:
        assert archive.read("lib/mod.py") == b"x = 1\n"
    assert "lib/new.py" not in names(out)


def test_scripts_keep_their_executable_bit(repo, tmp_path):
    (repo / "plugin" / "scripts" / "planner").chmod(0o755)
    git(repo, "add", "-A")
    git(repo, "commit", "-m", "exec")
    out = tmp_path / "p.zip"
    package_plugin.package(out, repo=repo, say=lambda _: None)
    with zipfile.ZipFile(out) as archive:
        assert archive.getinfo("scripts/planner").external_attr >> 16 & 0o111


def test_missing_manifest_is_refused(repo, tmp_path):
    git(repo, "rm", "-q", "plugin/.claude-plugin/plugin.json")
    git(repo, "commit", "-m", "drop manifest")
    with pytest.raises(package_plugin.PackageError, match="plugin.json"):
        package_plugin.package(tmp_path / "p.zip", repo=repo, say=lambda _: None)


def test_missing_claude_is_said_aloud_not_silently_skipped(repo, tmp_path, monkeypatch):
    monkeypatch.setattr(package_plugin.shutil, "which", lambda _: None)
    said = []
    package_plugin.package(tmp_path / "p.zip", repo=repo, say=said.append)
    assert said and "skipped" in said[0]


def test_real_plugin_packages_without_bin(tmp_path):
    out = tmp_path / "p.zip"
    package_plugin.package(out, say=lambda _: None)
    listed = names(out)
    assert ".claude-plugin/plugin.json" in listed
    assert not any(n.startswith("bin/") for n in listed)


def test_a_tag_in_a_skill_description_is_refused(tmp_path):
    """claude.ai and Cowork reject the whole upload when a description holds `<slug>`; validate doesn't catch it."""
    out = tmp_path / "p.zip"
    with zipfile.ZipFile(out, "w") as archive:
        archive.writestr(".claude-plugin/plugin.json", "{}")
        archive.writestr("skills/x/SKILL.md", "---\nname: x\ndescription: Writes docs/plan/<slug>.md.\n---\nbody <slug> is fine here\n")
    with pytest.raises(package_plugin.PackageError, match=r"skills/x/SKILL.md has <slug>"):
        package_plugin.verify_layout(out)


def test_no_shipped_skill_description_holds_a_tag():
    for path in sorted((REPO / "plugin" / "skills").glob("*/SKILL.md")):
        front = path.read_text(encoding="utf-8").split("---", 2)[1]
        match = package_plugin.DESCRIPTION.search(front)
        assert not (match and package_plugin.TAG.search(match.group(1))), path
