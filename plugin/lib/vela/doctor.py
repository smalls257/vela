"""vela doctor: what this machine has for vela, one plain line per item, and whether it is enough.

A missing optional piece is said here, once, with what it adds and the one command that gets it. Without this a
colleague meets it later as a feature that quietly does less (the diagram check skipped, Ask offering a prompt to
copy) and has to guess why. Pure: edge/machine.py gathers the facts and cli.py prints the lines.
"""
from dataclasses import dataclass
from typing import Optional, Tuple

from vela import voicescore

# The oldest Python vela runs on: what a Mac's /usr/bin/python3 ships. scripts/vela checks it before any import.
FLOOR = (3, 9)
PINNED_YAML = "6.0.3"  # lib/yaml/__init__.py says the same; tests hold the two together


@dataclass(frozen=True)
class Machine:
    """What edge/machine.py found. A program's version is None when it is not installed or would not run."""
    python: Tuple[int, int, int]
    python_path: str
    yaml_version: str
    yaml_bundled: bool  # imported from the plugin's lib/yaml, not a copy installed on the machine
    yaml_path: str
    git: Optional[str]
    node: Optional[str]
    claude: Optional[str]
    voice_missing: Tuple[str, ...]  # pip names of the voice-scoring packages this Python cannot import


@dataclass(frozen=True)
class Vault:
    """The folder doctor ran in. `problem` says why it is not a usable vault; empty when it is one."""
    root: str
    initiative: str = ""
    title: str = ""
    problem: str = ""


@dataclass(frozen=True)
class Line:
    status: str  # "ok", "missing" (vela cannot run without it), "optional" (vela runs; one feature does not), "info"
    text: str


@dataclass(frozen=True)
class Hook:
    """What edge/machine.py found about the vault's pre-commit hook (template/.githooks/pre-commit)."""
    hook_file: bool  # .githooks/pre-commit is in the vault
    hooks_on: bool  # core.hooksPath points git at .githooks
    env_vela: str  # VELA in doctor's environment ("" when unset); the hook reads it first
    config_path: str  # git config vela.path ("" when unset); the hook reads it second
    vendored: str  # the vendored launcher's path in the vault; the hook reads it last
    launcher: str  # the installed vela launcher doctor found ("" when none)


# The hook's own order (template/.githooks/pre-commit), kept here so doctor says what the hook will do; a test runs the
# hook against each case and holds the two together.
HOOK_ORDER = ("VELA", "git config vela.path", "the vendored copy in the vault")


def hook_finds(hook, is_file):
    """(source, path) of the launcher the pre-commit hook will run, or ("", "") when it finds none and stops the commit."""
    for source, path in zip(HOOK_ORDER, (hook.env_vela, hook.config_path, hook.vendored)):
        if path:
            return (source, path) if is_file(path) else (source, "")  # the hook takes the first one set, and stops if it is not there
    return "", ""


def wire_command(hook, found):
    """The one command that wires the hook to the installed launcher: turns the vault's hooks on when they are off, and
    records the launcher when the hook would not find it."""
    steps = [] if hook.hooks_on else ["git config core.hooksPath .githooks"]
    if found != hook.launcher:
        steps.append(f"git config vela.path {shell_quote(hook.launcher)}")
    return " && ".join(steps)


def shell_quote(path):
    return path if path and all(c.isalnum() or c in "/._-~@+" for c in path) else "'" + path.replace("'", "'\\''") + "'"


def hook_line(hook, is_file):
    """Whether a commit typed by hand in this vault is checked by vela it was installed with. The hook stops a
    commit when it cannot find vela (it never waves one through), so a hook that finds nothing is a vault where
    every hand commit stops; doctor names the one command that fixes it."""
    if hook is None:
        return None
    if not hook.hook_file:
        return Line("info", "this vault has no .githooks/pre-commit, so a commit typed by hand isn't checked for files "
                            "that must stay on this machine. Copy .githooks/ from vela's template folder.")
    source, found = hook_finds(hook, is_file)
    fix = f" Wire it: {wire_command(hook, found)}" if hook.launcher else " Install the plugin, then run vela doctor again."
    if not hook.hooks_on:
        return Line("optional", "the vault's pre-commit hook is off, so a commit typed by hand isn't checked." + fix)
    if not found:
        return Line("optional", f"the vault's pre-commit hook stops every commit typed by hand: {source} names a "
                                f"launcher that isn't there.{fix}")
    if hook.launcher and found != hook.launcher:
        return Line("optional", f"the vault's pre-commit hook runs vela at {found} (from {source}), not the "
                                f"installed one at {hook.launcher}, so two versions answer this vault.{fix}")
    return Line("ok", f"the vault's pre-commit hook checks hand commits with vela at {found}")


def report(machine, vault, plugin_version, hook=None, is_file=None):
    """One Line per item, required ones first."""
    lines = [python_line(machine), yaml_line(machine), git_line(machine), node_line(machine), claude_line(machine),
             voice_line(machine), vault_line(vault)]
    found = hook_line(hook, is_file or (lambda _: False)) if hook is not None else None
    return lines + ([found] if found else []) + [Line("info", f"vela plugin {plugin_version}")]


def python_line(machine):
    shown = ".".join(str(n) for n in machine.python)
    if machine.python[:2] < FLOOR:
        return Line("missing", f"Python {shown} at {machine.python_path} is too old; vela needs "
                               f"{FLOOR[0]}.{FLOOR[1]} or later. On a Mac: brew install python@3.12")
    return Line("ok", f"Python {shown} ({machine.python_path})")


def yaml_line(machine):
    if not machine.yaml_bundled:
        return Line("missing", f"PyYAML {machine.yaml_version} was loaded from {machine.yaml_path}, not the copy bundled "
                               "with the plugin, so pages may read differently here. Reinstall the plugin.")
    if machine.yaml_version != PINNED_YAML:
        return Line("missing", f"the bundled PyYAML is {machine.yaml_version}, not {PINNED_YAML}. Reinstall the plugin.")
    return Line("ok", f"PyYAML {machine.yaml_version}, bundled with the plugin (nothing to install)")


def git_line(machine):
    if machine.git is None:
        return Line("missing", "git is not installed, or did not answer git --version. Owners keep the vault in git. "
                               "On a Mac: xcode-select --install")
    return Line("ok", machine.git)


def node_line(machine):
    if machine.node is None:
        return Line("optional", "node is not installed, or did not answer node --version. With it, vela check "
                                "parses every diagram the way the explorer draws it. Get it: brew install node")
    return Line("ok", f"node {machine.node}: vela check parses the diagrams")


def claude_line(machine):
    if machine.claude is None:
        return Line("optional", "the claude command is not on the PATH. With it, the explorer's Ask Claude "
                                "box answers in the page. Get it: curl -fsSL https://claude.ai/install.sh | bash")
    return Line("ok", f"claude command found ({machine.claude}): the explorer's Ask Claude box works")


def voice_line(machine):
    if machine.voice_missing:
        # This Python's own pip: on a Mac, `python3` on the PATH is often not the interpreter running vela.
        return Line("optional", f"voice scoring needs {' and '.join(machine.voice_missing)}. With it, vela voicescore "
                                f"says how close a draft is to your own writing. Get it: {machine.python_path} -m pip "
                                f"install sentence-transformers ({voicescore.DEPENDENCY_SIZE})")
    return Line("ok", "sentence-transformers and torch: vela voicescore works")


def vault_line(vault):
    if vault.problem:
        return Line("info", f"{vault.root} is not a vault: {vault.problem} Run doctor from the vault to check it too.")
    return Line("info", f"{vault.root} is a vault: {vault.initiative} {vault.title}")


def exit_code(lines):
    """0 when everything vela needs is there; optional pieces never fail it."""
    return 1 if any(line.status == "missing" for line in lines) else 0


def render(lines):
    width = max(len(line.status) for line in lines)
    body = [f"{line.status.ljust(width)}  {line.text}" for line in lines]
    if exit_code(lines):
        body.append("vela doctor: something vela needs is missing; the line marked missing says how to get it.")
    else:
        body.append("vela doctor: ready.")
    return "\n".join(body)
