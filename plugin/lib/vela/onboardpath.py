"""A newcomer's personal path: choices only. Pure validation and the file's text; the command does the disk.

The Violation this module exists to prevent is an invented fact reaching a newcomer: if the personal path could hold
a sentence, "nothing is made up" would depend on someone checking it afterward. So the file holds module ids from
`onboarding.MODULE_IDS`, their order, a depth and whether the person wants diagrams, and nothing else. Any other
key, and any text, is a problem. What each module says is built from the vault when the page is built, every time.

The file lives at `.vela/onboard/<handle>.json`: working state, never committed, never published (`.vela/` is
excluded from a published copy). A person is their handle (`vela whoami`).
"""
import json
import re
from dataclasses import dataclass

from vela import onboarding

FOLDER = ".vela/onboard"
HANDLE = re.compile(r"^[A-Za-z0-9](?:[A-Za-z0-9-]{0,38})$")  # a GitHub login's shape, so a handle can't name a path
DEPTHS = ("gist", "normal", "everything")
KEYS = {"audience", "modules", "depth", "diagrams", "broughtBack"}


@dataclass(frozen=True)
class Path:
    handle: str
    audience: str
    modules: tuple
    depth: str = "normal"
    diagrams: bool = False
    brought_back: tuple = ()  # specifics the lead hid that this person asked for; recorded, never silent


def file_for(handle):
    return f"{FOLDER}/{handle}.json"


def make(handle, audience, modules, depth="normal", diagrams=False, hidden=(), bring_back=()):
    """(Path or None, problems). `hidden` is what the lead hid for this audience now; a module in it is refused unless
    the person asked for it by name in `bring_back`, which is then recorded on the path."""
    problems = []
    if not HANDLE.match(str(handle)):
        problems.append(f"'{handle}' is not a handle: letters, digits and hyphens, up to 39.")
    if audience not in onboarding.AUDIENCES:
        problems.append(f"'{audience}' is not a role: use one of {', '.join(onboarding.AUDIENCES)}.")
    if depth not in DEPTHS:
        problems.append(f"'{depth}' is not a depth: use one of {', '.join(DEPTHS)}.")
    if not isinstance(diagrams, bool):
        problems.append("diagrams must be yes or no.")
    modules = list(modules)
    if not modules:
        problems.append("a path needs at least one module.")
    for module in modules:
        if module not in onboarding.MODULE_IDS:
            problems.append(f"'{module}' is not a module Vela builds from the plan; `vela onboard modules` lists them.")
    for module in sorted({m for m in modules if modules.count(m) > 1}):
        problems.append(f"'{module}' is listed twice.")
    asked = [m for m in modules if m in hidden]
    for module in asked:
        if module not in bring_back:
            problems.append(f"the lead hid '{module}' for this role; it can come back if you ask for it by name (--bring-back {module}).")
    for module in bring_back:
        if module not in modules:
            problems.append(f"--bring-back {module} names a module that is not on the path.")
    if problems:
        return None, problems
    return Path(handle, audience, tuple(modules), depth, diagrams, tuple(asked)), []


def to_text(path):
    data = {"audience": path.audience, "modules": list(path.modules), "depth": path.depth, "diagrams": path.diagrams,
            "broughtBack": list(path.brought_back)}
    return json.dumps(data, indent=2, sort_keys=True) + "\n"


def from_text(handle, text):
    """(Path or None, problems) for a file's text. Unknown keys are problems: the file holds choices and nothing else."""
    try:
        data = json.loads(text)
    except ValueError as exc:
        return None, [f"the file is not readable ({exc})"]
    if not isinstance(data, dict):
        return None, ["the file should hold one object of choices"]
    extra = sorted(set(data) - KEYS)
    if extra:
        return None, [f"the file holds '{extra[0]}', which is not a choice; it keeps module ids, depth and diagrams only"]
    back = tuple(data.get("broughtBack") or ())
    modules = data.get("modules")
    if not isinstance(modules, list):
        return None, ["the file's modules should be a list"]
    # what the lead hid is judged when the page is built; here the file is checked for shape and vocabulary only
    return make(handle, data.get("audience"), modules, data.get("depth", "normal"), data.get("diagrams", False),
                hidden=back, bring_back=back)


def as_data(path):
    """The path as the page carries it (D.onboard.mine)."""
    return {"handle": path.handle, "audience": path.audience, "modules": list(path.modules), "depth": path.depth,
            "diagrams": path.diagrams, "broughtBack": list(path.brought_back)}
