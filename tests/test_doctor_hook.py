"""The vault's pre-commit hook and planner doctor (fix request 2026-10-14): a plugin installed from the marketplace lives
under ~/.claude/plugins/, where the hook did not look, so every hand commit stopped. The hook now also reads this clone's
`git config planner.path`; doctor finds the installed launcher and prints the one command that records it. The hook
still stops, never waves a commit through, when it cannot find the planner."""
import json
import os
import shutil
import subprocess

import pytest

from conftest import REPO, run
from planner import doctor
from planner.edge import machine

LAUNCHER = REPO / "plugin" / "scripts" / "planner"
HOOK = REPO / "template" / ".githooks" / "pre-commit"
INSTALLED = "/home/lead/.claude/plugins/cache/vela/planner/0.3.0/scripts/planner"


def a_hook(**fields):
    base = dict(hook_file=True, hooks_on=True, env_planner="", config_path="", vendored="/v/.claude/skills/planner/scripts/planner",
                launcher=INSTALLED)
    return doctor.Hook(**{**base, **fields})


def exists(*paths):
    return lambda path: path in paths


# --- what doctor says, pure ---------------------------------------------------------------------------------------

def test_a_hook_that_finds_nothing_names_the_one_command_that_wires_it():
    line = doctor.hook_line(a_hook(), exists(INSTALLED))
    assert line.status == "optional" and "stops every commit typed by hand" in line.text
    assert line.text.endswith(f"Wire it: git config planner.path {INSTALLED}")


def test_hooks_that_are_off_get_them_turned_on_in_the_same_command():
    line = doctor.hook_line(a_hook(hooks_on=False), exists(INSTALLED))
    assert "is off" in line.text and line.text.endswith(f"Wire it: git config core.hooksPath .githooks && git config planner.path {INSTALLED}")
    wired = doctor.hook_line(a_hook(hooks_on=False, config_path=INSTALLED), exists(INSTALLED))
    assert wired.text.endswith("Wire it: git config core.hooksPath .githooks")


def test_a_wired_hook_is_ok_and_one_on_another_copy_says_two_versions_answer():
    assert doctor.hook_line(a_hook(config_path=INSTALLED), exists(INSTALLED)).status == "ok"
    other = doctor.hook_line(a_hook(), exists(INSTALLED, "/v/.claude/skills/planner/scripts/planner"))
    assert other.status == "optional" and "two versions answer this vault" in other.text and "the vendored copy" in other.text
    gone = doctor.hook_line(a_hook(config_path="/old/0.2.0/scripts/planner"), exists(INSTALLED))
    assert "git config planner.path names a launcher that isn't there" in gone.text  # an updated plugin moved


def test_no_hook_file_is_information_and_a_path_with_spaces_is_quoted():
    assert doctor.hook_line(a_hook(hook_file=False), exists()).status == "info"
    spaced = doctor.hook_line(a_hook(launcher="/Users/A B/planner"), exists("/Users/A B/planner"))
    assert spaced.text.endswith("git config planner.path '/Users/A B/planner'")


def test_the_installed_launcher_is_read_from_claude_code_s_plugin_registry(tmp_path):
    install = tmp_path / "cache" / "vela" / "planner" / "0.3.0"
    (install / "scripts").mkdir(parents=True)
    (install / "scripts" / "planner").write_text("#!/usr/bin/env python3\n", encoding="utf-8")
    registry = {"version": 2, "plugins": {"other@x": [{"installPath": "/nowhere"}],
                                          "planner@vela": [{"scope": "user", "installPath": str(install)}]}}
    (tmp_path / "plugins").mkdir()
    (tmp_path / "plugins" / "installed_plugins.json").write_text(json.dumps(registry), encoding="utf-8")
    assert machine.installed_launcher({"CLAUDE_CONFIG_DIR": str(tmp_path)}) == str(install / "scripts" / "planner")
    # no registry entry: the launcher running doctor
    assert machine.installed_launcher({"CLAUDE_CONFIG_DIR": str(tmp_path / "empty")}) == str(machine.RUNNING)


# --- the hook and doctor agree, on a real clone ----------------------------------------------------------------------

def git(root, *args, env=None):
    return subprocess.run(["git", "-C", str(root), *args], capture_output=True, text=True, timeout=60,
                          env={**os.environ, **(env or {})})


@pytest.fixture
def vault(mini):
    (mini / ".githooks").mkdir()
    shutil.copy(HOOK, mini / ".githooks" / "pre-commit")
    os.chmod(mini / ".githooks" / "pre-commit", 0o755)
    git(mini, "init", "-q")
    for key, value in (("user.name", "Test Lead"), ("user.email", "lead@example.com")):
        git(mini, "config", key, value)
    return mini


def commit(root, name):
    (root / name).write_text("words\n", encoding="utf-8")
    git(root, "add", "--", name)
    env = {k: v for k, v in os.environ.items() if k != "PLANNER"}
    return subprocess.run(["git", "-C", str(root), "commit", "-q", "-m", name], capture_output=True, text=True, timeout=60, env=env)


@pytest.mark.parametrize("config,stops", [("", True), ("/nowhere/scripts/planner", True), (str(LAUNCHER), False)])
def test_the_hook_follows_doctor_s_order_and_stops_when_it_finds_nothing(vault, config, stops):
    git(vault, "config", "core.hooksPath", ".githooks")
    if config:
        git(vault, "config", "planner.path", config)
    facts = machine.hook_facts(vault, environ={})
    assert doctor.hook_finds(facts, os.path.isfile)[1] == ("" if stops else str(LAUNCHER))
    done = commit(vault, "notes.md")
    assert (done.returncode != 0) == stops, done.stderr
    if stops:
        assert "were not checked" in done.stderr and "planner doctor" in done.stderr


def test_doctor_prints_the_command_and_after_it_a_hand_commit_is_checked(vault, monkeypatch):
    monkeypatch.delenv("PLANNER", raising=False)
    monkeypatch.setattr(machine, "installed_launcher", lambda environ=None, home=None: str(LAUNCHER))
    _, out = run("doctor", "--vault", str(vault))
    line = next(x for x in out.splitlines() if "pre-commit hook" in x)
    command = line.split("Wire it: ", 1)[1]
    assert command == f"git config core.hooksPath .githooks && git config planner.path {LAUNCHER}"
    for step in command.split(" && "):
        assert subprocess.run(step.split(" "), cwd=vault, capture_output=True, timeout=60).returncode == 0
    _, out = run("doctor", "--vault", str(vault))
    assert f"ok        the vault's pre-commit hook checks hand commits with the planner at {LAUNCHER}" in out
    assert commit(vault, "notes.md").returncode == 0
