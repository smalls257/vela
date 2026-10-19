"""Inside an app, as the page draws it: each app's main containers from the vault, and each team's design beside it.

    containers(vault, keys) -> {app key: {heading, line, rows, edges, diagram} | None}
    inside(vault, keys, designs) -> {app key: design, with what the page draws from it}

Level 2 of "Inside this app" (DESIGN-INSIDE.md) is the app page's main containers table (Container | Job, the
header `ladder.containers` reads) and the mermaid flowchart under the same heading. The table is reliable; the
container-to-container arrows are read from the flowchart, best effort, and the page labels them so.

Level 3 is the team's design, read by design_data.py. Two things the page needs are not in the format, so they are
worked out here and labeled where they show:
- where an Integration point attaches: the component that cites its contract, else the one whose matrix row reads
  from or writes to it, else the one whose Depends on names it, else the app's own edge (`how` says which);
- the label on a Depends-on arrow: what the depended-on component's Exposes line offers "to" the depending one.

A design is checked against the vault with design_data.resolve, so the page can show who owns a vault item, what
no component owns (acknowledged by a gap or missed), and what the design cites that the vault does not hold.
"""
import re

from vela import schema

from . import design_data
from .record import title_of

CON = re.compile(r"\bCON-\d{3}\b")
SERVES = re.compile(r"\bserves?\b", re.I)
USES = re.compile(r"\buses?\b", re.I)
# mermaid flowchart: a node with its label (id["Label"], id[("Label")], id(("Label")), ...) and the arrows between
NODE_DEF = re.compile(r'([A-Za-z_][\w-]*)\s*(?:\[\(|\[\[|\(\(|\[|\(|\{)\s*"?([^"\]\)\}]*)"?\s*(?:\)\]|\]\]|\)\)|\]|\)|\})')
ARROW = re.compile(r'\s*(?:-->|-\.->|==>|---|-\.-)\s*(?:\|\s*"?([^|"]*)"?\s*\|\s*)?')
SKIP = ("flowchart", "graph", "subgraph", "end", "class ", "classdef", "style", "%%", "linkstyle", "click")


def flowchart(lines):
    """{"labels": {id: label}, "edges": [{"from", "to", "label"}]} from a mermaid flowchart, ends named by label."""
    labels, pairs = {}, []
    for raw in lines:
        line = raw.strip()
        if not line or line.lower().startswith(SKIP):
            continue
        for match in NODE_DEF.finditer(line):
            labels[match.group(1)] = match.group(2).strip()
        parts = ARROW.split(NODE_DEF.sub(lambda m: m.group(1), line))
        # re.split keeps the arrow's label: [ends, label, ends, label, ends, ...]
        for i in range(0, len(parts) - 2, 2):
            sources = [p.strip() for p in parts[i].split("&") if p.strip()]
            targets = [p.strip() for p in parts[i + 2].split("&") if p.strip()]
            pairs += [(a, b, (parts[i + 1] or "").strip()) for a in sources for b in targets]
    return {"labels": labels, "edges": [{"from": labels.get(a, a), "to": labels.get(b, b), "label": text}
                                        for a, b, text in pairs]}


def containers(vault, keys):
    """{app key: the app page's main containers, or None when its page has no containers table}."""
    out = {}
    for app in vault.apps:
        table = next((t for t in app.tables if not t.generated and tuple(t.header)[:2] == schema.CONTAINERS_HEADER), None)
        if table is None:
            out[keys.page(app)] = None
            continue
        heading = max((h for h in app.headings if h.level == 2 and h.line < table.line), key=lambda h: h.line,
                      default=None)
        stop = min((h.line for h in app.headings if h.level <= 2 and h.line > table.line), default=10 ** 9)
        header = [design_data._snake(h) for h in table.header]
        rows = []
        for cells, line in zip(table.rows, table.row_lines):
            row = dict(zip(header, (list(cells) + [""] * len(header))[:len(header)]))
            served, used = contracts_named(row.get("contracts_served_or_used", ""))
            rows.append({"name": row.get("container", ""), "job": row.get("job", ""), "serves": served, "uses": used,
                         "proposedBy": row.get("proposed_by", ""), "state": row.get("state", ""), "line": line})
        diagram = next((d for d in app.diagrams if table.line < d.line < stop and d.kind in ("flowchart", "graph")), None)
        names = {r["name"].lower(): r["name"] for r in rows}
        edges = []
        if diagram is not None:
            for e in flowchart(diagram.lines)["edges"]:
                a, b = names.get(e["from"].lower()), names.get(e["to"].lower())
                if a and b and a != b and not any(x["from"] == a and x["to"] == b for x in edges):
                    edges.append({"from": a, "to": b, "label": e["label"]})
        out[keys.page(app)] = {"heading": heading.text if heading else "", "line": table.line, "rows": rows,
                               "edges": edges, "diagram": "\n".join(diagram.lines) if diagram else "",
                               "diagramLine": diagram.line if diagram else None}
    return out


def contracts_named(cell):
    """(served, used) contract IDs from 'Serves CON-001, CON-007. Uses CON-003.'; an unlabeled ID counts as used."""
    served, used = [], []
    for sentence in re.split(r"(?<=\.)\s+|;\s*", cell):
        ids = CON.findall(sentence)
        (served if SERVES.search(sentence) and not USES.search(sentence) else used).extend(i for i in ids)
    return served, used


def _bare(name):
    return design_data._system_name(name)


def integration_stubs(design, vault, keys, app):
    """Each Integration point as a stub: which component it attaches to, how that was worked out, the vault boxes."""
    titles = {title_of(n).lower(): keys.page(n) for n in vault.apps}
    titles.update({p.name.lower(): p.id for p in vault.parties})
    contracts = {c.id: c for c in vault.contracts}
    stubs = []

    def nodes_for(system, ids):
        found = []
        name = _bare(system)
        if name in titles:
            found.append(titles[name])
        for cid in ids:
            c = contracts.get(cid)
            if c is None:
                continue
            ends = [keys.page(c.page)] + [keys.page(p) for p in vault.consumers(c)]
            provider = c.facts.get("Provider")
            for link in provider.links if provider else ():
                key = keys.link(link, c.page)
                if key:
                    ends[0] = key
            found += [k for k in ends if k != keys.page(app)]
        return list(dict.fromkeys(found))

    for row in design["integrations"]:
        system = row.get("system", "")
        # the contracts the System cell names; a contract the Auth cell mentions in passing is another system's
        ids = CON.findall(system) or CON.findall(" ".join(str(v) for v in row.values()))
        component, how = attach(design, system, ids, {k: c.name for k, c in contracts.items()})
        stubs.append({"system": system, "direction": (row.get("direction") or "").strip().lower(),
                      "protocol": row.get("protocol", ""), "auth": row.get("auth", ""), "contracts": ids,
                      "nodes": nodes_for(system, ids), "component": component, "how": how, "line": row.get("line")})
    integrated = {_bare(s["system"]) for s in stubs}
    for c in design["components"]:
        for name in c.get("depends_on_other", []):
            if _bare(name) in integrated:
                continue
            ids = CON.findall(name)
            if ids and any(set(ids) <= set(s["contracts"]) for s in stubs):
                continue  # the same contract the table already lists for an outside system, said another way
            stubs.append({"system": re.sub(r"\s*\(.*?\)\s*", " ", name).strip(), "direction": "out", "protocol": "",
                          "auth": "", "contracts": ids, "nodes": nodes_for(name, ids), "component": c["name"],
                          "how": "it depends on it, though the design doesn't list it as an outside system", "line": c["line"]})
    return stubs


def attach(design, system, ids, names=None):
    """(component name or None, how): the component an Integration point meets, by the first rule that finds one.
    `names` is {contract id: name}, so the reason says the contract's name, not its code."""
    for cid in ids:
        owner = next((name for name, entries in design["trace"].items() if any(e["id"] == cid for e in entries)), None)
        if owner and owner != "Operations":
            return owner, f"it delivers {(names or {}).get(cid) or cid}"
    name = _bare(system)
    for row in design["matrix"]:
        for column, say in (("reads_from", "reads from"), ("writes_to", "writes to")):
            if name and any(_bare(x) == name for x in design_data._split_names(row.get(column, ""))):
                component = next((c["name"] for c in design["components"]
                                  if c["name"].lower() == row.get("component", "").lower()), None)
                if component:
                    return component, f"the design's data table says it {say} it"
    for c in design["components"]:
        if any(_bare(x) == name for x in c.get("depends_on_other", [])):
            return c["name"], "the design says it depends on it"
    return None, "no component in the design connects to it"


def depends_edges(design):
    """[{from, to, label}] for each Depends on between components; the label is what `to` exposes to `from`."""
    by_name = {c["name"]: c for c in design["components"]}
    out = []
    for c in design["components"]:
        for target in c.get("depends_on_components", []):
            exposes = by_name[target]["exposes"]
            offer, _, audience = exposes.partition(" to ")
            label = offer.strip() if audience and c["name"].lower() in audience.lower() else ""
            out.append({"from": c["name"], "to": target, "label": label,
                        "labelFrom": f"the Exposes line of {target}" if label else ""})
    return out


def challenge_recorded(vault, vault_id):
    """A session with mode `challenge` that names the ID: the vault has recorded the senior's challenge."""
    pattern = re.compile(rf"\b{re.escape(vault_id)}\b")
    return next((s.name for s in vault.sessions if "challenge" in (s.meta.get("modes") or []) and pattern.search(s.text)),
                None)


def inside(vault, keys, designs):
    """{app key: design} for each `--design`, with what the page draws: stubs, depends edges, the resolve report."""
    known = design_data.vault_ids(vault)
    by_id = {a.id: a for a in vault.apps}
    out = {}
    for app_id, design in designs.items():
        app = by_id.get(app_id)
        if app is None:
            raise design_data.DesignError(f"--design names {app_id}, which is not an app in this vault")
        targets = design_data.trace_targets(vault, app_id)
        entry = dict(design)
        entry.update({
            "appId": app_id, "file": design["path"],  # basename only, to avoid leaking the builder's filesystem paths
            "resolved": design_data.resolve(design, known, targets), "targets": sorted(targets),
            "stubs": integration_stubs(design, vault, keys, app), "depends": depends_edges(design),
            "challenges": [{"oq": oq["id"], "id": vid, "title": oq["title"], "scenario": oq["other"].get("Scenario", ""),
                            "affects": oq["affects_ids"], "recorded": challenge_recorded(vault, vid), "line": oq["line"]}
                           for oq in design["open_questions"] for vid in oq["challenges"]],
        })
        out[keys.page(app)] = entry
    return out
