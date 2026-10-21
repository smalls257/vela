"""The plugin's Claude Code hooks (overhaul plan Task 24): what `vela hook bash|edit|post-edit` decide.

Every hook here is earlier feedback, never the gate (plan section 1, Silent Fallback row): `close stage` is the only
thing that stages, `decide` the only thing that moves a state, render refuses a hand-edited block, and `close push`
refuses without a consent capture. So these tests check the verdicts and the protocol (stdin JSON in, exit 0 always,
`permissionDecision` out), and that the bash hook judges paths by `guard.py` rather than a rule of its own.
"""
import json
import os
import pathlib
import shutil
import subprocess
import sys

import pytest

from conftest import REPO

PLUGIN = REPO / "plugin"
LAUNCHER = PLUGIN / "scripts" / "vela"
HOOKS = json.loads((PLUGIN / "hooks" / "hooks.json").read_text(encoding="utf-8"))

PAGE = """---
id: CON-limits
type: constraints
title: Limits
state: draft
---

# Limits

## Items

### CON-001 One team figure

- **State:** assumption
- **Statement:** One figure per team.

## Summary

<!-- generated:summary sha=0123abcd: do not edit, run vela render -->
| Item | State |
|---|---|
| One team figure | assumption |
<!-- /generated:summary -->

Some prose the lead wrote.
"""


def vault(tmp_path):
    folder = tmp_path / "vault"
    folder.mkdir()
    (folder / ".vela.yaml").write_text("initiative: INI-001\ntitle: Heron\n", encoding="utf-8")
    (folder / "02-constraints.md").write_text(PAGE, encoding="utf-8")
    return folder


def hook(which, payload, cwd=None):
    done = subprocess.run([sys.executable, str(LAUNCHER), "hook", which], input=json.dumps(payload),
                          capture_output=True, text=True, timeout=30, cwd=cwd)
    assert done.returncode == 0, done.stderr  # the hook protocol: a hook never fails the tool call by its exit code
    return json.loads(done.stdout) if done.stdout.strip() else {}


def decision(out):
    return out.get("hookSpecificOutput", {}).get("permissionDecision")


def reason(out):
    return out.get("hookSpecificOutput", {}).get("permissionDecisionReason", "")


def bash(folder, command):
    return hook("bash", {"hook_event_name": "PreToolUse", "tool_name": "Bash", "cwd": str(folder),
                         "tool_input": {"command": command}})


def edit(folder, tool_input, tool="Edit"):
    return hook("edit", {"hook_event_name": "PreToolUse", "tool_name": tool, "cwd": str(folder),
                         "tool_input": tool_input})


# --- first callers


@pytest.mark.parametrize("command", [
    "git add 02-constraints.md",
    "git add -A",
    "git add .",
    "git -C /some/where add -- 02-constraints.md",
    "git --no-pager -c core.quotepath=off add -u",
    "/usr/bin/git stage 02-constraints.md",
    "cd sub && git add x.md && git commit -m 'x'",
    "git commit -am 'Edit the limits'",
    "git commit -a -m x",
    "git commit --all -m x",
    "git commit -m x -- 02-constraints.md",
    "git commit -m x 02-constraints.md",
    "FOO=1 git add x",
    "env GIT_DIR=.git git add x",
    "bash -c 'git add x'",
    "sh -lc \"git add x\"",
    "echo $(git add x)",
    "echo \"`git add x`\"",
    "if true; then git add x; fi",
    "ls | xargs git add",
    "cat <<EOF\nhello\nEOF\ngit add x",  # the here-document ends, and the next line is a command again
    "eval 'git add x'",
    "git update-index --add x",
    "git commit -qam x",
])
def test_hook_bash_denies_any_git_add_with_reason(tmp_path, command):
    out = bash(vault(tmp_path), command)
    assert decision(out) == "deny", command
    said = reason(out)
    assert "vela close stage" in said and "vela close finish" in said  # the way that does work, in plain words


@pytest.mark.parametrize("command", [
    "python3 /plugins/vela/scripts/vela close stage --checkpoint",
    "vela() { python3 /p/scripts/vela \"$@\"; }; vela close finish --summary 'git add the pages'",
    "python3 /p/scripts/vela record add --origin @lead \"we should git add it later\"",
    "git status --short",
    "git commit -m 'git add nothing'",
    "git log --oneline -3",
    "python3 - <<'EOF'\nprint('git add x')\nEOF",
    "echo 'git add x'",
    "grep -rn 'git add' plugin/skills",
    "git rm -r --cached --quiet -- .inbox/call.md",  # guard staged's own remedy takes a file out of the index
    "git commit --amend -m x",
    "git commit -m x 2>&1 | tail -1",
])
def test_hook_allows_the_vela_cli(tmp_path, command):
    out = bash(vault(tmp_path), command)
    assert decision(out) is None, (command, out)


def test_hook_edit_of_state_line_denied(tmp_path):
    folder = vault(tmp_path)
    page = str(folder / "02-constraints.md")
    bullet = edit(folder, {"file_path": page, "old_string": "- **State:** assumption",
                           "new_string": "- **State:** decided"})
    assert decision(bullet) == "deny" and "vela decide" in reason(bullet)
    front = edit(folder, {"file_path": page, "content": PAGE.replace("state: draft", "state: decided")}, tool="Write")
    assert decision(front) == "deny" and "vela decide" in reason(front)
    many = edit(folder, {"file_path": page, "edits": [{"old_string": "One figure per team.", "new_string": "One."},
                                                      {"old_string": "state: draft", "new_string": "state: decided"}]},
                tool="MultiEdit")
    assert decision(many) == "deny"
    # prose and a new item's state are not a state change
    prose = edit(folder, {"file_path": page, "old_string": "Some prose the lead wrote.", "new_string": "Other prose."})
    assert decision(prose) is None
    added = edit(folder, {"file_path": page, "old_string": "## Summary",
                          "new_string": "### CON-002 Two\n\n- **State:** assumption\n\n## Summary"})
    assert decision(added) is None


def test_hook_push_asks(tmp_path):
    folder = vault(tmp_path)
    for command in ("git push origin session/x", "git push", "gh pr create --title x --body y",
                    "gh pr comment 12 --body hi", "cd . && git -C . push -u origin HEAD"):
        out = bash(folder, command)
        assert decision(out) == "ask", command
        assert reason(out)
    assert decision(bash(folder, "gh pr view 12")) is None


def test_hook_edit_inside_generated_denied(tmp_path):
    folder = vault(tmp_path)
    page = str(folder / "02-constraints.md")
    inside = edit(folder, {"file_path": page, "old_string": "| One team figure | assumption |",
                           "new_string": "| One team figure | decided |"})
    assert decision(inside) == "deny" and "vela render" in reason(inside)
    whole = edit(folder, {"file_path": page, "content": PAGE.replace("| One team figure | assumption |", "| x | y |")},
                 tool="Write")
    assert decision(whole) == "deny"


def test_hook_logic_is_guard_logic(tmp_path):
    """The bash hook names the files a commit may never carry by `guard.py`'s own rules: the same verdict, path for
    path, as `vela guard path`, so the hook holds no path rule of its own (Distributed Monolith ruled out)."""
    folder = vault(tmp_path)
    paths = [".inbox/call.md", "voice/local/x.md", "voice/corpus/a.md", ".vela/session.json",
             ".vela/explorer-pins.json", "02-constraints.md", ".Inbox/Notes.md", "sub/.inbox/y.md"]
    out = bash(folder, "git add -- " + " ".join(paths))
    hook_forbids = set(out["vela"]["forbidden"])
    guard_forbids = set()
    for path in paths:
        done = subprocess.run([sys.executable, str(LAUNCHER), "guard", "path", path, "--vault", str(folder)],
                              capture_output=True, text=True, timeout=30)
        if done.returncode == 1:
            guard_forbids.add(path)
    assert hook_forbids == guard_forbids and guard_forbids
    assert "meeting notes in the inbox" in reason(out)  # guard's own plain words reach the model


def test_hooks_json_validates():
    hooks = HOOKS["hooks"]
    assert "Stop" not in hooks  # plan 9.3 Q10: no blocking Stop hook
    commands = {h["command"] for entries in hooks.values() for entry in entries for h in entry["hooks"]}
    for which in ("hook bash", "hook edit", "hook post-edit", "hook session-start"):
        assert any(which in c and "sh \"${CLAUDE_PLUGIN_ROOT}/scripts/run-vela\"" in c for c in commands), which
    pre = {entry["matcher"]: entry for entry in hooks["PreToolUse"] if "hook " in entry["hooks"][0]["command"]}
    assert "Bash" in pre and all(tool in pre["Edit|Write|MultiEdit"]["matcher"] for tool in ("Edit", "Write"))
    assert hooks["PostToolUse"][0]["matcher"] == "Edit|Write|MultiEdit"
    if shutil.which("claude") is None:
        pytest.skip("the claude command is not installed here")
    result = subprocess.run(["claude", "plugin", "validate", str(PLUGIN)], capture_output=True, text=True, timeout=120)
    assert result.returncode == 0, result.stdout + result.stderr


def test_session_start_marker_kept(tmp_path):
    """Task 7's marker and canary stay: the host probe tells hooks that ran from hooks that didn't by them."""
    start = HOOKS["hooks"]["SessionStart"][0]["hooks"][0]["command"]
    assert "hook session-start" in start
    canary = HOOKS["hooks"]["PreToolUse"][0]
    assert canary["matcher"] == "Bash" and "hook-canary" in canary["hooks"][0]["command"]
    folder = vault(tmp_path)
    assert hook("session-start", {"session_id": "s1", "cwd": str(folder)}) == {}
    assert json.loads((folder / ".vela" / "hooks-active").read_text(encoding="utf-8"))["session_id"] == "s1"


# --- the rest of the protocol


def test_outside_a_vault_every_hook_stays_out_of_the_way(tmp_path):
    """A plugin enabled for a whole account must not deny `git add` in the user's other repositories."""
    other = tmp_path / "elsewhere"
    other.mkdir()
    assert bash(other, "git add -A") == {}
    assert bash(other, "git push") == {}
    (other / "notes.md").write_text("state: draft\n", encoding="utf-8")
    assert edit(other, {"file_path": str(other / "notes.md"), "old_string": "draft", "new_string": "done"}) == {}


def test_garbage_in_is_no_opinion_and_says_why(tmp_path):
    done = subprocess.run([sys.executable, str(LAUNCHER), "hook", "bash"], input="not json", capture_output=True,
                          text=True, timeout=30, cwd=tmp_path)
    assert done.returncode == 0 and done.stdout == "" and "hook bash" in done.stderr


def test_post_edit_reports_a_broken_page_to_the_model(tmp_path):
    folder = vault(tmp_path)
    page = folder / "02-constraints.md"
    page.write_text(PAGE.replace("<!-- /generated:summary -->", ""), encoding="utf-8")
    out = hook("post-edit", {"hook_event_name": "PostToolUse", "tool_name": "Edit", "cwd": str(folder),
                             "tool_input": {"file_path": str(page)}})
    context = out["hookSpecificOutput"]["additionalContext"]
    assert out["hookSpecificOutput"]["hookEventName"] == "PostToolUse"
    assert "Limits" in context and "E4" in context
    page.write_text(PAGE, encoding="utf-8")
    assert hook("post-edit", {"hook_event_name": "PostToolUse", "tool_name": "Edit", "cwd": str(folder),
                              "tool_input": {"file_path": str(page)}}) == {}
