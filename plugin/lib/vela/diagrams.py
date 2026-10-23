"""Vault model to Mermaid flowcharts. Pure and deterministic.

Every node comes from an entity: an app page, an external provider named in a
contract's **Provider:** bullet, or a capability page. Every edge is a contract,
drawn from its provider to each consumer. Nothing is drawn by hand.

A diagram never holds more than the flowchart budget. `fit` keeps the most
connected nodes (the app a page is about always stays; ties go by style, then key)
and returns the rest. A graph diagram then draws the left-out nodes as one dashed
"others" box that names them, with its edges rolled up per kept node, and the block
lists every left-out node in a table under the diagram, so nothing is dropped without a trace.
"""
import hashlib
import re
from dataclasses import dataclass, replace

UNSAFE = re.compile(r"[^\w .,()/'+-]")
KEY_UNSAFE = re.compile(r"[^A-Za-z0-9_]")

# Node classes. Mermaid draws a class only when a `class` line names it.
STYLES = {
    "focus": "fill:#2448b8,stroke:#19212d,color:#ffffff",
    "app": "fill:#eef1f5,stroke:#2448b8,color:#19212d",
    "new": "fill:#d9f2e3,stroke:#1e7a46,color:#10301d",
    "changed": "fill:#fdf0d5,stroke:#a06400,color:#3a2600",
    "unchanged": "fill:#eef1f5,stroke:#7a8494,color:#19212d",
    "retired": "fill:#f6e0de,stroke:#b3261e,color:#3a0d0a,stroke-dasharray:4 3",
    "external": "fill:#ffffff,stroke:#7a8494,color:#19212d,stroke-dasharray:2 2",
    "others": "fill:#ffffff,stroke:#2448b8,color:#19212d,stroke-dasharray:6 3",
}
APP_STYLE = {"new": "new", "changed": "changed", "integrated": "unchanged", "unchanged": "unchanged", "retired": "retired"}
CAPABILITY_STYLE = {"new": "new", "extend": "changed", "replace": "changed", "narrow": "changed",
                    "retire": "retired", "unchanged": "unchanged"}
# Lower ranks are drawn first when a diagram is over budget.
RANK = {"focus": 0, "new": 1, "changed": 1, "app": 2, "unchanged": 2, "retired": 3, "external": 4}
NO_DOMAIN = "No domain"
OTHERS_KEY = "others_box"
OTHERS_NAMES_SHOWN = 8  # names listed inside the others box; the rest are counted and left to the table under the diagram


@dataclass(frozen=True)
class Node:
    key: str  # Mermaid node id, letters, digits and _ only
    label: str  # already safe to put between double quotes
    style: str  # a key of STYLES
    ref: str  # what the node is: an app or capability id, or the external provider's name
    page: object  # the page the node stands for, None for an external provider


@dataclass(frozen=True)
class Edge:
    source: str  # node key of the provider
    target: str  # node key of the consumer
    label: str  # the contract id


@dataclass(frozen=True)
class Graph:
    nodes: tuple  # sorted by key
    edges: tuple  # sorted by (label, source, target)
    skipped: tuple = ()  # (contract id, reason) for each contract the diagram could not draw, sorted


def safe_label(text, fallback):
    """Text Mermaid draws as written: no quotes, brackets, pipes, #, ; or markup."""
    cleaned = " ".join(UNSAFE.sub(" ", str(text)).split())
    return cleaned or fallback


def node_key(prefix, name):
    return prefix + KEY_UNSAFE.sub("_", name)


def page_title(page):
    title = page.meta.get("title")
    return title if isinstance(title, str) and title.strip() else page.name


def app_node(page, style=None, show_change=True):
    """A node for an app page. Its label says the change in words, so color is never the only cue."""
    change = page.meta.get("change")
    change = change if isinstance(change, str) and change in APP_STYLE else ""
    name = page.id or page.name
    label = page_title(page) + (f" ({change})" if show_change and change else "")
    return Node(node_key("n_", name), safe_label(label, name), style or APP_STYLE.get(change, "unchanged"), name, page)


LINKED_NAME = re.compile(r"\[\[([^\]|#]*)(?:#([^\]|]*))?(?:\\?\|([^\]]*))?\]\]")


def external_name(text):
    """A provider as a reader names it: "[[03-context-and-scope#PTY-01 Spokewell|Spokewell]]" is Spokewell,
    not "03-context-and-scope PTY-01 Spokewell Spokewell"."""
    return LINKED_NAME.sub(lambda m: m.group(3) or m.group(2) or m.group(1), text).strip()


def external_node(name):
    name = external_name(name)
    return Node(node_key("x_", name.lower()), safe_label(name, "external"), "external", name, None)


def provider_of(contract, plain=False):
    """The node a contract starts from: its external **Provider:**, or the page it lives on."""
    external = contract.fact("Provider")
    if external:
        return external_node(external)
    return app_node(contract.page, "app", False) if plain else app_node(contract.page)


def _unique_keys(nodes):
    """{(base key, ref): final key}. Two different refs that share a base key each get a hash of their ref.

    The hash keeps both nodes visible, so a person can see the two spellings and fix one.
    """
    refs_by_key = {}
    for node in nodes:
        refs_by_key.setdefault(node.key, set()).add(node.ref)
    final = {}
    for key, refs in refs_by_key.items():
        for ref in refs:
            suffix = "_" + hashlib.sha1(ref.encode("utf-8")).hexdigest()[:6] if len(refs) > 1 else ""
            final[(key, ref)] = key + suffix
    return final


def edge_label(contract):
    """An arrow is labeled with the contract's name ("Consent check"), not its ID: a reader looking at the drawing knows
    what crosses, and the ID stays on the page the arrow's contract lives on. The ID when the contract has no name."""
    return safe_label(contract.name or contract.id, contract.id)


def _graph(nodes, edges, skipped=()):
    """`edges` is [(provider Node, consumer Node, contract id)], so keys can be settled before edges use them."""
    final = _unique_keys(list(nodes) + [n for e in edges for n in e[:2]])
    rekey = lambda n: replace(n, key=final[(n.key, n.ref)])
    by_key = {}
    for node in map(rekey, nodes):
        by_key.setdefault(node.key, node)
    drawn = {Edge(rekey(s).key, rekey(t).key, label) for s, t, label in edges}
    return Graph(tuple(sorted(by_key.values(), key=lambda n: n.key)),
                 tuple(sorted(drawn, key=lambda e: (e.label, e.source, e.target))),
                 tuple(sorted(set(skipped))))


def _provider_problem(contract, retired_pages, after):
    """Why a contract cannot be drawn from its provider, or "" when it can."""
    if contract.fact("Provider"):
        return ""
    if contract.page.type != "app-building-blocks":
        return "provider is not an app page"
    if after and contract.page in retired_pages:
        return f"provider {contract.page.id or contract.page.name} is retired"
    return ""


def context_graph(vault, after=False):
    """Every app page, every external provider, and one edge per contract and consumer.

    `after=True` is the after view: retired apps are left out (the caller lists them),
    and apps share one plain style because the change no longer matters. Every contract
    that cannot be drawn is named in `skipped` with its reason.
    """
    retired = [a for a in vault.apps if a.meta.get("change") == "retired"] if after else []
    apps = [a for a in vault.apps if a not in retired]
    nodes = [app_node(a, "app", False) if after else app_node(a) for a in apps]
    edges, skipped = [], []
    for contract in vault.contracts:
        problem = _provider_problem(contract, retired, after)
        if problem:
            skipped.append((contract.id, problem))
            continue
        source = provider_of(contract, plain=after)
        nodes.append(source)
        for consumer in vault.consumers(contract):
            if consumer in retired:
                skipped.append((contract.id, f"consumer {consumer.id or consumer.name} is retired"))
            else:
                edges.append((source, app_node(consumer, "app", False) if after else app_node(consumer), edge_label(contract)))
    return _graph(nodes, edges, skipped)


def app_graph(vault, app):
    """The app and its direct neighbors by contract, provided or consumed."""
    focus = app_node(app, "focus")
    nodes, edges, skipped = [focus], [], []
    for contract in vault.contracts:
        consumers = vault.consumers(contract)
        provides = contract.page is app and not contract.fact("Provider")
        consumes = app in consumers
        if not provides and not consumes:
            continue
        if not contract.fact("Provider") and contract.page.type != "app-building-blocks":
            skipped.append((contract.id, "provider is not an app page"))
            continue
        source = focus if provides else provider_of(contract)
        nodes.append(source)
        for target in consumers if provides else [app]:
            node = focus if target is app else app_node(target)
            nodes.append(node)
            edges.append((source, node, edge_label(contract)))
    return _graph(nodes, edges, skipped)


def capability_node(page):
    change = page.meta.get("change")
    style = CAPABILITY_STYLE.get(change if isinstance(change, str) else "", "unchanged")
    shown = f" ({change})" if isinstance(change, str) and change in CAPABILITY_STYLE else ""
    name = page.id if isinstance(page.id, str) and page.id else page.name
    label = safe_label(f"{name} {page_title(page)}{shown}", name)
    # ref is the page name, which is unique, so two pages that share an id or a key stay two nodes
    return Node(node_key("c_", name), label, style, page.name, page)


def domain_of(page):
    domain = page.meta.get("domain")
    return " ".join(domain.split()) if isinstance(domain, str) and domain.strip() else NO_DOMAIN


def domain_keys(domains):
    """{domain: subgraph key}. Two domains that share a key (such as Booking and booking) each get a hash."""
    base = {d: node_key("d_", d.lower()) for d in domains}
    shared = {k for k in base.values() if list(base.values()).count(k) > 1}
    return {d: k + ("_" + hashlib.sha1(d.encode("utf-8")).hexdigest()[:6] if k in shared else "") for d, k in base.items()}


def capability_groups(vault):
    """[(domain, [Node])], domains in name order with "No domain" last, nodes by id."""
    pages = sorted(vault.of_type("capability"), key=lambda p: (p.id if isinstance(p.id, str) else "", p.name))
    nodes = [capability_node(p) for p in pages]
    final = _unique_keys(nodes)
    groups = {}
    for page, node in zip(pages, nodes):
        groups.setdefault(domain_of(page), []).append(replace(node, key=final[(node.key, node.ref)]))
    order = sorted(groups, key=lambda d: (d == NO_DOMAIN, d.lower(), d))
    return [(d, groups[d]) for d in order]


def connections(graph):
    """{node key: how many contracts (edges) touch it in the full graph}."""
    count = {n.key: 0 for n in graph.nodes}
    for edge in graph.edges:
        for key in {edge.source, edge.target}:
            if key in count:
                count[key] += 1
    return count


def fit(graph, budget, reserved=0):
    """(drawn graph, nodes left out). Keeps the focus app, then the most connected nodes.

    Ties go to the lower style rank, then the lower key, so the result is the same every time.
    `reserved` is how many elements the caller adds itself, such as subgraphs.
    """
    room = max(budget - reserved, 0)
    if len(graph.nodes) <= room:
        return graph, ()
    links = connections(graph)
    ranked = sorted(graph.nodes, key=lambda n: (n.style != "focus", -links[n.key], RANK.get(n.style, 9), n.key))
    kept = {n.key for n in ranked[:room]}
    drawn = Graph(tuple(n for n in graph.nodes if n.key in kept),
                  tuple(e for e in graph.edges if e.source in kept and e.target in kept), graph.skipped)
    return drawn, tuple(n for n in ranked[room:])


def others_label(left_out):
    names = [safe_label(page_title(n.page) if n.page is not None else n.ref, n.key) for n in sorted(left_out, key=lambda n: n.key)]
    shown = names[:OTHERS_NAMES_SHOWN]
    if len(names) > len(shown):
        shown.append(f"and {len(names) - len(shown)} more, listed below")
    return "<br/>".join([f"{len(names)} others"] + shown)


def rolled_up(labels):
    """One arrow label for the contracts between a kept node and the others box."""
    return next(iter(labels)) if len(labels) == 1 else f"{len(labels)} contracts"


def others_edges(graph, drawn, left_out):
    """One edge per kept node and direction between it and the others box, provider to consumer."""
    gone = {n.key for n in left_out}
    kept = {n.key for n in drawn.nodes}
    into, out_of = {}, {}
    for e in graph.edges:
        if e.source in kept and e.target in gone:
            into.setdefault(e.source, set()).add(e.label)
        elif e.source in gone and e.target in kept:
            out_of.setdefault(e.target, set()).add(e.label)
    return ([Edge(k, OTHERS_KEY, rolled_up(into[k])) for k in sorted(into)]
            + [Edge(OTHERS_KEY, k, rolled_up(out_of[k])) for k in sorted(out_of)])


def fit_with_others(graph, budget, reserved=0):
    """(graph to draw, nodes left out). Left-out nodes become one "others" box that takes one slot of the budget."""
    if len(graph.nodes) <= max(budget - reserved, 0):
        return graph, ()
    kept, left_out = fit(graph, budget, reserved + 1)
    box = Node(OTHERS_KEY, others_label(left_out), "others", "others", None)
    nodes = tuple(sorted(kept.nodes + (box,), key=lambda n: n.key))
    edges = tuple(sorted(kept.edges + tuple(others_edges(graph, kept, left_out)), key=lambda e: (e.label, e.source, e.target)))
    return Graph(nodes, edges, graph.skipped), left_out


def flowchart(graph, direction="LR", groups=()):
    """Mermaid lines for a graph. `groups` is [(subgraph key, label, [node keys])]."""
    lines = [f"flowchart {direction}"]
    grouped = {key for _, _, keys in groups for key in keys}
    by_key = {n.key: n for n in graph.nodes}
    for group_key, label, keys in groups:
        lines.append(f'  subgraph {group_key}["{label}"]')
        lines.extend(f'    {k}["{by_key[k].label}"]' for k in keys if k in by_key)
        lines.append("  end")
    lines.extend(f'  {n.key}["{n.label}"]' for n in graph.nodes if n.key not in grouped)
    lines.extend(f'  {e.source} -->|"{e.label}"| {e.target}' for e in graph.edges)
    styles = sorted({n.style for n in graph.nodes})
    lines.extend(f"  classDef {s} {STYLES[s]}" for s in styles)
    for style in styles:
        members = ",".join(n.key for n in graph.nodes if n.style == style)
        lines.append(f"  class {members} {style}")
    return lines


# What each node style means, in the words a reader uses. A diagram's key lists only the styles it drew.
STYLE_WORDS = {
    "focus": "dark blue: the app this page is about",
    "app": "blue outline: an app in the initiative",
    "new": "green: new in this initiative",
    "changed": "amber: changed by this initiative",
    "unchanged": "gray: stays as it is",
    "retired": "red, dashed: retired by this initiative",
    "external": "white, dashed: outside this initiative (another company or system)",
    "others": "blue, dashed outline: the boxes left out to keep this readable, named inside it",
}


def key_line(graph):
    """One plain line under a diagram saying what its colors, dashes and arrows mean, for the styles it drew only."""
    if not graph.nodes:
        return ""
    used = [STYLE_WORDS[s] for s in sorted({n.style for n in graph.nodes}, key=lambda s: list(STYLE_WORDS).index(s)) if s in STYLE_WORDS]
    arrows = (["an arrow is a contract (an agreed interface), labeled with its name, pointing from the side that "
               "provides it to the app that uses it"] if graph.edges else [])
    return "Key: " + " · ".join(used + arrows) + "."


def overflow_contracts(graph, node):
    """The contracts that touch a node left out of a diagram, as "Seat hold from Booking to Till"."""
    names = {n.key: safe_label(page_title(n.page) if n.page is not None else n.ref, n.key) for n in graph.nodes}
    return [f"{e.label} from {names.get(e.source, e.source)} to {names.get(e.target, e.target)}"
            for e in graph.edges if node.key in (e.source, e.target)]
