"""`vela where --probe`, `.vela/host.json`, the stance it implies, and the SessionStart marker hook (plan 7.1-7.3).

Each probe runs the real launcher in a subprocess with a PATH we build, so "git is missing" and "gh hangs" are real
conditions, not mocks. HOME points into tmp_path so the outside-the-folder marker never touches the machine.
"""
import json
import os
import pathlib
import shutil
import subprocess
import sys
import time

import pytest

ROOT = pathlib.Path(__file__).resolve().parent.parent
PLUGIN = ROOT / "plugin"
LAUNCHER = PLUGIN / "scripts" / "vela"
sys.path.insert(0, str(PLUGIN / "lib"))

from vela.edge import hostprobe  # noqa: E402

HOST_FIELDS = ("git", "network", "gh", "python", "hooks", "injection", "skill_dir", "plugin_root", "checked")


def stub(bin_dir, name, body):
    path = bin_dir / name
    path.write_text("#!/bin/sh\n" + body + "\n", encoding="utf-8")
    path.chmod(0o755)


def signed_in_gh(bin_dir):
    stub(bin_dir, "gh", 'case "$1" in auth) echo "Logged in"; exit 0;; api) echo "heron-lead"; exit 0;; esac; exit 1')


def vault(tmp_path, git=True):
    folder = tmp_path / "vault"
    folder.mkdir()
    (folder / ".vela.yaml").write_text("initiative: INI-001\ntitle: Heron\n", encoding="utf-8")
    if git:
        subprocess.run(["git", "init", "-q", str(folder)], check=True)
    return folder


def path_with(tmp_path, *tools):
    """A bin folder holding the named real tools (symlinked) plus whatever stubs the test adds."""
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir(exist_ok=True)
    for tool in tools:
        found = shutil.which(tool)
        if found:
            (bin_dir / tool).symlink_to(found)
    return bin_dir


def probe(folder, bin_dir, *extra, home=None, env_extra=None):
    env = {"PATH": str(bin_dir), "HOME": str(home or folder.parent / "home"), "GIT_CONFIG_NOSYSTEM": "1"}
    env.update(env_extra or {})
    done = subprocess.run([sys.executable, str(LAUNCHER), "where", "--probe", "--vault", str(folder), *extra],
                          capture_output=True, text=True, env=env, timeout=60)
    return done


def probe_json(folder, bin_dir, *extra, **kw):
    done = probe(folder, bin_dir, "--json", *extra, **kw)
    assert done.returncode in (0, 1), done.stdout + done.stderr
    return done.returncode, json.loads(done.stdout)


def row(data, key):
    return next(r for r in data["rows"] if r["key"] == key)


def test_probe_reports_unsubstituted_plugin_root_as_no(tmp_path):
    folder = vault(tmp_path)
    bin_dir = path_with(tmp_path, "git")
    signed_in_gh(bin_dir)
    _, data = probe_json(folder, bin_dir, "--plugin-root", "${CLAUDE_PLUGIN_ROOT}", "--skill-dir", "")
    assert row(data, "plugin_root")["answer"] == "no"
    assert row(data, "skill_dir")["answer"] == "no"
    _, data = probe_json(folder, bin_dir, "--plugin-root", str(PLUGIN), "--skill-dir", str(PLUGIN / "skills" / "where"))
    assert row(data, "plugin_root")["answer"] == "yes"
    assert row(data, "skill_dir")["answer"] == "yes"


def test_probe_marks_git_missing_when_git_absent(tmp_path):
    folder = vault(tmp_path)
    bin_dir = path_with(tmp_path)  # no git on PATH
    signed_in_gh(bin_dir)
    code, data = probe_json(folder, bin_dir)
    assert code == 1
    assert row(data, "git")["answer"] == "no"
    assert "git" in row(data, "git")["meaning"]
    assert data["host"]["git"] == "no"
    assert "git" in data["missing"]


def test_probe_never_fails_silently_on_gh_timeout(tmp_path):
    folder = vault(tmp_path)
    bin_dir = path_with(tmp_path, "git")
    stub(bin_dir, "gh", "/bin/sleep 30")
    started = time.monotonic()
    code, data = probe_json(folder, bin_dir, "--timeout", "1")
    assert time.monotonic() - started < 20
    gh = row(data, "gh")
    assert gh["answer"] == "couldn't tell"
    assert "answer" in gh["meaning"] or "second" in gh["meaning"]
    assert code == 1 and "gh" in data["missing"]


def test_host_json_has_every_field(tmp_path):
    folder = vault(tmp_path)
    bin_dir = path_with(tmp_path, "git")
    signed_in_gh(bin_dir)
    probe_json(folder, bin_dir, "--injection", "no")
    host = json.loads((folder / ".vela" / "host.json").read_text(encoding="utf-8"))
    for field in HOST_FIELDS:
        assert field in host, field
    assert host["injection"] == "no"
    assert host["python"].startswith("3.")


def test_probe_lists_every_row_and_tells_the_lead_the_stance(tmp_path):
    folder = vault(tmp_path)
    bin_dir = path_with(tmp_path, "git")
    signed_in_gh(bin_dir)
    done = probe(folder, bin_dir)
    assert done.returncode in (0, 1), done.stderr
    assert len([line for line in done.stdout.splitlines() if ": yes:" in line or ": no:" in line
                or "couldn't tell" in line]) >= 10  # every row, for the model
    lead = probe(folder, bin_dir, "--for-lead").stdout.splitlines()
    assert lead and not any(": yes" in line for line in lead), lead  # the lead hears the stance, then what fails


def test_session_start_hook_writes_marker(tmp_path):
    folder = vault(tmp_path, git=False)
    payload = json.dumps({"session_id": "abc-123", "cwd": str(folder), "hook_event_name": "SessionStart",
                          "source": "startup"})
    done = subprocess.run([sys.executable, str(LAUNCHER), "hook", "session-start"], input=payload,
                          capture_output=True, text=True, timeout=30)
    assert done.returncode == 0
    assert done.stdout == ""  # SessionStart stdout is added to the model's context
    marker = json.loads((folder / ".vela" / "hooks-active").read_text(encoding="utf-8"))
    assert marker["session_id"] == "abc-123" and marker["at"]


def test_session_start_hook_exits_0_on_garbage_and_outside_a_vault(tmp_path):
    done = subprocess.run([sys.executable, str(LAUNCHER), "hook", "session-start"], input="not json",
                          capture_output=True, text=True, timeout=30, cwd=tmp_path)
    assert done.returncode == 0 and done.stdout == ""
    assert not (tmp_path / ".vela").exists()  # not a vault: the hook leaves the folder alone
    assert "hook" in done.stderr  # but it says why, for whoever runs claude --debug


def test_hooks_seen_only_when_both_markers_belong_to_this_session(tmp_path):
    folder = vault(tmp_path)
    bin_dir = path_with(tmp_path, "git")
    signed_in_gh(bin_dir)
    _, data = probe_json(folder, bin_dir, env_extra={"CLAUDECODE": "1"})
    assert row(data, "hooks")["answer"] == "no"
    (folder / ".vela").mkdir(exist_ok=True)
    (folder / ".vela" / "hooks-active").write_text(json.dumps({"session_id": "s1", "at": "2026-10-14T09:00:00Z"}))
    (folder / ".vela" / "hook-canary").write_text(json.dumps({"session_id": "s1", "tool_input": {"command": "x"}}))
    _, data = probe_json(folder, bin_dir)
    assert row(data, "hooks")["answer"] == "yes"
    (folder / ".vela" / "hooks-active").write_text(json.dumps({"session_id": "old", "at": "2026-10-13T09:00:00Z"}))
    _, data = probe_json(folder, bin_dir)
    assert row(data, "hooks")["answer"] == "no"


def test_canary_one_liner_stamps_only_the_probe(tmp_path):
    folder = vault(tmp_path, git=False)
    hooks = json.loads((PLUGIN / "hooks" / "hooks.json").read_text(encoding="utf-8"))
    command = hooks["hooks"]["PreToolUse"][0]["hooks"][0]["command"]
    env = {**os.environ, "CLAUDE_PROJECT_DIR": str(folder)}
    other = json.dumps({"session_id": "s1", "tool_input": {"command": "ls"}})
    assert subprocess.run(["sh", "-c", command], input=other, text=True, env=env).returncode == 0
    assert not (folder / ".vela" / "hook-canary").exists()
    mine = json.dumps({"session_id": "s1", "tool_input": {"command": "python3 x/vela where --probe --json"}})
    assert subprocess.run(["sh", "-c", command], input=mine, text=True, env=env).returncode == 0
    assert json.loads((folder / ".vela" / "hook-canary").read_text())["session_id"] == "s1"


def test_folder_persistence_needs_a_second_run_to_tell(tmp_path):
    folder = vault(tmp_path)
    bin_dir = path_with(tmp_path, "git")
    signed_in_gh(bin_dir)
    _, data = probe_json(folder, bin_dir, home=tmp_path / "home1")
    assert row(data, "folder")["answer"] == "couldn't tell"
    _, data = probe_json(folder, bin_dir, home=tmp_path / "home2")  # a fresh home: the outside marker is gone
    assert row(data, "folder")["answer"] == "yes"
    _, data = probe_json(folder, bin_dir, home=tmp_path / "home2")  # same home kept its marker too
    assert row(data, "folder")["answer"] == "no"


def everything(**changes):
    host = {"git": "yes", "network": "yes", "gh": "yes", "python": "3.13.1", "hooks": "no", "injection": "no",
            "skill_dir": "yes", "plugin_root": "no", "checked": "2026-10-14T09:00:00Z", "git_repo": True}
    host.update(changes)
    return host


def test_stance_everything_works():
    row_name, said = hostprobe.stance(everything())
    assert row_name == "everything"
    assert "close checks everything itself" in said


def test_stance_git_without_network_says_close_in_claude_code():
    for host in (everything(network="no"), everything(gh="couldn't tell")):
        row_name, said = hostprobe.stance(host)
        assert row_name == "no-send"
        assert "Claude Code" in said and "/vela:close" in said


def test_stance_git_present_but_not_running_is_reader_path():
    row_name, said = hostprobe.stance(everything(git="no", git_repo=True))
    assert row_name == "git-broken"
    assert "git doesn't run" in said and "draft" in said


def test_stance_no_git_or_old_python_is_reading_and_drafting():
    assert hostprobe.stance(everything(git="no", git_repo=False))[0] == "no-git"
    assert hostprobe.stance(everything(python="3.8.10"))[0] == "no-git"
    assert "proposal" in hostprobe.stance(everything(git="no", git_repo=False))[1]


def test_hooks_json_validates():
    hooks = json.loads((PLUGIN / "hooks" / "hooks.json").read_text(encoding="utf-8"))
    assert {"SessionStart", "PreToolUse"} <= set(hooks["hooks"])  # Task 24 adds PostToolUse (tests/test_hooks.py)
    start = hooks["hooks"]["SessionStart"][0]["hooks"][0]
    assert start["type"] == "command" and "hook session-start" in start["command"]
    assert "${CLAUDE_PLUGIN_ROOT}" in start["command"]
    assert hooks["hooks"]["PreToolUse"][0]["matcher"] == "Bash"
    if shutil.which("claude") is None:
        pytest.skip("the claude command is not installed here")
    result = subprocess.run(["claude", "plugin", "validate", str(PLUGIN)], capture_output=True, text=True, timeout=120)
    assert result.returncode == 0, result.stdout + result.stderr
