"""The mod validates and its own tests pass, wherever claude is installed (Task 11)."""
import json
import shutil
import subprocess

import pytest

from conftest import REPO

PLUGIN = REPO / "plugin"


def claude():
    found = shutil.which("claude")
    if found is None:
        pytest.skip("claude is not on PATH, so the mod can't be validated or tested here")
    return found


def test_the_hooks_file_keeps_every_settings_hook_and_adds_the_module():
    hooks = json.loads((PLUGIN / "hooks" / "hooks.json").read_text(encoding="utf-8"))
    assert hooks["modules"] == ["./companion.js"]
    assert set(hooks["hooks"]) == {"SessionStart", "UserPromptSubmit", "PreToolUse", "PostToolUse"}


def test_the_plugin_validates_with_the_mod():
    done = subprocess.run([claude(), "plugin", "validate", str(PLUGIN)], capture_output=True, text=True, timeout=300)
    assert done.returncode == 0, done.stdout + done.stderr
    assert "companion.js hooks:" in done.stdout and "tool.call" in done.stdout


def test_the_mods_own_tests_pass():
    done = subprocess.run([claude(), "plugin", "test", "."], cwd=PLUGIN, capture_output=True, text=True, timeout=300)
    assert done.returncode == 0, done.stdout + done.stderr


def test_the_mod_holds_no_panel_wording():
    source = (PLUGIN / "hooks" / "companion.js").read_text(encoding="utf-8")
    for words in ("decided", "next:", "Still open", "Said yes", "captures behind"):
        assert words not in source, words


def test_the_mod_sends_nothing_back_to_claude():
    """The owner's ruling of October 24, 2026: the panels only show. No Button, no prompt submission, in any companion."""
    source = (PLUGIN / "hooks" / "companion.js").read_text(encoding="utf-8")
    for word in ("Button", "prompt.submit", "buttons"):
        assert word not in source, word
