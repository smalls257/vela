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
    """A heading item: a contract, unknown or risk."""
    id: str
    kind: str  # "contract" | "unknown" | "risk"
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


ITEM_KINDS = {"CON": "contract", "UNK": "unknown", "R": "risk"}


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


def _collect_rows(vault, page):
    for table in page.tables:
        if table.generated or not table.header or table.header[0] != "ID":
            continue
        for row, line in zip(table.rows, table.row_lines):
            row_id = row[0].strip() if row else ""
            if schema.GOAL_ID_RE.match(row_id) or schema.CONSTRAINT_ID_RE.match(row_id) or schema.SOURCE_ID_RE.match(row_id):
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
