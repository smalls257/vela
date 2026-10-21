import json
import os
import re

from conftest import REPO

STUB = REPO / "tests" / "stub-conventions"


def test_manifest_names_the_plugin():
    data = json.loads((REPO / "plugin" / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8"))
    assert data["name"] == "vela"
    # Version must be in semantic versioning format (e.g., 0.3.0)
    assert re.match(r"^\d+\.\d+\.\d+$", data["version"]), f"version {data['version']} is not in semver format"
    assert data["author"]["name"]


def test_scripts_vela_is_executable():
    assert os.access(REPO / "plugin" / "scripts" / "vela", os.X_OK)


def test_bin_vela_is_only_a_shim_onto_scripts():
    shim = REPO / "plugin" / "bin" / "vela"
    assert os.access(shim, os.X_OK)
    code = [ln for ln in shim.read_text(encoding="utf-8").splitlines() if ln.strip() and not ln.startswith("#")]
    assert code == ['exec sh "$(dirname "$0")/../scripts/run-vela" "$@"']


def test_stub_plugin_holds_only_the_conventions():
    files = sorted(p.relative_to(STUB).as_posix() for p in STUB.rglob("*") if p.is_file())
    assert files == [".claude-plugin/plugin.json", "CONVENTIONS.md"]
    assert json.loads((STUB / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8"))["name"] == "vela-conventions"


def test_plugin_conventions_equal_the_template_copy():
    assert (REPO / "plugin" / "vault" / "CONVENTIONS.md").read_bytes() == (REPO / "template" / "CONVENTIONS.md").read_bytes()


def test_stub_conventions_equal_the_template_copy():
    assert (STUB / "CONVENTIONS.md").read_bytes() == (REPO / "template" / "CONVENTIONS.md").read_bytes()
