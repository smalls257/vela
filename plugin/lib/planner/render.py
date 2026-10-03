"""Vault model to generated block text. Pure and deterministic.

Each block is computed from the model only, never from another block. Output
holds links and numbers, dates and never ages, so two runs give equal bytes.
"""
import hashlib

from planner import schema
from planner.model import Finding

OPEN = "<!-- generated:{name} sha={sha}: do not edit, run planner render -->"
CLOSE = "<!-- /generated:{name} -->"


def normalise(content):
    lines = [line.rstrip() for line in content.replace("\r\n", "\n").split("\n")]
    while lines and not lines[0]:
        lines.pop(0)
    while lines and not lines[-1]:
        lines.pop()
    return "\n".join(lines)


def block_hash(content):
    return hashlib.sha256(normalise(content).encode("utf-8")).hexdigest()[:8]


def block_allowed(page, name):
    where = schema.BLOCKS.get(name)
    if where is None:
        return False
    if where.startswith("type:"):
        return page.type == where[len("type:"):]
    return page.id == where


def cell(text):
    """Make text safe inside a Markdown table cell."""
    return text.replace("|", "\\|")


def row(*cells):
    return "| " + " | ".join(cells) + " |"


def link(target, label, anchor=""):
    inner = f"{target}#{anchor}" if anchor else target
    return f"[[{inner}\\|{label}]]"


def title(page):
    return str(page.meta.get("title") or page.name)


# --------------------------------------------------------------- the blocks

def block_content(vault, page, name):
    return normalise(GENERATORS[name](vault, page))


def contracts_consumed(vault, page):
    rows = []
    for contract in vault.contracts:
        if page not in vault.consumers(contract):
            continue
        provider = cell(contract.fact("Provider")) or link(contract.page.name, title(contract.page))
        rows.append(row(link(contract.page.name, contract.heading, contract.heading), provider,
                        cell(contract.fact("Change policy")), contract.fact("State")))
    if not rows:
        return "none"
    return "\n".join(["| Contract | Provider | Change policy | State |", "|---|---|---|---|"] + rows)


def _here(item, page):
    """Link target for an item: "" when it sits on the page being rendered."""
    return "" if item.page is page else item.page.name


def unknowns_index(vault, page):
    rows = []
    for unknown in vault.unknowns:
        rows.append(row(link(_here(unknown, page), unknown.id, unknown.heading), cell(unknown.name),
                        cell(unknown.fact("Owner")), unknown.fact("State"), unknown.fact("Ask by")))
    for risk in vault.risks:
        rows.append(row(link(_here(risk, page), risk.id, risk.heading), cell(risk.name),
                        cell(risk.fact("Owner")), risk.fact("State"), ""))
    if not rows:
        return "none"
    return "\n".join(["| ID | Name | Owner | State | Ask by |", "|---|---|---|---|---|"] + rows)


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
        states = [cell_state(vault, c, app) for c in concerns]
        lines.append(row(link(app.name, title(app)), *states))
    return "\n".join(lines)


def _app_pages(vault, app):
    names = {app.name.lower()}
    if app.name.endswith("-building-blocks"):  # a page named otherwise has no runtime sibling to match
        names.add((app.name[: -len("-building-blocks")] + "-runtime").lower())
    return names


def blocking_unknowns(vault, app):
    names = _app_pages(vault, app)
    out = []
    for unknown in vault.unknowns:
        if unknown.fact("State") != "open" or "Blocks" not in unknown.facts:
            continue
        for l in unknown.facts["Blocks"].links:
            target = vault.resolve(l, unknown.page)
            if target is not None and target.name.lower() in names:
                out.append(unknown)
                break
    return out


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
        out += ["**Apps on the ladder**", "",
                "| App | Stage | Blocking unknowns | Unexamined cells | Contracts decided or fact |",
                "|---|---|---|---|---|"]
        for app in laddered:
            done, total = settled_contracts(vault, app)
            out.append(row(link(app.name, title(app)), str(app.meta.get("stage", "")), str(len(blocking_unknowns(vault, app))),
                           str(unexamined_cells(vault, app)), f"{done} of {total}"))
    else:
        out.append("**Apps on the ladder:** none")
    out.append("")
    open_unknowns = [u for u in vault.unknowns if u.fact("State") == "open"]
    if open_unknowns:
        out += ["**Open unknowns**", "", "| Unknown | Owner | Ask by | Blocks |", "|---|---|---|---|"]
        for unknown in open_unknowns:
            blocks = unknown.facts.get("Blocks")
            targets = [link(l.target or unknown.page.name, l.label or l.anchor or l.target, l.anchor)
                       for l in (blocks.links if blocks else ())]
            out.append(row(link(unknown.page.name, unknown.id, unknown.heading), cell(unknown.fact("Owner")),
                           unknown.fact("Ask by"), ", ".join(targets) or "nothing"))
    else:
        out.append("**Open unknowns:** none")
    out.append("")
    dates = sorted(str(s.meta.get("date", "")) for s in vault.sessions if s.meta.get("date"))
    out.append(f"**Last session:** {dates[-1] if dates else 'none recorded'}")
    if vault.of_type("epic"):
        out.append("")
        out.append("**Delivery status:** not tracked in this vault")
    return "\n".join(out)


GENERATORS = {
    "where-it-stands": where_it_stands,
    "concern-matrix": concern_matrix,
    "unknowns-index": unknowns_index,
    "contracts-consumed": contracts_consumed,
}


# ------------------------------------------------------------ page rewrite

def render_page(vault, page, discard_edits=False):
    """(new text or None, changed block names, discarded (name, old content) pairs, refusals)."""
    lines = page.text.split("\n")
    out, changed, discarded, refusals = [], [], [], []
    cursor = 0
    for block in sorted(page.blocks, key=lambda b: b.start):
        out.extend(lines[cursor:block.start - 1])
        current = normalise(block.content)
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
