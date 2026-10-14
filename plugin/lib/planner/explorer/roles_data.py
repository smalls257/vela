"""What the front doors, the map's groupings and the release timeline need, read from the planner's own modules.

- Releases: `releases.releases` and `releases.snapshots` (Today, then cumulative after each release). What a
  release touches is the apps and contracts that carry a share of what it delivers, from `allocation.carried`.
  With no releases, Today is still `snapshots`' first state, and the end state comes from each app's `change`.
- Domains: each app page's `domain:` frontmatter (CONVENTIONS, "Domains"); none is "No domain".
- Capabilities per app: the requirements an app's allocation rows carry (`allocation.rows`), else the epics that list
  the app and deliver the capability (`trace.epics`). The page labels which.
- Goals and constraints: the rows the model registers from the Goals and Constraints tables.
- Acceptance criteria: an epic's criteria in either shape, numbered lines under "acceptance criteria" or headed ones
  under "Done when", as `criteria.read` reads them (and so `trace.ac_markers`); a requirement's plain bullets under its heading, as `releases.criteria_count` counts them.
- Failure behaviour: the runtime page's sections whose heading `ladder.FAILURE` accepts.
- An engineer's slice: `handoff.slice_of`, the same list a handoff manifest records.
"""
import re

from planner import allocation, handoff, ladder, progress, readability, releases, schema, trace
from planner import criteria as criteria_reader

from . import slices_data
from .record import chips_html, inline_html, plain

LIST_MARK = re.compile(r"^[-*] |^\d+\. ")
APP_STATUS_END = {"new": "new", "changed": "changes", "retired": "absent", "retire": "absent"}


def domains(vault, keys):
    return {keys.page(a): (str(a.meta.get("domain") or "").strip() or "No domain") for a in vault.apps}


def capabilities_by_app(vault, keys):
    """{app key: {"caps": [capability ids], "via": "allocation" | "epics"}}."""
    out = {}
    for row in allocation.rows(vault):
        if not row.requirement:
            continue
        cap = row.requirement.split(".")[0]
        entry = out.setdefault(keys.page(row.app), {"caps": {}, "via": "allocation"})
        entry["caps"][cap] = entry["caps"].get(cap, 0) + 1
    caps = {c.id for c in vault.of_type("capability")}
    for epic in trace.epics(vault):
        for app_id in trace.listed(epic, "apps"):
            app = next((a for a in vault.apps if a.id == app_id), None)
            if app is None:
                continue
            entry = out.setdefault(keys.page(app), {"caps": {}, "via": "epics"})
            if entry["via"] != "epics":
                continue  # allocation says it better
            for cap in trace.listed(epic, "delivers"):
                if cap in caps:
                    entry["caps"][cap] = entry["caps"].get(cap, 0) + 1
    return {k: {"caps": sorted(v["caps"], key=lambda c: (-v["caps"][c], c)), "via": v["via"]} for k, v in out.items()}


def grouping(vault, keys):
    """Which Group buttons have anything to group by. Real vaults rarely carry `domain:` on an app page (the
    boundary session writes it only when the user names one) or capability requirements, and a grouping with one
    "none" box is a drawing that says nothing. Counts feed the "No domain yet (N apps)" labels."""
    by_domain = domains(vault, keys)
    by_cap = capabilities_by_app(vault, keys)
    undomained = [k for k, d in by_domain.items() if d == "No domain"]
    uncapped = [k for k in by_domain if not by_cap.get(k, {}).get("caps")]
    return {"domain": len(undomained) < len(by_domain), "capability": len(uncapped) < len(by_domain),
            "noDomain": len(undomained), "noCapability": len(uncapped)}




def release_data(vault, keys):
    found = releases.releases(vault)
    snaps = releases.snapshots(vault)
    carried = allocation.carried(vault)
    app_key = {a.id: keys.page(a) for a in vault.apps}
    reqs = {r.id: r for r in allocation.requirements(vault)}
    states = []
    for s in snaps:
        states.append({"name": s["name"], "target": s["target"], "state": s["state"],
                       "apps": {app_key[k]: v for k, v in s["apps"].items() if k in app_key},
                       "contracts": dict(s["contracts"]), "delivers": list(s["delivers"])})
    for i, rel in enumerate(found):
        touched, through = [], []
        for row in rel.rows:
            for share in carried.get(row.requirement, []):
                k = keys.page(share.app)
                if k not in touched:
                    touched.append(k)
                for cid in share.through:
                    if cid not in through:
                        through.append(cid)
        rows = [{"requirement": r.requirement, "criteria": list(r.criteria), "raw": r.raw_criteria, "note": r.note,
                 "of": releases.criteria_count(reqs[r.requirement]) if r.requirement in reqs else 0} for r in rel.rows]
        states[i + 1].update(rows=rows, touched=touched, through=through, heading=rel.name)
    end = None
    if not found:
        apps = {app_key[a.id]: APP_STATUS_END.get(str(a.meta.get("change") or ""), "exists") for a in vault.apps}
        cons = {c.id: ("new" if c.fact("Change") == "new" else "exists") for c in vault.contracts}
        end = {"name": "End state", "target": "", "state": "", "apps": apps, "contracts": cons, "delivers": [],
               "fromChange": True}
    page = releases.page(vault)
    return {"states": states, "end": end, "page": keys.page(page) if page else "", "count": len(found),
            "tracer": slices_data.tracer_data(vault, found[0] if found else None)}


def table_rows(vault, keys, header):
    out = []
    for page in vault.pages:
        for table in page.tables:
            if table.generated or tuple(table.header)[:len(header)] != header:
                continue
            for row, line in zip(table.rows, table.row_lines):
                padded = list(row) + [""] * (len(table.header) - len(row))
                out.append({"id": padded[0].strip(), "cols": [inline_html(c, keys, page) for c in padded[1:]],
                            "text": [plain(c) for c in padded[1:]], "page": keys.page(page)})
    return out


def goals(vault, keys):
    rows = table_rows(vault, keys, schema.GOALS_HEADER)
    return [{"id": r["id"], "goal": r["cols"][0], "goalText": r["text"][0], "measure": r["cols"][1],
             "state": r["text"][2] if len(r["text"]) > 2 else "", "page": r["page"]} for r in rows if r["id"]]


def constraints(vault, keys):
    out = []
    for page in vault.pages:
        for table in page.tables:
            if table.generated or tuple(table.header)[:2] != schema.CONSTRAINTS_HEADER:
                continue
            for row in table.rows:
                padded = list(row) + [""] * (len(table.header) - len(row))
                out.append({"id": padded[0].strip(), "text": plain(padded[1]), "html": inline_html(padded[1], keys, page),
                            "head": list(table.header[2:]), "rest": [inline_html(c, keys, page) for c in padded[2:]],
                            "page": keys.page(page)})
    return out


def risks(vault, keys):
    return [{"id": r.id, "title": r.name, "facts": {label: plain(b.value) for label, b in r.facts.items()}}
            for r in vault.risks]


def epic_criteria(vault, keys):
    """{epic key: [{"n", "heading", "html", "markers", "struck", "trace", "group"}]}: the epic's acceptance criteria in
    either shape, from `criteria.read`. A numbered criterion has no heading; `n` is its AC number in both."""
    out = {}
    for epic in trace.epics(vault):
        rows = []
        for c in criteria_reader.read(epic):
            rows.append({"n": c.n, "heading": c.heading, "html": inline_html(c.text, keys, epic), "markers": list(c.markers),
                         "struck": c.struck, "group": c.group,
                         "trace": chips_html(list(c.trace), keys) if c.trace else ""})
        out[keys.page(epic)] = rows
    return out


def requirement_criteria(vault, keys):
    """{requirement id: [criterion html]}: the plain bullets under its heading, after its facts."""
    out = {}
    for r in allocation.requirements(vault):
        lines = r.page.text.split("\n")
        found = []
        for line in lines[r.line:]:
            if line.startswith("#"):
                break
            if re.match(r"^- (?!\*\*[^*]+:\*\*)", line):
                found.append(inline_html(line[2:], keys, r.page))
            elif found and readability.is_trace(line):
                found[-1] += chips_html(readability.trace_ids(line), keys)
        out[r.id] = found
    return out


def failure(vault, keys):
    """{app key: {"runtime": key, "sections": [{"heading", "html"}]}} from the runtime page's failure sections."""
    out = {}
    for app in vault.apps:
        runtime = progress.runtime_page(vault, app)
        if runtime is None:
            out[keys.page(app)] = {"runtime": "", "sections": []}
            continue
        lines = runtime.text.split("\n")
        sections = []
        heads = [h for h in runtime.headings if h.level >= 2]
        for i, h in enumerate(heads):
            if not ladder.FAILURE.search(h.text):
                continue
            stop = next((x.line for x in heads[i + 1:] if x.level <= h.level), len(lines) + 1)
            body = [l.strip() for l in lines[h.line:stop - 1] if l.strip() and not l.strip().startswith(("|", "<!--", "```"))]
            sections.append({"heading": h.text, "id": h.text,
                             "html": "".join(f"<p>{inline_html(LIST_MARK.sub('', b), keys, runtime)}</p>" for b in body[:8]),
                             "more": len(body) > 8})
        out[keys.page(app)] = {"runtime": keys.page(runtime), "sections": sections}
    return out


def tested_by(vault):
    return {c.id: plain(c.fact("Tested by")) for c in vault.contracts}


def slices(vault, keys):
    return {keys.page(app): [{"id": e.id, "kind": e.kind, "state": e.state} for e in handoff.slice_of(vault, app)]
            for app in vault.apps}


def cells(vault, keys):
    """Every concern cell: concern page, app, state, as the model reads the concern pages' tables."""
    out = []
    for c in vault.cells:
        app = vault.page(c.app)
        out.append({"concern": keys.page(c.concern), "app": keys.page(app) if app is not None else c.app, "state": c.state,
                    "text": plain(c.text)[:220]})
    return out


def extract(vault, keys):
    return {"domains": domains(vault, keys), "appCaps": capabilities_by_app(vault, keys), "grouping": grouping(vault, keys),
            "releases": release_data(vault, keys), "goals": goals(vault, keys), "constraints": constraints(vault, keys),
            "riskList": risks(vault, keys), "epicCriteria": epic_criteria(vault, keys),
            "reqCriteria": requirement_criteria(vault, keys), "failure": failure(vault, keys),
            "testedBy": tested_by(vault), "slices": slices(vault, keys), "cells": cells(vault, keys),
            "slicePlan": slices_data.extract(vault, keys)}
