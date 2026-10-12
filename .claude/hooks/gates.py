#!/usr/bin/env python3
"""Claude Code hooks for this repo. One file, four entry points, wired in .claude/settings.json:

  gates.py after-edit   PostToolUse on Edit|Write|MultiEdit: ruff + semgrep on the one file (about 1 s)
  gates.py guard-bash   PreToolUse on Bash: refuses commands that skip or disable the git hooks
  gates.py session-start SessionStart: warns when this clone has not set core.hooksPath to .githooks
  gates.py before-stop  Stop and SubagentStop: semgrep on every changed file, CONVENTIONS sync, and the
                        tests named after changed planner modules (about 3 to 20 s)
  gates.py scannable    for .githooks/pre-commit: filters NUL-separated paths to the ones the gates lint

The decisions (what a command bypasses, which tests a change needs) are pure functions over strings, so
tests/test_gates.py can drive them without git, a network or Claude Code. Only main() touches the process.

Exit codes follow https://code.claude.com/docs/en/hooks: 2 on PostToolUse shows stderr to Claude (the edit
already happened); a JSON {"decision": "block"} on Stop sends Claude back to work. A hook that cannot run
(semgrep missing, git broken) says so on stderr and exits 1: a non-blocking error the user sees, never a
silent pass.
"""
import json
import os
import pathlib
import re
import shlex
import shutil
import subprocess
import sys

SCANNED = (".py", ".js", ".html")
CONVENTIONS = ("plugin/vault/CONVENTIONS.md", "examples/unified-booking/CONVENTIONS.md",
               "tests/stub-conventions/CONVENTIONS.md")
ENV = {**os.environ, "SEMGREP_SEND_METRICS": "off", "SEMGREP_ENABLE_VERSION_CHECK": "0"}

# What a cooperative agent might type to get past a failing hook. Text matching is guidance, not a security
# boundary (https://code.claude.com/docs/en/permissions: a Bash rule "isn't a security boundary around the
# program"); `sh -c` or an alias defeats it. It exists so the agent gets a reason instead of a habit.
HOOKED = {"commit", "push", "merge", "rebase", "am", "cherry-pick"}


def _segments(command):
    """The command split into simple commands on ; & | and newlines, each a token list. Unparseable text
    (an open quote) is one whitespace-split segment, so a typo cannot hide a flag."""
    try:
        lexer = shlex.shlex(command, posix=True, punctuation_chars=";&|")
        lexer.whitespace_split = True
        tokens = list(lexer)
    except ValueError:
        tokens = command.split()
    segment = []
    for token in tokens + [";"]:
        if token and set(token) <= set(";&|"):
            if segment:
                yield segment
            segment = []
        else:
            segment.append(token)


def bypass_reason(command):
    """Why `command` gets around the gates, or None. Pure."""
    for tokens in _segments(command):
        words = [t for t in tokens if "=" not in t or t.startswith("-")]
        if tokens and tokens[0] in ("rm", "mv", "chmod") and any(".githooks" in t for t in tokens[1:]):
            return "removes or disables a git hook"
        if any(t.startswith("SEMGREP_RULES=") for t in tokens) or "--exclude-rule" in tokens:
            return "turns semgrep rules off"
        if "git" not in words:
            continue
        # The setting itself, or -c core.hooksPath=...; the same words inside a quoted commit message are not it.
        at = next((i for i, t in enumerate(tokens) if t == "core.hooksPath" or t.startswith("core.hooksPath=")), None)
        if at is not None:
            # Reading it, or pointing it at .githooks, turns the gates on; anything else turns them off.
            value = tokens[at + 1] if at + 1 < len(tokens) else ""
            if "--get" in tokens or (value == ".githooks" and "--unset" not in tokens):
                continue
            return "changes where git looks for hooks"
        sub = next((t for t in words[words.index("git") + 1:] if not t.startswith("-") and t in HOOKED), None)
        if sub is None:
            continue
        if "--no-verify" in tokens:
            return "skips the git hooks"
        # Only for commit is -n short for --no-verify; on push it is --dry-run and on merge --no-stat.
        if sub == "commit" and any(re.fullmatch(r"-[a-zA-Z]*n[a-zA-Z]*", t) for t in tokens):
            return "skips the git hooks"
    return None


def tests_for(changed):
    """The test files named after changed planner modules: plugin/lib/planner/releases.py -> tests/test_releases.py.
    A heuristic floor, not a coverage map; pre-push runs the suite. Pure."""
    out = []
    for path in changed:
        p = pathlib.PurePosixPath(path)
        if p.parent.as_posix() == "plugin/lib/planner" and p.suffix == ".py" and p.stem not in ("__init__", "cli"):
            out.append(f"tests/test_{p.stem}.py")
        elif p.parent.as_posix() == "tests" and p.name.startswith("test_") and p.suffix == ".py":
            out.append(p.as_posix())
    return sorted(set(out))


def semgrep_ignores(path, ignore_lines):
    """Whether a .semgrepignore line covers this repo-relative path. Pure. Semgrep honours the file only when it
    walks a directory; a file named on its command line is scanned regardless, so the hooks filter first.
    Covers the forms that file uses: `dir/`, `**/dir/`, and a glob over a path."""
    parts = pathlib.PurePosixPath(path).parts
    for line in ignore_lines:
        pattern = line.strip()
        if not pattern or pattern.startswith("#"):
            continue
        if pattern.endswith("/"):
            dirs = pattern.rstrip("/").split("/")
            anywhere = dirs[0] == "**"
            dirs = dirs[1:] if anywhere else dirs
            starts = range(len(parts) - len(dirs)) if anywhere else [0]
            if any(list(parts[i:i + len(dirs)]) == dirs for i in starts):
                return True
        elif pathlib.PurePosixPath(path).match(pattern) and pattern.count("/") == path.count("/"):
            return True
    return False


def stop_decision(problems, already_continuing):
    """The Stop hook's JSON, or None to let Claude stop. Pure. When Claude is already continuing because of
    this hook (stop_hook_active), block no further: say it to the user instead of looping."""
    if not problems:
        return None
    text = "Before finishing, fix these (or tell the user why not):\n" + "\n".join(f"- {p}" for p in problems)
    if already_continuing:
        return {"systemMessage": "Gate still failing at stop:\n" + "\n".join(problems)}
    return {"decision": "block", "reason": text}


# ---------------------------------------------------------------- the process side

def repo_root(cwd):
    # cwd from the hook input follows Claude into .claude/worktrees; CLAUDE_PROJECT_DIR does not.
    done = subprocess.run(["git", "-C", cwd, "rev-parse", "--show-toplevel"], capture_output=True, text=True, timeout=10)
    if done.returncode != 0:
        raise RuntimeError(f"not a git checkout: {cwd}")
    return pathlib.Path(done.stdout.strip())


def run(argv, root, timeout):
    """(exit code, stdout + stderr), unstripped: porcelain status lines start with a meaningful space."""
    done = subprocess.run(argv, cwd=root, capture_output=True, text=True, timeout=timeout, env=ENV)
    return done.returncode, done.stdout + done.stderr


def lint(root, files):
    """Findings for these repo-relative files as text lines; empty when clean."""
    for tool in ("ruff", "semgrep"):
        if not shutil.which(tool):
            raise RuntimeError(f"{tool} is not installed, so the gate cannot run")
    problems = []
    py = [f for f in files if f.endswith(".py") or f == "plugin/scripts/planner"]
    if py:
        code, out = run(["ruff", "check", "--no-cache", "--quiet", "--output-format", "concise",
                         "--select", "E9,F63,F7,F82,E722,S506", "--extend-exclude", ".semgrep", *py], root, 30)
        if code:
            problems += out.splitlines()
    code, out = run(["semgrep", "scan", "--config", ".semgrep", "--metrics=off", "--disable-version-check",
                     "--error", "--quiet", "--emacs", *files], root, 60)
    if code:
        problems += [line for line in out.splitlines() if line.strip()]
    return problems


def scannable(root, paths):
    """The paths the gates lint: code files, minus what .semgrepignore names (generated pages, vendored and
    minified code, the rules' own fixtures)."""
    ignore = (root / ".semgrepignore").read_text().splitlines()
    return [p for p in paths if (p.endswith(SCANNED) or p == "plugin/scripts/planner")
            and not semgrep_ignores(p, ignore) and (root / p).is_file()]


def changed_files(root):
    code, out = run(["git", "status", "--porcelain", "-z", "--untracked-files=all"], root, 10)
    if code:
        raise RuntimeError(f"git status failed: {out.strip()}")
    paths = []
    for entry in out.split("\0"):
        if len(entry) > 3 and entry[0] != "D" and entry[1] != "D":
            paths.append(entry[3:])
    return paths


def after_edit(event):
    root = repo_root(event.get("cwd") or ".")
    path = pathlib.Path(event.get("tool_input", {}).get("file_path", ""))
    # Find the root by identity, not spelling: on a case-insensitive disk git says ~/Code while Claude may say
    # ~/code, and a string prefix test then skips every edit as "outside this checkout".
    base = next((p for p in path.resolve().parents if p.exists() and os.path.samefile(p, root)), None)
    if base is None:
        return 0  # outside this checkout
    rel = path.resolve().relative_to(base).as_posix()
    if not scannable(root, [rel]):
        return 0
    problems = lint(root, [rel])
    if problems:
        print(f"{rel} breaks a repo rule (see .semgrep/):\n" + "\n".join(problems[:30]), file=sys.stderr)
        return 2
    return 0


def guard_bash(event):
    command = event.get("tool_input", {}).get("command", "")
    why = bypass_reason(command)
    if why is None:
        return 0
    print(json.dumps({"hookSpecificOutput": {
        "hookEventName": "PreToolUse",
        "permissionDecision": "deny",
        "permissionDecisionReason": f"This command {why}. The gates are how this repo stays on track: fix what "
                                    "the hook reported, or stop and ask the user to waive it."}}))
    return 0


def before_stop(event):
    root = repo_root(event.get("cwd") or ".")
    changed = changed_files(root)
    if not changed:
        return 0
    problems = []
    code_files = scannable(root, changed)
    if code_files:
        problems += lint(root, code_files)
    template = (root / "template/CONVENTIONS.md").read_bytes()
    problems += [f"{c} differs from template/CONVENTIONS.md" for c in CONVENTIONS if (root / c).read_bytes() != template]
    tests = [t for t in tests_for(changed) if (root / t).is_file()]
    if tests:
        code, out = run([sys.executable, "-m", "pytest", "-q", "-x", "-p", "no:cacheprovider", *tests], root, 120)
        if code:
            problems.append(f"pytest {' '.join(tests)} failed:\n" + "\n".join(out.splitlines()[-15:]))
    decision = stop_decision(problems, bool(event.get("stop_hook_active")))
    if decision:
        print(json.dumps(decision))
    return 0


def session_start(event):
    """core.hooksPath is per clone and cannot be committed. If this clone has not set it, the git hooks never
    run; say so at the start of the session (SessionStart stdout becomes context Claude reads)."""
    root = repo_root(event.get("cwd") or ".")
    code, out = run(["git", "config", "--get", "core.hooksPath"], root, 10)
    if out.strip() != ".githooks":
        print("This clone's git hooks are not active (core.hooksPath is not .githooks), so commits and pushes "
              "skip the gate. Tell the user to run: git config core.hooksPath .githooks")
    return 0


def print_scannable(paths_in):
    """For .githooks/pre-commit: NUL-separated repo-relative paths in, the ones the gates lint out, so the
    commit gate and these hooks share one reading of .semgrepignore."""
    root = repo_root(".")
    print("\0".join(scannable(root, [p for p in paths_in.split("\0") if p])), end="")
    return 0


def main(argv):
    hooks = {"after-edit": after_edit, "guard-bash": guard_bash, "before-stop": before_stop,
             "session-start": session_start}
    if argv[1:] == ["scannable"]:
        try:
            return print_scannable(sys.stdin.read())
        except (RuntimeError, OSError) as exc:
            print(f"gates.py scannable: could not filter the files: {exc}", file=sys.stderr)
            return 1
    if len(argv) != 2 or argv[1] not in hooks:
        print(f"usage: gates.py {{{','.join(hooks)}}}", file=sys.stderr)
        return 1
    try:
        return hooks[argv[1]](json.load(sys.stdin))
    except (RuntimeError, OSError, ValueError, subprocess.TimeoutExpired) as exc:
        print(f"gates.py {argv[1]}: could not run the gate: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
