"""Input readers: a vault's files in, normalized tables out. Pure: they take {path: text}, never the disk.

Two sources feed the same CaseTable and EventTable records (decision D7):
- specs: `specs/<app>.openapi.yaml` (calls) and `specs/<app>.asyncapi.yaml` (events), with `x-vela-` fields;
- hand-written tables under a `### CON-nnn` or `### EVT-nnn` heading on a building-blocks page, for an app or an
  outside party with no spec.
A contract or event declared by both is a problem (two sources of one truth drift), never a silent pick.

Readers never decide what is wrong with a flow; they record what is written and report what they cannot read.
"""
import re

import yaml

from planner import parse, releases as release_pages
from planner.flowcheck import mermaid
from planner.flowcheck.tables import (App, Case, CaseTable, Catalog, Entity, EventTable, Flow, Override, Problem,
                                      Release, Retries)

DELIVERIES = ("exactly-once", "at-least-once", "may-be-lost")
CON = re.compile(r"^CON-\d+$")
EVT = re.compile(r"^EVT-\d+$")
HEADING_ITEM = re.compile(r"^###\s+((?:CON|EVT)-\d+)\s+(.*?)\s*$")
OVERRIDE = re.compile(r'^- \*\*Override:\*\*\s*"F1 (CON-\d+) (\w+) until (\d{4}-\d{2}-\d{2})"')
STATE_PAIR = re.compile(r"^(\w+)->(\w+)$")
HTTP_METHODS = ("get", "put", "post", "delete", "patch", "head", "options", "trace")


def read_vault(files):
    """A Catalog from the vault's files: {posix path relative to the vault root: text}. Iterates in sorted path
    order, so the same files always give the same catalogue."""
    cat = Catalog()
    channel_views = []
    for path in sorted(files):
        text = parse.normalise_text(files[path])
        if path.startswith("specs/") and path.endswith(".openapi.yaml"):
            _add_openapi(cat, path, text)
        elif path.startswith("specs/") and path.endswith(".asyncapi.yaml"):
            channel_views += _read_asyncapi(cat, path, text)
        elif path.startswith("05-building-blocks/") and path.endswith(".md"):
            channel_views += _read_contract_page(cat, path, text)
        elif path.startswith("entities/") and path.endswith(".md"):
            entity = read_entity(path, text, cat.problems)
            if entity is not None:
                cat.entities[entity.slug] = entity
                if entity.id:
                    cat.entities[entity.id] = entity
        elif path.startswith("06-runtime/flows/") and path.endswith(".md"):
            flow = read_flow(path, text, cat.problems)
            if flow is not None:
                cat.flows[flow.id] = flow
        elif path == "04b-releases.md":
            cat.releases = read_releases(text)
    _merge_events(cat, channel_views)
    return cat


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


# --- shared value readers -------------------------------------------------------------------------------------------

def read_retries(value, where, item, problems):
    """Retries from {max: 3, on: [timeout, 503 unavailable]} or the table text "max 3 on timeout, 503 unavailable".
    None for none. `on` is required (review 1.14): retrying a not_found is a bug, so nothing is assumed retried."""
    if value is None or (isinstance(value, str) and value.strip().lower() in ("", "none", "no", "-", "—")):
        return None
    if isinstance(value, str):
        found = re.match(r"^max\s+(\d+)(?:\s+on\s+(.+))?$", value.strip(), re.I)
        if not found:
            problems.append(Problem(where, f"{item}: retries '{value}' is not 'max <n> on <case>, <case>'.", item))
            return None
        top, on = int(found.group(1)), [p.strip() for p in (found.group(2) or "").split(",") if p.strip()]
    elif isinstance(value, dict):
        # YAML 1.1 reads a bare `on:` key as the boolean True, so `{max: 3, on: [timeout]}` arrives keyed True.
        top, on = value.get("max"), value.get("on", value.get(True))
        if not isinstance(top, int) or isinstance(top, bool):
            problems.append(Problem(where, f"{item}: x-vela-retries needs max: <attempts>.", item))
            return None
        on = [str(o) for o in on] if isinstance(on, list) else []
    else:
        problems.append(Problem(where, f"{item}: retries must be a mapping or 'max <n> on ...'.", item))
        return None
    if not on:
        problems.append(Problem(where, f"{item}: retries say how many attempts but not which outcomes are retried. "
                                       "Add 'on: [timeout, ...]'.", item))
        return None
    if top < 2:
        problems.append(Problem(where, f"{item}: retries max {top} allows no second attempt; write max 2 or more.", item))
        return None
    return Retries(top, tuple(o.split()[-1] for o in on))


def _states_of(value):
    return tuple(s for s in re.split(r"\s*(?:,|\bor\b)\s*", str(value).strip()) if s)


def read_sets(value, where, item, problems):
    """((entity, target), ...) from {hold: held} / {stock: {one: zero, zero: minus_one}} or "hold=held; stock=one->zero zero->minus_one"."""
    if value in (None, "", "-", "—"):
        return ()
    out = []
    if isinstance(value, dict):
        for entity, target in value.items():
            if isinstance(target, dict):
                out.append((str(entity), tuple((str(a), str(b)) for a, b in target.items())))
            else:
                out.append((str(entity), str(target)))
        return tuple(out)
    for part in str(value).split(";"):
        entity, eq, target = part.strip().partition("=")
        if not eq:
            problems.append(Problem(where, f"{item}: sets '{part.strip()}' is not '<entity>=<state>'.", item))
            continue
        pairs = [STATE_PAIR.match(p) for p in target.split()]
        if len(pairs) > 1 or (pairs and pairs[0]):
            if not all(pairs):
                problems.append(Problem(where, f"{item}: sets '{part.strip()}' mixes states and from->to pairs.", item))
                continue
            out.append((entity.strip(), tuple((m.group(1), m.group(2)) for m in pairs)))
        else:
            out.append((entity.strip(), target.strip()))
    return tuple(out)


def read_when(value, where, item, problems):
    """((entity, (state, ...)), ...) from {order: [pending]} or "order=new or pending; stock=one"."""
    if value in (None, "", "-", "—"):
        return ()
    if isinstance(value, dict):
        return tuple((str(e), tuple(str(s) for s in (v if isinstance(v, list) else [v]))) for e, v in value.items())
    out = []
    for part in str(value).split(";"):
        entity, eq, states = part.strip().partition("=")
        if not eq or not states.strip():
            problems.append(Problem(where, f"{item}: when '{part.strip()}' is not '<entity>=<state> or <state>'.", item))
            continue
        out.append((entity.strip(), _states_of(states)))
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
    key = path[len("specs/"):-len(suffix)]
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
    cases, seen = [], set()
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
            cases.append(Case(str(key), int(status), _ids(example.get("x-vela-emits")),
                              read_sets(example.get("x-vela-sets"), where, cid, problems),
                              read_when(example.get("x-vela-when"), where, cid, problems)))
    timeout = _yes_no(op.get("x-vela-timeout")) if "x-vela-timeout" in op else None
    return CaseTable(cid, str(op.get("summary") or cid), provider, tuple(cases), timeout,
                     read_retries(op.get("x-vela-retries"), where, cid, problems), bool(op.get("x-vela-idempotent")),
                     op.get("x-vela-delivery"), op.get("x-vela-order"), path)


# --- AsyncAPI: events -----------------------------------------------------------------------------------------------

def _read_asyncapi(cat, path, text):
    """One view per (file, channel): what this file says about the event. Views merge into EventTables."""
    doc = _load_yaml(path, text, cat.problems)
    if doc is None:
        return []
    app = _spec_app(cat, path, doc, ".asyncapi.yaml")
    channels = doc.get("channels") or {}
    views = {}
    for name, channel in sorted(channels.items()):
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
            view["receive"] = read_retries(op.get("x-vela-retries"), path, view["id"], cat.problems) or "none"
        else:
            cat.problems.append(Problem(path, f"{path}: operation '{name}' has action '{op.get('action')}', not send or receive.", view["id"]))
    return list(views.values())


# --- hand-written tables on a building-blocks page ------------------------------------------------------------------

def _bullets(lines):
    out = {}
    for line in lines:
        found = parse.BULLET.match(line.strip())
        if found:
            out.setdefault(found.group(1).strip(), found.group(2).strip())
    return out


def _tables(lines, start):
    """[(header, [(cells, line)])] for each Markdown table in `lines`, whose first line is file line `start`."""
    out, current = [], None
    for n, raw in enumerate(lines, start):
        text = raw.strip()
        if not text.startswith("|"):
            current = None
            continue
        if parse.TABLE_SEPARATOR.match(text):
            continue
        cells = parse.split_row(text)
        if current is None:
            current = (cells, [])
            out.append(current)
        else:
            current[1].append((cells, n))
    return out


def _link_text(value):
    found = parse.WIKILINK.search(value)
    if not found:
        return value.strip()
    link = parse.parse_link(found.group(1), 0)
    return link.label or re.sub(r"^[A-Z]+-\d+\s+", "", link.anchor) or link.target


def _read_contract_page(cat, path, text):
    meta, body_start, error = parse.split_frontmatter(text)
    if error is not None:
        return []
    page_app = re.sub(r"^APP-", "", str(meta.get("id") or "")) or None
    if page_app:
        _add_app(cat, page_app, str(meta.get("title") or page_app), False, path)
    lines = parse.lines_of(text)
    sections, current = [], None
    for n, raw in enumerate(lines, 1):
        if raw.startswith("#"):
            found = HEADING_ITEM.match(raw)
            current = [found.group(1), found.group(2), n, []] if found else None
            if current:
                sections.append(current)
        elif current is not None:
            current[3].append(raw)
    views = []
    for item, title, line, body in sections:
        where = f"{path}:{line}"
        facts = _bullets(body)
        tables = _tables(body, line + 1)
        if item.startswith("CON-"):
            table = next(((h, rows) for h, rows in tables if h and h[0].lower() == "case"), None)
            if table is not None:
                _add_contract(cat, _read_case_table(cat, item, title, page_app, facts, table, where))
        else:
            views.append(_read_event_section(cat, item, title, page_app, facts, tables, where))
    return views


def _read_case_table(cat, item, title, page_app, facts, table, where):
    header, rows = table
    columns = [h.strip().lower() for h in header]
    provider = page_app
    if facts.get("Provider"):
        name = _link_text(facts["Provider"])
        provider = _slug(name)
        _add_app(cat, provider, name, True, where)
    cases, timeouts, retries_text = [], set(), set()
    for cells, line in rows:
        row = dict(zip(columns, list(cells) + [""] * (len(columns) - len(cells))))
        at = f"{where.rsplit(':', 1)[0]}:{line}"
        key, status = row.get("case", "").strip(), row.get("status", "").strip()
        if not re.match(r"^\w+$", key) or not status.isdigit():
            cat.problems.append(Problem(at, f"{item}: the row '{' | '.join(cells)}' needs a case key and a status code.", item))
            continue
        cases.append(Case(key, int(status), _ids(row.get("emits")), read_sets(row.get("sets"), at, item, cat.problems),
                          read_when(row.get("when"), at, item, cat.problems)))
        if row.get("timeout", "").strip():
            timeouts.add(row["timeout"].strip().lower())
        if row.get("retries", "").strip():
            retries_text.add(row["retries"].strip())
    # Timeout and Retries are properties of the call, written on each row; rows that disagree are a problem, not a pick.
    if len(timeouts) > 1 or len(retries_text) > 1:
        cat.problems.append(Problem(where, f"{item}: rows disagree on Timeout or Retries; they describe the call, so every row says the same.", item))
    timeout = _yes_no(next(iter(timeouts))) if len(timeouts) == 1 else None
    retries = read_retries(next(iter(retries_text)), where, item, cat.problems) if len(retries_text) == 1 else None
    return CaseTable(item, title, provider, tuple(cases), timeout, retries, bool(_yes_no(facts.get("Idempotent"))),
                     facts.get("Delivery"), facts.get("Order"), where)


def _read_event_section(cat, item, title, page_app, facts, tables, where):
    view = {"id": item, "title": title, "app": page_app, "delivery": facts.get("Delivery"), "order": facts.get("Order"),
            "key_of": facts.get("Key of"), "send": True, "receive": None, "where": where, "subscribers": []}
    for header, rows in tables:
        if header and header[0].lower() == "subscriber":
            for cells, _ in rows:
                name = _link_text(cells[0])
                app = cat.app_named(name)
                view["subscribers"].append((app.key if app else _slug(name),
                                            read_retries(cells[1] if len(cells) > 1 else None, where, item, cat.problems)))
    return view


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
            if len(written) > 1:
                cat.problems.append(Problem(group[0]["where"], f"{eid}: files disagree on its {name.replace('_', ' ')} ({', '.join(sorted(map(str, written)))}).", eid))
            facts[name] = (sender or {}).get(name) or next(iter(sorted(map(str, written))), None)
        subscribers = [(v["app"], None if v["receive"] == "none" else v["receive"]) for v in group if v["receive"] is not None]
        for view in group:
            subscribers += view.get("subscribers", [])
        cat.events[eid] = EventTable(eid, str(facts["title"] or eid), sender["app"] if sender else None, facts["delivery"],
                                     facts["order"], facts["key_of"], tuple(sorted(set(subscribers), key=lambda s: s[0])),
                                     (sender or group[0])["where"])


# --- entities ------------------------------------------------------------------------------------------------------

def read_entity(path, text, problems):
    meta, body_start, error = parse.split_frontmatter(text)
    slug = path[len("entities/"):-len(".md")]
    if error is not None:
        problems.append(Problem(path, f"{path}: {error.message}", slug))
        return None
    eid = str(meta.get("id") or "")
    for key in ("id", "title", "owner", "shared", "initial", "final"):
        if key not in meta:
            problems.append(Problem(path, f"{path}: the entity has no '{key}:' in its frontmatter.", eid or slug))
    shared = meta.get("shared") if isinstance(meta.get("shared"), bool) else None
    if "shared" in meta and shared is None:
        problems.append(Problem(path, f"{path}: shared must be true or false.", eid or slug))
    final = meta.get("final")
    if final is not None and not (isinstance(final, list) and all(isinstance(s, str) for s in final)):
        problems.append(Problem(path, f"{path}: final must be a list of states, such as [released, captured].", eid or slug))
        final = []
    lines = parse.lines_of(text)
    table, invariants = set(), []
    for header, rows in _tables(lines[body_start - 1:], body_start):
        if [h.lower() for h in header[:3]] != ["from", "to", "allowed by"]:
            continue
        for cells, line in rows:
            if len(cells) < 3 or not all(cells[:3]):
                problems.append(Problem(f"{path}:{line}", f"{path}:{line}: a transition row needs From, To and Allowed by.", eid or slug))
                continue
            table.add((cells[0], cells[1], " ".join(cells[2].split())))
    for n, raw in enumerate(lines, 1):
        found = re.match(r"^- \*\*Invariant:\*\*\s*(.+)$", raw.strip())
        if found:
            expr, problem = parse_invariant(found.group(1))
            if problem:
                problems.append(Problem(f"{path}:{n}", f"{path}:{n}: invariant '{found.group(1)}': {problem}", eid or slug))
            else:
                invariants.append((found.group(1).strip(), n, expr))
    return Entity(eid, slug, str(meta.get("title") or slug), meta.get("owner"), shared,
                  str(meta["initial"]) if meta.get("initial") is not None else None, tuple(final or ()),
                  frozenset(table), tuple(invariants), path)


def parse_invariant(text):
    """(expression, problem). Grammar: implies (lowest, right), and, not, `<entity>=<state>`. A bare expression with no
    implies is allowed ("not stock=minus_one"); the design wrote the implies form only."""
    tokens = text.replace("(", " ( ").replace(")", " ) ").split()
    pos = [0]

    def peek():
        return tokens[pos[0]] if pos[0] < len(tokens) else None

    def take():
        pos[0] += 1
        return tokens[pos[0] - 1]

    def implies():
        left = conj()
        if peek() == "implies":
            take()
            return ("implies", left, implies())
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


# --- flows and releases --------------------------------------------------------------------------------------------

def read_flow(path, text, problems):
    meta, body_start, error = parse.split_frontmatter(text)
    if error is not None or not meta.get("id"):
        problems.append(Problem(path, f"{path}: the flow page has no readable frontmatter id."))
        return None
    fid = str(meta["id"])
    lines = parse.lines_of(text)
    body, start, has_diagram, i = [], 0, False, body_start - 1
    while i < len(lines):
        fence = parse.FENCE.match(lines[i])
        if fence and fence.group(2) == "mermaid":
            block, j = [], i + 1
            while j < len(lines) and not parse.closes_fence(lines[j], fence.group(1)):
                block.append(lines[j])
                j += 1
            first = next((b.strip() for b in block if b.strip()), "")
            if first == "sequenceDiagram" and not has_diagram:
                has_diagram, body, start = True, block, i + 2
            i = j
        i += 1
    tokens = mermaid.tokenize(body, start, path, fid, problems) if has_diagram else ()
    overrides = []
    for n, raw in enumerate(lines, 1):
        found = OVERRIDE.match(raw.strip())
        if found:
            overrides.append(Override(found.group(1), found.group(2), found.group(3), raw.strip(), n))
    return Flow(fid, str(meta.get("title") or fid), path, tuple(tokens), tuple(overrides), has_diagram)


def read_releases(text):
    """Each `##` release with its flows: `**Tracer:**` (release one) or `**Flows:**` (later releases, the design's
    "the same way"), read with the releases module's tracer reader."""
    out, current = [], None
    for n, line in enumerate(parse.lines_of(text), 1):
        if line.startswith("## "):
            current = [line[3:].strip(), (), n]
            out.append(current)
            continue
        found = re.match(r"^- \*\*(Tracer|Flows):\*\*\s*(.*)$", line)
        if found and current is not None:
            current[1] = release_pages.read_tracer(found.group(2))[0]
    return [Release(name, flows, n) for name, flows, n in out if flows]
