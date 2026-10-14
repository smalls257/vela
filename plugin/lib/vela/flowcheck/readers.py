"""Input readers: a vault's files in, normalized tables out. Pure: they take {path: text}, never the disk.

One reader per format, and the vault's own readers wherever the vault already has one, so the checker can never
read a page differently from `planner check`:
- Markdown pages go through `parse.parse_page` and `model.build`, like every other command;
- a contract's case table and its Can time out, Retries and Idempotent bullets go through `cases` (the same parser
  W380 to W385 use);
- which flows make up a slice goes through `slices.read_slices`;
- overrides go through `override.overrides`, and `flow_overrides` here is the one place that reads the flow checker's
  quoted rules out of them.
The readers of their own here are for formats only the checker reads: OpenAPI and AsyncAPI specs with `x-vela-`
fields, `### EVT-nnn` event sections, entity pages and the strict sequence diagram.

A contract or event declared by both a spec and a page is a problem (two sources of one truth drift), never a silent
pick. Readers never decide what is wrong with a flow; they record what is written and report what they cannot read.
"""
import re

import yaml

from vela import cases, model, override, parse, slices
from vela.flowcheck import mermaid
from vela.flowcheck.tables import (App, Case, CaseTable, Catalog, Entity, EventTable, Flow, Override, Problem,
                                      Retries)

DELIVERIES = ("exactly-once", "at-least-once", "may-be-lost")
HTTP_METHODS = ("get", "put", "post", "delete", "patch", "head", "options", "trace")
EVENT_HEADING = re.compile(r"^(EVT-\d{3})\s+(.*?)\s*$")
FLOW_RULE = re.compile(r'^"(F\d+) ((?:CON|EVT|ENT)-\d{3}) (\w+) until (\d{4}-\d{2}-\d{2})"$')
UNOVERRIDABLE = ("F10", "F11")  # not fully checked is never a pass, so nothing covers it (R0)
QUOTE = " YAML reads on, off, yes and no as true or false; quote such a state, as \"off\"."
_CLAUSE = re.compile(r"^(?P<entity>[a-z][a-z0-9_.]*) (?:(?P<op>is not|is) (?P<state>[A-Za-z0-9_.-]+)|in \[(?P<states>[^\]]+)\])$")


def read_vault(files):
    """A Catalog from the vault's files: {posix path relative to the vault root: text}. Markdown is parsed the way
    every planner command parses it; specs are read here."""
    pages = [parse.parse_page(path, files[path]) for path in sorted(files) if path.endswith(".md")]
    specs = {path: files[path] for path in sorted(files) if path.startswith("specs/") and path.endswith((".yaml", ".yml"))}
    return read_catalog(model.build(pages, {}), specs)


def read_catalog(vault, specs):
    """A Catalog from a vault model and the spec files' texts. `planner check` calls this with the vault it has
    already built, so W391 costs no second parse."""
    cat = Catalog()
    channel_views = []
    for page in vault.apps:
        _add_app(cat, _app_key(page.id), str(page.meta.get("title") or page.id), False, page.path)
    for path, text in specs.items():
        text = parse.normalize_text(text)
        if path.endswith((".openapi.yaml", ".openapi.yml")):
            _add_openapi(cat, path, text)
        elif path.endswith((".asyncapi.yaml", ".asyncapi.yml")):
            channel_views += _read_asyncapi(cat, path, text)
    for contract in vault.contracts:
        _read_contract(cat, vault, contract)
    for page in vault.pages:
        channel_views += _read_event_sections(cat, page)
        if page.type == "entity" or page.path.startswith("entities/"):
            entity = read_entity(page, cat.problems)
            if entity is not None:
                cat.entities[entity.slug] = entity
                if entity.id:
                    cat.entities[entity.id] = entity
                cat.entities.setdefault(entity.title.lower(), entity)
        elif page.path.startswith("06-runtime/flows/") or page.type == "flow":
            flow = read_flow(page, cat.problems)
            if flow is not None:
                cat.flows[flow.id] = flow
    _merge_events(cat, channel_views)
    cat.slices = slices.read_slices(vault)
    by_path = {p.path: p for p in slices.pages(vault)}
    for found in cat.slices:
        if found.path in by_path:
            cat.slice_overrides[found.key] = flow_overrides(by_path[found.path], cat.problems)
    cat.consumes = _consumes(cat, vault)
    cat.crossing = _crossing(cat, vault)
    return cat


def _app_key(page_id):
    return re.sub(r"^APP-", "", str(page_id or ""))


def _slug(text):
    return re.sub(r"[^a-z0-9]+", "-", str(text).lower()).strip("-")


def _add_app(cat, key, title, outside, where):
    known = cat.apps.get(key)
    if known is None:
        cat.apps[key] = App(key, title, outside)
    elif known.title != title or known.outside != outside:
        cat.problems.append(Problem(where, f"{where} names app '{key}' as \"{title}\", and another file as \"{known.title}\"."))


def _add_contract(cat, table):
    if table.id in cat.contracts:
        cat.problems.append(Problem(table.source, f"{table.id} has two case tables, in {cat.contracts[table.id].source} "
                                    f"and {table.source}. Keep one: two sources of one contract drift.", table.id))
        return
    cat.contracts[table.id] = table


def _consumes(cat, vault):
    """{app key: {contract id}}: the contracts each app calls, as a consumer named on the contract or a caller drawn in
    any flow. Only an app that calls something can miss something in its handling, so only it gets F12 when its
    handling is not drawn (revision 2, item 8), and only for what it calls that the slice never draws it calling."""
    found = {}
    for contract in vault.contracts:
        for page in vault.consumers(contract):
            found.setdefault(_app_key(page.id), set()).add(contract.id)
    for flow in cat.flows.values():
        names = {t.parts[0]: t.parts[1] or t.parts[0] for t in flow.lines if t.kind == "participant"}
        for token in flow.lines:
            if token.kind == "call":
                app = cat.app_named(names.get(token.parts[0], token.parts[0]))
                if app is not None:
                    found.setdefault(app.key, set()).add(token.parts[2])
    return found


def _crossing(cat, vault):
    """{contract id: {flow id}}: every flow that crosses each contract, drawn or not, by its Steps (the vault's own
    reader, `flows.steps`) or its diagram. F4 needs it: a case is "reached by no flow" only once every flow that
    crosses its contract is drawn."""
    from vela import flows  # flows imports slices, which this module's callers import first
    found = {}
    for step in flows.steps(vault):
        for contract in step.contracts:
            found.setdefault(contract.id, set()).add(step.page.id)
    for flow in cat.flows.values():
        for token in flow.lines:
            if token.kind == "call":
                found.setdefault(token.parts[2], set()).add(flow.id)
    return found


# --- shared value readers -------------------------------------------------------------------------------------------

def _keys(values):
    return tuple(str(v).split()[-1] for v in values)


def read_yaml_retries(value, where, item, problems):
    """Retries from a spec's {max: 3, retried: [timeout, unavailable]}: `max` is attempts in all, the first included.
    None for none. The retried outcomes are required (revision 2, item 7), and the key is `retried`, never `on`: YAML
    1.1 reads a bare `on:` as true, which is how a key goes missing without a word (item 18)."""
    if value is None or (isinstance(value, str) and value.strip().lower() in ("", "none")):
        return None
    if not isinstance(value, dict):
        problems.append(Problem(where, f"{item}: x-vela-retries must be a mapping, {{max: 3, retried: [timeout]}}.", item))
        return None
    if "on" in value or True in value:
        problems.append(Problem(where, f"{item}: x-vela-retries says on:, which YAML reads as true. Write retried: instead.", item))
        return None
    top, retried = value.get("max"), value.get("retried")
    if not isinstance(top, int) or isinstance(top, bool) or top < 2:
        problems.append(Problem(where, f"{item}: x-vela-retries needs max: <attempts in all>, 2 or more.", item))
        return None
    if not isinstance(retried, list) or not retried:
        problems.append(Problem(where, f"{item}: x-vela-retries says how many attempts but not which outcomes are retried. "
                                       "Add retried: [timeout, ...].", item))
        return None
    return Retries(top, _keys(retried))


def read_vault_retries(value, where, item, problems):
    """Retries from the vault's own form, `2 after timeout, unavailable` (tries again twice) or `none`, read by
    `cases.retries`, the parser W381 uses. None for none or absent."""
    if value is None or not str(value).strip():
        return None
    parsed = cases.retries(str(value))
    if parsed is None:
        problems.append(Problem(where, f"{item}: retries '{value}' are not 'none' or '<n> after <case>, <case>'.", item))
        return None
    count, keys = parsed
    return Retries(count + 1, keys) if count else None


def _state(value, where, item, problems, what):
    if isinstance(value, bool):
        problems.append(Problem(where, f"{item}: {what} is a yes or no, not a state.{QUOTE}", item))
        return None
    return str(value)


def read_yaml_sets(value, where, item, problems):
    """((entity, target), ...) from {hold: held} or {stock: {one: zero, zero: minus_one}}."""
    if value in (None, ""):
        return ()
    if not isinstance(value, dict):
        problems.append(Problem(where, f"{item}: x-vela-sets must map entities to states.", item))
        return ()
    out = []
    for entity, target in value.items():
        if isinstance(target, dict):
            pairs = [(_state(a, where, item, problems, "a state in x-vela-sets"), _state(b, where, item, problems, "a state in x-vela-sets"))
                     for a, b in target.items()]
            if all(a is not None and b is not None for a, b in pairs):
                out.append((str(entity), tuple(pairs)))
        else:
            state = _state(target, where, item, problems, "a state in x-vela-sets")
            if state is not None:
                out.append((str(entity), state))
    return tuple(out)


def read_yaml_when(value, where, item, problems):
    """((entity, "in", (state, ...)), ...) from {order: [pending]} or {order: pending}."""
    if value in (None, ""):
        return ()
    if not isinstance(value, dict):
        problems.append(Problem(where, f"{item}: x-vela-when must map entities to states.", item))
        return ()
    out = []
    for entity, states in value.items():
        found = [_state(s, where, item, problems, "a state in x-vela-when") for s in (states if isinstance(states, list) else [states])]
        if all(s is not None for s in found):
            out.append((str(entity), "in", tuple(found)))
    return tuple(out)


def sets_of(case):
    """The checker's ((entity, target), ...) from a case table row's `cases` changes, ((entity, from, to), ...)."""
    out, by_entity = [], {}
    for entity, start, to in case.sets:
        if not start:
            out.append((entity, to))
        else:
            by_entity.setdefault(entity, []).append((start, to))
    out += [(entity, tuple(pairs)) for entity, pairs in by_entity.items()]
    return tuple(out)


def when_of(text):
    """((entity, "in" | "not in", (state, ...)), ...) from a When cell `cases` has already accepted."""
    if not text:
        return ()
    out = []
    for clause in re.split(r" and (?![^\[]*\])", text):
        found = _CLAUSE.match(clause.strip())
        if found["states"]:
            out.append((found["entity"], "in", tuple(s.strip() for s in found["states"].split(","))))
        else:
            out.append((found["entity"], "not in" if found["op"] == "is not" else "in", (found["state"],)))
    return tuple(out)


def _yes_no(value):
    if isinstance(value, bool):
        return value
    text = str(value).strip().lower() if value is not None else ""
    return {"yes": True, "true": True, "no": False, "false": False}.get(text)


def _ids(value):
    if value in (None, "", "-", "—"):
        return ()
    items = value if isinstance(value, list) else re.split(r"[,\s]+", str(value))
    return tuple(str(i).strip() for i in items if str(i).strip())


def _load_yaml(path, text, problems):
    try:
        doc = yaml.safe_load(text)
    except yaml.YAMLError as exc:
        problems.append(Problem(path, f"{path} is not valid YAML: {exc}"))
        return None
    if not isinstance(doc, dict):
        problems.append(Problem(path, f"{path} is not a YAML mapping."))
        return None
    return doc


def _spec_app(cat, path, doc, suffix):
    key = path[len("specs/"):].split(".", 1)[0]
    info = doc.get("info") or {}
    title = str(info.get("title") or key)
    _add_app(cat, key, title, bool(info.get("x-vela-outside")), path)
    return key


# --- OpenAPI: calls -------------------------------------------------------------------------------------------------

def _add_openapi(cat, path, text):
    doc = _load_yaml(path, text, cat.problems)
    if doc is None:
        return
    provider = _spec_app(cat, path, doc, ".openapi.yaml")
    for route, item in sorted((doc.get("paths") or {}).items()):
        for method in HTTP_METHODS:
            op = (item or {}).get(method)
            if not isinstance(op, dict) or "x-vela-id" not in op:
                continue
            _add_contract(cat, _read_operation(path, f"{method.upper()} {route}", op, provider, cat.problems))


def _read_operation(path, name, op, provider, problems):
    cid = str(op["x-vela-id"])
    where = f"{path} ({name})"
    found, seen = [], set()
    for status, response in (op.get("responses") or {}).items():
        if not str(status).isdigit():
            problems.append(Problem(where, f"{cid}: response '{status}' has no status code, so it is no case.", cid))
            continue
        examples = {}
        for media in ((response or {}).get("content") or {}).values():
            examples.update((media or {}).get("examples") or {})
        if not examples:
            problems.append(Problem(where, f"{cid}: response {status} has no named example, so it declares no case. "
                                           "Name one example per case; the name is the case key.", cid))
        for key, example in examples.items():
            example = example or {}
            if key in seen:
                problems.append(Problem(where, f"{cid}: case key '{key}' is used twice; keys are unique per operation.", cid))
                continue
            seen.add(key)
            found.append(Case(str(key), str(status), _ids(example.get("x-vela-emits")),
                              read_yaml_sets(example.get("x-vela-sets"), where, cid, problems),
                              read_yaml_when(example.get("x-vela-when"), where, cid, problems)))
    timeout = _yes_no(op.get("x-vela-timeout")) if "x-vela-timeout" in op else None
    return CaseTable(cid, str(op.get("summary") or cid), provider, tuple(found), timeout,
                     read_yaml_retries(op.get("x-vela-retries"), where, cid, problems), bool(op.get("x-vela-idempotent")),
                     op.get("x-vela-delivery"), op.get("x-vela-order"), path)


# --- AsyncAPI: events -----------------------------------------------------------------------------------------------

def _read_asyncapi(cat, path, text):
    """One view per (file, channel): what this file says about the event. Views merge into EventTables."""
    doc = _load_yaml(path, text, cat.problems)
    if doc is None:
        return []
    app = _spec_app(cat, path, doc, ".asyncapi.yaml")
    views = {}
    for name, channel in sorted((doc.get("channels") or {}).items()):
        channel = channel or {}
        if "x-vela-id" not in channel:
            continue
        views[name] = {"id": str(channel["x-vela-id"]), "title": channel.get("title") or channel.get("summary"),
                       "app": app, "delivery": channel.get("x-vela-delivery"), "order": channel.get("x-vela-order"),
                       "key_of": channel.get("x-vela-key-of"), "send": False, "receive": None, "where": path}
    for name, op in sorted((doc.get("operations") or {}).items()):
        op = op or {}
        ref = str(((op.get("channel") or {}).get("$ref")) or "")
        view = views.get(ref.rsplit("/", 1)[-1]) if ref.startswith("#/channels/") else None
        if view is None:
            cat.problems.append(Problem(path, f"{path}: operation '{name}' names no channel with an x-vela-id."))
            continue
        if op.get("action") == "send":
            view["send"] = True
        elif op.get("action") == "receive":
            view["receive"] = read_yaml_retries(op.get("x-vela-retries"), path, view["id"], cat.problems) or "none"
        else:
            cat.problems.append(Problem(path, f"{path}: operation '{name}' has action '{op.get('action')}', not send or receive.", view["id"]))
    return list(views.values())


# --- contracts on a building-blocks page, through the vault's case-table parser --------------------------------------

def _link_text(value):
    found = parse.WIKILINK.search(value)
    if not found:
        return value.strip()
    link = parse.parse_link(found.group(1), 0)
    return link.label or re.sub(r"^[A-Z]+-\d+\s+", "", link.anchor) or link.target


def _read_contract(cat, vault, contract):
    page = contract.page
    table = cases.case_table(page, contract)
    if table is None:
        return  # no table: a slice that calls it gets "no case table" (F10); W380 says so in check
    where = f"{page.path}:{contract.line}"
    for problem in table.problems:
        cat.problems.append(Problem(f"{page.path}:{problem.line}", f"{problem.message} {problem.fix}", contract.id))
    for line, message, fix in cases.facts_problems(contract):
        cat.problems.append(Problem(f"{page.path}:{line}", f"{message} {fix}", contract.id))
    provider = _app_key(page.id)
    if contract.fact("Provider"):
        name = _link_text(contract.fact("Provider"))
        provider = _slug(name)
        _add_app(cat, provider, name, True, where)
    retries_bullet = contract.facts.get("Retries")
    retries = None
    if retries_bullet and cases.RETRIES.match(retries_bullet.value.strip().lower()):
        retries = read_vault_retries(retries_bullet.value, where, contract.id, cat.problems)
    found = tuple(Case(c.key, c.status, c.emits, sets_of(c), when_of(c.when)) for c in table.cases)
    _add_contract(cat, CaseTable(contract.id, contract.name, provider, found, cases.yes_no(contract, "Can time out"), retries,
                                 bool(cases.yes_no(contract, "Idempotent")), contract.fact("Delivery") or None,
                                 contract.fact("Order") or None, where))


# --- events: a `### EVT-nnn <name>` section, on its producer's page ---------------------------------------------------

def _section(page, heading):
    later = [h.line for h in page.headings if h.line > heading.line and h.level <= 3]
    return heading.line, later[0] if later else len(page.text.split("\n")) + 1


def _read_event_sections(cat, page):
    views = []
    for heading in page.headings:
        found = EVENT_HEADING.match(heading.text) if heading.level == 3 else None
        if not found:
            continue
        start, end = _section(page, heading)
        facts = {}
        for bullet in page.bullets:
            if start < bullet.line < end and not bullet.generated:
                facts.setdefault(bullet.label, bullet.value.strip())
        where = f"{page.path}:{heading.line}"
        item = found.group(1)
        view = {"id": item, "title": found.group(2), "app": _app_key(page.id) or None, "delivery": facts.get("Delivery"),
                "order": facts.get("Order"), "key_of": facts.get("Key of"), "send": page.type == "app-building-blocks",
                "receive": None, "where": where, "subscribers": []}
        for table in page.tables:
            if table.generated or not (start < table.line < end) or not table.header or table.header[0].lower() != "subscriber":
                continue
            for cells in table.rows:
                name = _link_text(cells[0])
                app = cat.app_named(name)
                view["subscribers"].append((app.key if app else _slug(name),
                                            read_vault_retries(cells[1] if len(cells) > 1 else None, where, item, cat.problems)))
        views.append(view)
    return views


def _merge_events(cat, views):
    """EventTables from every file's view of each event. The producer's view carries delivery and order."""
    by_id = {}
    for view in views:
        by_id.setdefault(view["id"], []).append(view)
    for eid in sorted(by_id):
        group = by_id[eid]
        senders = [v for v in group if v["send"]]
        if len(senders) > 1:
            cat.problems.append(Problem(senders[1]["where"], f"{eid} has two producers ({senders[0]['app']} and "
                                        f"{senders[1]['app']}); the checker models one.", eid))
        sender = senders[0] if senders else None
        facts = {}
        for name in ("delivery", "order", "key_of", "title"):
            written = {v[name] for v in group if v[name]}
            if len(written) > 1 and name != "title":
                cat.problems.append(Problem(group[0]["where"], f"{eid}: files disagree on its {name.replace('_', ' ')} ({', '.join(sorted(map(str, written)))}).", eid))
            facts[name] = (sender or {}).get(name) or next(iter(sorted(map(str, written))), None)
        subscribers = [(v["app"], None if v["receive"] == "none" else v["receive"]) for v in group if v["receive"] is not None]
        for view in group:
            subscribers += view.get("subscribers", [])
        cat.events[eid] = EventTable(eid, str(facts["title"] or eid), sender["app"] if sender else None, facts["delivery"],
                                     facts["order"], facts["key_of"], tuple(sorted(set(subscribers), key=lambda s: s[0])),
                                     (sender or group[0])["where"])


# --- entities: a page of type entity -----------------------------------------------------------------------------------

def read_entity(page, problems):
    meta, path = page.meta, page.path
    slug = page.name
    if page.errors and not meta:
        problems.append(Problem(path, f"{path}: {page.errors[0].message}", slug))
        return None
    eid = page.id
    for key in ("id", "title", "app", "shared", "initial", "final"):
        if key not in meta:
            problems.append(Problem(path, f"{path}: the entity has no '{key}:' in its frontmatter.", eid or slug))
    shared = meta.get("shared") if isinstance(meta.get("shared"), bool) else None
    if "shared" in meta and shared is None:
        problems.append(Problem(path, f"{path}: shared must be true or false.", eid or slug))
    final = meta.get("final")
    if final is not None and not (isinstance(final, list) and all(isinstance(s, str) for s in final)):
        hint = QUOTE if isinstance(final, list) and any(isinstance(s, bool) for s in final) else ""
        problems.append(Problem(path, f"{path}: final must be a list of states, such as [released, captured].{hint}", eid or slug))
        final = []
    initial = meta.get("initial")
    if initial is not None and not isinstance(initial, str):
        problems.append(Problem(path, f"{path}: initial must be a state name.{QUOTE if isinstance(initial, bool) else ''}", eid or slug))
        initial = None
    table, invariants = set(), []
    for found in page.tables:
        if [h.lower() for h in found.header[:3]] != ["from", "to", "allowed by"]:
            continue
        for cells, line in zip(found.rows, found.row_lines):
            if len(cells) < 3 or not all(cells[:3]):
                problems.append(Problem(f"{path}:{line}", f"{path}:{line}: a transition row needs From, To and Allowed by.", eid or slug))
                continue
            table.add((cells[0], cells[1], " ".join(cells[2].split())))
    for bullet in page.bullets:
        if bullet.label != "Invariant" or bullet.generated:
            continue
        expr, problem = parse_invariant(bullet.value)
        if problem:
            problems.append(Problem(f"{path}:{bullet.line}", f"{path}:{bullet.line}: invariant '{bullet.value}': {problem}", eid or slug))
        else:
            invariants.append((bullet.value.strip(), bullet.line, expr))
    app = _app_key(meta.get("app")) or None
    return Entity(eid, slug, str(meta.get("title") or slug), app, shared, initial, tuple(final or ()),
                  frozenset(table), tuple(invariants), path)


def parse_invariant(text):
    """(expression, problem). Grammar, lowest first: implies (right), or, and, not, parentheses, `<entity>=<state>`.
    A bare expression with no implies is allowed: `not (digest=shown and consent=none)`."""
    tokens = text.replace("(", " ( ").replace(")", " ) ").split()
    pos = [0]

    def peek():
        return tokens[pos[0]] if pos[0] < len(tokens) else None

    def take():
        pos[0] += 1
        return tokens[pos[0] - 1]

    def implies():
        left = disj()
        if peek() == "implies":
            take()
            return ("implies", left, implies())
        return left

    def disj():
        left = conj()
        while peek() == "or":
            take()
            left = ("or", left, conj())
        return left

    def conj():
        left = unary()
        while peek() == "and":
            take()
            left = ("and", left, unary())
        return left

    def unary():
        token = peek()
        if token == "not":
            take()
            return ("not", unary())
        if token == "(":
            take()
            inner = implies()
            if take() != ")":
                raise ValueError("a ( is never closed")
            return inner
        if token is None or "=" not in token:
            raise ValueError(f"expected <entity>=<state>, found {token or 'the end'}")
        take()
        entity, state = token.split("=", 1)
        return ("is", entity, state)

    try:
        expr = implies()
        if peek() is not None:
            raise ValueError(f"unexpected '{peek()}'")
        return expr, ""
    except (ValueError, IndexError) as exc:
        return None, str(exc)


# --- flows and their overrides ---------------------------------------------------------------------------------------

def read_flow(page, problems):
    if not page.id.startswith("FLO-"):
        problems.append(Problem(page.path, f"{page.path}: the flow page has no readable frontmatter id."))
        return None
    diagram = next((d for d in page.diagrams if d.kind == "sequenceDiagram"), None)
    tokens = mermaid.tokenize(diagram.lines, diagram.line + 1, page.path, page.id, problems) if diagram else ()
    return Flow(page.id, str(page.meta.get("title") or page.id), page.path, tuple(tokens), flow_overrides(page, problems),
                diagram is not None)


def flow_overrides(page, problems):
    """The checker's overrides on a flow page or a slice page: the vault's Override bullet with a quoted rule, read
    by `override`.

        - **Override:** "F1 CON-010 unavailable until 2026-12-01" by @lead on 2026-10-13: next sprint

    The one reader of them: one on a flow page covers that flow's findings wherever it is checked, one under a slice
    page's `## Overrides` covers the finding in any flow of that slice. A quoted rule that
    starts like one of ours and does not read is a problem, never ignored: a typo would leave the user believing a
    finding is covered when it is not, the Silent Fallback overrides exist to prevent."""
    out = []
    for found in override.overrides(page):
        where = f"{page.path}:{found.line}"
        if found.problem:
            if '"F' in found.text:
                problems.append(Problem(where, f"This override does not read: it {found.problem}.", page.id))
            continue
        for rule in found.rules:
            if not rule.startswith('"F'):
                continue
            match = FLOW_RULE.match(rule)
            if not match:
                problems.append(Problem(where, f"The override {rule} is not \"<code> <ID> <case> until YYYY-MM-DD\".", page.id))
            elif match.group(1) in UNOVERRIDABLE:
                problems.append(Problem(where, f"The override {rule} names {match.group(1)}: a slice that is not fully "
                                               "checked is never a pass, so no override covers it.", page.id))
            else:
                out.append(Override(match.group(1), match.group(2), match.group(3), match.group(4), found.text, where))
    return tuple(out)
