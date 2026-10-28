"""The Library's pure parts: what type a link or file is, what a kept file is called, a spec's version, and the
register's rows grouped by type (`vela library add|list`).

The Violation this exists to prevent is a Leaky Narrative at the call site: if `vela library add` made the caller say
`--type design` for every Figma link, the lead's skill would carry host names it had to learn from source. The guess
lives here once, and `--type` is only for overriding it. Text and names in, answers out; the file copy, the size and
the git calls are the command's (Buffer).

Vela never opens a link, so a URL is typed by its address alone. A local file is read, because a spec says what it is
in its first lines (`openapi:`, `asyncapi:`, `swagger:`).
"""
import json
import re

from vela import parse, sourcerows

MAX_BYTES = 20 * 1024 * 1024  # past this a link is the better row; the file is still kept, with a note
SPEC_KEYS = ("openapi", "asyncapi", "swagger")
SPEC_EXTENSIONS = (".yaml", ".yml", ".json")
_SPEC_NAME = re.compile(r"(openapi|asyncapi|swagger)", re.IGNORECASE)
_YAML_SPEC = re.compile(r"^(?:openapi|asyncapi|swagger)\s*:", re.MULTILINE)
_YAML_INFO = re.compile(r"^info\s*:\s*$")
_YAML_VERSION = re.compile(r"^\s+version\s*:\s*(.+?)\s*$")


def host_and_path(url):
    """(lowercase host, lowercase path) of a URL; ("", "") for anything that is not an address."""
    found = re.match(r"^[a-z][a-z0-9+.-]*://(?:[^/@\s]*@)?([^/:\s?#]+)(?::\d+)?(/[^?#\s]*)?", url.strip(), re.IGNORECASE)
    return (found.group(1).lower(), (found.group(2) or "").lower()) if found else ("", "")


def is_url(text):
    return host_and_path(text)[0] != ""


def type_of_url(url):
    """Figma is a design; Atlassian's /wiki or Confluence is a wiki; /browse and Jira are a tracker; a YAML or JSON
    address named like a spec is a spec; anything else is a link."""
    host, path = host_and_path(url)
    if host == "figma.com" or host.endswith(".figma.com"):
        return "design"
    if host.endswith("atlassian.net") or host.endswith("atlassian.com"):
        if path.startswith("/browse") or "/jira/" in path or path.startswith("/jira"):
            return "tracker"
        if path.startswith("/wiki") or "/wiki/" in path:
            return "wiki"
    if "/wiki/" in path:
        return "wiki"
    if path.endswith(SPEC_EXTENSIONS) and _SPEC_NAME.search(path.rsplit("/", 1)[-1]):
        return "spec"
    return "link"


def spec_version(text, name):
    """(is a spec, its `info.version` or ""). JSON is parsed; YAML is read for the `info:` block's `version:` line,
    because the standard library has no YAML reader and a spec's first lines are all this needs."""
    if name.lower().endswith(".json"):
        try:
            doc = json.loads(text)
        except ValueError:
            return False, ""
        if not isinstance(doc, dict) or not any(k in doc for k in SPEC_KEYS):
            return False, ""
        info = doc.get("info")
        return True, str(info.get("version", "")) if isinstance(info, dict) else ""
    if not _YAML_SPEC.search(text):
        return False, ""
    inside = False
    for line in text.splitlines():
        if _YAML_INFO.match(line):
            inside = True
        elif inside and line.strip() and not line[0].isspace():
            inside = False
        elif inside and (found := _YAML_VERSION.match(line)):
            return True, found.group(1).strip("'\"")
    return True, ""


def type_of_file(name, text):
    """(type, version) for a local file: a spec when its content says so, else a document."""
    is_spec, version = spec_version(text, name) if name.lower().endswith(SPEC_EXTENSIONS) else (False, "")
    return ("spec", version) if is_spec else ("document", "")


def version_cell(version):
    """`1.2.0` is written `v1.2.0`, the way the register shows versions; one already starting with a letter is kept."""
    return f"v{version}" if version[:1].isdigit() else version


def slug(text):
    """Lowercase letters and digits joined by single hyphens; empty when nothing is left."""
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


def stored_name(source_type, title, filename):
    """What a kept file is called in library/<folder>/. A spec keeps its own name (slugged around its dots), because
    the flow checker finds the provider app from `<app>.openapi.yaml`; everything else is named from its title."""
    stem, dot, ext = filename.rpartition(".") if "." in filename else (filename, "", "")
    extension = f".{ext.lower()}" if dot else ""
    if source_type == "spec":
        kept = ".".join(part for part in (slug(p) for p in stem.split(".")) if part)
        return (kept or slug(title) or "spec") + extension
    return (slug(title) or slug(stem) or "file") + extension


def rows(register_text):
    """Every Library row of a sources.md text, in file order, read by header name."""
    page = parse.parse_page("sources.md", register_text)
    found = []
    for table in page.tables:
        if table.generated or not sourcerows.is_register(table.header):
            continue
        found += [sourcerows.read(table.header, cells) for cells in table.rows]
    return found


def row_json(row):
    return {"id": row.id, "title": row.title, "owner": row.owner, "date": row.date, "kind": row.kind,
            "type": row.type, "relates": list(row.relates), "version": row.version, "newer": row.newer,
            "stored": row.stored, "location": row.location}


def grouped(found, only=None):
    """[(type, [Row, ...])] in the order of `sourcerows.TYPES`, a type with no rows left out."""
    return [(kind, [r for r in found if r.type == kind]) for kind in sourcerows.TYPES
            if (only is None or kind == only) and any(r.type == kind for r in found)]
