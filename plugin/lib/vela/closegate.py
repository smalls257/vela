"""Whether a session is ready to finish: the wave-1 part of `planner close gate` (overhaul Task 10a). Pure.

The Violation this exists to prevent is a Silent Fallback in the record. Writing `state: decided` with the Edit tool and
never asking the lead looks exactly like a decision the lead gave: E303 catches only a decided page with no
`**Decision:**` link. So the gate looks at what changed since the branch point and asks the record for the lead's own
words behind every change into or out of `decided`:

- the session record's `## Changes` table has a row with the item's ID and the same To (and From, when it names one);
- the row cites a capture (`[[<record>#^cNN]]`) that exists, whose origin is a person, not anything starting `claude`
  (CONVENTIONS' captures grammar: a person's origin means "words quoted verbatim"; `claude, from <name>` is Claude's
  summary of them);
- and whose words are not a bare non-yes ("ok", "okay", "sure", "next", "fine", or nothing), which START already says
  is not a yes.

What this proves is limited, and said plainly (plan 4.3, a Sensor, not a Shield): the model writes every field these
checks read, so the gate shows a missing or malformed yes; it cannot prove the lead said the words. That is why
`consent_block` puts every quote in the PR body, where the reviewer reads the exact words behind each decision.

The lead may still go ahead without a quoted yes (the user can override any rule): an `**Override:**` bullet on the
item naming `QUOTED_YES_RULE`, with their reason. The gate then lets the change through and lists the override, never
hides it.

Only changes into or out of `decided` are judged. Other state moves (a page set to match its rows, an unknown opened)
are filing, which close does from its defaults; holding every one of them to a quoted yes would make the lead approve
bookkeeping, which close is meant to spare them.
"""
import re
from dataclasses import dataclass

from vela import override, schema

QUOTED_YES_RULE = '"a decision needs the lead\'s quoted yes"'
BARE_NON_YES = ("", "ok", "okay", "sure", "next", "fine")
CONSENT_STATE = "decided"

CAPTURE_RE = re.compile(r"^- \[(?P<tag>[\w-]+)\] \((?P<origin>[^)]*)\) (?P<words>.*?)(?: → (?P<mark>.*?))? \^c(?P<n>\d+)\s*$")
CAPTURE_LINK_RE = re.compile(r"\[\[(?P<record>[^\]#|]*)#\^c(?P<n>\d+)(?:\\?\|[^\]]*)?\]\]")
QUOTE_RE = re.compile(r"[\"“](?P<q>[^\"”]+)[\"”]")


@dataclass(frozen=True)
class Capture:
    n: str  # the number after ^c, as written ("07")
    tag: str
    origin: str
    words: str

    @property
    def is_person(self):
        return not self.origin.strip().lower().startswith("claude")

    @property
    def quote(self):
        """The lead's own words: the first quoted span when there is one (sessions write `"Yes to these." says yes to
        ...`), else the whole line."""
        found = QUOTE_RE.search(self.words)
        return (found.group("q") if found else self.words).strip()

    @property
    def is_bare_non_yes(self):
        return re.sub(r"[^\w\s]", "", self.quote).strip().lower() in BARE_NON_YES


@dataclass(frozen=True)
class ChangeRow:
    item: str
    before: str
    after: str
    source: str
    line: int

    @property
    def capture_number(self):
        found = CAPTURE_LINK_RE.search(self.source)
        return found.group("n") if found else ""


@dataclass(frozen=True)
class StateChange:
    item: str
    name: str  # the plain name a lead knows it by
    before: str  # "-" when it is new
    after: str


@dataclass(frozen=True)
class Problem:
    """One reason the session can't finish yet. `plain` is what the lead hears; `detail` carries the IDs."""
    plain: str
    detail: str


@dataclass(frozen=True)
class Consent:
    """One line of the PR body's Consent block: a decision and the lead's exact words, or an override and its reason."""
    item: str
    name: str
    change: str
    words: str
    link: str


def captures(record_text):
    """{number: Capture} for every capture line in a session record."""
    found = {}
    for line in record_text.split("\n"):
        match = CAPTURE_RE.match(line.strip())
        if match:
            found[match["n"]] = Capture(match["n"], match["tag"], match["origin"], match["words"])
    return found


def change_rows(record_text):
    """Every row of the record's `## Changes` table, in order."""
    rows, inside = [], False
    for number, line in enumerate(record_text.split("\n"), 1):
        if line.startswith("## "):
            inside = line.strip() == "## Changes"
            continue
        cells = [c.strip() for c in re.split(r"(?<!\\)\|", line.strip())[1:-1]] if inside and line.startswith("|") else []
        if len(cells) != len(schema.CHANGES_HEADER) or tuple(cells) == schema.CHANGES_HEADER or set(cells[0]) <= {"-", ":"}:
            continue
        rows.append(ChangeRow(cells[0], cells[1], cells[2], cells[3], number))
    return rows


def states(vault):
    """{ID: state} for every page with a `state:` field and every item with a `**State:**` bullet."""
    found = {}
    for page in vault.pages:
        if page.meta.get("id") and page.meta.get("state"):
            found[str(page.meta["id"])] = str(page.meta["state"]).strip().lower()
    for item_id, items in vault.items.items():
        value = items[0].fact("State")
        if value:
            found[item_id] = value.split()[0].strip(".,;").lower()
    return found


def consent_changes(before, after, vault):
    """The changes into or out of `decided` from the `before` states to the `after` states."""
    out = []
    for item, now in sorted(after.items()):
        was = before.get(item, "-")
        if was != now and CONSENT_STATE in (was, now):
            out.append(StateChange(item, vault.name_of(item), was, now))
    return out


def overrides_for(vault, item):
    """Valid overrides on the item (or, for a page, at page level) that name the quoted-yes rule."""
    found = vault.item(item)
    if found is not None:
        scope = (found.page, found.id)
    else:
        pages = vault.by_id.get(item)
        if not pages:
            return []
        scope = (pages[0], "")
    return [o for o in override.valid_overrides(*scope) if QUOTED_YES_RULE in o.rules]


def judge_change(change, rows, said, vault, record_name):
    """(Problem or None, Consent or None) for one change into or out of decided."""
    allowed = overrides_for(vault, change.item)
    if allowed:
        o = allowed[0]
        return None, Consent(change.item, change.name, f"{change.before} to {change.after}, by override",
                             o.reason, f"{o.by} on {o.date}")
    row = next((r for r in rows if r.item == change.item and r.after == change.after
                and r.before in (change.before, "-", "")), None)
    if row is None:
        return Problem(f"{change.name} was made {change.after} with nothing on record saying the lead agreed.",
                       f"{change.item}: {change.before} -> {change.after} has no ## Changes row"), None
    capture = said.get(row.capture_number)
    if capture is None:
        return Problem(f"{change.name} was made {change.after}, but the note it points to isn't in the session record.",
                       f"{change.item}: Changes row line {row.line} cites {row.source or 'nothing'}"), None
    if not capture.is_person:
        return Problem(f"{change.name} was made {change.after} on my suggestion; I need the lead's own yes for that.",
                       f"{change.item}: ^c{capture.n} has origin '{capture.origin}'"), None
    if capture.is_bare_non_yes:
        return Problem(f"{change.name} was made {change.after} on an 'ok', which isn't a yes.",
                       f"{change.item}: ^c{capture.n} says only '{capture.quote}'"), None
    return None, Consent(change.item, change.name, f"{change.before} to {change.after}", capture.quote,
                         f"[[{record_name}#^c{capture.n}]]")


def reader_changes(rows, after):
    """A reader copy has no branch point: every Changes row into or out of decided is judged as written."""
    return [StateChange(r.item, r.item, r.before or "-", r.after) for r in rows
            if CONSENT_STATE in (r.before, r.after) and r.item in after]


def judge(changes, record_text, record_name, vault):
    """(problems, consent lines) for the given changes against one session record."""
    rows, said = change_rows(record_text), captures(record_text)
    problems, consent = [], []
    for change in changes:
        named = StateChange(change.item, vault.name_of(change.item), change.before, change.after)
        problem, line = judge_change(named, rows, said, vault, record_name)
        problems += [problem] if problem else []
        consent += [line] if line else []
    return problems, consent


def consent_block(consent):
    """The PR body's **Consent** list: every decision with the lead's exact words and the capture link."""
    if not consent:
        return ["**Consent**", "", "- No item was decided or reopened in this session."]
    return ["**Consent**", ""] + [f'- {c.name} ({c.item}), {c.change}: "{c.words}" {c.link}' for c in consent]
