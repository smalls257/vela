"""The normalized records the checker reasons over. Pure data, no reading.

This is the Filter boundary of decision D7: the model builder and the explorer only ever see case tables and event
tables. Whether a table came from an OpenAPI/AsyncAPI spec or was written by hand on a contract page (a legacy or
vendor app with no spec) is recorded in `source` for the reader and nowhere else, so the semantics cannot come to
depend on the format that fed them.

Every record keeps what was written, even when it is wrong; the builder decides what is a finding. A field the
author left out is None, never a default: R0 says nothing is assumed.
"""
from dataclasses import dataclass, field


@dataclass(frozen=True)
class Problem:
    """Something a reader could not read (F10). `item` is the ID it belongs to, "" for a whole file, so the builder
    keeps only the problems of items the slice uses."""
    where: str
    text: str
    item: str = ""


@dataclass(frozen=True)
class Retries:
    max: int  # attempts in all, the first included
    on: tuple  # outcomes that are retried: case keys and "timeout"


@dataclass(frozen=True)
class Case:
    key: str
    status: str  # "409", or "ok" / "error" for a contract that is not HTTP
    emits: tuple = ()  # event IDs the provider publishes when it answers this way
    sets: tuple = ()  # ((entity, target), ...); target is a state, or ((from, to), ...) for a change that depends on where it starts
    when: tuple = ()  # ((entity, "in" | "not in", (state, ...)), ...): the provider answers this way only then

    @property
    def is_error(self):
        return self.status == "error" or (self.status.isdigit() and int(self.status) >= 400)


@dataclass(frozen=True)
class CaseTable:
    """One contract: the cases its provider can answer with, and how the call behaves."""
    id: str
    title: str  # "Place a hold"; read in traces as "asks Inventory to place a hold"
    provider: str  # app key
    cases: tuple
    timeout: object  # True, False, or None when not written
    retries: object  # Retries, or None for none
    idempotent: bool
    delivery: object  # for a call an outside app makes (a webhook): like an event's; None otherwise
    order: object
    source: str  # "specs/inventory.openapi.yaml" or "05-building-blocks/inventory-building-blocks.md:31"


@dataclass(frozen=True)
class EventTable:
    id: str
    title: str
    producer: object  # app key, or None when no send operation names one
    delivery: object  # "exactly-once" | "at-least-once" | "may-be-lost" | None
    order: object  # "any" | "per-producer" | "per:<field>" | None
    key_of: object  # entity a per:<field> ordering key identifies, or None
    subscribers: tuple  # ((app key, Retries or None), ...)
    source: str


@dataclass(frozen=True)
class App:
    key: str  # "order-service"
    title: str  # "Order service"
    outside: bool  # an outside party: answers from its contract alone (D6), never drawn


@dataclass(frozen=True)
class Entity:
    id: str
    slug: str
    title: str
    owner: object  # the app key that keeps it
    shared: object  # True, False, or None when not written
    initial: object
    final: tuple
    table: frozenset  # {(from, to, allowed by)}
    invariants: tuple  # ((text, line, expression), ...)
    where: str

    @property
    def states(self):
        found = {self.initial} if self.initial else set()
        found |= set(self.final)
        for a, b, _ in self.table:
            found |= {a, b}
        return found


@dataclass(frozen=True)
class FlowLine:
    line: int
    kind: str
    parts: tuple


@dataclass(frozen=True)
class Override:
    """`- **Override:** "F1 CON-012 timeout until 2026-12-01" by @lead on 2026-10-13: reason` on a flow page: it covers
    that finding, about that contract (or event, or entity) and case, on that flow, until the date and no longer."""
    code: str
    item: str
    case: str
    until: str
    text: str
    where: str


@dataclass(frozen=True)
class Flow:
    id: str
    title: str
    path: str
    lines: tuple  # FlowLine, in order
    overrides: tuple
    has_diagram: bool


@dataclass
class Catalog:
    """Everything the readers found, keyed by ID. Built once per run from the vault's files."""
    apps: dict = field(default_factory=dict)  # key -> App
    contracts: dict = field(default_factory=dict)  # CON id -> CaseTable
    events: dict = field(default_factory=dict)  # EVT id -> EventTable
    entities: dict = field(default_factory=dict)  # slug and id -> Entity
    flows: dict = field(default_factory=dict)  # FLO id -> Flow
    slices: list = field(default_factory=list)  # [slices.Slice], in order
    callers: set = field(default_factory=set)  # app keys that call a contract of the vault: their handling can miss something
    problems: list = field(default_factory=list)

    def app_named(self, title):
        """The app a participant's title names: by title, ignoring case, or by key."""
        wanted = " ".join(str(title).split()).lower()
        for app in self.apps.values():
            if app.title.lower() == wanted or app.key == wanted:
                return app
        return None

    def entity(self, name):
        return self.entities.get(name) or self.entities.get(str(name).lower())
