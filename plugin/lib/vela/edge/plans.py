"""Finding plans on disk: the periphery for `planscope.py`, which decides from strings.

A plan is a folder holding `.vela.yaml`. One git repo may hold several, each in its own folder; a plan that is its
own repo is the one at the repo's root. Everything here reads the disk only (no git is run), so a hook can ask on
every tool call without a subprocess. The repo's root is the nearest folder above holding `.git` (a directory, or
the file a linked worktree has).

The walk down never enters a plan's own folder (a plan's `examples/` or a vendored copy is not another plan) or a
folder that is tooling, not content: dot-folders (`.git`, `.vela`, `.worktrees`), `node_modules`, virtualenvs.
"""
import os
import pathlib

CONFIG = ".vela.yaml"
STATE = ".vela"
SKIPPED = {"node_modules", "__pycache__", "venv", "site-packages"}


def is_plan(folder):
    return (pathlib.Path(folder) / CONFIG).is_file()


def is_vault(folder):
    """A plan, or a published copy of one (which has `.vela/` even where it was copied without `.vela.yaml`)."""
    folder = pathlib.Path(folder)
    return (folder / CONFIG).is_file() or (folder / STATE).is_dir()


def repo_root(start):
    """The nearest folder at or above `start` that holds `.git`, or None when `start` is in no repo."""
    start = pathlib.Path(start).resolve()
    for folder in [start, *start.parents]:
        if (folder / ".git").exists():
            return folder
    return None


def plan_above(start):
    """The plan folder that holds `start` (a folder, or a file's folder): the nearest at or above it holding a plan
    marker, stopping at the repo's root. With no repo above, the walk goes to the filesystem's root, as a published
    copy outside any repo needs. None when no plan is above."""
    start = pathlib.Path(start).resolve()
    top = repo_root(start)
    for folder in [start, *start.parents]:
        if is_vault(folder):
            return folder
        if top is not None and folder == top:
            return None
    return None


def plans_in(top):
    """Every plan folder under `top` (itself included), sorted by path. A plan's own folder is not searched."""
    top = pathlib.Path(top).resolve()
    found = []
    for folder, subfolders, _ in os.walk(top):
        if is_plan(folder):
            found.append(pathlib.Path(folder))
            subfolders[:] = []
            continue
        subfolders[:] = sorted(d for d in subfolders if not d.startswith(".") and d not in SKIPPED
                               and not os.path.islink(os.path.join(folder, d)))
    return found


def prefix_of(folder, top):
    """The folder's path inside the repo as git writes a prefix: `projects/heron/`, or "" for the root."""
    rel = pathlib.Path(folder).resolve().relative_to(pathlib.Path(top).resolve()).as_posix()
    return "" if rel == "." else rel + "/"
