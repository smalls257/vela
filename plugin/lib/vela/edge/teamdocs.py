"""What the team has written in a vault's docs/ folder, and the next team-side step it implies. Reads local files only.

    team_step(root, name) -> "the <app> team: ... (/vela:breakdown)." or "... (/vela:tickets)." or None

The Violation this exists to prevent is a Black Box in the handover: a senior finishes a design or a build plan and
nothing in `vela next` says the next skill exists, so the plan waits for someone to remember it. The team sessions
leave their work in docs/tech-design/, docs/plan/ and docs/work/, so those folders are the only sensor needed.
"""
import pathlib

from vela import breakdown

DONE = ("complete", "complete-with-gaps")
TICKET_FILES = ("tickets.csv", "tickets.md")


def meta_of(path):
    """The frontmatter of one doc, or {} when it has none or cannot be read: a doc we cannot read is not a step."""
    try:
        meta, _, _ = breakdown.split_frontmatter(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError):
        return {}
    return meta if isinstance(meta, dict) else {}


def app_of(meta):
    vault_block = meta.get("vault")
    return str(vault_block.get("app", "")) if isinstance(vault_block, dict) else ""


def named_in_prereqs(meta, design_name):
    raw = meta.get("prereqs")
    entries = raw if isinstance(raw, list) else [raw]
    paths = [e.get("path") if isinstance(e, dict) else e for e in entries]
    return any(isinstance(p, str) and pathlib.PurePosixPath(p).name == design_name for p in paths)


# A design or plan status as a reader says it; the raw values are frontmatter.
STATUS_WORDS = {"complete": "finished", "complete-with-gaps": "finished apart from known gaps"}


def team_step(root, name=lambda app: app):
    """The first team-side step waiting in `root`, or None. A tickets step comes before a breakdown step. `name` turns
    an app ID into what a reader calls the app."""
    root = pathlib.Path(root)
    designs = {}
    for path in sorted((root / "docs" / "tech-design").glob("*.md")):
        meta = meta_of(path)
        if app_of(meta) and meta.get("status") in DONE:
            designs[path.name] = (app_of(meta), str(meta.get("slug", path.stem)), meta["status"])
    plans = {path.name: meta_of(path) for path in sorted((root / "docs" / "plan").glob("*-breakdown.md"))}
    ticketed = any((root / "docs" / "work" / name).is_file() for name in TICKET_FILES)
    steps = []
    for design_name, (app, slug, status) in designs.items():
        mine = [meta for meta in plans.values() if named_in_prereqs(meta, design_name)]
        if not mine:
            steps.append((1, app, f"the {name(app)} team: their design is {STATUS_WORDS.get(status, status)} and there's no build plan yet, "
                                  f"so break the work into stories and tasks (/vela:breakdown)."))
        elif not ticketed and any(meta.get("status") in DONE for meta in mine):
            steps.append((0, app, f"the {name(app)} team: their build plan is {STATUS_WORDS.get(mine[0].get('status'), mine[0].get('status'))} "
                                  f"and no tickets have been made from it yet, so write them (/vela:tickets)."))
    return min(steps)[2] if steps else None
