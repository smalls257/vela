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
        "optional": ("stage", "initiative", "arc42", "c4", "sources", "handed_off", "domain"),
        "states": STATE_ITEM,
    },
    "app-runtime": {
        "required": ("id", "type", "title", "state", "owner", "authored"),
        "optional": ("initiative", "arc42", "sources"),
        "states": STATE_ITEM,
    },
    "flow": {
        "required": ("id", "type", "title", "state", "owner", "authored"),
        "optional": ("initiative", "arc42", "sources", "capabilities"),
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
    # Something whose state the flow checker follows: an order, a hold, a consent (design 19). `app` is the APP-id that
    # keeps it; `shared` says whether two journeys can touch the same one; `initial` and `final` name its states.
    "entity": {
        "required": ("id", "type", "title", "app", "shared", "initial", "final"),
        "optional": ("owner", "sources"),
        "states": None,
    },
    # A slice: one journey proven end to end, the unit of done (the tracer plan's amendment). Its facts are bullets
    # under the title (SLICE_LABELS: Status, Flows, After, Joins and the rest), so the page itself is the record.
    "slice": {
        "required": ("id", "type", "title", "authored"),
        "optional": ("initiative", "sources"),
        "states": None,
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

# Any page but a session record may say when someone last checked it against its sources, and where its work lives
# outside the vault (links.py): `links:`, label to URL, or label to key with .vela.yaml's link_templates.
VERIFY_FIELDS = ("last_verified", "verified_by")
LINKS_FIELD, LINKS_LABEL, LINK_TEMPLATES_KEY = "links", "Links", "link_templates"
for _type, _spec in PAGE_TYPES.items():
    if _type != "session":
        _spec["optional"] = _spec["optional"] + VERIFY_FIELDS + (LINKS_FIELD,)
# An app page may name the picture views draw for it, as one short word, such as `icon: payments`.
ICON_FIELD = "icon"
ICON_RE = re.compile(r"^[a-z][a-z0-9-]{0,23}$")
DESIGN_FIELD = "design"  # an app page's path to its team's tech design doc, for `vela explore` (explorer/design_find.py)
PAGE_TYPES["app-building-blocks"]["optional"] += (ICON_FIELD, DESIGN_FIELD)

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
LIST_FIELDS = ("sources", "apps", "delivers", "consumes", "flows", "depends_on", "modes", "capabilities")
DOMAIN_MIN_APPS = 6  # W352 applies from this many apps
SESSION_MODES = ("dump", "discover", "shape", "boundary", "allocate", "releases", "grill", "requirements", "epics", "challenge", "answer")
LADDERED_CHANGES = ("new", "changed")  # app pages with these carry `stage`

HANDLE = r"@[A-Za-z0-9][A-Za-z0-9-]*(?:/[A-Za-z0-9._-]+)?"
OWNER_RE = re.compile(rf"^{HANDLE}(?: {HANDLE})*$")
OWNER_BULLET_RE = re.compile(rf"^{HANDLE}\b")
# "PR pending" until close has opened the PR and knows its number; W325 warns until then.
HANDED_OFF_RE = re.compile(r"^.+, \d{4}-\d{2}-\d{2}, PR (?:#\d+|pending)$")
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
    "entity": re.compile(r"^ENT-\d{3}$"),
    "slice": re.compile(r"^SLC-\d{3}$"),
    "sources": re.compile(r"^sources$"),
}
ITEM_ID_RE = re.compile(r"^(CON-\d{3}|UNK-\d{3}|R-\d{2,}|CAP-\d{3}\.FR\d+|PTY-\d{2,}|SV-\d{2,})$")
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
    if page_type in ("flow", "decision", "epic", "capability", "slice"):
        return ("prefix", page_id + "-")
    return None


# ------------------------------------------------------------- fact bullets

CONTRACT_REQUIRED = ("Crosses the boundary", "Consumers", "Change policy", "Change", "State")
WHY_LABEL = "Why"  # the lead's own reasons for a decision, written by the Grill that made it
OPTIONS_LABEL = "Options considered"  # what Shape recorded: the picked option, and each rejected one with its reason
# The user's word over a rule, and a decision made on an absent owner's behalf. Allowed on any item or page.
OVERRIDE_LABEL, DECIDED_BY_LABEL, CONFIRMED_BY_LABEL = "Override", "Decided by", "Confirmed by"
OVERRIDE_LABELS = (OVERRIDE_LABEL, DECIDED_BY_LABEL, CONFIRMED_BY_LABEL)
# A reader's decision or override, awaiting the owner's review. Not an override: it sets no rule aside.
PENDING_LABEL = "Pending approval"
# Auth, Can time out, Retries and Idempotent are what a stub and a flow check read beside the case table (cases.py).
# Delivery and Order go on a contract an outside party calls (a webhook): the checker treats the call like an event.
CONTRACT_BEHAVIOR_LABELS = ("Auth", "Can time out", "Retries", "Idempotent", "Delivery", "Order")
CONTRACT_OPTIONAL = ("Provider", "Tested by", "Source", "Decision", WHY_LABEL, "Dissent", OPTIONS_LABEL, LINKS_LABEL, PENDING_LABEL) \
    + CONTRACT_BEHAVIOR_LABELS + OVERRIDE_LABELS
CONTRACT_STATES = ("inkling", "assumption", "fact", "decided")
CONTRACT_CHANGES = ("new", "changed", "new consumers", "unchanged")

UNKNOWN_REQUIRED = ("Question", "Owner", "State", "Blocks")
UNKNOWN_OPEN_REQUIRED = ("Ask by",)
UNKNOWN_RESOLVED_REQUIRED = ("Outcome", "Resolved in")
# Ask is who holds the answer when that is not the owner. It must be a known label: vela style tells a session to
# turn every unknown label into prose, and close then deletes the Ask line the views that group by who to ask read.
UNKNOWN_OPTIONAL = ("Opened", "Notes", "Ask")
UNKNOWN_STATES = ("open", "resolved")

RISK_REQUIRED = ("Owner", "State")
RISK_OPTIONAL = ("Mitigation",)
RISK_STATES = ("open", "mitigated", "accepted", "closed")

# Target is a release's date and Owning team an epic's receiving team; both are read or required, so style must not
# call them prose.
# A slice page's facts, which slices.py reads; a release points at its slices with Slices, or names flows with Flows.
SLICE_STATUSES = ("planned", "building", "journey passes", "live but off", "on")
SLICE_LABELS = ("Status", "Flows", "After", "Ships switched off", "Done when", "Owner", "Milestone", "Journey", "Journey due")
# Labels a slice page once had and no longer reads: still known, so W405 can say the line is not read instead of the
# typo rules calling it unknown. Joins now come from the flows' steps.
RETIRED_SLICE_LABELS = ("Joins",)
SLICE_DIR = "slices"
PAGE_LABELS = ("Decision", WHY_LABEL, "Dissent", OPTIONS_LABEL, PENDING_LABEL, "Target", "Owning team", "Tracer", "Not in the tracer",
               "Slices") + SLICE_LABELS + RETIRED_SLICE_LABELS + OVERRIDE_LABELS

# `- Trace: CAP-001.FR1, CON-001` under a criterion or bullet holds the IDs its sentence no longer shows. Vela
# reads it, so `vela style` must never call it prose, and close must never delete it.
TRACE_LABEL = "Trace"
READING_LABELS = (TRACE_LABEL,)

# Subjects the question catalog fires on that are not pages: an outside party, and value held for customers.
PARTY_REQUIRED = ("Relationship", "Agreements")
PARTY_OPTIONAL = (LINKS_LABEL,)
PARTY_RELATIONSHIPS = ("partner", "supplier", "regulator", "customer group")
STORED_VALUE_REQUIRED = ("Holder", "Owner")
SUBJECT_LABELS = PARTY_REQUIRED + STORED_VALUE_REQUIRED + PARTY_OPTIONAL
SUBJECT_PAGE = "03-context-and-scope.md"  # the one home of parties and stored value
# A heading whose first word begins like a subject ID (PTY or SV, any case), whether or not it is well formed.
# A level-3 heading that opens like an item ID (UNK-12, CON-001:, R-3x) and is not one is dropped from every index and gate.
ITEM_LOOKALIKE_RE = re.compile(r"^(CON|UNK|R)-\d|^CAP-\d+\.FR", re.IGNORECASE)
ITEM_FORMS = {"CON": "CON-nnn", "UNK": "UNK-nnn", "R": "R-nn", "CAP": "CAP-nnn.FRn"}
SUBJECT_LOOKALIKE_RE = re.compile(r"^(PTY|SV)(?![A-Za-z])", re.IGNORECASE)

# ------------------------------------------------------------------ overrides

# Rule name in an **Override:** bullet -> the check codes it turns into warnings. A gate check
# cannot see (GATE-1, 2, 3, 5) turns nothing: the bullet is the record.
OVERRIDE_RULES = {
    "GATE-1": (), "GATE-2": (), "GATE-3": (), "GATE-4": ("E316",), "GATE-5": (),
    "grill": ("E303", "E317"),
    "E303": ("E303",), "E304": ("E304",), "E316": ("E316",), "E317": ("E317",), "E318": ("E318",),
    "E805": ("E805",),
}
# Two classes, because they end differently (plan 4.4). A standing rule guards a condition that stays true until
# someone acts (an unknown still open, a case table still missing), so its override says the date it ends: without
# one it would cover the rule forever, a Silent Fallback with a signature on it. An event rule was met or not at the
# moment of deciding (who was in the room, how many options a Shape weighed), so its override has nothing to end.
# A quoted rule is standing when it is "case table" or a flow-check finding ("F<n> ..."), and an event otherwise.
STANDING_RULES = ("GATE-4", "grill", "E303", "E304", "E316", "E317", "E318", "E805")
EVENT_RULES = ("GATE-1", "GATE-2", "GATE-3", "GATE-5")
STANDING_QUOTED = ('"case table"',)
# How far ahead the date a refusal offers sits when the item feeds no release with a Target still to come.
SUGGEST_UNTIL_DAYS = 30
# Error -> the warning it becomes when an Override on the same item names it.
# The sentence an E805 fix ends with. An overridden E805 prints as W805 without it, so the way to end an
# override never suggests writing another one.
E805_OVERRIDE_HINT = ("To finish the epics anyway, record an exception under the Question ledger heading: "
                      "- **Override:** E805 by @handle on YYYY-MM-DD until YYYY-MM-DD: <why>.")
OVERRIDE_CODES = {"E303": "W303", "E304": "W304", "E316": "W316", "E317": "W317", "E318": "W318", "E805": "W805"}
# Codes only a gate reports. An override of one is judged idle (W323) only when its gate ran, so the
# override that lets an epics gate pass never warns on the plain check of every PR.
GATE_ONLY_CODES = {"E805": "epics"}

# ---------------------------------------------------------------- fact tables

GOALS_HEADER = ("ID", "Goal", "Measure", "State")
CONSTRAINTS_HEADER = ("ID", "Constraint")
SOURCES_HEADER = ("ID", "Title", "Owner", "Date", "Kind", "Location")
SOURCE_KINDS = ("exists", "intends", "repo")
CONTAINERS_HEADER = ("Container", "Job")
# An app page's share of each functional requirement, under ## Requirements allocated.
ALLOCATION_HEADER = ("Requirement", "Share", "Through", "State")
# A page's history sits at its end under this heading, so the page opens with what is true now. "#### <ID>" under
# it holds an item's history. HISTORY_LABELS are the bullets that belong there.
HISTORY_HEADING = "History"
HISTORY_LABELS = ("Decision", WHY_LABEL, "Override", "Decided by", "Confirmed by", "Options considered", "Dissent")
# The line a Boundary writes under a stub app page's title; vela next sends such a page back to Boundary.
BOUNDARY_STUB_LINE = "Its boundary sheet is still to be read back."
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
    "allocation": "capability-delta",
    "progress-map": "goals",
    "undisposed-questions": "unknowns-and-risks",
}
NEW_BLOCK_SHA = "00000000"

# ------------------------------------------------------------------ diagrams

FLOWCHART_BUDGET = 20
SEQUENCE_BUDGET = 8
DIAGRAM_KINDS = ("flowchart", "graph", "sequenceDiagram")

# ------------------------------------------------------------ freshness

PLACEHOLDER_TITLE = "New initiative"  # what template/.vela.yaml ships; W718 while a vault keeps it
STALE_AFTER_DAYS = 60  # default for .vela.yaml's stale_after_days
SESSION_GAP_DAYS = 30  # W711 when no session has closed for longer than this

# ------------------------------------------------------------ progress

# What `vela status`, `vela next` and the progress-map block may suggest.
NEXT_MODES = ("probe", "discover", "shape", "requirements", "boundary", "allocate", "releases", "grill", "epics", "dump", "none")

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
    "E209": "a fact label is written twice under one heading",
    "E210": "two rows claim one ID, or one app on a concern page",
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
    "E321": "override is malformed",
    "E322": "decided-by or confirmed-by is malformed",
    "E323": "a History heading names no item on its page",
    "W325": "app is handed off but its PR number is not recorded",
    "W326": "page is less settled than its rows",
    "W327": "reader's decisions pending approval",
    "W329": "a table row's link label pipe is not escaped as `\\|`",
    "W717": "CONVENTIONS.md is not the copy the plugin ships",
    "W718": "the initiative's title in .vela.yaml is still the template's placeholder",
    "W334": "prose calls an answered question open",
    "E340": "release row names no functional requirement",
    "E341": "release row names a criterion the requirement does not have",
    "E342": "release has no valid state",
    "W343": "no release delivers a functional requirement",
    "W345": "release one has no Tracer bullet",
    "W347": "the tracer passes through an app or contract release one delivers no share of",
    "E344": "release target is not a YYYY-MM-DD date",
    "E350": "flow step names a sender or receiver its contract does not join",
    "W351": "flow step links a contract but names no sender and receiver",
    "W352": "app has no domain though other apps in a large initiative do",
    "W353": "two domains differ only by case or a trailing s",
    "W355": "unknown asks the person who owns it",
    "W356": "changing capability has no functional requirements",
    "W357": "functional requirement lists no acceptance criteria",
    "W358": "flow names no capability though the initiative has capability pages",
    "E359": "flow names a capability that is not a capability page",
    "W360": "one sentence holds three or more IDs",
    "W361": "an ID in prose, outside a link and not followed by its name",
    "W362": "a list of more than nine items with no subheadings",
    "W363": "a long page with no opening summary",
    "W364": "an epic lists more than nine acceptance criteria",
    "W365": "a paragraph over 150 words or 3 links, or an opening over 90 words or 3 links",
    "W366": "a table cell over 40 words",
    "W367": "a phrase of three or more words repeated across pages",
    "W368": "the opening is a line the template wrote",
    "W369": "an abbreviation not spelled out on the page",
    "W370": "an epic criterion has no AC id on its Trace line, or two share one",
    "W371": "two or more openings above the first heading, over 150 words together",
    "W372": "a British spelling in the page's own words",
    "W380": "contract has no case table",
    "W381": "a case table row, or a Can time out, Retries or Idempotent line, cannot be read",
    "W382": "two cases of one contract share a key",
    "W383": "a case emits an event the vault does not name",
    "W384": "a case sets an entity the vault does not name",
    "W385": "decided contract has no error case",
    "W386": "an app at handoff has an item in its handoff list that is not decided",
    "W387": "an app at handoff calls a provider nobody has designed",
    "W389": "prose leaves a matter for a Grill with no open question linked",
    "W390": "decided item records no Why",
    "W391": "a drawn slice does not pass the flow check",
    "W392": "a slice names no flows",
    "W393": "a slice's Flows or After names nothing in the vault",
    "E394": "slices come after each other in a circle",
    "W395": "a slice at building or later has flow-check findings no override covers",
    "W396": "a slice at journey passes or later records no readable Journey line",
    "W397": "a slice is at building or later while a slice it comes after has not passed its journey",
    "E398": "an override has passed its end date",
    "W399": "slices are still named on the releases page, not in slices/",
    "W400": "a slice's journey due date has passed and no Journey line records the run, or the date does not read",
    "E346": "slice status is not one of the five",
    "W348": "a release's Slices names no slice page, or a slice's Milestone names a release that does not list it",
    "W388": "a handoff manifest pins a commit this repository does not have, or cannot be read",
    "E330": "allocation row names no functional requirement",
    "E331": "allocation row goes through no such contract",
    "E332": "allocation row has no valid state",
    "E333": "allocation row is a fact on a page with no sources",
    "W303": "decided without a Grill, by override",
    "W304": "fact without a source, by override",
    "W316": "decided while an open unknown blocks it, by override",
    "W317": "decided by a requirements session, by override",
    "W318": "decided contract has no Tested by, by override",
    "W323": "override not needed",
    "W324": "decided on the owner's behalf, not yet confirmed",
    "E401": "generated block was edited by hand",
    "W402": "generated block is out of date",
    "E403": "generated block not allowed here",
    "E404": "generated block markers are broken",
    "W405": "a slice page still has a Joins line, which is no longer read: joins come from its flows",
    "W406": "two or more slices name no After, or none does: the tracer is the one slice with no After",
    "E601": "flowchart over its element budget",
    "E602": "sequence diagram over its participant budget",
    "E603": "diagram type not supported",
    "E604": "diagram does not parse in mermaid, so it does not draw",
    "W604": "diagrams not checked: no mermaid parser could run",
    "W704": "page not verified within stale_after_days",
    "W705": "unknown is past its ask-by date",
    "W711": "no session closed in the last 30 days",
    "W716": "source row older than stale_after_days",
    "W501": "no epic delivers a capability that changes",
    "W502": "no epic delivers a new or changed contract",
    "W503": "no epic covers a concern cell with work",
    "W504": "epic delivers nothing",
    "W505": "no app carries a functional requirement",
    "E501": "no epic delivers a capability that changes",
    "E502": "no epic delivers a new or changed contract",
    "E503": "no epic covers a concern cell with work",
    "E504": "epic delivers nothing",
    "E505": "no app carries a functional requirement",
    "E801": "question ledger row is malformed",
    "E802": "ledger state lacks the evidence it needs",
    "E803": "ledger row names nothing the catalog owes",
    "W804": "ledger row is orphaned or no longer owed",
    "E805": "high-severity question not disposed at the epics gate",
    "W805": "high-severity question not disposed, by override",
    "W806": "assumed question not resolved at the end of shape",
    "W807": "open question blocks the grilled item",
    "E808": "party or stored value is missing a required fact",
    "W809": "possibly an untyped subject",
    "E810": "heading looks like an item or subject ID but is not one",
    "W811": "subject defined off its page",
    "W812": "ledger row is dated in the future",
    "W813": "ledger page has no question ledger heading",
}

# ------------------------------------------------------------- traceability

# Rule -> (code in a plain check, code under --gate epics).
TRACE_CODES = {"T1": ("W501", "E501"), "T2": ("W502", "E502"), "T4": ("W503", "E503"), "T6": ("W504", "E504"),
               "T7": ("W505", "E505")}
GATES = ("epics", "shape", "grill")
TRACE_CONTRACT_CHANGES = ("new", "changed")  # contracts T2 needs an epic for
OWNERSHIP_CONCERN = "concern-ownership"  # covered by an epic listing the app, not by a marker
WAIVER_RE = re.compile(rf"^no work \({HANDLE}(?: {HANDLE})*, review \d{{4}}-\d{{2}}-\d{{2}}\): \S")

# ------------------------------------------------------------ reading load

# People hold about four to seven things at once (Cowan 2001; Miller 1956). Pages are written to that size; the
# warnings fire a little past it, so a page at the edge of the convention is never nagged.
SENTENCE_ID_LIMIT = 3  # W360 from this many IDs in one sentence
LIST_LIMIT = 9  # W362: more list items than this under one heading, with no subheadings
LONG_PAGE_WORDS = 900  # W363: a page this long opens with a summary
EPIC_CRITERIA_LIMIT = 9  # W364: more acceptance criteria than this on one epic
# W365 to W369 (design session 16). Pages are written to 80 words in an opening and 120 in a paragraph; the warnings fire
# a little past that, so a page at the edge is not nagged. digital.gov's ceiling for a paragraph is 150.
PARAGRAPH_WORD_LIMIT = 150  # W365: more words than this in one paragraph
OPENING_WORD_LIMIT = 90  # W365: more words than this in a page's opening paragraph, the part most readers read
PARAGRAPH_LINK_LIMIT = 3  # W365: more links than this in one paragraph or opening; each link is a decision for the reader
CELL_WORD_LIMIT = 40  # W366: two sentences; a cell is read as one chunk
PHRASE_WORDS = 3  # W367: words in a phrase. A four-word phrase over the limit makes its three-word parts over it, so three finds both.
PHRASE_PAGE_LIMIT = 5  # W367: a phrase on more pages than this
PHRASE_TIME_LIMIT = 10  # W367: or used more times than this across the vault
# Words that cannot make a phrase on their own: "of the first" is a phrase only because of "first".
PHRASE_FILLER = frozenset("a an the of to in on at by for and or but is are was were be been it its that this these those as "
                          "with from has have had will would can could should may might which who there their they we you "
                          "i he she his her our your".split())
# W369: capitalized words of two to five letters that need no spelling out, and shouted ordinary words.
ABBREVIATIONS_UNDERSTOOD = frozenset("IT PC ID IDS OK AM PM US UK EU UTC URL PDF FAQ CEO API QA SMS HTML SQL JSON CSV UI UX "
                                     "NOT AND OR MUST ONLY NEVER ALL NO YES TBC TBD".split())

# ------------------------------------------------------------ voice examples

# voice/examples/<type>/VX-<type>-NNN.md frontmatter. The check never reads voice/; these
# names are here so CONVENTIONS.md, the template and the tests agree on them.
VOICE_TYPES = ("diagnosis", "decision", "how-it-works")
VOICE_SOURCES = ("public-seed", "owner", "owner-edit")
VOICE_STATES = ("active", "retired")
VOICE_ACTIVE_MAX = 5

# Files the check never parses as pages (paths relative to the vault root).
SKIP_FILES = ("CLAUDE.md", "CONVENTIONS.md", "CONTEXT.md")
# docs/ holds the team's tech designs, build plans and ADRs (tech-design-grill and work-breakdown write there when run from the vault root).
SKIP_DIRS = ("voice", "handoffs", "docs")
HANDOFF_DIR = "handoffs"  # vela handoff writes <APP-id>.md here; it is a record, not a page
