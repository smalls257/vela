"""Read-only answers about the vault, for /ask and for people. Pure: the CLI passes the date.

Every answer is a dict json.dumps can write. An ID the vault does not hold comes
back as {"id": ..., "not_found": true}. Nothing is guessed: no near match, no
change of case.
"""
import re

from planner import model, override, progress, schema

LIST_FIELDS = ("apps", "delivers", "consumes", "flows", "depends_on", "sources")
ROW_KINDS = ((schema.GOAL_ID_RE, "goal"), (schema.CONSTRAINT_ID_RE, "constraint"), (schema.SOURCE_ID_RE, "source"))


def text(value):
    return value.strip() if isinstance(value, str) else ""


def text_list(value):
    return [v for v in value if isinstance(v, str)] if isinstance(value, list) else []


def decision_links(bullets):
    return [link.target for bullet in bullets for link in bullet.links if link.target]


def not_found(item_id):
    return {"id": item_id, "not_found": True}


def blocked_by(vault, unit_id):
    return [u.id for u in model.blockers(vault).get(unit_id, [])]


def page_answer(vault, pages, item_id):
    page = pages[0]
    return {
        "id": item_id,
        "kind": page.type,
        "page": page.path,
        "heading": text(page.meta.get("title")) or page.name,
        "state": text(page.meta.get("state")),
        "owner": text(page.meta.get("owner")),
        "sources": text_list(page.meta.get("sources")),
        "decision": decision_links(page.page_bullets("Decision")),
        "dissent": [b.value for b in page.page_bullets("Dissent")],
        "blocked_by": blocked_by(vault, item_id),
        "link": f"[[{page.name}|{item_id}]]",
        "also": [p.path for p in pages[1:]],
        **override.summary(page),
    }


def item_answer(vault, items):
    item = items[0]
    decision = item.facts.get("Decision")
    source = item.fact("Source")
    return {
        "id": item.id,
        "kind": item.kind,
        "page": item.page.path,
        "heading": item.heading,
        "state": item.fact("State"),
        "owner": item.fact("Owner") or text(item.page.meta.get("owner")),
        "sources": [source] if source else [],
        "decision": decision_links([decision] if decision else []),
        "dissent": [item.fact("Dissent")] if item.fact("Dissent") else [],
        "blocked_by": blocked_by(vault, item.id),
        "link": f"[[{item.page.name}#{item.heading}|{item.id}]]",
        "also": [f"{i.page.path}:{i.line}" for i in items[1:]],
        **override.summary(item.page, item.id),
    }


def row_cells(page, line):
    for table in page.tables:
        for row, row_line in zip(table.rows, table.row_lines):
            if row_line == line:
                return row
    return ()


def row_answer(vault, item_id):
    page, line = vault.row_ids[item_id]
    kind = next(k for pattern, k in ROW_KINDS if pattern.match(item_id))
    cells = row_cells(page, line)
    state = cells[3] if kind == "goal" and len(cells) > 3 else ""
    owner = cells[2] if kind == "source" and len(cells) > 2 else text(page.meta.get("owner"))
    return {
        "id": item_id,
        "kind": kind,
        "page": page.path,
        "heading": cells[1] if len(cells) > 1 else "",
        "state": state,
        "owner": owner,
        "sources": text_list(page.meta.get("sources")),
        "decision": decision_links(page.page_bullets("Decision")),
        "dissent": [b.value for b in page.page_bullets("Dissent")],
        "blocked_by": blocked_by(vault, item_id),
        "link": f"[[{page.name}|{item_id}]]",
        "also": [],
        **override.summary(page),
    }


def get(vault, item_id):
    """The item's page, heading, state, owner, sources and decision link."""
    if vault.items.get(item_id):
        return item_answer(vault, vault.items[item_id])
    if vault.by_id.get(item_id):
        return page_answer(vault, vault.by_id[item_id], item_id)
    if item_id in vault.row_ids:
        return row_answer(vault, item_id)
    return not_found(item_id)


def points_at(vault, link, page, item_id):
    target = vault.resolve(link, page)
    if target is None:
        return False
    item = vault.item(item_id)
    if item is not None:
        first = link.anchor.split()[0] if link.anchor.split() else ""
        return target is item.page and first == item_id
    return target.id == item_id


def definition_lines(vault, item_id):
    """(path, line) pairs where the ID is defined, so a page does not cite itself."""
    lines = {(i.page.path, i.line) for i in vault.items.get(item_id, [])}
    if item_id in vault.row_ids:
        page, line = vault.row_ids[item_id]
        lines.add((page.path, line))
    for page in vault.by_id.get(item_id, []):
        for number, raw in enumerate(page.text.split("\n"), 1):
            if re.match(rf"\s*id:\s*[\"']?{re.escape(item_id)}[\"']?\s*$", raw) or raw.startswith(f"# {item_id}"):
                lines.add((page.path, number))
    return lines


def mention_lines(page, item_id):
    """Line numbers outside code fences that hold the exact ID as a whole token."""
    pattern = re.compile(rf"(?<![\w.-]){re.escape(item_id)}(?![\w-]|\.\w)")
    fence, hits = None, []
    for number, raw in enumerate(page.text.split("\n"), 1):
        opener = re.match(r"^\s*(```+|~~~+)", raw)
        if fence:
            if raw.strip().startswith(fence):
                fence = None
        elif opener:
            fence = opener.group(1)
        elif pattern.search(raw):
            hits.append(number)
    return hits


def refs(vault, item_id):
    """Every page line that links to the ID, and every epic list that names it."""
    if get(vault, item_id).get("not_found"):
        return not_found(item_id)
    found = []
    for page in vault.pages:
        for link in page.links:
            if points_at(vault, link, page, item_id):
                found.append({"page": page.path, "line": link.line, "via": "link"})
        for key in LIST_FIELDS:
            if item_id in text_list(page.meta.get(key)):
                found.append({"page": page.path, "line": model.meta_line(page, key), "via": key})
    seen = {(r["page"], r["line"]) for r in found}
    skip = definition_lines(vault, item_id)
    for page in vault.pages:
        for line in mention_lines(page, item_id):
            if (page.path, line) not in seen and (page.path, line) not in skip:
                found.append({"page": page.path, "line": line, "via": "mention"})
    unique = {(r["page"], r["line"], r["via"]): r for r in found}
    return {"id": item_id, "refs": [unique[k] for k in sorted(unique)]}


def find(vault, words):
    """Page titles, item headings and goal, constraint and source rows that hold every word, ignoring case."""
    wanted = [w.lower() for w in words if w.strip()]
    matches = []
    if wanted:
        for page in vault.pages:
            title = text(page.meta.get("title"))
            if title and all(w in title.lower() for w in wanted):
                matches.append({"id": page.id, "kind": page.type, "page": page.path, "line": 1, "match": title})
        for items in vault.items.values():
            for item in items:
                if all(w in item.heading.lower() for w in wanted):
                    matches.append({"id": item.id, "kind": item.kind, "page": item.page.path, "line": item.line,
                                    "match": item.heading})
        for item_id, (page, line) in vault.row_ids.items():
            cells = row_cells(page, line)
            if len(cells) > 1 and all(w in " ".join(cells[1:]).lower() for w in wanted):
                kind = next(k for pattern, k in ROW_KINDS if pattern.match(item_id))
                matches.append({"id": item_id, "kind": kind, "page": page.path, "line": line, "match": cells[1]})
    matches.sort(key=lambda m: (m["page"], m["line"]))
    answer = {"words": words, "matches": matches}
    if not matches:
        answer["not_found"] = True
    return answer


def status(vault, today):
    """The planner status grid as data."""
    apps = []
    for row in progress.grid(vault, today):
        inkling, assumption, fact, decided = row.mix
        apps.append({
            "app": row.app.id, "title": text(row.app.meta.get("title")) or row.app.name, "stage": row.stage,
            "inkling": inkling, "assumption": assumption, "fact": fact, "decided": decided,
            "decided_by_override": row.by_override,
            "oldest_unknown": row.oldest.id if row.oldest else None, "opened": row.opened or None,
            "next": row.mode, "subject": row.subject, "reason": row.reason,
        })
    return {"today": today, "apps": apps}
