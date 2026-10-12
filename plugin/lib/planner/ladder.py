"""How far up the stage ladder an app's pages already reach. Pure: reads the vault, decides nothing.

`stage` is typed by hand (CONVENTIONS.md, "Areas and stages"), so an app whose pages have moved on keeps the stage it
was given. This computes the highest stage whose entry list, and every one below it, holds today, and what the next
stage still needs. Close reports it once, as a line, never as a question: the lead types the stage or ignores it.
"""
import re

from planner import model, schema

ORDER = schema.ENUMS["stage"]
SETTLED = ("decided", "fact")
CONTAINER_DONE = ("confirmed", "unchanged", "retired")
# "How the app behaves on failure": boundary writes "## On failure", and the example says "When a dependency is slow
# or down". Either counts.
FAILURE = re.compile(r"\bfail|\bdown\b|\bslow\b|\boutage", re.I)


def runtime_page(vault, app):
    if not app.name.endswith("-building-blocks"):
        return None
    page = vault.page(app.name[: -len("-building-blocks")] + "-runtime")
    return page if page is not None and page.type == "app-runtime" else None


def containers(app):
    """The State cell of each row of the app's containers table, or None when it has no such table."""
    for table in app.tables:
        if table.generated or tuple(table.header)[:2] != schema.CONTAINERS_HEADER:
            continue
        column = list(table.header).index("State") if "State" in table.header else len(table.header) - 1
        return [row[column].strip().lower() if len(row) > column else "" for row in table.rows]
    return None


def cites_more_than_a_dump(vault, app):
    """A source counts unless it is a session that only dumped: a document, a review, a measurement, a Grill."""
    sources = app.meta.get("sources")
    for source in sources if isinstance(sources, list) else ():
        session = vault.page(str(source))
        if session is None or session.type != "session" or set(session.meta.get("modes") or []) - {"dump"}:
            return True
    return False


def flows_naming(vault, app):
    names = {app.name.lower()}
    runtime = runtime_page(vault, app)
    if runtime is not None:
        names.add(runtime.name.lower())
    return [f for f in vault.of_type("flow") if any(link.target.lower() in names for link in f.links)]


def missing(vault, app, stage):
    """What `stage`'s own entry list still needs for this app, in words. Empty when it holds."""
    # A contract kept on the app's page for an outside provider (it has **Provider:**) is one the app consumes.
    provided = [c for c in vault.contracts if c.page is app and not c.fact("Provider")]
    consumed = [c for c in vault.contracts
                if (c.page is not app and app in vault.consumers(c)) or (c.page is app and c.fact("Provider"))]
    blocked = model.blockers(vault)
    if stage == "target":
        return [] if cites_more_than_a_dump(vault, app) else ["the app page cites no source that is not a dump"]
    if stage == "boundaries":
        return [f"{f.id} is at {f.meta.get('state') or 'no state'}" for f in flows_naming(vault, app)
                if f.meta.get("state") not in ("assumption", "fact", "decided")]
    if stage == "contracts":
        out = [] if app.meta.get("state") == "decided" else [f"{app.id} is at {app.meta.get('state') or 'no state'}"]
        return out + ([] if containers(app) is not None else ["the app page has no containers table"])
    if stage == "handoff":
        out = [f"{c.id} it provides is at {c.fact('State') or 'no state'}" for c in provided
               if c.fact("State") not in SETTLED or (c.fact("State") == "fact" and c.fact("Change") != "unchanged")]
        out += [f"{c.id} it consumes is at {c.fact('State') or 'no state'}" for c in consumed
                if c.fact("State") not in SETTLED]
        runtime = runtime_page(vault, app)
        if runtime is None or not any(FAILURE.search(h.text) for h in runtime.headings):
            out.append("its runtime page has no section on failure")
        out += [f"{u.id} blocks {c.id}" for c in provided + consumed for u in blocked.get(c.id, [])]
        return out
    if stage == "epics":
        cells = {(c.concern.id, c.app) for c in vault.cells if c.state != "unexamined"}
        out = [f"{p.id} has no examined cell for it" for p in vault.of_type("concern") if (p.id, app.name) not in cells]
        states = containers(app) or []
        return out + [f"a container is at {s or 'no state'}" for s in states if s not in CONTAINER_DONE]
    return []


def allows(vault, app):
    """(the highest stage the app's pages reach, what the next stage still needs). Each stage needs every stage
    below it, as the ladder's order says. ("", []) for an app outside the ladder."""
    if app.meta.get("change") not in schema.LADDERED_CHANGES:
        return "", []
    reached = ORDER[0]
    for stage in ORDER[1:]:
        gaps = missing(vault, app, stage)
        if gaps:
            return reached, gaps
        reached = stage
    return reached, []


def ahead_of_stage(vault, app):
    """The stage the pages reach when it is later than the app's typed stage, or ""."""
    reached, _ = allows(vault, app)
    typed = app.meta.get("stage")
    if not reached or typed not in ORDER:
        return ""
    return reached if ORDER.index(reached) > ORDER.index(typed) else ""
