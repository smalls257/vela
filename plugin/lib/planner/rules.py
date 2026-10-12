"""Vault model to findings. Pure: `today` is passed in, nothing reads the disk.

Every rule runs on every page it can read. No rule stops the others.
"""
import datetime
import re

from planner import allocation, flows, links, override, parse, pending, questions, readability, readload, releases, render, schema, trace
from planner.model import Finding, blocked_units, cell_table, decided_goal_rows, goal_rows_at, meta_line


def check(vault, today, gate=None, items=()):
    """All findings for the vault, sorted by path, line and code.

    `gate="epics"` is the moment epics are called complete: every trace gap
    becomes an error, even in a vault that has no epic yet, and so does every
    high-severity question not yet disposed. `gate="shape"` is the end of a
    Shape: each assumed question still unresolved warns. `gate="grill"` with
    `items` is a Grill on those items: each open question that blocks one warns.
    Overrides apply last, so an override can soften an error but never hide one:
    see override.apply.
    """
    findings = []
    for rule in RULES:
        findings.extend(rule(vault, today))
    if gate == "epics":
        trace_warnings = {warning for warning, _ in schema.TRACE_CODES.values()}
        findings = [f for f in findings if f.code not in trace_warnings]
        findings.extend(trace_findings(vault, gated=True))
        findings.extend(questions.epics_gate(vault))
    elif gate == "shape":
        findings.extend(questions.shape_gate(vault))
    elif gate == "grill":
        findings.extend(questions.grill_gate(vault, items))
    return sorted(set(override.apply(vault, findings, gate) + pending.findings(vault)))


# ------------------------------------------------------------------ helpers

def is_date(value):
    if not isinstance(value, str) or not schema.DATE_RE.match(value):
        return False
    try:
        datetime.date.fromisoformat(value)
    except ValueError:
        return False
    return True


def readable(page):
    """Pages whose frontmatter parsed into a known type."""
    return bool(page.meta) and isinstance(page.type, str) and page.type in schema.PAGE_TYPES


def _f(page, line, code, message, fix):
    return Finding(page.path, line, code, message, fix)


# ------------------------------------------------------- parse and frontmatter

def parse_errors(vault, today):
    for page in vault.pages:
        for error in page.errors:
            yield _f(page, error.line, error.code, error.message, error.fix)


def frontmatter_rules(vault, today):
    for page in vault.pages:
        if not page.meta:
            continue
        page_type = page.meta.get("type")
        if page_type is None:
            yield _f(page, 1, "E103", "Field 'type' is missing.", "Add a type, for example type: initiative-section.")
            continue
        if not isinstance(page_type, str) or page_type not in schema.PAGE_TYPES:
            yield _f(page, meta_line(page, "type"), "E104", f"Page type '{page_type}' is not one CONVENTIONS.md defines.",
                     "Use one of: " + ", ".join(schema.PAGE_TYPES) + ".")
            continue
        spec = schema.PAGE_TYPES[page_type]
        for key in spec["required"]:
            if key not in page.meta or page.meta[key] in (None, ""):
                yield _f(page, 1, "E103", f"Field '{key}' is missing. A {page_type} page needs it.",
                         f"Add '{key}:' to the frontmatter.")
        yield from _enum_findings(vault, page, page_type, spec)
        yield from _id_findings(page, page_type)


def _enum_findings(vault, page, page_type, spec):
    meta = page.meta
    checks = [("authored", schema.ENUMS["authored"]), ("c4", schema.ENUMS["c4"]),
              ("origin", schema.ENUMS["origin"]), ("stage", schema.ENUMS["stage"]),
              ("status", schema.ENUMS["status"])]
    if spec["states"]:
        checks.append(("state", spec["states"]))
    change_enum = schema.ENUMS.get(f"change@{page_type}")
    if change_enum:
        checks.append(("change", change_enum))
    for key, allowed in checks:
        if key in meta and meta[key] not in allowed:
            yield _f(page, meta_line(page, key), "E105", f"'{key}: {meta[key]}' is not allowed on a {page_type} page.",
                     f"Use one of: {', '.join(allowed)}.")
    for key in schema.LIST_FIELDS:
        if key in meta and not (isinstance(meta[key], list) and all(isinstance(v, str) for v in meta[key])):
            yield _f(page, meta_line(page, key), "E105", f"'{key}' must be a list of text values.",
                     f"Write it as {key}: [A, B].")
    if meta.get("owner") is not None and not (isinstance(meta["owner"], str) and schema.OWNER_RE.match(meta["owner"])):
        yield _f(page, meta_line(page, "owner"), "E105", f"Owner '{meta['owner']}' is not a GitHub handle or team.",
                 "Write owner: \"@handle\" or \"@org/team\", several separated by spaces.")
    if "domain" in meta and not (isinstance(meta["domain"], str) and meta["domain"].strip()):
        yield _f(page, meta_line(page, "domain"), "E105", "'domain' must be a short text, such as Booking.",
                 "Write domain: Booking, or remove the field.")
    if "last_verified" in meta and not is_date(meta["last_verified"]):
        yield _f(page, meta_line(page, "last_verified"), "E106", f"last_verified '{meta['last_verified']}' is not a YYYY-MM-DD date.",
                 "Write last_verified: 2026-11-20.")
    if "verified_by" in meta and not (isinstance(meta["verified_by"], str) and schema.OWNER_RE.match(meta["verified_by"])):
        yield _f(page, meta_line(page, "verified_by"), "E105", f"verified_by '{meta['verified_by']}' is not a GitHub handle.",
                 "Write verified_by: \"@handle\".")
    if "handed_off" in meta and not (isinstance(meta["handed_off"], str) and schema.HANDED_OFF_RE.match(meta["handed_off"])):
        yield _f(page, meta_line(page, "handed_off"), "E105", "'handed_off' is not in the form '<name>, <date>, PR #N'.",
                 "Write handed_off: \"Booking senior, 2026-11-20, PR #41\".")
    elif isinstance(meta.get("handed_off"), str) and meta["handed_off"].endswith("PR pending"):
        yield _f(page, meta_line(page, "handed_off"), "W325", f"{page.id} is handed off, but its PR number is not recorded yet.",
                 "Once the PR exists, write its number in place of 'pending', as close does after gh prints the URL.")
    initiative = vault.config.get("initiative")
    if "initiative" in meta and meta["initiative"] != initiative:
        yield _f(page, meta_line(page, "initiative"), "E105",
                 f"'initiative: {meta['initiative']}' differs from .planner.yaml ({initiative}).",
                 f"Set initiative: {initiative}, or remove the field.")
    if page_type == "session":
        modes = meta.get("modes")
        for mode in modes if isinstance(modes, list) else []:
            if mode not in schema.SESSION_MODES:
                yield _f(page, meta_line(page, "modes"), "E105", f"Session mode '{mode}' is not one CONVENTIONS.md defines.",
                         "Use: " + ", ".join(schema.SESSION_MODES) + ".")
        if "date" in meta and not is_date(meta["date"]):
            yield _f(page, meta_line(page, "date"), "E106", f"Session date '{meta['date']}' is not a YYYY-MM-DD date.",
                     "Write date: 2026-08-12.")


def _id_findings(page, page_type):
    page_id = page.id
    if not page_id:
        return
    if not schema.PAGE_ID_RE[page_type].match(page_id) or (page_id.endswith("-runtime") and page_type == "app-building-blocks"):
        yield _f(page, meta_line(page, "id"), "E107", f"id '{page_id}' does not fit the pattern for a {page_type} page.",
                 "See the ID table in CONVENTIONS.md.")
        return
    rule = schema.expected_basename(page_type, page_id)
    if rule:
        kind, expected = rule
        ok = page.name == expected if kind == "exact" else page.name.startswith(expected)
        if not ok:
            want = f"'{expected}'" if kind == "exact" else f"one starting '{expected}'"
            yield _f(page, meta_line(page, "id"), "E107", f"File name '{page.name}' does not match id '{page_id}'.",
                     f"Rename the file to {want}, or fix the id.")
    if page_type == "session" and isinstance(page.meta.get("date"), str) and page_id[:10] != page.meta["date"]:
        yield _f(page, meta_line(page, "date"), "E107", f"Session id '{page_id}' does not start with its date {page.meta['date']}.",
                 "Make the id and file name start with the session date.")


# ---------------------------------------------------------------- duplicates

def duplicate_rules(vault, today):
    for page_id, pages in sorted(vault.by_id.items()):
        if len(pages) > 1:
            others = ", ".join(p.path for p in pages[1:])
            yield _f(pages[0], meta_line(pages[0], "id"), "E108", f"id '{page_id}' is also used by {others}.",
                     "Give each page its own id.")
    for name, pages in sorted(vault.by_name.items()):
        if len(pages) > 1:
            others = ", ".join(p.path for p in pages[1:])
            yield _f(pages[0], 1, "E204", f"Basename '{pages[0].name}' is also used by {others}, so links to it are ambiguous.",
                     "Rename one of the files. Basenames must be unique across the vault.")
    for item_id, items in sorted(vault.items.items()):
        if len(items) > 1:
            where = ", ".join(f"{i.page.path}:{i.line}" for i in items[1:])
            yield _f(items[0].page, items[0].line, "E208", f"{item_id} is also a heading at {where}.",
                     "Keep one heading per ID and link to it from elsewhere.")
    yield from repeated_fact_rules(vault)
    for row_id, (kept_page, kept_line), (page, line) in vault.row_repeats:
        yield _f(page, line, "E210", f"{row_id} is also a row at {kept_page.path}:{kept_line}, and only that first row counts.",
                 "Give each goal, constraint and source its own ID.")


FACTS_MAY_REPEAT = set(schema.HISTORY_LABELS) | {schema.PENDING_LABEL}  # a History keeps every decision and override


def repeated_fact_rules(vault):
    """E209: a label written twice under one heading. The first bullet is the one every rule reads, so a later
    '- **State:** decided' appended by hand would change nothing and say nothing."""
    for found in vault.items.values():
        for item in found:
            for kept, ignored in item.repeats:
                if ignored.label not in FACTS_MAY_REPEAT:
                    yield _f(item.page, ignored.line, "E209", f"{item.id} has '**{ignored.label}:**' twice; line {kept.line} counts and this one is ignored.",
                             f"Keep one '**{ignored.label}:**' bullet under {item.id}, with the value you mean.")


# --------------------------------------------------------------------- links

def history_rules(vault, today):
    """E323: a "#### <ID>" under History gives its bullets to that item, so one with no item of that ID on its page
    would hold a decision or an override no rule reads."""
    for page in vault.pages:
        here = {i.id for found in vault.items.values() for i in found if i.page is page}
        for item_id, (line, _) in parse.history_items(page).items():
            if item_id not in here:
                yield _f(page, line, "E323", f"'#### {item_id}' under History names no item on this page, so what is "
                         "under it counts for nothing.", f"Use the ID of a '### <ID>' heading on this page, or move it "
                         f"to the History of the page where {item_id} is.")


def link_rules(vault, today):
    for page in vault.pages:
        for link in page.links:
            target = vault.resolve(link, page)
            if target is None:
                if link.target.lower() in vault.other_names:
                    continue
                yield _f(page, link.line, "E201", f"[[{link.target}]] links to a page that does not exist.",
                         _missing_page_hint(vault, link.target))
                continue
            if not link.anchor:
                continue
            if link.anchor.startswith("^"):
                if link.anchor[1:] not in target.block_ids:
                    yield _f(page, link.line, "E202", f"Block reference #{link.anchor} matches no line in {target.name}.",
                             f"Point it at a line in {target.name} that ends with {link.anchor}.")
                continue
            texts = [h.text for h in target.headings]
            if link.anchor in texts:
                continue
            row = vault.row_ids.get(link.anchor)
            if row is not None and row[0] is target:
                continue  # [[sources#SRC-04|the latency measurement]]: a source row is cited by its ID
            words = link.anchor.split()
            first = words[0] if words else ""
            near = [t for t in texts if first and t.split() and t.split()[0] == first]
            hint = f"Use [[{target.name}#{near[0]}]]." if near else f"Link to a heading that exists in {target.name}."
            yield _f(page, link.line, "E202", f"Anchor #{link.anchor} matches no heading in {target.name}. Anchors must equal the full heading text.",
                     hint)


def _missing_page_hint(vault, target):
    base = target.rsplit("/", 1)[-1]
    if base.endswith(".md"):
        base = base[:-3]
    if base != target and vault.page(base) is not None:
        return f"Link by basename alone: [[{base}]]."
    return "Fix the basename, or create the page."


# ------------------------------------------------------------ ID references

EPIC_LISTS = ("apps", "delivers", "consumes", "flows", "depends_on")


def reference_rules(vault, today):
    known = vault.known_ids()
    for page in vault.of_type("epic"):
        for key in EPIC_LISTS:
            values = page.meta.get(key)
            for value in values if isinstance(values, list) else []:
                if not isinstance(value, str) or value not in known:
                    yield _f(page, meta_line(page, key), "E207", f"{key} lists '{value}', which is not an ID in this vault.",
                             "Fix the ID, or remove it from the list.")
    sources = {i for i in vault.row_ids if schema.SOURCE_ID_RE.match(i)}
    for page in vault.pages:
        values = page.meta.get("sources")
        for value in values if isinstance(values, list) else []:
            for token in schema.SOURCE_TOKEN_RE.findall(str(value)):
                if token not in sources:
                    yield _f(page, meta_line(page, "sources"), "E207", f"Source {token} is not a row in sources.md.",
                             "Add the row to sources.md, or fix the ID.")
        for bullet in page.bullets:
            if bullet.label != "Source" or bullet.generated:
                continue
            for token in schema.SOURCE_TOKEN_RE.findall(str(bullet.value)):
                if token not in sources:
                    yield _f(page, bullet.line, "E207", f"Source {token} is not a row in sources.md.",
                             "Add the row to sources.md, or fix the ID.")


# --------------------------------------------------------------- fact tables

def table_rules(vault, today):
    for page in vault.pages:
        for table in page.tables:
            if table.generated:
                continue
            header = tuple(table.header)
            if header[:4] == schema.GOALS_HEADER:
                yield from _rows(page, table, schema.GOAL_ID_RE, 3, schema.STATE_ITEM, "goal", "G1")
            elif header[:2] == schema.CONSTRAINTS_HEADER:
                yield from _rows(page, table, schema.CONSTRAINT_ID_RE, None, (), "constraint", "CST-1")
            elif header[:6] == schema.SOURCES_HEADER:
                yield from _rows(page, table, schema.SOURCE_ID_RE, 4, schema.SOURCE_KINDS, "source", "SRC-01")
            elif header[:2] == schema.CONTAINERS_HEADER and "State" in header:
                col = header.index("State")
                for row, line in zip(table.rows, table.row_lines):
                    state = row[col] if len(row) > col else ""
                    if state not in schema.CONTAINER_STATES:
                        yield _f(page, line, "E306", f"Container '{row[0]}' has state '{state}'.",
                                 "Use one of: " + ", ".join(schema.CONTAINER_STATES) + ".")


def _rows(page, table, id_re, col, allowed, what, example):
    for row, line in zip(table.rows, table.row_lines):
        row_id = row[0] if row else ""
        if not id_re.match(row_id):
            yield _f(page, line, "E306", f"'{row_id}' is not a valid {what} ID.", f"Write IDs like {example}.")
        if col is not None:
            value = row[col] if len(row) > col else ""
            if value not in allowed:
                yield _f(page, line, "E306", f"{what.capitalize()} {row_id} has '{value}' where one of {', '.join(allowed)} belongs.",
                         f"Use one of: {', '.join(allowed)}.")


# ------------------------------------------------------------------ requirements

def requirement_rules(vault, today):
    """A functional requirement (### CAP-nnn.FRn) carries a state like a contract does, so it
    cannot be decided without a Grill."""
    for fr in vault.requirements:
        state = fr.fact("State")
        if not state:
            yield _f(fr.page, fr.line, "E320", f"{fr.id} has no **State:** bullet.",
                     f"Add '- **State:** assumption' under the {fr.id} heading.")
        elif state not in schema.CONTRACT_STATES:
            yield _f(fr.page, fr.facts["State"].line, "E105", f"{fr.id} has state '{state}'.",
                     "Use one of: " + ", ".join(schema.CONTRACT_STATES) + ".")


# ----------------------------------------------------------------- contracts

def contract_rules(vault, today):
    for contract in vault.contracts:
        page = contract.page
        for label in schema.CONTRACT_REQUIRED:
            if not contract.fact(label):
                yield _f(page, contract.line, "E320", f"{contract.id} has no **{label}:** bullet.",
                         f"Add '- **{label}:** ...' under the {contract.id} heading.")
        state, change = contract.fact("State"), contract.fact("Change")
        if state and state not in schema.CONTRACT_STATES:
            yield _f(page, contract.facts["State"].line, "E105", f"{contract.id} has state '{state}'.",
                     "Use one of: " + ", ".join(schema.CONTRACT_STATES) + ".")
        if change and change not in schema.CONTRACT_CHANGES:
            yield _f(page, contract.facts["Change"].line, "E105", f"{contract.id} has change '{change}'.",
                     "Use one of: " + ", ".join(schema.CONTRACT_CHANGES) + ".")
        consumers = contract.fact("Consumers")
        if consumers and not vault.consumers(contract) and not consumers.lower().startswith("none"):
            yield _f(page, contract.facts["Consumers"].line, "E311",
                     f"{contract.id} names its consumers in words, so no app page knows it consumes this contract.",
                     "Link each consumer's building-blocks page, for example [[website-building-blocks|Public website]], or write 'none'.")
        if state == "decided" and not contract.fact("Tested by"):
            yield _f(page, contract.line, "E318", f"{contract.id} is decided but says nothing about who tests it.",
                     "Add '- **Tested by:** ...' naming the test on each side.")


# ------------------------------------------------------------ unknowns, risks

def unknown_rules(vault, today):
    for unknown in vault.unknowns:
        page, state = unknown.page, unknown.fact("State")
        required = list(schema.UNKNOWN_REQUIRED)
        if state == "open":
            required += schema.UNKNOWN_OPEN_REQUIRED
        if state == "resolved":
            required += schema.UNKNOWN_RESOLVED_REQUIRED
        for label in required:
            if not unknown.fact(label):
                yield _f(page, unknown.line, "E302", f"{unknown.id} has no **{label}:** bullet.",
                         f"Add '- **{label}:** ...' under the {unknown.id} heading.")
        if state and state not in schema.UNKNOWN_STATES:
            yield _f(page, unknown.facts["State"].line, "E105", f"{unknown.id} has state '{state}'.",
                     "Use open or resolved.")
        owner = unknown.fact("Owner")
        if owner and not schema.OWNER_BULLET_RE.match(owner):
            yield _f(page, unknown.facts["Owner"].line, "E302", f"{unknown.id} owner '{owner}' is not a GitHub handle or team.",
                     "Start the Owner value with @handle or @org/team.")
        ask = unknown.fact("Ask")
        if ask.startswith("@") and not schema.OWNER_BULLET_RE.match(ask):
            yield _f(page, unknown.facts["Ask"].line, "E302", f"{unknown.id} ask '{ask}' starts like a handle but is not one.",
                     "Write a handle, @handle or @org/team, or the person's role in words, such as 'outside counsel'.")
        blocks = unknown.facts.get("Blocks")
        if blocks and blocks.value and not blocks.links and not blocks.value.lower().startswith("nothing"):
            yield _f(page, blocks.line, "E302", f"{unknown.id} says what it blocks in words only.",
                     "List links to what it blocks, or write 'nothing'.")
        ask_by = unknown.fact("Ask by")
        if ask_by and not is_date(ask_by):
            yield _f(page, unknown.facts["Ask by"].line, "E106", f"{unknown.id} ask-by '{ask_by}' is not a YYYY-MM-DD date.",
                     "Write - **Ask by:** 2027-03-01.")
        elif state == "open" and ask_by and ask_by < today:
            yield _f(page, unknown.facts["Ask by"].line, "W705",
                     f"{unknown.id} was due to be asked by {ask_by}; today is {today}.",
                     f"Ask {owner or 'the owner'}, then record the outcome or move the Ask by date.")


def risk_rules(vault, today):
    for risk in vault.risks:
        for label in schema.RISK_REQUIRED:
            if not risk.fact(label):
                yield _f(risk.page, risk.line, "E302", f"{risk.id} has no **{label}:** bullet.",
                         f"Add '- **{label}:** ...' under the {risk.id} heading.")
        state = risk.fact("State")
        if state and state not in schema.RISK_STATES:
            yield _f(risk.page, risk.facts["State"].line, "E105", f"{risk.id} has state '{state}'.",
                     "Use one of: " + ", ".join(schema.RISK_STATES) + ".")
        owner = risk.fact("Owner")
        if owner and not schema.OWNER_BULLET_RE.match(owner):
            yield _f(risk.page, risk.facts["Owner"].line, "E302", f"{risk.id} owner '{owner}' is not a GitHub handle or team.",
                     "Start the Owner value with @handle or @org/team.")


# ------------------------------------------------------------------ subjects

def subject_rules(vault, today):
    """A party or a stored value is a subject the question catalogue fires on. One that cannot be
    typed would leave its questions never owed and the ledger looking clean, so every gap is said."""
    for item, required, what in [(p, schema.PARTY_REQUIRED, "party") for p in vault.parties] + \
            [(s, schema.STORED_VALUE_REQUIRED, "stored value") for s in vault.stored_values]:
        for label in required:
            if not item.fact(label):
                yield _f(item.page, item.line, "E808", f"{item.id} is a {what} with no **{label}:** bullet.",
                         f"Add '- **{label}:** ...' under the {item.id} heading.")
    for page in vault.pages:
        history = parse.history_items(page)
        for heading in page.headings:
            first = heading.text.split()[0] if isinstance(heading.text, str) and heading.text.split() else ""
            in_history = heading.level == 4 and history.get(first, (0,))[0] == heading.line
            if schema.SUBJECT_LOOKALIKE_RE.match(first) and not (heading.level == 3 and schema.ITEM_ID_RE.match(first)) \
                    and not in_history:
                form = "### PTY-nn <name>" if first.upper().startswith("PTY") else "### SV-nn <name>"
                yield _f(page, heading.line, "E810", f"'{heading.text}' looks like a subject heading but does not read as one.",
                         f"Write it as '{form}': level 3, a two-digit ID in capitals, then a space and the name.")
    for page in vault.pages:
        for heading in page.headings:
            first = heading.text.split()[0] if heading.text.split() else ""
            if heading.level == 3 and schema.ITEM_LOOKALIKE_RE.match(first) and not schema.ITEM_ID_RE.match(first):
                form = schema.ITEM_FORMS[first.split("-")[0].upper()]
                yield _f(page, heading.line, "E810", f"'{heading.text}' looks like an item heading but does not read as one, "
                         "so no index or gate sees it.",
                         f"Write it as '### {form} <name>': the ID in capitals with its digits, then a space and the name, no colon after the ID.")
    for item in vault.parties + vault.stored_values:
        if item.page.path != schema.SUBJECT_PAGE:
            yield _f(item.page, item.line, "W811", f"{item.id} is defined on {item.page.path}, not on {schema.SUBJECT_PAGE}.",
                     f"Move the {item.id} heading to {schema.SUBJECT_PAGE}.")
    for party in vault.parties:
        relationship = party.fact("Relationship")
        if relationship and relationship.lower() not in schema.PARTY_RELATIONSHIPS:
            yield _f(party.page, party.facts["Relationship"].line, "E105", f"{party.id} has relationship '{relationship}'.",
                     "Use one of: " + ", ".join(schema.PARTY_RELATIONSHIPS) + ".")


# ------------------------------------------------------------------ the question ledger

def question_rules(vault, today):
    """E801, E802, E803, W804 and W812 on the question ledger, and W809 for a subject nobody typed. An
    open row, or a copy with no row, is never a finding here: the lead sets the pace, and the gates decide
    when it matters."""
    yield from questions.ledger_findings(vault, today)
    yield from questions.untyped_mentions(vault)


# ----------------------------------------------------------------- certainty

def decided_units(vault):
    """(unit id, page, line, Decision bullets) for every decided page and contract."""
    for page in vault.pages:
        if not readable(page):
            continue  # an unreadable type is already an E104; never look it up
        if schema.PAGE_TYPES[page.type]["states"] and page.meta.get("state") == "decided":
            yield page.id, page, meta_line(page, "state"), page.page_bullets("Decision")
        elif page.meta.get("state") != "decided":
            # A decided page already answers for its rows with the same Decision bullet.
            for row_id, line in decided_goal_rows(page):
                yield row_id, page, line, page.page_bullets("Decision")
    for contract in (*vault.contracts, *vault.requirements):
        if contract.fact("State") == "decided":
            bullet = contract.facts.get("Decision")
            yield contract.id, contract.page, contract.line, [bullet] if bullet else []
    # An allocation row has no heading of its own, so its Decision is the app page's, as for a goal row.
    for subject, row in allocation.decided_rows(vault):
        yield subject, row.app, row.line, row.app.page_bullets("Decision")
    # A release has no heading ID, so its unit is named by its heading and its Decision is the releases page's.
    for release in releases.releases(vault):
        if release.state == "decided":
            page = releases.page(vault)
            yield f"release '{release.name}'", page, release.line, page.page_bullets("Decision")


def _modes(session):
    """A session's modes, or nothing when the field is not a list (E105 reports that)."""
    modes = session.meta.get("modes")
    return modes if isinstance(modes, list) else []


STATE_ORDER = ("inkling", "assumption", "fact", "decided")


def page_state_rules(vault, today):
    """W326: a page whose rows are all further along than the page says. A goals page whose every goal is decided,
    or a constraints page whose every constraint cites its source, still reads inkling until someone types its state,
    and the page then looks unsettled to every reader and to planner status."""
    for page in vault.pages:
        state = page.meta.get("state")
        if page.type != "initiative-section" or state not in STATE_ORDER:
            continue
        for table in page.tables:
            if table.generated or not table.rows:
                continue
            head = tuple(table.header)
            if head[:len(schema.GOALS_HEADER)] == schema.GOALS_HEADER:
                rows = [r[3].strip() for r in table.rows if len(r) > 3]
                least = min((s for s in rows if s in STATE_ORDER), key=STATE_ORDER.index, default=None)
                if least and len(rows) == len([s for s in rows if s in STATE_ORDER]) \
                        and STATE_ORDER.index(least) > STATE_ORDER.index(state):
                    yield _f(page, meta_line(page, "state"), "W326",
                             f"{page.id} is {state}, but every goal on it is at least {least}.",
                             f"Set state: {least}, the least settled goal, with the page's Decision in its History.")
            elif head[:len(schema.CONSTRAINTS_HEADER)] == schema.CONSTRAINTS_HEADER and state in ("inkling", "assumption"):
                if all("[[" in " ".join(r[2:]) or "SRC-" in " ".join(r[2:]) for r in table.rows):
                    yield _f(page, meta_line(page, "state"), "W326",
                             f"{page.id} is {state}, but every constraint on it cites where it comes from.",
                             "Set state: fact, and list the sources the rows cite in its sources field.")


def allocation_rules(vault, today):
    """E330-E333: an allocation row must name a functional requirement that exists, contracts that exist, and a
    state, and a fact row needs its page's sources. A decided row answers to the decision rules in decided_units."""
    known = {item.id for found in vault.items.values() for item in found if item.kind == "requirement"}
    contracts = {c.id for c in vault.contracts}
    for row in allocation.rows(vault):
        if row.requirement not in known:
            yield _f(row.app, row.line, "E330", f"An allocation row on {row.app.id} names "
                     f"{row.requirement or 'no functional requirement'}, which is not a CAP-nnn.FRn heading in this vault.",
                     "Link the requirement's heading, [[CAP-nnn-<slug>#CAP-nnn.FRn <name>|CAP-nnn.FRn]].")
        for cid in row.through:
            if cid not in contracts:
                yield _f(row.app, row.line, "E331", f"An allocation row on {row.app.id} says it goes through {cid}, "
                         "which is no contract in this vault.", "Name the contract that carries it, or write it first.")
        if row.state not in allocation.ALLOCATED_STATES:
            yield _f(row.app, row.line, "E332", f"An allocation row on {row.app.id} has State '{row.state}'.",
                     "Use inkling, assumption, fact or decided.")
        elif row.state == "fact" and not row.app.meta.get("sources"):
            yield _f(row.app, row.line, "E333", f"The allocation row for {row.requirement} on {row.app.id} is a fact, "
                     "but the page lists no sources.", "Add sources: [SRC-nn] to the page, or lower the row to assumption.")


# Wording that says a question is still waiting. Matched only in the sentence that links an answered one.
STALE_WORDING = re.compile(r"\b(still open|remains? open|is open|still to be (decided|answered|settled)|not (yet )?"
                           r"(decided|answered|known|settled|confirmed|in writing)|waits? (on|for)|waiting (on|for)|"
                           r"pending|unanswered|open question|undecided|to be confirmed|is unclear)\b", re.I)
UNKNOWN_ANCHOR = re.compile(r"^(UNK-\d{3})\b")
# A sentence that already says the question was answered is not stale, whatever else it says.
SAYS_ANSWERED = re.compile(r"\b(resolved|answered|confirmed|ruled|agreed|measured|settled at|now known)\b", re.I)


LINK_PARTS = re.compile(r"\[\[([^\]|]*?)(?:\\?\|([^\]]*))?\]\]")


def prose_of(sentence):
    """The sentence as a reader takes it, for the stale-wording test. A link's target never counts, and nor does a
    label that only repeats the linked heading ("how long a paper order may stay pending" names the question; it
    says nothing about its state). A label that adds words, such as "still open", is what the sentence claims."""
    def keep(m):
        target, label = m.group(1), (m.group(2) or "")
        return "" if not label or label.lower() in target.lower() else label
    return LINK_PARTS.sub(keep, sentence)


def stale_mention_rules(vault, today):
    """W334: prose that calls an answered question open. Close rewrites the pages a session changed, and the session
    that answers a question rarely changes the pages that describe it, so their sentences go stale while every other
    check stays green. Only the sentence holding the link is read, and History and generated blocks are left alone."""
    for page in vault.pages:
        if page.type == "session" or page.id == "unknowns-and-risks":
            continue
        lines = page.text.split("\n")
        skip, inside = set(), False
        for n, line in enumerate(lines, 1):
            if line.startswith("<!-- generated:"):
                inside = True
            if inside or line.strip().lower() == f"## {schema.HISTORY_HEADING.lower()}":
                skip.add(n)
            if line.startswith("<!-- /generated:"):
                inside = False
        history = next((n for n, l in enumerate(lines, 1) if l.strip().lower() == f"## {schema.HISTORY_HEADING.lower()}"),
                       len(lines) + 1)
        seen = set()
        for link in page.links:
            m = UNKNOWN_ANCHOR.match(link.anchor or "")
            if not m or link.line in skip or link.line >= history or (link.line, m.group(1)) in seen:
                continue
            items = vault.items.get(m.group(1)) or []
            if not items or items[0].kind != "unknown" or items[0].fact("State") != "resolved":
                continue
            line = lines[link.line - 1] if 0 < link.line <= len(lines) else ""
            sentence = next((s for s in re.split(r"(?<=[.!?])\s+", line) if m.group(1) in s), line)
            prose = prose_of(sentence)
            found = STALE_WORDING.search(prose)
            if found and not SAYS_ANSWERED.search(prose):
                seen.add((link.line, m.group(1)))
                yield _f(page, link.line, "W334", f"This sentence says '{found.group(0)}' of {m.group(1)}, which is resolved: "
                         f"{(items[0].fact('Outcome') or 'see its Outcome')[:120]}",
                         f"Rewrite the sentence to say what was answered, or run planner query refs {m.group(1)} to find every mention.")


def reading_load_rules(vault, today):
    """W360-W369. A page a person cannot hold in mind: codes in sentences, a long flat list, a wall with no summary,
    an epic too big to carry as one piece of work, then a paragraph, cell, stock phrase, template opening or abbreviation
    that costs the reader more than a careful writer would. Warnings only; each fix says how to write it in plain words."""
    names = readability.NameIndex(vault)
    for page in vault.pages:
        for line, code, message, fix in readability.findings(page, names):
            yield _f(page, line, code, message, fix)
        for line, code, message, fix in readload.page_findings(page, vault.template_lines):
            yield _f(page, line, code, message, fix)
    for page, line, code, message, fix in readload.phrase_findings(vault):
        yield _f(page, line, code, message, fix)


def release_rules(vault, today):
    """E340-E342 and W343. A release row must name a requirement of this vault and criteria it has; each release a
    state. Once any release exists, a requirement at assumption or later that no release delivers is a warning:
    nothing says when it ships."""
    found = releases.releases(vault)
    if not found:
        return
    page = releases.page(vault)
    reqs = {r.id: r for r in allocation.requirements(vault)}
    for release in found:
        if not is_date(release.target):
            yield _f(page, release.line, "E344", f"Release '{release.name}' has Target '{release.target or 'none'}', not a YYYY-MM-DD date.",
                     "Add '- **Target:** 2027-01-15' under its heading; a bad date drops it from the timeline.")
        if release.state not in releases.STATES:
            yield _f(page, release.line, "E342", f"Release '{release.name}' has State '{release.state or 'none'}'.",
                     "Add '- **State:** inkling', assumption or decided under its heading.")
        for row in release.rows:
            if row.requirement not in reqs:
                yield _f(page, row.line, "E340", f"A row of '{release.name}' names {row.requirement or 'no requirement'}, "
                         "which is not a CAP-nnn.FRn heading in this vault.", "Link the requirement's heading.")
                continue
            _, problem = releases.criteria_of(row.raw_criteria)
            count = releases.criteria_count(reqs[row.requirement])
            over = [n for n in row.criteria if n > count or n < 1]
            if problem or over:
                yield _f(page, row.line, "E341", f"A row of '{release.name}' asks for "
                         f"{problem or ', '.join(f'AC{n}' for n in over)} of {row.requirement}, which lists {count} criteria.",
                         "Write all, or ACn for the nth acceptance criterion under the requirement.")
    delivered = {row.requirement for r in found for row in r.rows}
    for req in allocation.due(vault):
        if req.id not in delivered:
            yield _f(req.page, req.line, "W343", f"{req.id} is at {req.fact('State')}, but no release on 04b-releases.md "
                     "delivers it, so nothing says when it ships.", "Add it to the release that delivers it.")


def flow_sender_rules(vault, today):
    """E350 and W351. A step that names a sender and receiver must name two parties its linked contract joins; a
    step that links a contract and names none leaves the explorer guessing the direction. W351 only warns: a
    step can honestly be one actor's act, and every flow written before the pair existed has it."""
    for step in flows.steps(vault):
        if not step.contracts:
            continue
        if not step.pair:
            yield _f(step.page, step.line, "W351", f"Step {step.number} links {step.contracts[0].id} but names no sender and receiver, "
                     "so a reader can only guess the direction.",
                     "Start the step with 'Sender -> Receiver:', or leave it if one actor does it alone.")
            continue
        ends = [flows.endpoint(vault, step.page, text) for text in step.pair]
        for contract in step.contracts:
            joined = flows.contract_parties(vault, contract)
            stray = [text for text, key in zip(step.pair, ends) if key not in joined]
            if stray or ends[0] == ends[1]:
                yield _f(step.page, step.line, "E350", f"Step {step.number} says {step.pair[0]} sends to {step.pair[1]} over "
                         f"{contract.id}, which joins {', '.join(sorted(joined))}.",
                         "Name the two ends of the contract, or link the contract the step really uses.")
                break


def flow_capability_rules(vault, today):
    """W358 and E359. A flow's `capabilities:` is what groups it in the explorer's flow picker, first one primary. A
    vault that has capability pages should say which one each journey serves (a warning: the picker guesses from the
    steps until it is written); an ID that is not a capability page would group the flow under nothing (an error)."""
    known = {c.id for c in vault.of_type("capability")}
    for flow in vault.of_type("flow"):
        named = flow.meta.get("capabilities")
        if not named:
            if known:
                yield _f(flow, 1, "W358", f"{flow.id} names no capability, so the flow picker can only guess where it belongs.",
                         "Add capabilities: [CAP-nnn] to its frontmatter, the capability the journey serves.")
            continue
        if not isinstance(named, list):
            continue  # E105 already says it must be a list
        for value in named:
            if isinstance(value, str) and value not in known:
                yield _f(flow, meta_line(flow, "capabilities"), "E359", f"{flow.id} names '{value}', which is not a capability page.",
                         "Use the ID of a capability page, such as CAP-013, or take it out.")


def domain_rules(vault, today):
    """W352 and W353. Once any app names a domain, a large initiative's other apps should; two spellings of one
    domain split the Group: Domain view in two."""
    named = [p for p in vault.apps + vault.of_type("capability") if isinstance(p.meta.get("domain"), str) and p.meta["domain"].strip()]
    if not named:
        return
    if len(vault.apps) >= schema.DOMAIN_MIN_APPS and any(p in named for p in vault.apps):
        for app in vault.apps:
            if app not in named:
                yield _f(app, 1, "W352", f"{app.id} has no domain, but other apps in this {len(vault.apps)}-app initiative do.",
                         "Add 'domain: <name>' to its frontmatter, using the area your people already call it.")
    spellings = {}
    for page in named:
        spellings.setdefault(" ".join(page.meta["domain"].split()), []).append(page)
    groups = {}
    for spelling in spellings:
        groups.setdefault(re.sub(r"s$", "", spelling.lower()), []).append(spelling)
    for same in groups.values():
        if len(same) < 2:
            continue
        common = max(same, key=lambda s: (len(spellings[s]), s))
        for spelling in same:
            if spelling != common:
                for page in spellings[spelling]:
                    yield _f(page, meta_line(page, "domain"), "W353", f"Domain '{spelling}' and '{common}' differ only by case or a trailing s.",
                             f"Use one spelling, probably '{common}', so the apps group together.")


def ask_rules(vault, today):
    """W355. An **Ask:** that names the owner says nothing the Owner line does not."""
    for unknown in vault.unknowns:
        ask, owner = unknown.fact("Ask"), unknown.fact("Owner")
        if ask.startswith("@") and owner and ask.split()[0] == owner.split()[0]:
            yield _f(unknown.page, unknown.facts["Ask"].line, "W355", f"{unknown.id} asks the person who owns it.",
                     "Delete the Ask line, or name the person or role who actually holds the answer.")


def requirement_coverage_rules(vault, today):
    """W356 and W357. Once a vault has written any requirement, a changing capability left with none leaves the
    explorer's requirement door looking finished; a requirement with no acceptance criteria gives a release no AC to cite."""
    written = allocation.requirements(vault)
    if vault.apps and written:  # a vault that never ran Requirements is reported by planner next and planner capture
        have = {r.id.split(".")[0] for r in written}
        for cap in sorted(vault.of_type("capability"), key=lambda p: p.id):
            change = cap.meta.get("change")
            if change in schema.ENUMS["change@capability"] and change != "unchanged" and cap.id not in have:
                yield _f(cap, meta_line(cap, "change"), "W356", f"{cap.id} is {change} but has no functional requirements.",
                         "Run /planner:requirements on it, or set change: unchanged if nothing changes.")
    for req in allocation.requirements(vault):
        if releases.criteria_count(req) == 0:
            yield _f(req.page, req.line, "W357", f"{req.id} lists no acceptance criteria, so a release cannot say which it delivers.",
                     "Add the checks that must hold as plain bullets under the requirement.")


def certainty_rules(vault, today):
    for unit_id, page, line, decisions in decided_units(vault):
        sessions = [vault.resolve(l, page) for b in decisions for l in b.links]
        sessions = [s for s in sessions if s is not None and s.type == "session"]
        modes = [m for s in sessions for m in _modes(s)]
        if "grill" in modes:
            continue
        if "requirements" in modes:
            yield _f(page, line, "E317", f"{unit_id} is decided by a requirements session, which can only write assumptions.",
                     "Run a Grill on it and link that session in **Decision:**, or set it back to assumption.")
        else:
            yield _f(page, line, "E303", f"{unit_id} is decided, but no **Decision:** bullet links a Grill session.",
                     "Add '- **Decision:** [[<grill session>]]', or set the state back to assumption.")
    for page in vault.pages:
        if readable(page) and page.meta.get("state") == "fact" and not page.meta.get("sources"):
            yield _f(page, meta_line(page, "state"), "E304", f"{page.id} is a fact but lists no sources.",
                     "Add sources: [SRC-nn], or lower the state to assumption.")
    for page in vault.pages:
        if page.meta.get("sources") or page.meta.get("state") == "fact":
            continue  # a fact page without sources is already one E304
        for row_id, line in goal_rows_at(page, "fact"):
            yield _f(page, line, "E304", f"Goal {row_id} is a fact but this page lists no sources.",
                     "Add sources: [SRC-nn] to the page, or lower the goal to assumption.")
    for contract in (*vault.contracts, *vault.requirements):
        if contract.fact("State") == "fact" and not contract.fact("Source"):
            yield _f(contract.page, contract.line, "E304", f"{contract.id} is a fact but has no **Source:** bullet.",
                     "Add '- **Source:** SRC-nn', or lower the state to assumption.")
    yield from _gate_four(vault)


def _gate_four(vault):
    for unknown in vault.unknowns:
        if unknown.fact("State") != "open" or "Blocks" not in unknown.facts:
            continue
        for link in unknown.facts["Blocks"].links:
            for unit_id, state, page, line in blocked_units(vault, link, unknown.page):
                if state != "decided":
                    continue
                back = "set it to reopened" if page.meta.get("type") == "epic" else "set it back to assumption"
                yield _f(page, line, "E316", f"{unit_id} is decided, but open unknown {unknown.id} blocks it.",
                         f"Resolve {unknown.id} first, or {back}.")


# --------------------------------------------------------------------- stage

def stage_rules(vault, today):
    for app in vault.apps:
        change, stage = app.meta.get("change"), app.meta.get("stage")
        if change not in schema.ENUMS["change@app-building-blocks"]:
            continue  # E103 or E105 already reports it
        if change in schema.LADDERED_CHANGES and not stage:
            yield _f(app, meta_line(app, "change"), "E319", f"{app.id} is {change} but has no stage.",
                     "Add stage: baseline (or the stage the app is in now).")
        if change and change not in schema.LADDERED_CHANGES and stage:
            yield _f(app, meta_line(app, "stage"), "E319", f"{app.id} is {change}, so it sits outside the ladder and takes no stage.",
                     "Remove the stage field, or set change: changed if the app now changes.")


# ------------------------------------------------------------------ concerns

def concern_rules(vault, today):
    app_names = {a.name.lower(): a for a in vault.apps}
    for concern in sorted(vault.of_type("concern"), key=lambda p: p.id):
        seen = set()
        for cell in (c for c in vault.cells if c.concern is concern):
            if cell.app and cell.app.lower() in seen:
                yield _f(concern, cell.line, "E210", f"{cell.app} already has a cell on this page, so this row is ignored.",
                         "Keep one row per app on a concern page.")
                continue
            seen.add(cell.app.lower())
            label = cell.app or "a row"
            if not cell.app:
                yield _f(concern, cell.line, "E301", "A cell row does not link an app page in its App column.",
                         "Write the App column as [[<app>-building-blocks|<App name>]].")
                continue
            if cell.app.lower() not in app_names:
                if vault.page(cell.app) is not None:
                    yield _f(concern, cell.line, "E301", f"The App column links {cell.app}, which is not an app page.",
                             "Link the app's building-blocks page, for example [[<app>-building-blocks|<App name>]].")
                continue  # a missing page is already reported as E201
            if cell.state not in schema.CELL_STATES:
                yield _f(concern, cell.line, "E301", f"Cell for {label} has state '{cell.state}'.",
                         "Use one of: " + ", ".join(schema.CELL_STATES) + ".")
            elif cell.state == "n/a" and not cell.text:
                yield _f(concern, cell.line, "E301", f"Cell for {label} is n/a with no reason.",
                         "Say in the next column why the concern does not apply.")
            elif cell.state == "unknown" and not any(l.anchor.startswith("UNK-") for l in cell.links):
                yield _f(concern, cell.line, "E301", f"Cell for {label} is unknown but links no unknown.",
                         "Link the unknown, for example [[11-unknowns-and-risks#UNK-004 Kiosk authentication|UNK-004]].")
        line = cell_table(concern).line if cell_table(concern) else 1
        for name, app in sorted(app_names.items()):
            if name not in seen:
                yield _f(concern, line, "E315", f"No cell for {app.id} on this concern page, so it counts as unexamined.",
                         f"Add a row for [[{app.name}|{str(app.meta.get('title') or app.name)}]] with its state.")


# ------------------------------------------------------------------ diagrams

FLOW_SKIP = re.compile(r"^(flowchart|graph|classDef|class|style|linkStyle|click|direction|end)\b|^%%")
EDGE_TEXT = re.compile(r"(?<![-.=])--\s+.+?\s+--[->ox]|(?<![-.=])-\.\s+.+?\s+\.-[->ox]|(?<![-.=])==\s+.+?\s+==[=>ox]")
PIPE_LABEL = re.compile(r"\|[^|]*\|")
QUOTED = re.compile(r'"[^"]*"')
SHAPES = re.compile(r"\[\[.*?\]\]|\[\(.*?\)\]|\(\[.*?\]\)|\(\(.*?\)\)|\{\{.*?\}\}|\[.*?\]|\(.*?\)|\{.*?\}|(?<=[A-Za-z0-9_])>[^\]]*\]")
CLASS_SUFFIX = re.compile(r":::[\w-]+")
EDGE_OP = re.compile(r"<?[-.=~]{2,}[->ox]?|&")
NODE_ID = re.compile(r"^[A-Za-z0-9_](?:[A-Za-z0-9_.-]*[A-Za-z0-9_])?$")
STATEMENT_SEPARATOR = re.compile(r';(?=(?:[^"]*"[^"]*")*[^"]*$)')
PARTICIPANT = re.compile(r"^\s*(?:create\s+)?(?:participant|actor)\s+(\S+)")
SEQ_ID = r"[A-Za-z0-9_](?:[A-Za-z0-9_.-]*[A-Za-z0-9_])?"
MESSAGE = re.compile(rf"^\s*({SEQ_ID})\s*(?:<<-->>|<<->>|-->>|->>|-->|->|--x|-x|--\)|-\))\s*[+-]?\s*({SEQ_ID})\s*:")


def flowchart_elements(lines):
    """Distinct node IDs plus subgraphs, in Mermaid flowchart lines."""
    nodes, subgraphs, subgraph_ids = set(), 0, set()
    statements = (part for raw in lines for part in STATEMENT_SEPARATOR.split(raw))
    for raw in statements:
        line = raw.strip()
        if not line or FLOW_SKIP.match(line):
            continue
        if line.startswith("subgraph"):
            subgraphs += 1
            rest = line[len("subgraph"):].strip()
            match = re.match(r"[A-Za-z0-9_]+", rest)
            if match:
                subgraph_ids.add(match.group(0))
            continue
        line = QUOTED.sub("", line)
        line = EDGE_TEXT.sub(" --> ", line)
        line = PIPE_LABEL.sub(" ", line)
        line = SHAPES.sub(" ", line)
        line = CLASS_SUFFIX.sub(" ", line)
        line = EDGE_OP.sub(" ", line)
        nodes.update(t for t in line.split() if NODE_ID.match(t))
    return len(nodes - subgraph_ids) + subgraphs


def sequence_participants(lines):
    names = []
    for raw in lines:
        match = PARTICIPANT.match(raw)
        if match:
            names.append(match.group(1))
            continue
        match = MESSAGE.match(raw)
        if match:
            names.extend([match.group(1), match.group(2)])
    return len(set(names))


def diagram_rules(vault, today):
    for page in vault.pages:
        for diagram in page.diagrams:
            if diagram.kind in ("flowchart", "graph"):
                count = flowchart_elements(diagram.lines)
                if count > schema.FLOWCHART_BUDGET:
                    yield _f(page, diagram.line, "E601", f"This flowchart has {count} elements; the budget is {schema.FLOWCHART_BUDGET}.",
                             "Split it into two diagrams, or draw one level higher.")
            elif diagram.kind == "sequenceDiagram":
                count = sequence_participants(diagram.lines)
                if count > schema.SEQUENCE_BUDGET:
                    yield _f(page, diagram.line, "E602", f"This sequence diagram has {count} participants; the budget is {schema.SEQUENCE_BUDGET}.",
                             "Merge lanes that play the same part, or split the flow.")
            else:
                yield _f(page, diagram.line, "E603", f"Mermaid '{diagram.kind or 'empty'}' diagrams are not supported, so their size is never checked.",
                         "Draw it as a flowchart or a sequenceDiagram.")


# ------------------------------------------------------------ generated blocks

def block_rules(vault, today):
    unreadable = [p for p in vault.pages if not readable(p)]
    for page in vault.pages:
        if not readable(page):
            continue
        for block in page.blocks:
            if not render.block_allowed(page, block.name):
                where = schema.BLOCKS.get(block.name)
                why = f"It belongs on {where.replace('type:', 'pages of type ')}." if where else "No generator has this name."
                yield _f(page, block.start, "E403", f"Generated block '{block.name}' is not allowed on this page. {why}",
                         "Remove the block, or move it to the right page.")
                continue
            current = render.normalise(block.content)
            if current and render.block_hash(current) != block.sha:
                yield _f(page, block.start, "E401", f"Someone edited the '{block.name}' block by hand. The next render would overwrite it.",
                         "Undo the edit and change the source pages instead, or run planner render --discard-edits.")
                continue
            if unreadable:
                continue  # a page the model cannot read would make every staleness verdict a guess
            if current != render.block_content(vault, page, block.name):
                yield _f(page, block.start, "W402", f"The '{block.name}' block is out of date.",
                         "Run planner render.")


# ----------------------------------------------------------------- freshness

def days_between(earlier, later):
    return (datetime.date.fromisoformat(later) - datetime.date.fromisoformat(earlier)).days


def stale_after_days(config):
    """The vault's window, or the default. The CLI refuses a bad value before any rule runs."""
    value = config.get("stale_after_days", schema.STALE_AFTER_DAYS)
    return value if isinstance(value, int) and not isinstance(value, bool) and value > 0 else schema.STALE_AFTER_DAYS


def freshness_rules(vault, today):
    """W704, W716 and W711. All are warnings: a page nobody has reread never blocks a PR."""
    window = stale_after_days(vault.config)
    for page in vault.pages:
        verified = page.meta.get("last_verified")
        if not readable(page) or not is_date(verified):
            continue  # a missing field is not judged; a malformed one is already an E106
        age = days_between(verified, today)
        if age < 0:
            yield _f(page, meta_line(page, "last_verified"), "W704",
                     f"{page.id} last_verified is dated in the future ({verified}); check for a typo.",
                     "Set last_verified to the date you last reread the page, no later than today.")
        elif age > window:
            yield _f(page, meta_line(page, "last_verified"), "W704",
                     f"{page.id} was last verified on {verified}, {age} days ago; stale_after_days is {window}.",
                     "Reread the page against its sources, then set last_verified to today and verified_by to your handle.")
    for page in vault.of_type("sources"):
        for table in page.tables:
            if table.generated or tuple(table.header)[:len(schema.SOURCES_HEADER)] != schema.SOURCES_HEADER:
                continue
            for row, line in zip(table.rows, table.row_lines):
                source, date = (row[0] if row else ""), (row[3] if len(row) > 3 else "")
                if not is_date(date):
                    yield _f(page, line, "W716", f"{source} has Date '{date}', which is not a YYYY-MM-DD date, so its age cannot be judged.",
                             "Write the document's date as YYYY-MM-DD.")
                elif days_between(date, today) < 0:
                    yield _f(page, line, "W716", f"{source} is dated in the future ({date}); check for a typo.",
                             "Write the document's own date, no later than today.")
                elif days_between(date, today) > window:
                    yield _f(page, line, "W716", f"{source} is dated {date}, {days_between(date, today)} days ago; stale_after_days is {window}.",
                             "Check the document still says what the vault cites, then update its Date, or register the newer version.")
    closed = [s for s in vault.sessions if s.meta.get("status") == "closed" and is_date(s.meta.get("date"))]
    if closed:
        last = max(closed, key=lambda s: (s.meta["date"], s.name))
        gap = days_between(last.meta["date"], today)
        if gap < 0:  # a typo here would hide every real gap until the date passes, so it is said, not skipped
            yield _f(last, meta_line(last, "date"), "W711",
                     f"The last closed session is dated in the future ({last.meta['date']}); check for a typo.",
                     "Set the session's date to the day it ran.")
        elif gap > schema.SESSION_GAP_DAYS:
            yield _f(last, meta_line(last, "date"), "W711",
                     f"The last session closed on {last.meta['date']}, {gap} days ago.",
                     "Run a session, even a short Probe of the overdue unknowns, so the vault keeps up with the work.")


# ------------------------------------------------------------- traceability

def trace_findings(vault, gated):
    """One finding per trace gap: a warning, or an error under the gate."""
    for gap in trace.report(vault).gaps:
        warning, error = schema.TRACE_CODES[gap.rule]
        line = gap.line or meta_line(gap.page, gap.field)
        yield _f(gap.page, line, error if gated else warning, f"{gap.rule}: {gap.message}", gap.fix)


def trace_rules(vault, today):
    """T1, T2, T4 and T6 as warnings, once the vault has its first epic; T7 once it has its first app page.

    Before the first epic every changing capability would warn on every PR for months,
    and a warning nobody can act on teaches people to skip the output. T7 is different:
    allocation comes before epics, so it is the warning that allocate session acts on.
    """
    if vault.of_type("epic"):
        yield from trace_findings(vault, gated=False)
    elif vault.apps:
        yield from (f for f in trace_findings(vault, gated=False) if f.code == schema.TRACE_CODES["T7"][0])


def link_field_rules(vault, today):
    """E105 for a `links:` map, a **Links:** bullet or an `icon:` planner cannot read. Links are never fetched."""
    _, broken = links.templates(vault.config)
    for problem in broken:
        page = next((p for p in vault.pages if p.meta.get(schema.LINKS_FIELD)), None)
        if page is not None:  # a template nobody uses breaks nothing
            yield _f(page, meta_line(page, schema.LINKS_FIELD), "E105", problem + ".",
                     "Write it as link_templates: {Tracker: \"https://tracker.example.com/browse/{key}\"}.")
    for page in vault.pages:
        if not page.meta:
            continue
        for problem in links.of_page(page, vault.config)[1]:
            yield _f(page, meta_line(page, schema.LINKS_FIELD), "E105", problem[0].upper() + problem[1:] + ".",
                     "Write each link as Label: https://..., or add a link_templates entry for the label to .planner.yaml.")
        icon = page.meta.get(schema.ICON_FIELD)
        if icon is not None and not (isinstance(icon, str) and schema.ICON_RE.match(icon)):
            yield _f(page, meta_line(page, schema.ICON_FIELD), "E105", f"'icon: {icon}' is not one short lower-case word.",
                     "Write icon: payments, or remove the field; views pick an icon from the title without it.")
        design = page.meta.get(schema.DESIGN_FIELD)
        if design is not None and not (isinstance(design, str) and design.strip()):
            yield _f(page, meta_line(page, schema.DESIGN_FIELD), "E105", f"'design: {design}' is not a path to a design doc.",
                     "Write design: ../team-repo/docs/tech-design/booking.md, relative to the vault root, or remove the field.")
    for found in vault.items.values():
        item = found[0]
        for problem in links.of_item(item)[1]:
            yield _f(item.page, item.facts[schema.LINKS_LABEL].line, "E105", problem + ".",
                     "Write - **Links:** [API spec](https://...), [Docs](https://...).")


BARE_LINK_PIPE = re.compile(r"\[\[[^\[\]\n|]*(?<!\\)\|[^\[\]\n]*\]\]")


def link_pipe_rules(vault, today):
    """W329: a [[link|label]] in a table row written with a bare |. Obsidian, GitHub and other Markdown readers take it
    as a column break and the row falls apart; the planner reads it as the link's, so nothing is lost here."""
    for page in vault.pages:
        lines = parse.lines_of(page.text)
        for table in page.tables:
            if table.generated:
                continue
            for line in table.row_lines:
                row = lines[line - 1] if 0 < line <= len(lines) else ""
                for link in BARE_LINK_PIPE.findall(row):
                    yield _f(page, line, "W329", f"The link {link} in a table row has a bare |, which splits the row in other readers.",
                             "Write its label pipe as \\| inside a table, as in [[page#Heading\\|label]].")


RULES = (parse_errors, frontmatter_rules, duplicate_rules, link_rules, reference_rules, table_rules,
         history_rules, page_state_rules, stale_mention_rules, allocation_rules, release_rules, flow_sender_rules, flow_capability_rules, domain_rules, ask_rules, requirement_coverage_rules, contract_rules, requirement_rules, unknown_rules, risk_rules, subject_rules, question_rules, certainty_rules, stage_rules, concern_rules,
         diagram_rules, block_rules, trace_rules, freshness_rules, link_field_rules, link_pipe_rules, reading_load_rules)
