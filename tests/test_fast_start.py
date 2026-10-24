"""The commands a chat waits on start without the whole CLI, and an installed plugin keeps its bytecode outside
itself (plan Task 3, rulings 2 and 3)."""
import json
import os
import subprocess
import sys

import pytest

from budget import installed_copy, measure
from conftest import REPO
from vela import cli
from vela.commands import fast

SCRIPT = REPO / "plugin" / "scripts" / "vela"


def imported(argv, stdin="{}", env=None):
    done = subprocess.run([sys.executable, "-X", "importtime", str(SCRIPT), *argv], input=stdin,
                          capture_output=True, text=True, env=env, timeout=60)
    return {line.rsplit("|", 1)[-1].strip() for line in done.stderr.splitlines() if "|" in line}


@pytest.mark.parametrize("argv", [["hook", "said"], ["hook", "session-start"], ["hook", "bash"], ["hook", "post-edit"]])
def test_fast_commands_never_import_the_whole_cli(tmp_path, argv):
    found = imported(argv, stdin=json.dumps({"cwd": str(tmp_path), "prompt": "hello"}))
    assert "vela.cli" not in found and "vela.explorer.build" not in found, argv


def test_everything_else_still_goes_through_the_cli():
    assert not fast.serves(["check"]) and not fast.serves(["--help"]) and fast.serves(["hook", "said"])


def test_the_fast_and_full_parsers_say_the_same(tmp_path, capsys):
    payload = json.dumps({"cwd": str(tmp_path), "prompt": "hello"})
    full = subprocess.run([sys.executable, "-c", "import sys; sys.path.insert(0, sys.argv[1]); from vela import cli; "
                           "sys.exit(cli.main(sys.argv[2:]))", str(REPO / "plugin" / "lib"), "hook", "said"],
                          input=payload, capture_output=True, text=True)
    quick = subprocess.run([sys.executable, str(SCRIPT), "hook", "said"], input=payload, capture_output=True, text=True)
    assert (full.returncode, full.stdout) == (quick.returncode, quick.stdout)


def test_tool_errors_keep_their_exit_code_through_the_fast_entry(tmp_path):
    done = subprocess.run([sys.executable, str(SCRIPT), "hook", "nonsense"], capture_output=True, text=True)
    assert done.returncode == 2


def test_an_installed_copy_writes_no_cache_inside_itself(tmp_path):
    plugin = installed_copy(tmp_path)
    env = {**os.environ, "VELA_PYCACHE": str(tmp_path / "cache")}
    done = subprocess.run(["sh", str(plugin / "scripts" / "run-vela"), "--version"], capture_output=True, text=True, env=env)
    assert done.returncode == 0, done.stdout
    assert not list(plugin.rglob("__pycache__")) and list((tmp_path / "cache").rglob("*.pyc"))


def test_the_default_cache_is_the_users_cache_folder_never_dot_claude(tmp_path):
    plugin = installed_copy(tmp_path / "p")
    env = {k: v for k, v in os.environ.items() if k not in ("VELA_PYCACHE", "XDG_CACHE_HOME", "LOCALAPPDATA")}
    env["HOME"] = str(tmp_path / "home")
    done = subprocess.run(["sh", str(plugin / "scripts" / "run-vela"), "--version"], capture_output=True, text=True, env=env)
    assert done.returncode == 0, done.stdout
    cached = list((tmp_path / "home").rglob("*.pyc"))
    assert cached and all(".claude" not in p.parts for p in cached)
    assert any(part in ("Caches", ".cache") for part in cached[0].parts)


def test_a_hook_costs_little_from_an_installed_copy(tmp_path):
    plugin = installed_copy(tmp_path)
    (tmp_path / "plan").mkdir()
    (tmp_path / "plan" / ".vela.yaml").write_text("initiative: INI-001\ntitle: A plan\n", encoding="utf-8")
    env = {**os.environ, "VELA_PYCACHE": str(tmp_path / "cache")}
    got = measure(plugin, ["hook", "said"], env, stdin=json.dumps({"cwd": str(tmp_path / "plan"), "prompt": "hi"}))
    print(f"hook said: {got['cpu']:.3f} s CPU, {got['wall']:.3f} s wall")
    assert got["cpu"] < 0.2, got   # why: it runs before every message the person sends


def test_cli_still_raises_the_same_tool_error():
    from vela import errors
    assert cli.ToolError is errors.ToolError


def test_the_companion_session_command_never_imports_the_whole_cli(tmp_path):
    from companion_vault import grill_session
    root = grill_session(tmp_path)
    found = imported(["companion", "session", "--json", "--vault", str(root)])
    assert "vela.cli" not in found and "vela.explorer.build" not in found


def test_two_versions_at_one_path_get_separate_bytecode_caches(tmp_path):
    """The release zip stamps every file 1980-01-01, so a same-size edit unzipped over the same path looks unchanged to
    Python; a cache folder per plugin version keeps the old bytecode from being served to the new code."""
    plugin = installed_copy(tmp_path / "p")
    env = {k: v for k, v in os.environ.items() if k not in ("VELA_PYCACHE", "XDG_CACHE_HOME", "LOCALAPPDATA")}
    env["HOME"] = str(tmp_path / "home")
    manifest = plugin / ".claude-plugin" / "plugin.json"
    for version in ("1.0.0", "1.0.1"):
        data = json.loads(manifest.read_text(encoding="utf-8"))
        data["version"] = version
        manifest.write_text(json.dumps(data), encoding="utf-8")
        done = subprocess.run(["sh", str(plugin / "scripts" / "run-vela"), "--version"], capture_output=True, text=True, env=env)
        assert done.returncode == 0, done.stdout
    cache = next((tmp_path / "home").rglob("pycache"))
    assert {"1.0.0", "1.0.1"} <= {child.name for child in cache.iterdir()}
