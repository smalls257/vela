"""Who may decide: an owner or a reader, judged by access and never by title. Pure: no disk, clock or network.

The Violation to prevent is authority that travels with the file. A published copy ships `.planner.yaml`, so
if that file could say `role: owner`, any reader could promote themselves. Access is the only grant: an owner
works in the vault's git work tree and can commit; a reader has a published copy with no `.git`. The config
can only give authority up (a git owner browsing safely), never take it.

edge/access.py gathers the Facts from the disk and git; this module only decides.
"""
from dataclasses import dataclass

OWNER, READER, NONE = "owner", "reader", "none"
NEITHER = "this folder is neither a vault repo nor a published copy"


@dataclass(frozen=True)
class Facts:
    in_work_tree: bool = False  # git says this directory is inside a work tree
    git_here: bool = False  # a .git sits in this very directory
    has_origin: bool = False
    can_commit: bool = False  # user.name and user.email resolve and .git is writable
    commit_problem: str = ""  # why not, when in_work_tree and not can_commit
    has_workspace: bool = False  # .planner/workspace.json exists
    git_error: str = ""  # git itself could not run: missing, timed out
    config_role: object = None  # .planner.yaml `role:` as written, or None
    config_error: str = ""  # .planner.yaml could not be read


@dataclass(frozen=True)
class Role:
    role: str  # owner, reader or none
    reason: str  # one plain sentence on why
    notes: tuple = ()  # true but not a problem: "nothing can be pushed"
    warnings: tuple = ()  # something the user should fix or know the tool ignored

    def as_dict(self):
        return {"role": self.role, "reason": self.reason, "notes": list(self.notes), "warnings": list(self.warnings)}


def _by_access(facts):
    """(role, reason, notes) from what the user can reach, before .planner.yaml has a say."""
    if facts.has_workspace and not facts.git_here:
        return READER, "this is a published copy: it has .planner/workspace.json and no .git", ()
    if facts.in_work_tree and facts.can_commit:
        notes = () if facts.has_origin else ("this vault has no remote called origin, so nothing can be pushed",)
        return OWNER, "you are working in the vault's git work tree and can commit", notes
    if facts.in_work_tree:
        return NONE, f"this is a git work tree but you cannot commit: {facts.commit_problem or 'git identity or .git access is missing'}", ()
    if facts.git_error:
        return NONE, f"{NEITHER}; git could not run ({facts.git_error})", ()
    return NONE, NEITHER, ()


def _config_warnings(facts):
    if facts.config_error:
        return (f".planner.yaml could not be read ({facts.config_error}), so its role setting was not applied",)
    if facts.config_role is None or facts.config_role == "reader":
        return ()
    if facts.config_role == "owner":
        return ("`role: owner` in .planner.yaml is ignored: the file ships in published copies, so access decides",)
    return (f"`role: {facts.config_role}` in .planner.yaml is not understood; only `role: reader` is honoured",)


def decide(facts):
    role, reason, notes = _by_access(facts)
    warnings = _config_warnings(facts)
    if role == OWNER and facts.config_role == "reader":
        return Role(READER, "you can commit here, but .planner.yaml says `role: reader`, which gives authority up", notes, warnings)
    return Role(role, reason, notes, warnings)
