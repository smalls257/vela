"""Which plan a path or a branch belongs to when several plans share one git repository.

The Violation this module exists to prevent is a Distributed Monolith: two plans in one repo whose correctness
depends on shared mutable state, here the repo's index, its status and one flat namespace of `session/<id>`
branches. A plan's commands must look at the plan's own folder, and its branches must carry its name, so one
plan's session can be swapped, resumed or deleted without the other noticing.

A plan that is its own repo has an empty scope and every name below comes out exactly as it did before there
was a scope. Pure: prefixes and paths arrive as strings from `edge/`, which asks git and the disk.
"""
import re

ROOT = ""


def slug_of(prefix):
    """The plan's short name from its folder inside the repo: `projects/heron/` -> `heron`. "" for a plan at the
    repo's root, which needs no name because nothing else shares its branches."""
    parts = [part for part in str(prefix or "").split("/") if part]
    if not parts:
        return ROOT
    return re.sub(r"[^a-z0-9]+", "-", parts[-1].lower()).strip("-") or "plan"


def session_branch(scope, record_id):
    """The branch a new session sits on: `session/<id>`, or `session/<plan>/<id>` in a plan that shares its repo."""
    return f"session/{scope}/{record_id}" if scope else f"session/{record_id}"


def dashboard_branch(scope, today):
    return f"dashboard/{scope}/{today}" if scope else f"dashboard/{today}"


def owns_session_branch(scope, branch):
    """True when a session branch's short name (`session/...`) is this plan's. A plan at the repo's root owns every
    session branch, as before. A plan in a subfolder owns `session/<plan>/...` and the old unscoped
    `session/<id>` (one name part after `session/`), and none of another plan's."""
    if not scope:
        return True
    rest = branch[len("session/"):] if branch.startswith("session/") else branch
    return "/" not in rest or rest.startswith(f"{scope}/")


def titled(scope, title):
    """A pull request's title with the plan named in front, when the plan shares its repo with others."""
    return f"[{scope}] {title}" if scope else title


def plan_of(path, folders):
    """The folder (one of `folders`, repo-relative with a trailing slash, "" for the root) that holds this
    repo-relative path: the deepest one. None when the path is in no plan."""
    best = None
    for folder in folders:
        if path.startswith(folder) and (best is None or len(folder) > len(best)):
            best = folder
    return best


def inside(path, folder):
    """`path` relative to `folder`, or None when it is not under it."""
    return path[len(folder):] if path.startswith(folder) else None


def changed_plans(changed, folders):
    """The plan folders that hold at least one changed repo-relative path, in the order of `folders`."""
    hit = {plan_of(path, folders) for path in changed}
    return [folder for folder in folders if folder in hit]


def duplicate_slugs(folders):
    """{slug: [folders]} for slugs two plans share: their session branches would live in one namespace."""
    by_slug = {}
    for folder in folders:
        by_slug.setdefault(slug_of(folder), []).append(folder)
    return {slug: group for slug, group in by_slug.items() if slug and len(group) > 1}
