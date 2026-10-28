"""QG-NAME: a function, class or module named for a vague role.

The Violation this prevents is Leaky Narrative's cousin at the naming layer: `process_rows` or `PageManager` hides
which capability the unit has, and vague names are where a God Class's extra responsibilities go to hide. The fix
is always a rename into the domain's words, so the gate has no waiver.

`handle` and `Handler` are not banned: in vela a handle is a person's @handle and a Handler is a flow's event
handler, so the domain's own words win. Tool-named functions (`git_*`) are not banned either: git is vela's
domain, and the boundaries rules already keep tool calls out of the core.
"""
from __future__ import annotations

import ast
import pathlib
import re

from quality_report import Finding

VAGUE_VERBS = ("process", "manage", "do")
VAGUE_WHOLE = ("common", "helper", "helpers", "util", "utils", "misc", "stuff", "run_all")
VAGUE_CLASS_SUFFIX = ("Manager", "Helper", "Helpers", "Util", "Utils", "Misc", "Common")
# The standard library's BaseHTTPRequestHandler dispatches to do_GET, do_POST and so on by name.
HTTP_VERB_METHOD = re.compile(r"do_[A-Z]+")


def _is_vague_function(name: str) -> bool:
    if HTTP_VERB_METHOD.fullmatch(name):
        return False
    bare = name.lstrip("_")
    return bare in VAGUE_WHOLE or bare.split("_")[0] in VAGUE_VERBS


def _is_vague_class(name: str) -> bool:
    return name in VAGUE_WHOLE or name.endswith(VAGUE_CLASS_SUFFIX)


def _finding(path: str, line: int, name: str) -> Finding:
    return Finding(path, line, "QG-NAME",
                   f"{name}: a vague name hides which capability this is. Name what it does in the domain's words")


def vague_names(path: str, tree: ast.Module) -> list[Finding]:
    """One finding per vaguely named module, function or class in the tree."""
    found = []
    stem = pathlib.PurePosixPath(path).stem
    if stem in VAGUE_WHOLE:
        found.append(_finding(path, 1, stem))
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and _is_vague_function(node.name):
            found.append(_finding(path, node.lineno, node.name))
        elif isinstance(node, ast.ClassDef) and _is_vague_class(node.name):
            found.append(_finding(path, node.lineno, node.name))
    return sorted(found, key=lambda f: f.line)
