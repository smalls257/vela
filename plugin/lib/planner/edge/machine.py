"""The facts planner doctor reports: this Python, the YAML reader it loaded, and the programs on the PATH.

Periphery (Buffer): doctor.py decides what each fact means; this only looks. A program that is on the PATH but
will not answer `--version` within the timeout counts as not installed, with no guess at a version.
"""
import importlib.util
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
