"""Generated files are written whole or not at all, and render is all-or-nothing (C29, C34)."""
import os

import pytest

from conftest import edit, run
from vela.edge import atomic


def test_an_interrupted_write_leaves_the_old_file_whole_and_no_temp_file(tmp_path, monkeypatch):
    target = tmp_path / "manifest.md"
    target.write_text("old, whole", encoding="utf-8")

    def die(src, dst):
        raise OSError(28, "No space left on device")
    monkeypatch.setattr(os, "replace", die)
    with pytest.raises(atomic.WriteFailed):
        atomic.write_atomic(target, "new")
    assert target.read_text(encoding="utf-8") == "old, whole"
    assert [p.name for p in tmp_path.iterdir()] == ["manifest.md"]


def test_a_file_that_cannot_be_staged_leaves_every_target_untouched(tmp_path):
    a, b = tmp_path / "a.md", tmp_path / "missing-folder" / "b.md"
    a.write_text("old", encoding="utf-8")
    with pytest.raises(atomic.WriteFailed) as seen:
        atomic.write_all_atomic({a: "new a", b: "new b"})
    assert a.read_text(encoding="utf-8") == "old"
    assert seen.value.written == []


def test_render_writes_nothing_when_one_page_cannot_be_written(mini, monkeypatch):
    edit(mini / "11-unknowns-and-risks.md", "- **Owner:** @mini-qa", "- **Owner:** @mini-lead")  # two pages' blocks go out of date
    before = {p: p.read_bytes() for p in mini.rglob("*.md")}
    real = atomic._temp_name
    calls = []

    def temp_name(path):
        calls.append(path)
        return mini / "no-such-folder" / "x.tmp" if len(calls) == 2 else real(path)
    monkeypatch.setattr(atomic, "_temp_name", temp_name)
    code, out = run("render", "--vault", str(mini))
    assert code == 2 and "render could not finish" in out and "Not written" in out, out
    assert {p: p.read_bytes() for p in mini.rglob("*.md")} == before
    assert not list(mini.rglob("*.tmp"))


def test_view_and_export_leave_no_temp_file(mini, tmp_path):
    out_dir = tmp_path / "out"
    out_dir.mkdir()
    assert run("view", "--vault", str(mini), "--out", str(out_dir / "v.html"), "--date", "2026-01-15")[0] == 0
    assert [p.name for p in out_dir.iterdir()] == ["v.html"]
