"""Where the planner program is, found the same way by every skill. Pure: callers pass the strings they were given
and a file test, so each case runs in a fake environment.

The Violation to prevent is a Distributed Monolith in miniature: every vault carrying its own vendored copy of the
plugin means two versions answer one vault. A skill must run the INSTALLED planner when there is one. But the
variables that say where it is are expanded by the host, and whether Cowork expands them is unverified, so a
literal `${CLAUDE_PLUGIN_ROOT}` must be recognised as "not expanded" and skipped, not run as a path.

Order (design session 15, "Plugin path"): the plugin root, the skill's own directory, the vendored copy in the
vault, and last the path a reader workspace recorded when it was opened.
"""
import posixpath
from dataclasses import dataclass

PROGRAM = "scripts/planner"
VENDORED = ".claude/skills/planner/scripts/planner"
NOT_FOUND = "I cannot find the planner program. Run `/planner:where` and send me what it prints."


@dataclass(frozen=True)
class Candidate:
    source: str  # which rule in the order produced it
    path: str  # the program path this rule points at, "" when the rule gave none
    skipped: str  # why it was not usable ("" when it was tried and exists)

    @property
    def usable(self):
        return bool(self.path) and not self.skipped


def expanded(value):
    """True when the host replaced the variable: something is there and no `${` is left in it."""
    return bool(value and value.strip()) and "${" not in value


def _from_variable(source, value, suffix):
    if not value or not value.strip():
        return Candidate(source, "", "is empty")
    if not expanded(value):
        return Candidate(source, "", f"is the literal text {value!r}: the host did not expand it")
    return Candidate(source, posixpath.join(value.rstrip("/"), suffix), "")


def candidates(plugin_root, skill_dir, vault, workspace_path):
    """Every rule in order with its path or the reason it gave none. Existence is checked by `resolve`."""
    return [
        _from_variable("${CLAUDE_PLUGIN_ROOT}", plugin_root, PROGRAM),
        _from_variable("${CLAUDE_SKILL_DIR}", skill_dir, "../../" + PROGRAM),
        Candidate("the vendored copy in the vault", posixpath.join(vault.rstrip("/") or ".", VENDORED), ""),
        Candidate("planner_path in .planner/workspace.json", workspace_path, "" if workspace_path else "is not recorded"),
    ]


def resolve(plugin_root, skill_dir, vault, workspace_path, is_file):
    """(chosen Candidate or None, every Candidate with its skip reason filled in). `is_file(path)` is the disk test."""
    tried = []
    chosen = None
    for found in candidates(plugin_root, skill_dir, vault, workspace_path):
        if found.usable and not is_file(found.path):
            found = Candidate(found.source, found.path, "does not exist")
        tried.append(found)
        if chosen is None and found.usable:
            chosen = found
    return chosen, tried
