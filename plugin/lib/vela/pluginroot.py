"""Where the vela program is, found the same way by every skill. Pure: callers pass the strings they were given
and a file test, so each case runs in a fake environment.

The Violation to prevent is a Distributed Monolith in miniature: every vault carrying its own vendored copy of the
plugin means two versions answer one vault. A skill must run the INSTALLED vela when there is one. But the
variables that say where it is are expanded by the host, and whether Cowork expands them is unverified, so a
literal `${CLAUDE_PLUGIN_ROOT}` must be recognized as "not expanded" and skipped, not run as a path.

Order (design session 15, "Plugin path", revised 2026-10-14 by the CLI/skill overhaul, Task 1, and again after the
Cowork probe): the skill's own directory, the plugin root, an installed copy in the documented plugin folders, the
vendored copy in the vault, and last the path a reader workspace recorded when it was opened. Cowork's run showed
both variables empty and the skill loaded from /mnt/skills with nothing beside it, while the plugin itself sat in
~/.claude/plugins/synced/<id>/vela/, the folder the Claude Code docs name for plugins synced from claude.ai; a
marketplace install sits in ~/.claude/plugins/cache/<marketplace>/vela/<version>/. The caller finds those copies
(INSTALLED_GLOBS, newest first) and passes them in, so this module stays pure. `/vela:where` lists the same order;
START.md keeps one line pointing there (the six-step ladder it once held cost every session ~250 words).

Why skills call `sh <plugin root>/scripts/run-vela` and not a shell variable holding the command: `P="sh .../run-vela";
$P check` exits 127 in zsh, which doesn't split `$P` into words (44 retries in two runs, diagnosis 6C), and shell state may
not carry from one command to the next. `run-vela` picks whichever of `python3`, `python` or `py` the machine has.
"""
import posixpath
from dataclasses import dataclass

PROGRAM = "scripts/vela"
VENDORED = ".claude/skills/vela/scripts/vela"
# Under the plugins root (CLAUDE_CODE_PLUGIN_CACHE_DIR, else ~/.claude/plugins): synced from claude.ai (Cowork), then
# installed from a marketplace. The plugin name is the folder name.
INSTALLED_GLOBS = ("synced/*/vela/" + PROGRAM, "cache/*/vela/*/" + PROGRAM)
NOT_FOUND = "I cannot find the vela program. Run `/vela:where` and send me what it prints."


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


def _installed(paths):
    if not paths:
        return Candidate("an installed copy under the plugins folder", "", "none found")
    note = f" (newest of {len(paths)})" if len(paths) > 1 else ""
    return Candidate("an installed copy under the plugins folder" + note, paths[0], "")


def candidates(plugin_root, skill_dir, vault, workspace_path, installed=()):
    """Every rule in order with its path or the reason it gave none. Existence is checked by `resolve`.
    `installed` is the INSTALLED_GLOBS matches, newest first."""
    return [
        _from_variable("${CLAUDE_SKILL_DIR}", skill_dir, "../../" + PROGRAM),
        _from_variable("${CLAUDE_PLUGIN_ROOT}", plugin_root, PROGRAM),
        _installed(list(installed)),
        Candidate("the vendored copy in the vault", posixpath.join(vault.rstrip("/") or ".", VENDORED), ""),
        Candidate("vela_path in .vela/workspace.json", workspace_path, "" if workspace_path else "is not recorded"),
    ]


def resolve(plugin_root, skill_dir, vault, workspace_path, is_file, installed=()):
    """(chosen Candidate or None, every Candidate with its skip reason filled in). `is_file(path)` is the disk test."""
    tried = []
    chosen = None
    for found in candidates(plugin_root, skill_dir, vault, workspace_path, installed):
        if found.usable and not is_file(found.path):
            found = Candidate(found.source, found.path, "does not exist")
        tried.append(found)
        if chosen is None and found.usable:
            chosen = found
    return chosen, tried
