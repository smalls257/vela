"""The onboarding mode's data (D.onboard), from the same modules the command line reads.

The Violation this module exists to prevent is a Distributed Monolith: if the dashboard and `vela onboard` each
worked out the stage, the modules and the lead's tuning, the skill could promise a path the page doesn't show. Here
the page's data and the command's answers come from one call, `extract`, over the explorer's own data.

The lead's page (ONBOARDING.md at the vault root) is read here and nowhere else. A page that can't be read stops the
build with the reason; one with mistakes still applies everything it said, and the mistakes ride in `problems` and in
the build report. The personal path, when a build is made for one person, is checked against the lead's page again,
because the page may have changed since the path was written.
"""
from vela import cli, onboardmodules, onboardpath, onboardtune, onboarding


class OnboardError(Exception):
    """The lead's page exists but can't be read. The message says why; nothing is built."""


def read_tuning(root):
    try:
        text = cli.read_text_if_present(root, onboardtune.FILE)  # the file read lives in cli.py: the core takes text (Infected Core)
    except (OSError, UnicodeDecodeError) as exc:
        raise OnboardError(f"the onboarding page can't be read ({exc}), so no onboarding was built. Fix or remove it.") from exc
    return onboardtune.EMPTY if text is None else onboardtune.parse(text)


def standard(data, tuning):
    """(stage, {audience: {"modules": [keys], "hidden": [names], "note"}}): the standard path for each audience."""
    stage = onboarding.stage_of(data)
    paths = {}
    for audience in onboarding.AUDIENCES:
        role = tuning.for_audience(audience)
        ids = onboarding.standard_ids(audience, stage, role)
        paths[audience] = {"modules": onboarding.path_keys(audience, ids),
                           "hidden": [onboarding.NAMES[m] for m in onboarding.hidden_ids(audience, stage, role)],
                           "note": role.note if role else ""}
    return stage, paths


def personal(stage, tuning, path):
    """(mine dict or None, problems): the person's path as the page carries it, after being checked against the lead's
    page as it is now. A path that no longer fits is not shown; the standard path is, and `problems` says why."""
    hidden = onboarding.hidden_ids(path.audience, stage, tuning.for_audience(path.audience))
    checked, problems = onboardpath.make(path.handle, path.audience, path.modules, path.depth, path.diagrams, hidden, path.brought_back)
    if checked is None:
        return None, [f"{path.handle}'s own path was not used: {p}" for p in problems]
    mine = onboardpath.as_data(checked)
    mine["keys"] = onboarding.path_keys(checked.audience, checked.modules)
    return mine, []


def recorded_roles(root):
    """({handle: role}, problems): the lead's record of who holds which role, `roles:` in .vela.yaml. A handle is written
    with or without its @. A role that is not one of the six is a problem and is left out, never guessed."""
    found, problems = {}, []
    written = cli.load_config(root).get("roles") or {}
    if not isinstance(written, dict):
        return {}, ["The roles in the plan's settings should list a handle and a role for each person."]
    for handle, word in written.items():
        role = onboarding.ROLE_WORDS.get(str(word).strip().casefold())
        if role is None:
            problems.append(f"The roles in the plan's settings give {handle} the role '{word}', which is not one of: " + ", ".join(onboarding.AUDIENCES))
        else:
            found[str(handle).lstrip("@")] = role
    return found, problems


def extract(data, root, mine_path=None, me=None):
    """D.onboard. `data` is the explorer's data so far; `mine_path` is an `onboardpath.Path` or None; `me` is
    {"handle", "role"} for a page built for one person (the role is their own choice), None for the shared page, which
    carries nobody's handle. `roles` is the lead's record, which is committed and so is shared."""
    tuning = read_tuning(root)
    roles, role_problems = recorded_roles(root)
    stage, paths = standard(data, tuning)
    mine, problems = (None, []) if mine_path is None else personal(stage, tuning, mine_path)
    return {"stage": stage, "audiences": [{"id": a, "label": onboarding.AUDIENCE_LABELS[a]} for a in onboarding.AUDIENCES],
            "modules": onboardmodules.build_all(data), "paths": paths, "depths": onboardmodules.DEPTHS,
            "problems": onboardtune.problems_text(tuning) + role_problems + problems, "mine": mine, "roles": roles, "me": me}
