"""Vault model to generated block text. Pure and deterministic.

Each block is computed from the model only, never from another block. Output
holds links and numbers, dates and never ages, so two runs give equal bytes.
"""
import hashlib
import re

from vela import allocation, diagrams, parse, plainwords, progress, questions, schema, trace
from vela.model import Finding, blocking_unknowns

OPEN = "<!-- generated:{name} sha={sha}: " + parse.MARKER_TEXT + " -->"
CLOSE = "<!-- /generated:{name} -->"


def normalize(content):
    lines = [line.rstrip() for line in content.replace("\r\n", "\n").split("\n")]
    while lines and not lines[0]:
        lines.pop(0)
    while lines and not lines[-1]:
        lines.pop()
    return "\n".join(lines)


def block_hash(content):
    return hashlib.sha256(normalize(content).encode("utf-8")).hexdigest()[:8]


def block_allowed(page, name):
    where = schema.BLOCKS.get(name)
    if where is None:
        return False
    if where.startswith("type:"):
        return page.type == where[len("type:"):]
    return page.id == where


UNESCAPED_PIPE = re.compile(r"(?<!\\)\|")


def cell(text):
    """Make text safe inside a Markdown table cell. A pipe already written as \\| is left alone, so escaping twice is harmless."""
    return UNESCAPED_PIPE.sub("\\\\|", text)


def row(*cells):
    return "| " + " | ".join(cells) + " |"


def link(target, label, anchor=""):
    inner = f"{target}#{anchor}" if anchor else target
    return f"[[{inner}\\|{cell(label)}]]"


def title(page):
    return str(page.meta.get("title") or page.name)


# --------------------------------------------------------------- the blocks

def block_content(vault, page, name):
    return normalize(GENERATORS[name](vault, page))


def contracts_consumed(vault, page):
    rows = []
    for contract in vault.contracts:
        if page not in vault.consumers(contract):
            continue
        provider = cell(contract.fact("Provider")) or link(contract.page.name, title(contract.page))
        rows.append(row(link(contract.page.name, trace.named(contract.name, contract.id), contract.heading), provider,
                        cell(contract.fact("Change policy")), plainwords.state_word(contract.fact("State"))))
    if not rows:
        return "none"
    return "\n".join(["| Contract | Provided by | Who can change it, and how | How sure |", "|---|---|---|---|"] + rows)


def _here(item, page):
    """Link target for an item: "" when it sits on the page being rendered."""
    return "" if item.page is page else item.page.name


def unknowns_index(vault, page):
    """Questions and risks in two tables: an unknown is a question someone has to answer, a risk is something that may
    go wrong, and a reader treats the two differently. Each row leads with the name; the ID is the link's tag."""
    out = []
    asked = [row(link(_here(u, page), trace.named(u.name, u.id), u.heading), cell(u.fact("Owner")),
                 plainwords.state_word(u.fact("State")), u.fact("Ask by")) for u in vault.unknowns]
    if asked:
        out += ["**Questions**", "", "| Question | Who answers | Status | Answer needed by |", "|---|---|---|---|"] + asked
    risks = [row(link(_here(r, page), trace.named(r.name, r.id), r.heading), cell(r.fact("Owner")),
                 plainwords.state_word(r.fact("State"))) for r in vault.risks]
    if risks:
        out += ([""] if out else []) + ["**Risks**", "", "| Risk | Owner | Status |", "|---|---|---|"] + risks
    return "\n".join(out) if out else "none"


def cell_state(vault, concern, app):
    for c in vault.cells:
        if c.concern is concern and c.app.lower() == app.name.lower():
            return c.state
    return "unexamined (no row)"


def concern_matrix(vault, page):
    concerns = sorted(vault.of_type("concern"), key=lambda p: p.id)
    apps = vault.apps
    if not concerns or not apps:
        return "none"
    header = row("App", *(link(c.name, title(c)) for c in concerns))
    lines = [header, "|---|" + "---|" * len(concerns)]
    for app in apps:
        states = [plainwords.cell_word(cell_state(vault, c, app)) for c in concerns]
        lines.append(row(link(app.name, title(app)), *states))
    return "\n".join(lines)


def unexamined_cells(vault, app):
    return sum(1 for c in vault.of_type("concern") if cell_state(vault, c, app).startswith("unexamined"))


def settled_contracts(vault, app):
    mine = [c for c in vault.contracts if c.page is app or app in vault.consumers(c)]
    settled = [c for c in mine if c.fact("State") in ("decided", "fact")]
    return len(settled), len(mine)


def _stage_rank(app, order):
    stage = app.meta.get("stage")
    return order.get(stage, len(order)) if isinstance(stage, str) else len(order)


def where_it_stands(vault, page):
    order = {stage: i for i, stage in enumerate(schema.ENUMS["stage"])}
    laddered = [a for a in vault.apps if a.meta.get("change") in schema.LADDERED_CHANGES]
    laddered.sort(key=lambda a: (_stage_rank(a, order), a.id))
    out = []
    if laddered:
        out += ["**Where each app has got to**", "",
                "| App | Step reached | Open questions holding it up | Topics nobody has looked at | Contracts settled |",
                "|---|---|---|---|---|"]
        for app in laddered:
            done, total = settled_contracts(vault, app)
            out.append(row(link(app.name, title(app)), plainwords.stage_word(app.meta.get("stage", "")),
                           str(len(blocking_unknowns(vault, app))), str(unexamined_cells(vault, app)), f"{done} of {total}"))
    else:
        out.append("**Where each app has got to:** no app is being built or changed yet")
    handed = [a for a in vault.apps if schema.HANDED_OFF_RE.match(str(a.meta.get("handed_off", "")))]
    if handed:
        out += ["", "**Handed to its team:** " + "; ".join(f"{plain_link(a.name, title(a))} ({a.meta['handed_off']})" for a in handed)]
    out.append("")
    open_unknowns = [u for u in vault.unknowns if u.fact("State") == "open"]
    if open_unknowns:
        out += ["**Open questions**", "", "| Question | Who answers | Answer needed by | Holds up |", "|---|---|---|---|"]
        for unknown in open_unknowns:
            blocks = unknown.facts.get("Blocks")
            targets = [link(l.target or unknown.page.name, l.label or l.anchor or l.target, l.anchor)
                       for l in (blocks.links if blocks else ())]
            out.append(row(link(unknown.page.name, trace.named(unknown.name, unknown.id), unknown.heading),
                           cell(unknown.fact("Owner")), unknown.fact("Ask by"), ", ".join(targets) or "nothing yet"))
    else:
        out.append("**Open questions:** none")
    out.append("")
    dates = sorted(str(s.meta.get("date", "")) for s in vault.sessions if s.meta.get("date"))
    out.append(f"**Last session:** {dates[-1] if dates else 'none recorded'}")
    if vault.of_type("epic"):
        gaps = len(trace.report(vault).gaps)
        index = vault.by_id.get("epics")
        where = f", listed on {plain_link(index[0].name, title(index[0]))}" if index else ""
        out.append("")
        out.append(f"**Gaps in the planned work:** {gaps}{where}")
        out.append("")
        out.append("**Build progress:** tracked in each team's tickets, not in this vault")
    return "\n".join(out)


def plain_link(target, label):
    """A wikilink outside a table, where the pipe needs no escape."""
    return f"[[{target}|{label}]]"


def id_link(vault, item_id):
    """A table-safe link to whatever an ID names, or the bare ID if it names nothing (E207 reports that)."""
    pages = vault.by_id.get(item_id)
    if pages:
        page = pages[0]
        label = title(page) if page.type == "app-building-blocks" else f"{item_id} {title(page)}"
        return link(page.name, cell(label))
    item = vault.item(item_id)
    if item is not None:
        return link(item.page.name, cell(f"{item.id} {item.name}"), item.heading)
    if item_id in vault.row_ids:
        return link(vault.row_ids[item_id][0].name, item_id)
    return item_id


def epic_table(epics):
    if not epics:
        return "none"
    rows = [row(link(e.name, cell(f"{e.id} {title(e)}")), cell(str(e.meta.get("owner", ""))), str(e.meta.get("state", "")))
            for e in epics]
    return "\n".join(["| Epic | Owner | State |", "|---|---|---|"] + rows)


def epics_for_app(vault, page):
    return epic_table([e for e in trace.epics(vault) if page.id in trace.listed(e, "apps")])


def delivered_by(vault, page):
    return epic_table([e for e in trace.epics(vault) if page.id in trace.listed(e, "delivers")])


TRACE_LISTS = (("Apps", "apps"), ("Delivers", "delivers"), ("Consumes", "consumes"), ("Flows", "flows"),
               ("Depends on", "depends_on"))


def traces_to(vault, page):
    rows = []
    for label, key in TRACE_LISTS:
        ids = trace.listed(page, key)
        rows.append(row(label, ", ".join(id_link(vault, i) for i in ids) or "none"))
    concerns = []
    for name in sorted(trace.ac_markers(page)):
        found = vault.by_id.get(f"concern-{name}")
        concerns.append(link(found[0].name, cell(title(found[0]))) if found else f"[{name}] matches no concern page")
    rows.append(row("Concerns", ", ".join(concerns) or "none"))
    return "\n".join(["| Traces to | Items |", "|---|---|"] + rows)


def traceability(vault, page):
    result = trace.report(vault)
    if not result.checked:
        return "**Gaps in the planned work:** nothing to check yet."
    passes = f"{result.passed} {'check passes' if result.passed == 1 else 'checks pass'}"
    if not result.gaps:
        return f"**Gaps in the planned work:** none. {passes}."
    count = len(result.gaps)
    lines = [f"**Gaps in the planned work:** {count}. {passes}.", "",
             "| Item | What is missing | Check |", "|---|---|---|"]
    for gap in result.gaps:
        lines.append(row(link(gap.page.name, cell(gap.label or gap.subject), gap.anchor), cell(gap.message), gap.rule))
    return "\n".join(lines)


# ------------------------------------------------------------------ diagrams

def mermaid_fence(lines):
    return ["```mermaid", *lines, "```"]


def node_link(node):
    """A table-safe link to the page a node stands for, or its name for an external provider."""
    if node.page is None:
        return cell(diagrams.safe_label(node.ref, node.key))
    return link(node.page.name, cell(diagrams.safe_label(title(node.page), node.page.name)))


def left_out_table(count, header, rows):
    """The table under a diagram that lists what the budget kept out of it."""
    if not rows:
        return []
    return ["", f"**Not drawn, to keep the diagram readable (at most {schema.FLOWCHART_BUDGET} boxes):** {count}", "",
            f"| Not drawn | {header} |", "|---|---|", *rows]


def skipped_table(skipped):
    """The table under a diagram that names each contract it could not draw, and why."""
    if not skipped:
        return []
    rows = [row(cell(diagrams.safe_label(cid, "contract")), cell(diagrams.safe_label(why, "unknown"))) for cid, why in skipped]
    return ["", f"**Contracts not drawn:** {len(skipped)}", "", "| Contract | Why not drawn |", "|---|---|", *rows]


def graph_block(graph, direction="LR", groups=(), reserved=0):
    drawn, left_out = diagrams.fit(graph, schema.FLOWCHART_BUDGET, reserved)
    rows = [row(node_link(n), cell(", ".join(diagrams.overflow_contracts(graph, n)) or "none")) for n in left_out]
    fence = mermaid_fence(diagrams.flowchart(drawn, direction, groups)) + ["", diagrams.key_line(drawn)] if graph.nodes else []
    return fence + left_out_table(len(left_out), "Contracts", rows) + skipped_table(graph.skipped)


def context_map(vault, page):
    graph = diagrams.context_graph(vault)
    if not graph.nodes and not graph.skipped:
        return "none"
    return "\n".join(graph_block(graph)).lstrip("\n")


def system_context(vault, page):
    graph = diagrams.context_graph(vault, after=True)
    retired = [a for a in vault.apps if a.meta.get("change") == "retired"]
    if not graph.nodes and not graph.skipped and not retired:
        return "none"
    scope = diagrams.safe_label(vault.config.get("title", ""), "In scope")
    apps = [n.key for n in graph.nodes if n.page is not None]
    out = graph_block(graph, groups=[("scope", scope, apps)], reserved=1)
    if retired:
        out += ["", "**Retired, not drawn:** " + ", ".join(plain_link(a.name, diagrams.safe_label(title(a), a.name)) for a in retired)]
    return "\n".join(out).lstrip("\n")


def app_context(vault, page):
    return "\n".join(graph_block(diagrams.app_graph(vault, page)))


def capability_block(groups):
    """One diagram for these domain groups, each a subgraph, with the left-out table under it."""
    nodes = [n for _, members in groups for n in members]
    graph = diagrams.Graph(tuple(sorted(nodes, key=lambda n: n.key)), ())
    drawn, left_out = diagrams.fit(graph, schema.FLOWCHART_BUDGET, reserved=len(groups))
    keys = diagrams.domain_keys([domain for domain, _ in groups])
    subgraphs = [(keys[domain], diagrams.safe_label(domain, diagrams.NO_DOMAIN), [n.key for n in members])
                 for domain, members in groups]
    rows = [row(node_link(n), cell(str(n.page.meta.get("change", "")))) for n in left_out]
    return (mermaid_fence(diagrams.flowchart(drawn, "TB", subgraphs)) + ["", diagrams.key_line(drawn)]
            + left_out_table(len(left_out), "Change", rows))


def capability_map(vault, page):
    groups = diagrams.capability_groups(vault)
    if not groups:
        return "none"
    if sum(len(members) for _, members in groups) + len(groups) <= schema.FLOWCHART_BUDGET:
        return "\n".join(capability_block(groups))
    out = []
    for domain, members in groups:  # over budget: one diagram per domain
        out += ([""] if out else []) + [f"**{diagrams.safe_label(domain, diagrams.NO_DOMAIN)}**", ""]
        out += capability_block([(domain, members)])
    return "\n".join(out)


# ------------------------------------------------------------------ progress

# The session `planner next` suggests, as the Next session column says it; "probe" is a mode name, not a reader's word.
MODE_WORDS = {"probe": "Chase the answer to", "discover": "Discover", "shape": "Shape", "grill": "Grill",
              "boundary": "Boundary", "epics": "Epics"}


def subject_name(vault, item_id):
    """What a reader calls the thing an ID names, with the ID as a tag; the bare ID when it names nothing."""
    pages = vault.by_id.get(item_id)
    if pages:
        return trace.named(title(pages[0]), item_id)
    item = vault.item(item_id)
    return trace.named(item.name, item_id) if item is not None else item_id


def next_cell(vault, entry):
    """What the Next session column says for one progress.Row."""
    if entry.rule == 7:
        return f"waits on {cell(subject_name(vault, entry.subject))}"
    if entry.mode == "none":
        return "none"
    word = MODE_WORDS.get(entry.mode, entry.mode)
    return f"{word}: {cell(subject_name(vault, entry.subject))}" if entry.subject else word


def unknown_cell(entry):
    if entry.oldest is None:
        return "none"
    target = link(entry.oldest.page.name, trace.named(entry.oldest.name, entry.oldest.id), entry.oldest.heading)
    return f"{target}, open since {entry.opened}" if entry.opened else f"{target}, open since: not recorded"


def progress_map(vault, page):
    as_of = progress.last_session_date(vault)
    rows = progress.grid(vault, as_of)
    if not rows:
        return "none"
    when = (f"**How sure each app's items are,** as of {as_of} (the last session)" if as_of
            else "**How sure each app's items are:** no session yet, so no question counts as overdue")
    out = [when, "", "| App | Step reached | Early ideas | Assumed | Confirmed | Decided | Oldest open question | Next session |",
           "|---|---|---|---|---|---|---|---|"]
    for r in rows:
        out.append(row(link(r.app.name, cell(title(r.app))), plainwords.stage_word(r.stage) if r.stage else "-",
                       *(str(n) for n in r.mix[:3]), progress.decided_text(r), unknown_cell(r), next_cell(vault, r)))
    return "\n".join(out)


# ------------------------------------------------------------------ questions

def undisposed_questions(vault, page):
    """The coverage line, then every pending copy and reviewer question (undisposed, or asked and still waiting):
    the to-do list above the record. The line counts exactly the rows the table lists."""
    found = questions.dispositions(vault)
    copies = [d for d in found if d.pending]
    lines = [row(d.copy.id, d.label, vault.catalog.area_label(d.copy.entry.area), d.copy.entry.severity, id_link(vault, d.copy.subject.id),
                 cell(d.copy.entry.question)) for d in copies]
    reviewers = questions.reviewer_rows(vault)
    for r in reviewers:
        answer = questions.reviewer_answer(vault, r)
        if questions.reviewer_pending(vault, r):
            lines.append(row(r.copy, questions.state_label(r.state, answer["valid"]), vault.catalog.area_label(r.area),
                             answer["severity"], "a reviewer's question", cell(answer["question"] or "")))
    opened = sum(1 for r in reviewers if questions.reviewer_open(vault, r))
    line = questions.coverage_line(vault, len(found), sum(1 for d in found if d.undisposed), opened,
                                   questions.asked_count(vault, found, reviewers))
    out = [f"**Questions:** {line}."]
    if lines:
        out += ["", "| Ref | Status | Area | How serious | About | Question |", "|---|---|---|---|---|---|"] + lines
    return "\n".join(out)


def allocation_block(vault, page):
    """One row per functional requirement, one column per app that carries any: each cell is that app's share,
    with the contracts it goes through. A blank row is a requirement nobody owns yet."""
    apps, lines = allocation.matrix(vault)
    if not lines:
        return "**Who does what:** no requirement is firm enough to split between the apps yet."
    open_ = sum(1 for _, shares in lines if not shares)
    noun = "requirement is" if len(lines) == 1 else "requirements are"
    left = "none is waiting for an app" if not open_ else f"{open_} still {'has' if open_ == 1 else 'have'} no app"
    head = f"**Who does what:** {len(lines)} {noun} firm enough to split between the apps (assumed or later); {left}."
    out = [head, "", row("Requirement", *[link(a.name, cell(title(a))) for a in apps]) if apps else row("Requirement"),
           "|" + "---|" * (len(apps) + 1)]
    for req, shares in lines:
        out.append(row(link(req.page.name, cell(trace.named(req.name, req.id)), req.heading), *[cell(shares.get(a.id, "")) for a in apps]))
    return "\n".join(out)


GENERATORS = {
    "where-it-stands": where_it_stands,
    "concern-matrix": concern_matrix,
    "unknowns-index": unknowns_index,
    "contracts-consumed": contracts_consumed,
    "traceability": traceability,
    "epics-for-app": epics_for_app,
    "traces-to": traces_to,
    "delivered-by": delivered_by,
    "context-map": context_map,
    "system-context": system_context,
    "app-context": app_context,
    "capability-map": capability_map,
    "progress-map": progress_map,
    "undisposed-questions": undisposed_questions,
    "allocation": allocation_block,
}


# ------------------------------------------------------------ page rewrite

def render_page(vault, page, discard_edits=False):
    """(new text or None, changed block names, discarded (name, old content) pairs, refusals)."""
    lines = page.text.split("\n")
    out, changed, discarded, refusals = [], [], [], []
    cursor = 0
    for block in sorted(page.blocks, key=lambda b: b.start):
        out.extend(lines[cursor:block.start - 1])
        current = normalize(block.content)
        new = block_content(vault, page, block.name) if block_allowed(page, block.name) else None
        edited = bool(current) and block_hash(current) != block.sha
        if new is None or (edited and not discard_edits):
            if edited:
                refusals.append(Finding(page.path, block.start, "E401",
                                        f"Someone edited the '{block.name}' block by hand, so render left the page alone.",
                                        "Undo the edit and change the source pages instead, or run planner render --discard-edits."))
            out.extend(lines[block.start - 1:block.end])
        else:
            if edited:
                discarded.append((block.name, current))
            if new != current or block.sha != block_hash(new):
                changed.append(block.name)
            out.append(OPEN.format(name=block.name, sha=block_hash(new)))
            out.extend(new.split("\n") if new else [])
            out.append(CLOSE.format(name=block.name))
        cursor = block.end
    out.extend(lines[cursor:])
    text = "\n".join(out)
    return (text if text != page.text else None), changed, discarded, refusals


def render_vault(vault, discard_edits=False):
    """(dict path -> new text, list of (path, block) changed, discarded, refusals).

    All or nothing: if any page has a parse error, nothing is rendered.
    """
    blocking = [Finding(p.path, e.line, e.code, e.message, e.fix) for p in vault.pages for e in p.errors]
    if blocking:
        return {}, [], [], blocking
    texts, changed, discarded, refusals = {}, [], [], []
    for page in vault.pages:
        text, names, dropped, refused = render_page(vault, page, discard_edits)
        refusals.extend(refused)
        if text is not None:
            texts[page.path] = text
        changed.extend((page.path, n) for n in names)
        discarded.extend((page.path, n, old) for n, old in dropped)
    if refusals:
        return {}, [], [], refusals
    return texts, changed, discarded, []
