"""The facts planner doctor reports: this Python, the YAML reader it loaded, and the programs on the PATH.

Periphery (Buffer): doctor.py decides what each fact means; this only looks. A program that is on the PATH but
will not answer `--version` within the timeout counts as not installed, with no guess at a version.
"""
import importlib.util
import json
import os
import pathlib
import shutil
import subprocess
import sys

import yaml

from planner import doctor
from planner.edge import mermaidjs

LIB = pathlib.Path(__file__).resolve().parents[2]  # plugin/lib, where the bundled yaml/ lives
VERSION_TIMEOUT = 10


def survey():
    yaml_path = pathlib.Path(yaml.__file__).resolve()
    return doctor.Machine(
        python=tuple(sys.version_info[:3]), python_path=sys.executable or "python3",
        yaml_version=yaml.__version__, yaml_bundled=yaml_path.parent == LIB / "yaml", yaml_path=str(yaml_path.parent),
        git=version_of(shutil.which("git")), node=version_of(node_path()), claude=shutil.which("claude"),
        voice_missing=tuple(pip for module, pip in (("sentence_transformers", "sentence-transformers"), ("torch", "torch"))
                            if importlib.util.find_spec(module) is None))


VENDORED = ".claude/skills/planner/scripts/planner"
RUNNING = LIB.parent / "scripts" / "planner"  # the launcher of the planner running doctor


def hook_facts(root, environ=None, home=None):
    """doctor.Hook for the vault at `root`, or None when it is not a vault in git."""
    environ = os.environ if environ is None else environ
    root = pathlib.Path(root)
    if not (root / ".planner.yaml").is_file() or git_config(root, "--git-dir") is None:
        return None
    hooks = git_config(root, "core.hooksPath") or ""
    on = bool(hooks) and (root / hooks).resolve() == (root / ".githooks").resolve()
    return doctor.Hook(hook_file=(root / ".githooks" / "pre-commit").is_file(), hooks_on=on,
                       env_planner=environ.get("PLANNER", ""), config_path=git_config(root, "planner.path") or "",
                       vendored=str(root / VENDORED), launcher=installed_launcher(environ, home))


def git_config(root, key):
    """`git config --get <key>` in the vault (`--git-dir` asks whether it is a repository at all), or None."""
    argv = ["git", "-C", str(root), "rev-parse", "--git-dir"] if key == "--git-dir" else ["git", "-C", str(root), "config", "--get", key]
    try:
        done = subprocess.run(argv, capture_output=True, text=True, timeout=VERSION_TIMEOUT)
    except (OSError, subprocess.TimeoutExpired):
        return None
    return done.stdout.strip() if done.returncode == 0 else None


def installed_launcher(environ=None, home=None):
    """The planner launcher Claude Code installed from a marketplace (its plugin registry,
    <config dir>/plugins/installed_plugins.json, entry planner@<marketplace>), else the launcher running doctor."""
    environ = os.environ if environ is None else environ
    config = pathlib.Path(environ.get("CLAUDE_CONFIG_DIR") or pathlib.Path(home or pathlib.Path.home()) / ".claude")
    try:
        registry = json.loads((config / "plugins" / "installed_plugins.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        registry = {}
    plugins = registry.get("plugins") if isinstance(registry, dict) else None
    for name, installs in sorted((plugins or {}).items()):
        if not name.startswith("planner@") or not isinstance(installs, list):
            continue
        for install in installs:
            path = pathlib.Path(str((install or {}).get("installPath", ""))) / "scripts" / "planner"
            if (install or {}).get("installPath") and path.is_file():
                return str(path)
    return str(RUNNING) if RUNNING.is_file() else ""


def node_path():
    """The node the diagram check would use, PLANNER_NODE included, or None."""
    try:
        return mermaidjs.find_node()
    except mermaidjs.Unavailable:
        return None


def version_of(program):
    """`program --version`'s first line, or None when there is no program or it does not answer.
    On a Mac without the developer tools, /usr/bin/git exists but only offers to install them; that is None."""
    if program is None:
        return None
    try:
        done = subprocess.run([program, "--version"], capture_output=True, text=True, timeout=VERSION_TIMEOUT)
    except (OSError, subprocess.TimeoutExpired):
        return None
    lines = done.stdout.strip().splitlines()
    return lines[0] if done.returncode == 0 and lines else None
