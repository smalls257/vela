"""Vault model to findings. Pure: `today` is passed in, nothing reads the disk.

Every rule runs on every page it can read. No rule stops the others.
"""
import datetime

from planner import schema
from planner.model import Finding


def check(vault, today):
    """All findings for the vault, sorted by path, line and code."""
    findings = []
    for rule in RULES:
        findings.extend(rule(vault, today))
    return sorted(set(findings))


# ------------------------------------------------------------------ helpers

def meta_line(page, key):
    """Line number of `key:` in the frontmatter, or 1."""
    lines = page.text.split("\n")
    for n, line in enumerate(lines[1:], start=2):
        if line.strip() == "---":
            break
        if line.startswith(f"{key}:"):
            return n
    return 1


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
    if "owner" in meta and not (isinstance(meta["owner"], str) and schema.OWNER_RE.match(meta["owner"])):
        yield _f(page, meta_line(page, "owner"), "E105", f"Owner '{meta['owner']}' is not a GitHub handle or team.",
                 "Write owner: \"@handle\" or \"@org/team\", several separated by spaces.")
    if "handed_off" in meta and not (isinstance(meta["handed_off"], str) and schema.HANDED_OFF_RE.match(meta["handed_off"])):
        yield _f(page, meta_line(page, "handed_off"), "E105", "'handed_off' is not in the form '<name>, <date>, PR #N'.",
                 "Write handed_off: \"Booking senior, 2026-11-20, PR #41\".")
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


# --------------------------------------------------------------------- links

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


RULES = (parse_errors, frontmatter_rules, duplicate_rules, link_rules, reference_rules)
