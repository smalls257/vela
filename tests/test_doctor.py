"""vela doctor, the bundled PyYAML and the Python 3.9 floor: install is add the marketplace, install the plugin,
run vela doctor, and nothing else."""
import os
import pathlib
import re
import shutil
import subprocess
import sys

import pytest

from conftest import REPO, run
from vela import doctor

LAUNCHER = REPO / "plugin" / "scripts" / "vela"
VENDORED = REPO / "plugin" / "lib" / "yaml"

EVERYTHING = doctor.Machine(python=(3, 9, 6), python_path="/usr/bin/python3", yaml_version=doctor.PINNED_YAML,
                            yaml_bundled=True, yaml_path=str(VENDORED), git="git version 2.50.1", node="v22.1.0",
                            claude="/usr/local/bin/claude", voice_missing=())
A_VAULT = doctor.Vault("/v", "INI-001", "Heron")


def lines_for(machine=EVERYTHING, vault=A_VAULT):
    return doctor.report(machine, vault, "0.3.0")


def changed(**fields):
    return doctor.Machine(**{**EVERYTHING.__dict__, **fields})


# --- the report, pure ---------------------------------------------------------------------------------------------

def test_one_line_per_item_and_ready_when_all_there():
    lines = lines_for()
    assert [line.status for line in lines] == ["ok"] * 6 + ["info", "info"]
    assert doctor.exit_code(lines) == 0
    text = doctor.render(lines)
    assert len(text.splitlines()) == 9 and text.endswith("vela doctor: ready.")
    for words in ("Python 3.9.6", "PyYAML 6.0.3, bundled with the plugin", "git version 2.50.1", "node v22.1.0",
                  "Ask Claude", "voicescore works", "/v is a vault: INI-001 Heron", "vela plugin 0.3.0"):
        assert words in text


@pytest.mark.parametrize("fields, adds, command", [
    ({"node": None}, "parses every diagram", "brew install node"),
    ({"claude": None}, "Ask Claude box answers in the page", "curl -fsSL https://claude.ai/install.sh | bash"),
    ({"voice_missing": ("sentence-transformers", "torch")}, "how close a draft is to your own writing",
     "/usr/bin/python3 -m pip install sentence-transformers"),
])
def test_a_missing_optional_piece_says_what_it_adds_and_how_to_get_it_and_still_exits_0(fields, adds, command):
    lines = lines_for(changed(**fields))
    flagged = [line for line in lines if line.status == "optional"]
    assert len(flagged) == 1 and adds in flagged[0].text and command in flagged[0].text
    assert doctor.exit_code(lines) == 0


@pytest.mark.parametrize("fields, words", [
    ({"python": (3, 8, 10)}, "brew install python@3.12"),
    ({"git": None}, "xcode-select --install"),
    ({"yaml_bundled": False, "yaml_path": "/site-packages/yaml"}, "not the copy bundled"),
    ({"yaml_version": "5.4"}, "not 6.0.3"),
])
def test_a_missing_required_piece_exits_1_and_says_the_fix(fields, words):
    lines = lines_for(changed(**fields))
    assert doctor.exit_code(lines) == 1
    assert [line.text for line in lines if line.status == "missing"][0].count(words) == 1
    assert "something vela needs is missing" in doctor.render(lines)


def test_not_being_in_a_vault_is_information_not_a_failure():
    lines = lines_for(vault=doctor.Vault("/home/me", problem="there is no .vela.yaml here."))
    assert doctor.exit_code(lines) == 0
    assert "/home/me is not a vault: there is no .vela.yaml here." in doctor.render(lines)


# --- the command, on this machine ---------------------------------------------------------------------------------

def test_doctor_in_a_vault_names_it(mini):
    code, out = run("doctor", "--vault", str(mini))
    assert f"{mini.resolve()} is a vault: INI-" in out
    assert "PyYAML 6.0.3, bundled with the plugin" in out
    assert code == (1 if shutil.which("git") is None else 0)


def test_doctor_names_a_broken_vela_yaml(tmp_path):
    (tmp_path / ".vela.yaml").write_text("title: x\n", encoding="utf-8")
    code, out = run("doctor", "--vault", str(tmp_path))
    assert "is not a vault: .vela.yaml needs 'initiative: INI-nnn'" in out


# --- the bundled PyYAML -------------------------------------------------------------------------------------------

def test_the_bundled_pyyaml_is_the_pinned_pure_python_release_with_its_license():
    assert re.search(r"^__version__ = '6\.0\.3'$", (VENDORED / "__init__.py").read_text(encoding="utf-8"), re.M)
    assert doctor.PINNED_YAML == "6.0.3"
    assert "Permission is hereby granted" in (VENDORED / "LICENSE").read_text(encoding="utf-8")
    assert not [p for p in VENDORED.iterdir() if p.suffix in (".so", ".pyd", ".c", ".pyx")]


def test_the_launcher_loads_the_bundled_pyyaml_even_when_the_machine_has_another(tmp_path):
    shadow = tmp_path / "shadow" / "yaml"
    shadow.mkdir(parents=True)
    (shadow / "__init__.py").write_text("__version__ = '0.0-machine'\n", encoding="utf-8")
    done = subprocess.run([sys.executable, str(LAUNCHER), "doctor", "--vault", str(tmp_path)], capture_output=True,
                          text=True, timeout=120, env={**os.environ, "PYTHONPATH": str(shadow.parent)})
    assert "PyYAML 6.0.3, bundled with the plugin" in done.stdout, done.stdout + done.stderr
    assert "0.0-machine" not in done.stdout


def test_the_launcher_has_no_pip_step_and_states_the_floor():
    text = LAUNCHER.read_text(encoding="utf-8")
    assert "pip install pyyaml" not in text
    assert f"sys.version_info < {doctor.FLOOR}" in text and "brew install python@3.12" in text


def test_the_cowork_zip_ships_the_bundled_pyyaml():
    sys.path.insert(0, str(REPO / "tools"))
    import package_plugin
    assert not package_plugin.excluded("lib/yaml/__init__.py") and not package_plugin.excluded("lib/yaml/LICENSE")


def test_lint_skips_the_bundled_pyyaml_and_nothing_else_of_lib():
    ignore = (REPO / ".semgrepignore").read_text(encoding="utf-8").splitlines()
    assert "plugin/lib/yaml/" in ignore
    assert not any(line.startswith("plugin/lib/vela") and line.endswith("/") for line in ignore)


# --- Python 3.9, what a Mac ships -------------------------------------------------------------------------------

def python39():
    for candidate in ("python3.9", "/usr/bin/python3"):
        found = shutil.which(candidate)
        if found:
            done = subprocess.run([found, "-c", "import sys; print(sys.version_info[:2] == (3, 9))"],
                                  capture_output=True, text=True, timeout=60)
            if done.stdout.strip() == "True":
                return found
    return None


@pytest.mark.skipif(python39() is None, reason="no Python 3.9 on this machine")
def test_every_plugin_module_parses_and_the_cli_runs_on_python_39(mini):
    sources = [str(p) for p in (REPO / "plugin" / "lib").rglob("*.py")] + [str(LAUNCHER)]
    parse = subprocess.run([python39(), "-c", "import ast, sys\nfor p in sys.argv[1:]: ast.parse(open(p, encoding='utf-8').read(), p)",
                            *sources], capture_output=True, text=True, timeout=120)
    assert parse.returncode == 0, parse.stderr
    done = subprocess.run([python39(), str(LAUNCHER), "check"], cwd=mini, capture_output=True, text=True, timeout=120)
    assert done.returncode in (0, 1) and "Traceback" not in done.stdout + done.stderr, done.stdout + done.stderr
