"""The Library as the dashboard's Library view reads it: one row per register line, in the register's own order.

The Violation this exists to prevent is a Leaky Narrative on the page: if view-library.js had to learn that a Figma
address means a design, that `v1.0 (latest v1.1)` means a newer version, or that "cited by" means a text search of
every page, each of those rules would live in script where no test of the vault reaches them. They are decided here,
once, from the register's rows and the pages' text, and the page only draws them.

"Cited by" is counted, never typed: a page or item cites a row when its text names the row's ID (a `sources:` line, a
`Source:` fact, an unknown's `source:` cell). Sessions and the register itself do not count; a session mentions
everything it touched and would drown the real citations (the same rule the panel's backlinks follow).

Pure: it takes the vault and the keys; whether a stored file exists is the checker's question (E313), not the page's.
"""
import re

from vela import library, say, schema, sourcerows

EXTENSION_WORD = {"pdf": "PDF", "doc": "Word", "docx": "Word", "xls": "Excel", "xlsx": "Excel", "ppt": "Slides", "pptx": "Slides"}
KEY_PREFIX = "lib:"
ITEM_HEADING = re.compile(r"^\s*([A-Z]+-\d[\w.]*)\b")


def register_rows(vault):
    """Every Library row of the vault's register page(s), by header name."""
    found = []
    for page in vault.of_type("sources"):
        for table in page.tables:
            if table.generated or not sourcerows.is_register(table.header):
                continue
            found += [sourcerows.read(table.header, cells) for cells in table.rows]
    return [row for row in found if schema.SOURCE_ID_RE.match(row.id)]


def extension(path):
    return path.rsplit(".", 1)[-1].lower() if "." in path.rsplit("/", 1)[-1] else ""


def format_of(row):
    """What the item is, in a word a person knows: OpenAPI, Figma, PDF, Confluence, Jira."""
    host, _ = library.host_and_path(row.location)
    name = (row.stored or row.location).lower()
    if row.type == "spec":
        if "asyncapi" in name:
            return "AsyncAPI"
        return "OpenAPI" if "openapi" in name or "swagger" in name else "API spec"
    if row.type == "design":
        return "Figma" if host.endswith("figma.com") else "Design"
    if row.type == "wiki":
        return "Confluence" if host.endswith("atlassian.net") or host.endswith("atlassian.com") else "Wiki"
    if row.type == "tracker":
        return "Jira" if host.endswith("atlassian.net") or host.endswith("atlassian.com") else "Tracker"
    if row.type == "link":
        return "Link"
    return EXTENSION_WORD.get(extension(row.stored), extension(row.stored).upper() or "Document")


def is_web_address(text):
    return text.lower().startswith(("http://", "https://"))


def where_kept(row):
    """newer (a later version is out), both (a link and a kept file), vault (a kept file), link (a web address only) or
    listed (a row that says where it lives, in words: "Procurement, local only"; there is nothing to open)."""
    if row.newer:
        return "newer"
    if row.stored and row.location:
        return "both"
    if row.stored:
        return "vault"
    return "link" if is_web_address(row.location) else "listed"


def relate_key(vault, keys, ident, register_ids):
    """The key the page names an item by: an item ID, a page's ID, or another Library row. None when it names nothing."""
    if vault.item(ident) is not None:
        return ident
    pages = vault.by_id.get(ident)
    if pages:
        return keys.page(pages[0])
    return KEY_PREFIX + ident if ident in register_ids else None


def citations(vault, keys, ids):
    """{row ID: [key, ...]}: the items and pages whose text names the ID, an item when the mention sits inside one."""
    found = {i: [] for i in ids}
    for page in vault.pages:
        if page.type in ("sources", "session") or page.path.startswith("voice/"):
            continue
        headings = sorted(page.headings, key=lambda h: h.line)
        for number, line in enumerate(page.text.split("\n"), start=1):
            for token in schema.SOURCE_TOKEN_RE.findall(line):
                if token not in found:
                    continue
                key = _owner_key(vault, keys, page, headings, number)
                if key not in found[token]:
                    found[token].append(key)
    return found


def _owner_key(vault, keys, page, headings, number):
    """The item whose section holds this line, else the page."""
    above = [h for h in headings if h.line <= number]
    if above:
        match = ITEM_HEADING.match(above[-1].text)
        item = vault.item(match.group(1)) if match else None
        if item is not None and item.page is page:
            return item.id
    return keys.page(page)


def plain_title(text):
    """A title may name someone by handle; the page says the name (the rule item headings follow)."""
    return say.LEAD_PATTERNS["handle"].sub(lambda m: say.person_words(m.group(0)), text)


def extract(vault, keys):
    """{"rows": [...]}: each row with its key, format, where it is kept, what it relates to and what cites it."""
    rows = register_rows(vault)
    ids = {r.id for r in rows}
    cited = citations(vault, keys, ids)
    out = []
    for r in rows:
        relates = [k for k in (relate_key(vault, keys, i, ids) for i in r.relates) if k]
        out.append({"id": r.id, "key": KEY_PREFIX + r.id, "title": plain_title(r.title), "type": r.type, "format": format_of(r), "owner": r.owner,
                    "date": r.date, "kind": r.kind, "version": r.version, "newer": r.newer, "stored": r.stored, "location": r.location,
                    "where": where_kept(r), "web": is_web_address(r.location), "ext": EXTENSION_WORD.get(extension(r.stored), "file") if r.stored else "",
                    "relates": relates, "citedBy": cited[r.id]})
    return {"rows": out}
