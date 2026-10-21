"""scripts/run-vela picks the Python. Windows installs `python`, and its `python3` is often a store shortcut that
prints a hint and exits, so the first name on the PATH is not proof: each candidate has to run Python 3.9 or later,
and when none does the launcher says so and exits 2 instead of failing somewhere later."""
import os
import pathlib
import shutil
import subprocess
import sys

from conftest import REPO

RUN_VELA = REPO / "plugin" / "scripts" / "run-vela"
SH = shutil.which("sh")


def fake(folder, name, body):
    path = folder / name
    path.write_text("#!/bin/sh\n" + body + "\n", encoding="utf-8")
    path.chmod(0o755)


def run(path_dirs):
    env = {**os.environ, "PATH": os.pathsep.join(str(d) for d in path_dirs)}
    return subprocess.run([SH, str(RUN_VELA), "--version"], env=env, capture_output=True, text=True, timeout=60)


def test_a_store_shortcut_named_python3_is_passed_over_for_a_python_that_runs(tmp_path):
    stub, real = tmp_path / "stub", tmp_path / "real"
    stub.mkdir(), real.mkdir()
    fake(stub, "python3", 'echo "Python was not found; run without arguments to install from the Microsoft Store" >&2; exit 9009')
    (real / "python").symlink_to(sys.executable)
    done = run([stub, real])
    assert done.returncode == 0 and "vela" in (done.stdout + done.stderr).lower(), done


def test_a_python_older_than_3_9_is_passed_over(tmp_path):
    old, real = tmp_path / "old", tmp_path / "real"
    old.mkdir(), real.mkdir()
    fake(old, "python3", "exit 1")  # what `python3 -c 'sys.exit(version < (3, 9))'` returns on 3.8
    (real / "python").symlink_to(sys.executable)
    assert run([old, real]).returncode == 0


def test_no_python_is_a_loud_exit_2(tmp_path):
    fake(tmp_path, "python3", "exit 9009")
    done = run([tmp_path])
    assert done.returncode == 2 and "no Python 3.9 or later found as python3, python or py" in done.stderr


def test_every_hook_and_skill_runs_vela_through_the_launcher():
    hooks = (REPO / "plugin" / "hooks" / "hooks.json").read_text(encoding="utf-8")
    assert "python3" not in hooks
    for path in sorted((REPO / "plugin").rglob("*.md")):
        text = path.read_text(encoding="utf-8")
        assert "python3 ${CLAUDE_PLUGIN_ROOT}/scripts/vela" not in text and "Bash(python3 " not in text, path
