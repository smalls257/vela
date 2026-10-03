import json
import os

from conftest import REPO

STUB = REPO / "tests" / "stub-conventions"


def test_manifest_names_the_plugin():
    data = json.loads((REPO / "plugin" / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8"))
    assert data["name"] == "planner"
    assert data["version"] == "0.1.0"
    assert data["author"]["name"]


def test_bin_planner_is_executable():
    assert os.access(REPO / "plugin" / "bin" / "planner", os.X_OK)


def test_stub_plugin_holds_only_the_conventions():
    files = sorted(p.relative_to(STUB).as_posix() for p in STUB.rglob("*") if p.is_file())
    assert files == [".claude-plugin/plugin.json", "CONVENTIONS.md"]
    assert json.loads((STUB / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8"))["name"] == "planner-conventions"


def test_stub_conventions_equal_the_template_copy():
    assert (STUB / "CONVENTIONS.md").read_bytes() == (REPO / "template" / "CONVENTIONS.md").read_bytes()
