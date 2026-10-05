"""The vault vocabulary: page types, fields, enums, ID patterns, fact labels,
generated block names and finding codes.

CONVENTIONS.md explains every name defined here, and a test fails if one is
missing from it. Change a name here and in CONVENTIONS.md in the same commit.
"""
import re

# ---------------------------------------------------------------- page types

STATE_ITEM = ("inkling", "assumption", "fact", "decided")

# Per page type: required fields, optional fields, and the enum for `state`
# (None means the type has no `state` field).
PAGE_TYPES = {
    "index": {
        "required": ("id", "type", "title", "authored"),
        "optional": ("initiative", "arc42", "c4", "owner", "sources"),
        "states": None,
    },
    "initiative-section": {
        "required": ("id", "type", "title", "state", "owner", "authored"),
        "optional": ("initiative", "arc42", "c4", "sources"),
        "states": STATE_ITEM,
    },
    "app-building-blocks": {
        "required": ("id", "type", "title", "state", "owner", "authored", "change"),
        "optional": ("stage", "initiative", "arc42", "c4", "sources", "handed_off"),
        "states": STATE_ITEM,
    },
    "app-runtime": {
        "required": ("id", "type", "title", "state", "owner", "authored"),
        "optional": ("initiative", "arc42", "sources"),
        "states": STATE_ITEM,
    },
    "flow": {
        "required": ("id", "type", "title", "state", "owner", "authored"),
        "optional": ("initiative", "arc42", "sources"),
        "states": STATE_ITEM,
    },
    "concern": {
        "required": ("id", "type", "title", "owner", "authored"),
        "optional": ("initiative", "arc42", "sources"),
        "states": None,
    },
    "decision": {
        "required": ("id", "type", "title", "state", "owner", "authored"),
        "optional": ("initiative", "arc42", "sources"),
        "states": ("proposed", "decided", "superseded", "rejected"),
    },
    "epic": {
        "required": ("id", "type", "title", "state", "owner", "authored", "apps", "delivers"),
        "optional": ("consumes", "flows", "depends_on", "initiative", "sources"),
        "states": ("draft", "decided", "reopened"),
    },
    "capability": {
        "required": ("id", "type", "title", "state", "owner", "authored", "origin", "change"),
        "optional": ("sources", "domain"),
        "states": ("inkling", "assumption", "decided"),
    },
    "session": {
        "required": ("id", "type", "date", "modes", "status", "summary"),
        "optional": ("title",),
        "states": None,
    },
    "sources": {
        "required": ("id", "type", "title", "authored"),
        "optional": ("owner",),
        "states": None,
    },
}

# Any page but a session record may say when someone last checked it against its sources.
VERIFY_FIELDS = ("last_verified", "verified_by")
for _type, _spec in PAGE_TYPES.items():
    if _type != "session":
        _spec["optional"] = _spec["optional"] + VERIFY_FIELDS

# Field value rules shared by every type.
ENUMS = {
    "authored": ("authored", "generated", "mixed"),
    "c4": ("landscape", "context", "container"),
    "change@app-building-blocks": ("new", "changed", "integrated", "unchanged", "retired"),
    "change@capability": ("new", "extend", "replace", "narrow", "retire", "unchanged"),
    "origin": ("proposed", "imported"),
    "stage": ("baseline", "target", "boundaries", "contracts", "handoff", "epics"),
    "status": ("open", "closed"),
}
LIST_FIELDS = ("sources", "apps", "delivers", "consumes", "flows", "depends_on", "modes")
SESSION_MODES = ("dump", "discover", "shape", "grill", "requirements", "epics", "challenge", "answer")
LADDERED_CHANGES = ("new", "changed")  # app pages with these carry `stage`

HANDLE = r"@[A-Za-z0-9][A-Za-z0-9-]*(?:/[A-Za-z0-9._-]+)?"
OWNER_RE = re.compile(rf"^{HANDLE}(?: {HANDLE})*$")
OWNER_BULLET_RE = re.compile(rf"^{HANDLE}\b")
HANDED_OFF_RE = re.compile(r"^.+, \d{4}-\d{2}-\d{2}, PR #\d+$")
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
INITIATIVE_RE = re.compile(r"^INI-\d{3}$")

# ------------------------------------------------------------------ ID rules

SLUG = r"[a-z0-9]+(?:-[a-z0-9]+)*"
PAGE_ID_RE = {
    "index": re.compile(rf"^{SLUG}$"),
    "initiative-section": re.compile(rf"^{SLUG}$"),
    "app-building-blocks": re.compile(rf"^APP-{SLUG}$"),
    "app-runtime": re.compile(rf"^RUN-{SLUG}$"),
    "flow": re.compile(r"^FLO-\d{3}$"),
    "concern": re.compile(rf"^concern-{SLUG}$"),
    "decision": re.compile(r"^ADR-\d{4}$"),
    "epic": re.compile(r"^EPC-\d{3}$"),
    "capability": re.compile(r"^CAP-\d{3}$"),
    "session": re.compile(rf"^\d{{4}}-\d{{2}}-\d{{2}}-{SLUG}$"),
    "sources": re.compile(r"^sources$"),
}
ITEM_ID_RE = re.compile(r"^(CON-\d{3}|UNK-\d{3}|R-\d{2,}|CAP-\d{3}\.FR\d+)$")
GOAL_ID_RE = re.compile(r"^G\d+$")
CONSTRAINT_ID_RE = re.compile(r"^CST-\d+$")
SOURCE_ID_RE = re.compile(r"^SRC-\d{2,}$")
SOURCE_TOKEN_RE = re.compile(r"\bSRC-\d{2,}\b")


def expected_basename(page_type, page_id):
    """The basename rule for a type: an exact name, a prefix, or None."""
    if page_type == "app-building-blocks":
        return ("exact", page_id[len("APP-"):] + "-building-blocks")
    if page_type == "app-runtime":
        return ("exact", page_id[len("RUN-"):] + "-runtime")
    if page_type in ("concern", "session", "sources"):
        return ("exact", page_id)
    if page_type in ("flow", "decision", "epic", "capability"):
        return ("prefix", page_id + "-")
    return None


# ------------------------------------------------------------- fact bullets

CONTRACT_REQUIRED = ("Crosses the boundary", "Consumers", "Change policy", "Change", "State")
OPTIONS_LABEL = "Options considered"  # what Shape recorded: the picked option, and each rejected one with its reason
CONTRACT_OPTIONAL = ("Provider", "Tested by", "Source", "Decision", "Dissent", OPTIONS_LABEL)
CONTRACT_STATES = ("inkling", "assumption", "fact", "decided")
CONTRACT_CHANGES = ("new", "changed", "new consumers", "unchanged")

UNKNOWN_REQUIRED = ("Question", "Owner", "State", "Blocks")
UNKNOWN_OPEN_REQUIRED = ("Ask by",)
UNKNOWN_RESOLVED_REQUIRED = ("Outcome", "Resolved in")
UNKNOWN_OPTIONAL = ("Opened", "Notes")
UNKNOWN_STATES = ("open", "resolved")

RISK_REQUIRED = ("Owner", "State")
RISK_OPTIONAL = ("Mitigation",)
RISK_STATES = ("open", "mitigated", "accepted", "closed")

PAGE_LABELS = ("Decision", "Dissent", OPTIONS_LABEL)

# ---------------------------------------------------------------- fact tables

GOALS_HEADER = ("ID", "Goal", "Measure", "State")
CONSTRAINTS_HEADER = ("ID", "Constraint")
SOURCES_HEADER = ("ID", "Title", "Owner", "Date", "Kind", "Location")
SOURCE_KINDS = ("exists", "intends", "repo")
CONTAINERS_HEADER = ("Container", "Job")
CONTAINER_STATES = ("assumption", "confirmed", "unchanged", "retired")
CELLS_HEADER = ("App", "State")
CELL_STATES = ("addressed", "unchanged", "n/a", "unknown", "unexamined")
CHANGES_HEADER = ("ID", "From", "To", "Source")

# ------------------------------------------------------------ generated blocks

# Block name -> the page it may sit on: a page id, or "type:<page type>".
BLOCKS = {
    "where-it-stands": "goals",
    "concern-matrix": "concerns",
    "unknowns-index": "unknowns-and-risks",
    "contracts-consumed": "type:app-building-blocks",
    "traceability": "epics",
    "epics-for-app": "type:app-building-blocks",
    "traces-to": "type:epic",
    "delivered-by": "type:capability",
    "context-map": "building-blocks",
    "system-context": "context-and-scope",
    "app-context": "type:app-building-blocks",
    "capability-map": "capability-delta",
    "progress-map": "goals",
}
NEW_BLOCK_SHA = "00000000"

# ------------------------------------------------------------------ diagrams

FLOWCHART_BUDGET = 20
SEQUENCE_BUDGET = 8
DIAGRAM_KINDS = ("flowchart", "graph", "sequenceDiagram")

# ------------------------------------------------------------ freshness

STALE_AFTER_DAYS = 60  # default for .planner.yaml's stale_after_days
SESSION_GAP_DAYS = 30  # W711 when no session has closed for longer than this

# ------------------------------------------------------------ progress

# What `planner status`, `planner next` and the progress-map block may suggest.
NEXT_MODES = ("probe", "discover", "shape", "grill", "epics", "dump", "none")

# ------------------------------------------------------------- finding codes

CODES = {
    "E101": "page has no frontmatter",
    "E102": "frontmatter is not a valid YAML mapping",
    "E103": "required field missing",
    "E104": "unknown page type",
    "E105": "value not allowed",
    "E106": "not a YYYY-MM-DD date",
    "E107": "id does not fit its type or file name",
    "E108": "two pages share an id",
    "E201": "link to a page that does not exist",
    "E202": "link anchor matches no heading",
    "E204": "two files share a basename",
    "E207": "ID reference resolves to nothing",
    "E208": "item ID used by two headings",
    "E301": "concern cell is not valid",
    "E302": "unknown or risk is missing a required fact",
    "E303": "decided without a Grill decision",
    "E304": "fact without a source",
    "E306": "fact table row is not valid",
    "E311": "consumers name no app",
    "E315": "app has no cell on a concern page",
    "E316": "decided while an open unknown blocks it",
    "E317": "a requirements session cannot decide",
    "E318": "decided contract has no Tested by",
    "E319": "stage does not fit the app's change",
    "E320": "contract is missing a required fact",
    "E401": "generated block was edited by hand",
    "W402": "generated block is out of date",
    "E403": "generated block not allowed here",
    "E404": "generated block markers are broken",
    "E601": "flowchart over its element budget",
    "E602": "sequence diagram over its participant budget",
    "E603": "diagram type not supported",
    "W704": "page not verified within stale_after_days",
    "W705": "unknown is past its ask-by date",
    "W711": "no session closed in the last 30 days",
    "W716": "source row older than stale_after_days",
    "W501": "no epic delivers a capability that changes",
    "W502": "no epic delivers a new or changed contract",
    "W503": "no epic covers a concern cell with work",
    "W504": "epic delivers nothing",
    "E501": "no epic delivers a capability that changes",
    "E502": "no epic delivers a new or changed contract",
    "E503": "no epic covers a concern cell with work",
    "E504": "epic delivers nothing",
}

# ------------------------------------------------------------- traceability

# Rule -> (code in a plain check, code under --gate epics).
TRACE_CODES = {"T1": ("W501", "E501"), "T2": ("W502", "E502"), "T4": ("W503", "E503"), "T6": ("W504", "E504")}
GATES = ("epics",)
TRACE_CONTRACT_CHANGES = ("new", "changed")  # contracts T2 needs an epic for
OWNERSHIP_CONCERN = "concern-ownership"  # covered by an epic listing the app, not by a marker
WAIVER_RE = re.compile(rf"^no work \({HANDLE}(?: {HANDLE})*, review \d{{4}}-\d{{2}}-\d{{2}}\): \S")

# ------------------------------------------------------------ voice examples

# voice/examples/<type>/VX-<type>-NNN.md frontmatter. The check never reads voice/; these
# names are here so CONVENTIONS.md, the template and the tests agree on them.
VOICE_TYPES = ("diagnosis", "decision", "how-it-works")
VOICE_SOURCES = ("public-seed", "owner", "owner-edit")
VOICE_STATES = ("active", "retired")
VOICE_ACTIVE_MAX = 5

# Files the check never parses as pages (paths relative to the vault root).
SKIP_FILES = ("CLAUDE.md", "CONVENTIONS.md")
SKIP_DIRS = ("voice", "handoffs")
HANDOFF_DIR = "handoffs"  # planner handoff writes <APP-id>.md here; it is a record, not a page
