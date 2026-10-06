"""Pages to a vault model, built once. Pure: no disk, clock or network."""
from dataclasses import dataclass, field

from planner import schema
from planner.parse import links_in


@dataclass(frozen=True, order=True)
class Finding:
    path: str
    line: int
    code: str
    message: str
    fix: str

    @property
    def is_error(self):
        return self.code.startswith("E")

    def format(self):
        return f"{self.path}:{self.line}: {self.code} {self.message} Fix: {self.fix}"


@dataclass
class Item:
    """A heading item: a contract, unknown, risk, functional requirement, party or stored value."""
    id: str
    kind: str  # "contract" | "unknown" | "risk" | "requirement" | "party" | "stored-value"
    name: str  # heading text after the ID
    heading: str  # full heading text, which is the anchor
    page: object
    line: int
    facts: dict  # label -> Bullet (first one wins)

    def fact(self, label):
        bullet = self.facts.get(label)
        return bullet.value.strip() if bullet else ""


@dataclass
class Cell:
    concern: object  # the concern Page
    app: str  # app page basename
    state: str
    text: str  # the remaining columns joined with " | "
    links: tuple
    line: int


@dataclass
class Vault:
    config: dict
    pages: list
    other_names: set = field(default_factory=set)
    by_name: dict = field(default_factory=dict)  # lower-case basename -> [Page]
    by_id: dict = field(default_factory=dict)  # page id -> [Page]
    items: dict = field(default_factory=dict)  # item id -> [Item]
    row_ids: dict = field(default_factory=dict)  # goal/constraint/source id -> (Page, line)
    cells: list = field(default_factory=list)

    def page(self, name):
        found = self.by_name.get(name.lower())
        return found[0] if found else None

    def of_type(self, page_type):
        return [p for p in self.pages if p.type == page_type]

    def item(self, item_id):
        found = self.items.get(item_id)
        return found[0] if found else None

    @property
    def apps(self):
        return sorted(self.of_type("app-building-blocks"), key=lambda p: p.id)

    @property
    def contracts(self):
        return sorted((i[0] for i in self.items.values() if i[0].kind == "contract"), key=lambda i: i.id)

    @property
    def unknowns(self):
        return sorted((i[0] for i in self.items.values() if i[0].kind == "unknown"), key=lambda i: i.id)

    @property
    def risks(self):
        return sorted((i[0] for i in self.items.values() if i[0].kind == "risk"), key=lambda i: i.id)

    @property
    def requirements(self):
        return sorted((i[0] for i in self.items.values() if i[0].kind == "requirement"), key=lambda i: i.id)

    @property
    def parties(self):
        return sorted((i[0] for i in self.items.values() if i[0].kind == "party"), key=lambda i: i.id)

    @property
    def stored_values(self):
        return sorted((i[0] for i in self.items.values() if i[0].kind == "stored-value"), key=lambda i: i.id)

    @property
    def sessions(self):
        return sorted(self.of_type("session"), key=lambda p: p.name)

    def resolve(self, link, from_page):
        """The page a link points at, or None."""
        return from_page if not link.target else self.page(link.target)

    def consumers(self, contract):
        """App pages linked from a contract's Consumers bullet."""
        bullet = contract.facts.get("Consumers")
        if not bullet:
            return []
        out = []
        for link in bullet.links:
            target = self.resolve(link, contract.page)
            if target is not None and target.type == "app-building-blocks" and target not in out:
                out.append(target)
        return out

    def known_ids(self):
        return set(self.by_id) | set(self.items) | set(self.row_ids)


ITEM_KINDS = {"CON": "contract", "UNK": "unknown", "R": "risk", "CAP": "requirement", "PTY": "party", "SV": "stored-value"}


def build(pages, config, other_names=()):
    vault = Vault(config=config, pages=list(pages), other_names={n.lower() for n in other_names})
    for page in vault.pages:
        vault.by_name.setdefault(page.name.lower(), []).append(page)
        if page.id:
            vault.by_id.setdefault(page.id, []).append(page)
        _collect_items(vault, page)
        _collect_rows(vault, page)
    for concern in vault.of_type("concern"):
        _collect_cells(vault, concern)
    return vault


def _collect_items(vault, page):
    for heading in page.headings:
        first = heading.text.split()[0] if heading.text.split() else ""
        if heading.level != 3 or not schema.ITEM_ID_RE.match(first):
            continue
        kind = ITEM_KINDS[first.split("-")[0]]
        facts = {}
        for bullet in page.bullets:
            if bullet.item == first and not bullet.generated and bullet.line > heading.line:
                facts.setdefault(bullet.label, bullet)
        name = heading.text[len(first):].strip()
        vault.items.setdefault(first, []).append(Item(first, kind, name, heading.text, page, heading.line, facts))


def _row_id_pattern(page, header):
    """The ID pattern a table's rows may register, or None. Only the goals, constraints and
    sources tables register IDs; a session's Changes table only mentions them."""
    head = tuple(header)
    if head[:len(schema.GOALS_HEADER)] == schema.GOALS_HEADER:
        return schema.GOAL_ID_RE
    if head[:len(schema.CONSTRAINTS_HEADER)] == schema.CONSTRAINTS_HEADER:
        return schema.CONSTRAINT_ID_RE
    if page.type == "sources" and head[:len(schema.SOURCES_HEADER)] == schema.SOURCES_HEADER:
        return schema.SOURCE_ID_RE
    return None


def _collect_rows(vault, page):
    for table in page.tables:
        if table.generated or not table.header:
            continue
        pattern = _row_id_pattern(page, table.header)
        if pattern is None:
            continue
        for row, line in zip(table.rows, table.row_lines):
            row_id = row[0].strip() if row else ""
            if pattern.match(row_id):
                vault.row_ids.setdefault(row_id, (page, line))


def cell_table(page):
    for table in page.tables:
        if not table.generated and tuple(table.header[:2]) == schema.CELLS_HEADER:
            return table
    return None


def _collect_cells(vault, concern):
    table = cell_table(concern)
    if table is None:
        return
    for row, line in zip(table.rows, table.row_lines):
        app_links = links_in(row[0], line) if row else ()
        app = app_links[0].target if app_links else ""
        state = row[1].strip() if len(row) > 1 else ""
        text = " | ".join(c for c in row[2:]).strip()
        vault.cells.append(Cell(concern, app, state, text, links_in(" ".join(row[2:]), line), line))


# ------------------------------------------------- what blocks what, shared by rules, render and progress

def meta_line(page, key):
    """Line number of `key:` in the frontmatter, or 1."""
    lines = page.text.split("\n")
    for n, line in enumerate(lines[1:], start=2):
        if line.strip() == "---":
            break
        if line.startswith(f"{key}:"):
            return n
    return 1


def goal_rows_at(page, state):
    """(row id, line) of each goal row whose State cell says `state`."""
    for table in page.tables:
        if table.generated or tuple(table.header)[:4] != schema.GOALS_HEADER:
            continue
        for row, line in zip(table.rows, table.row_lines):
            if len(row) > 3 and row[3] == state:
                yield row[0], line


def decided_goal_rows(page):
    return goal_rows_at(page, "decided")


def unit_state(vault, link, from_page):
    """(unit id, state, page, line) of what a link points at, or None."""
    target = vault.resolve(link, from_page)
    if target is None:
        return None
    parts = link.anchor.split() if link.anchor else []
    first = parts[0].upper() if parts else ""
    item = vault.item(first) if first else None
    if item is not None and item.page is target:
        return item.id, item.fact("State"), item.page, item.line
    return target.id, target.meta.get("state", ""), target, meta_line(target, "state")


def is_requirement(vault, unit_id):
    item = vault.item(unit_id)
    return item is not None and item.kind == "requirement"


def blocked_units(vault, link, from_page):
    """Every (id, state, page, line) a Blocks link holds up. An item anchor means that
    item. A page link means the page and each item on it, so linking the page
    cannot dodge the gate."""
    target = vault.resolve(link, from_page)
    if target is None:
        return
    found = unit_state(vault, link, from_page)
    if found and found[0] != target.id:
        yield found
        if is_requirement(vault, found[0]):
            # An FR sits on a capability page. Blocking it holds the page's own decision too (E316 before FRs were items).
            yield target.id, target.meta.get("state", ""), target, meta_line(target, "state")
        return
    if found:
        yield found
    for contract in (*vault.contracts, *vault.requirements):
        if contract.page is target:
            yield contract.id, contract.fact("State"), contract.page, contract.line
    for row_id, line in decided_goal_rows(target):
        yield row_id, "decided", target, line


def open_unknowns(vault):
    return [u for u in vault.unknowns if u.fact("State") == "open"]


def blockers(vault):
    """{unit id: [open unknowns that block it]}, each list in unknown-ID order."""
    out = {}
    for unknown in open_unknowns(vault):
        blocks = unknown.facts.get("Blocks")
        for link in blocks.links if blocks else ():
            for unit_id, _, _, _ in blocked_units(vault, link, unknown.page):
                if unknown not in out.setdefault(unit_id, []):
                    out[unit_id].append(unknown)
    return out


def app_page_names(app):
    """Lower-case basenames of an app's building-blocks page and its runtime sibling."""
    names = {app.name.lower()}
    if app.name.endswith("-building-blocks"):  # a page named otherwise has no runtime sibling to match
        names.add((app.name[: -len("-building-blocks")] + "-runtime").lower())
    return names


def blocking_unknowns(vault, app):
    """Open unknowns whose **Blocks:** links the app's building-blocks or runtime page."""
    names = app_page_names(app)
    out = []
    for unknown in open_unknowns(vault):
        blocks = unknown.facts.get("Blocks")
        for link in blocks.links if blocks else ():
            target = vault.resolve(link, unknown.page)
            if target is not None and target.name.lower() in names:
                out.append(unknown)
                break
    return out
