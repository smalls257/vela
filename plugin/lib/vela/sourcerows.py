"""The Library register, read by header name (CONVENTIONS "Certainty and sources").

`sources.md` is the Library: every document, spec, design and link the plan rests on or builders need. The header is
`ID | Title | Owner | Date | Kind | Type | Relates to | Version | Stored | Location`, but a register written before
Type, Relates to, Version and Stored existed has six columns and still reads: a missing column is empty, and an empty
Type is `document`. Reading by name (not by position) is what lets the two shapes live together without five modules
each counting to column 5 (a Distributed Monolith in larval form).

Pure: text in, rows out. Whether a stored file exists is the edge's question (cli.source_file_findings).
"""
import re
from collections import namedtuple

CORE = ("ID", "Title", "Owner", "Date", "Kind")
HEADER = CORE + ("Type", "Relates to", "Version", "Stored", "Location")
TYPES = ("spec", "design", "document", "wiki", "tracker", "link")
DEFAULT_TYPE = "document"
# Where a stored file lives: library/<folder>/. A spec has its own folder because the flow checker reads it; a design
# is a mock or export; everything else a person keeps is a document.
STORE_FOLDERS = ("specs", "designs", "documents")
LIBRARY = "library"
FOLDER_OF_TYPE = {"spec": "specs", "design": "designs"}
# "v1.0 (latest v1.1)": the version in the vault, and the newer one the owner was told of (vela never opens links).
NEWER = re.compile(r"^(?P<version>.*?)\s*\(\s*latest\s+(?P<newer>[^()]+?)\s*\)\s*$", re.IGNORECASE)

Row = namedtuple("Row", "id title owner date kind type relates version newer stored location")


def is_register(header):
    """True for the Library's table: the five core columns first, and a Location column somewhere."""
    head = tuple(h.strip() for h in header)
    return head[:len(CORE)] == CORE and "Location" in head


def folder_for(source_type):
    """The library folder a file of this type is kept in."""
    return FOLDER_OF_TYPE.get(source_type, "documents")


def split_version(text):
    """(version, newer) from `v1.0 (latest v1.1)`; newer is empty when the cell names no later version."""
    found = NEWER.match(text or "")
    if found is None:
        return (text or "").strip(), ""
    return found["version"].strip(), found["newer"].strip()


def read(header, cells):
    """One Row from a table row, by the table's own header names."""
    head = tuple(h.strip() for h in header)

    def cell(name):
        index = head.index(name) if name in head else None
        return cells[index].strip() if index is not None and index < len(cells) else ""

    version, newer = split_version(cell("Version"))
    return Row(id=cell("ID"), title=cell("Title"), owner=cell("Owner"), date=cell("Date"), kind=cell("Kind"),
               type=cell("Type") or DEFAULT_TYPE, relates=tuple(cell("Relates to").split()), version=version,
               newer=newer, stored=cell("Stored"), location=cell("Location"))


def stored_problem(row):
    """Why a Stored path is not a library path, or None: `library/<folder>/<file>`, no `..`, no leading slash."""
    parts = row.stored.split("/")
    if parts[0] != LIBRARY or len(parts) < 3 or any(p in ("", ".", "..") for p in parts):
        return f"Stored is '{row.stored}', not a path like {LIBRARY}/{folder_for(row.type)}/<file>."
    if parts[1] not in STORE_FOLDERS:
        return f"Stored is in {LIBRARY}/{parts[1]}/, and the folders are {', '.join(STORE_FOLDERS)}."
    if row.type == "spec" and parts[1] != "specs":
        return f"A spec is kept in {LIBRARY}/specs/, and Stored says {LIBRARY}/{parts[1]}/."
    return None
