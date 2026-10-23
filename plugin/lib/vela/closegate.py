"""Whether a session is ready to finish: the wave-1 part of `vela close gate` (overhaul Task 10a). Pure.

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
the read-back puts every line that goes on record in the lead's name in front of the lead, and the PR carries receipts,
not words.

The lead may still go ahead without a quoted yes (the user can override any rule): an `**Override:**` bullet on the
item naming `QUOTED_YES_RULE`, with their reason. The gate then lets the change through and lists the override, never
hides it.

Only changes into or out of `decided` are judged. Other state moves (a page set to match its rows, an unknown opened)
are filing, which close does from its defaults; holding every one of them to a quoted yes would make the lead approve
bookkeeping, which close is meant to spare them.
"""
import re
from dataclasses import dataclass, replace

from vela import override, privaterecord, say, schema
from vela.schema import QUOTED_YES_RULE
from vela.said import is_unverified

CONSENT_CLEAR = ("The lead's own yes, quoted in the session record with a Changes row citing it, clears it; so does "
                 "their override with a reason.")
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
    mark: str = ""  # keep/park/drop, added at close; "" while the capture is still unfiled

    @property
    def is_person(self):
        return not self.origin.strip().lower().startswith("claude")

    @property
    def unverified(self):
        """Written where nothing could check the person typed these words (`vela/said.py`): not a yes until they confirm."""
        return is_unverified(self.origin)

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
    """One reason the session can't finish yet (or, in `Readiness.notes`, one thing the lead hears that doesn't stop
    it). `plain` is what the lead hears, any ID left in it resolved by the caller; `detail` carries the IDs and paths;
    `clear` is what would clear it, for the model (the lead hears `plain`, which asks them the question). `kind`
    groups problems the lead hears as one thing (`KINDS`); `audience` is say.MODEL for a step Claude takes itself
    (render, sync-main, the hooks note), which the gate still counts but never asks the lead about."""
    plain: str
    detail: str
    clear: str = ""
    kind: str = ""
    audience: str = say.LEAD


# What holds a close up, in the order the lead hears it: one line per kind when there is more than one of it.
CONSENT, ELSEWHERE, RECEIPT, READBACK, UNMARKED, CHECK, REMOVED_ROW, STRAY, RENDER, SYNC = (
    "consent", "elsewhere", "receipt", "readback", "unmarked", "check", "removed", "stray", "render", "sync")
KINDS = (SYNC, CONSENT, RECEIPT, ELSEWHERE, READBACK, UNMARKED, CHECK, REMOVED_ROW, STRAY, RENDER)


@dataclass(frozen=True)
class Consent:
    """One decision the gate judged, or one override and its reason, with the lead's words and the capture link. The gate's own data; the PR body never prints it."""
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
            found[match["n"]] = Capture(match["n"], match["tag"], match["origin"], match["words"],
                                        (match["mark"] or "").strip())
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


def judge_change(change, rows, said, vault, record_name, part=1):
    """(Problem or None, Consent or None) for one change into or out of decided."""
    allowed = overrides_for(vault, change.item)
    if allowed:
        o = allowed[0]
        return None, Consent(change.item, change.name, f"{change.before} to {change.after}, by override",
                             o.reason, f"{o.by} on {o.date}")
    # An item new this session may pass through a state on its way (an import writes a decision record as proposed,
    # then decides it with the lead's yes): its row's From is that state, not the branch point's "-".
    row = change_row(change, rows)
    if row is None:
        return Problem(f"You haven't said yes to {moving(change)} yet.",
                       f"{change.item}: {change.before} -> {change.after} has no ## Changes row", kind=CONSENT), None
    capture = said.get(row.capture_number)
    if capture is None:
        return Problem(f"I can't find where you said yes to {moving(change)}. Can you say it again?",
                       f"{change.item}: Changes row line {row.line} cites {row.source or 'nothing'}", kind=CONSENT), None
    if not capture.is_person:
        return Problem(f"{moving(change, capital=True)} was my suggestion, not your yes. Do you agree?",
                       f"{change.item}: ^c{capture.n} has origin '{capture.origin}'", kind=CONSENT), None
    if capture.unverified:
        return Problem(f'I couldn\'t check that you said "{capture.quote}" on {change.name}. Did you say it?',
                       f"{change.item}: ^c{capture.n} is unverified (no log of what was typed); "
                       f"`vela record confirm {capture.n}` after the lead says yes", kind=CONSENT), None
    if capture.is_bare_non_yes:
        return Problem(f"You said '{capture.quote or 'ok'}' on {change.name}. Was that a yes to {moving(change)}?",
                       f"{change.item}: ^c{capture.n} says only '{capture.quote}'", kind=CONSENT), None
    return None, Consent(change.item, change.name, f"{change.before} to {change.after}", capture.quote,
                         privaterecord.citation(record_name, part, int(capture.n)))


def change_row(change, rows):
    """The Changes row that records `change`, or None."""
    return next((r for r in rows if r.item == change.item and r.after == change.after
                 and (r.before in (change.before, "-", "") or change.before == "-")), None)


def moving(change, capital=False):
    """'deciding Calendar entries' / 'reopening Calendar entries': the change the lead says yes to, as a verb."""
    verb = "deciding" if change.after == CONSENT_STATE else "reopening"
    return f"{verb.capitalize() if capital else verb} {change.name}"


def reader_changes(rows, after):
    """A reader copy has no branch point: every Changes row into or out of decided is judged as written."""
    return [StateChange(r.item, r.item, r.before or "-", r.after) for r in rows
            if CONSENT_STATE in (r.before, r.after) and r.item in after]


def judge(changes, record_text, record_name, vault, part=1):
    """(problems, consent lines) for the given changes against one session record."""
    rows, said = change_rows(record_text), captures(record_text)
    problems, consent = [], []
    for change in changes:
        named = StateChange(change.item, vault.name_of(change.item), change.before, change.after)
        problem, line = judge_change(named, rows, said, vault, record_name, part)
        problems += [replace(problem, clear=CONSENT_CLEAR)] if problem else []
        consent += [line] if line else []
    return problems, consent


# ------------------------------------------------------------------ Task 10: the rest of the one list

REMOVED = "removed"  # the To of a Changes row that records the lead's yes to removing a ledger row or an override


@dataclass(frozen=True)
class Seen:
    """What the edge observed for `ready`, so the judging stays pure.

    `before` is the vault at the branch point, or None in a reader copy (no git, so no branch point). `errors` are
    check's error findings, already past the overrides (rules.check applies them), so each one left has no recorded
    choice. `stray` is every changed path the close's allow-list would leave out; `stale` the pages render would still
    rewrite (`render_problems` when render can't run at all). `flow` is ((default line, lead line), ...), one per slice
    this session's changes reach, and `flow_note` says why there are none when the check couldn't run. `host` is
    `.vela/host.json` as read, or None. `lead` is `(handle, display names)` from `vela whoami`, or None when no handle
    is kept: then the receipt check's lead clause cannot run, and `vela check`'s form check is all that judges them."""
    today: str
    sync: object  # closestate.Verdict
    before: object = None
    errors: tuple = ()
    stray: tuple = ()
    stale: tuple = ()
    render_problems: int = 0
    flow: tuple = ()
    flow_note: str = ""
    hooks_ran: bool = False
    host: dict = None
    reader: bool = False
    lead: object = None
    readback: object = None  # the digest `.vela/close/<id>.readback.json` holds, or None when the lead has not read back
    picked: tuple = ()  # the quotes the lead picked (`.vela/close/<id>.quotes.json`), for the read-back


@dataclass(frozen=True)
class Readiness:
    """The gate's answer: `problems` stop the close, `notes` are said and don't, `consent` feeds the PR body."""
    problems: tuple
    notes: tuple
    consent: tuple

    @property
    def ready(self):
        return not self.problems


def _plural(n, one, many):
    return one if n == 1 else many


def unmarked(record_text):
    """Captures with no keep/park/drop mark, in record order. Close files every capture, so one left unmarked is
    something the lead said that would drop out of the plan without anyone choosing that."""
    return [c for c in captures(record_text).values() if not c.mark]


def ledger_copies(vault):
    """{copy cell: page title} for every question-ledger row in the vault."""
    from vela import ledger
    return {row.copy: str(page.meta.get("title") or page.name) for page in vault.pages for row in ledger.rows(page)}


def override_scopes(vault):
    """{(page id, item id or "", rules, by, date): (plain scope name, Override)} for every well-formed override. The key
    leaves out the reason and the end date, so rewording a reason or moving `until` is not a removal."""
    found = {}
    for page in vault.pages:
        items = []
        for bullet in page.bullets:
            if bullet.label == schema.OVERRIDE_LABEL and not bullet.generated and bullet.item not in items:
                items.append(bullet.item)
        page_id = str(page.meta.get("id") or page.name)
        for item in items:
            name = vault.name_of(item) if item else str(page.meta.get("title") or page.name)
            for o in override.valid_overrides(page, item):
                found[(page_id, item, o.rules, o.by, o.date)] = (name, o)
    return found


def removal_agreed(key, rows, said):
    """Whether the record holds the lead's own yes to removing `key` (a ledger copy, or an item or page ID): a Changes
    row `| <key> | <what> | removed | [[record#^cNN]] |` citing a person's capture that is not a bare non-yes, the
    same test a decision's yes passes."""
    for row in rows:
        if row.item != key or row.after != REMOVED:
            continue
        capture = said.get(row.capture_number)
        if capture is not None and capture.is_person and not capture.unverified and not capture.is_bare_non_yes:
            return True
    return False


def lead_path(path):
    """A path the lead may hear: as it is, unless it holds something the lead check forbids (`ADR-0004-x.md`)."""
    from vela import say
    if say.leak_in(path) is None:
        return path
    folder = path.rsplit("/", 1)[0] if "/" in path else ""
    return f"a file in {folder}" if folder and say.leak_in(folder) is None else "one more file"


def unmarked_problem(record_text):
    left = unmarked(record_text)
    if not left:
        return []
    n = len(left)
    first = _first_words(left[0].words)
    said = (f"One thing you said isn't sorted yet: keep it, set it aside for later, or drop it? It was: '{first}'."
            if n == 1 else
            f"{say.count_words(n, capital=True)} things you said aren't sorted yet: each needs a keep, a set aside "
            f"for later or a drop. The first was: '{first}'.")
    return [Problem(said, "unmarked: " + ", ".join(f"^c{c.n}" for c in left),
                    "Marking each one keep, park or drop clears it.", kind=UNMARKED)]


def _first_words(words, limit=12):
    """The opening of a capture, short enough to say back: its first `limit` words."""
    parts = words.split()
    return " ".join(parts[:limit]) + ("..." if len(parts) > limit else "")


ERROR_CLEAR = "Fixing it with the lead clears it, or recording the lead's choice as an override with their reason."
_BLOCKED = re.compile(r"^(?P<unit>\S+) is decided, but open unknown (?P<unknown>\S+) blocks it\.$")


def error_problems(errors, vault):
    """One problem per page and rule, so an item blocked by seven open questions is one thing to the lead, not seven
    lines that each repeat its name. `detail` still lists every finding."""
    grouped = {}
    for finding in errors:
        grouped.setdefault((finding.path, finding.code), []).append(finding)
    out = []
    for (path, code), found in grouped.items():
        detail = "; ".join(f"{f.path}:{f.line} {f.code}" for f in found)
        out.append(Problem(_error_words(found, vault), detail, ERROR_CLEAR, kind=CHECK))
    return out


_NO_GRILL = re.compile(r"^(?P<unit>\S+) is decided, but no \*\*Decision:\*\* bullet links a Grill session\.$")


def _lead_message(message, vault):
    """A check's message where its own words are the page grammar (a bullet's markup), said the lead's way."""
    found = _NO_GRILL.match(message)
    if found:
        return f"{vault.name_of(found['unit'])} is decided, but nothing says which grill decided it."
    return message


def _error_words(found, vault):
    blocked = [_BLOCKED.match(f.message) for f in found]
    if all(blocked):
        unit = vault.name_of(blocked[0].group("unit"))
        questions = [vault.name_of(m.group("unknown")) for m in blocked]
        if len(questions) == 1:
            return f"{unit} can't stay decided while a question under it is still open: {questions[0]}."
        return (f"{unit} can't stay decided while {say.count_words(len(questions))} questions under it are still open, "
                f"among them {say.names_said(questions[:2])}.")
    first = found[0]
    stem = first.path.rsplit("/", 1)[-1]
    page = vault.page(stem[:-3]) if stem.endswith(".md") else None
    where = str(page.meta.get("title") or "") if page is not None else ""
    message = _lead_message(first.message, vault)
    said = f"On {where}: {message}" if where else message
    return said + (f" (and {say.count_words(len(found) - 1)} more like it)" if len(found) > 1 else "")


@dataclass(frozen=True)
class Removal:
    """A ledger row or an override that was there at the branch point and is gone now, with no recorded yes to its
    removal. `key` is the ledger copy, or the override's scope (an item or page ID); `name` is what the lead hears."""
    key: str
    name: str
    problem: Problem
    is_override: bool = False


def unagreed_removals(before, after, rows, said):
    """Every `Removal` the record holds no yes for. Deleting the row or the override is the one edit that quiets a
    check without answering it, and deletion is detectable, so it is refused rather than asked about in prose."""
    out = []
    now = ledger_copies(after)
    for copy, title in sorted(ledger_copies(before).items()):
        if copy not in now and not removal_agreed(copy, rows, said):
            out.append(Removal(copy, f"a question taken off {title}", Problem(
                f"A question was taken off {title} this session ({copy}). Was that on purpose?",
                f"ledger row {copy} removed since the branch point", kind=REMOVED_ROW, clear=
                "Putting the row back clears it, or the lead's own words for removing it, recorded in "
                "the session record.")))
    kept = override_scopes(after)
    for key, (name, o) in sorted(override_scopes(before).items(), key=lambda pair: tuple(map(str, pair[0]))):
        scope = key[1] or key[0]
        if key not in kept and not removal_agreed(scope, rows, said):
            out.append(Removal(scope, f"an exception taken off {name}", Problem(
                f'The exception on {name} was taken out this session ("{o.reason}"). Was that on purpose?',
                f"override on {scope} ({', '.join(o.rules)} by {o.by} on {o.date}) removed since the "
                "branch point",
                "Putting it back clears it, or the lead's own words for removing it, recorded in the "
                "session record.", kind=REMOVED_ROW), is_override=True))
    return out


def removal_problems(before, after, rows, said):
    return [r.problem for r in unagreed_removals(before, after, rows, said)]


# ------------------------------------------------------------------ Task 12: what the other machine decided

STILL_YES = "These were decided on the other machine: {names}. Still yes?"
STILL_YES_CLEAR = ("The lead's yes in this part, recorded with vela close reconfirm --yes ^cNN and the IDs, clears it. "
                   "A no leaves the item as it is, and the lead may reopen it.")
LEDGER_ROW, OVERRIDE_ROW = "ledger row", "override"  # the From cell of a removal's Changes row


@dataclass(frozen=True)
class Away:
    """One thing the other machine did that this part holds no yes for. `id` is what the Changes row names (an item or
    page ID, a ledger copy, or an override's scope), `name` what the lead hears, `before` and `after` the row's From
    and To. `is_removal` marks a ledger row or an override taken off."""
    id: str
    name: str
    before: str
    after: str
    is_removal: bool = False


def decision_bullets(vault, item):
    """[(page, bullet)] for the item's (or the page's) `**Decision:**` line."""
    found = vault.item(item)
    if found is not None:
        bullet = found.facts.get("Decision")
        return [(found.page, bullet)] if bullet else []
    pages = vault.by_id.get(item) or []
    return [(pages[0], b) for b in pages[0].bullets if b.label == "Decision" and not b.item and not b.generated] if pages else []


def cites_another_part(vault, item, record_id, part):
    """Whether the item's receipt names this session's notes in a part other than this one."""
    from vela import receipts
    for _, bullet in decision_bullets(vault, item):
        found = receipts.parse_decision(bullet.value)
        if found is not None and found.record == record_id and found.ref is not None and found.ref.part != part:
            return True
    return False


def away(vault, before, rows, said, record_id, part):
    """The `Away` things in a later part (part 2 and up): each change into or out of decided with no Changes row here
    whose receipt cites another part of this session, and every removal this part holds no yes for. Part 1 has no
    other machine to ask, and a reader copy has no branch point to compare with."""
    if part < 2 or before is None:
        return []
    out = [Away(c.item, vault.name_of(c.item), c.before, c.after)
           for c in consent_changes(states(before), states(vault), vault)
           if not overrides_for(vault, c.item) and change_row(c, rows) is None
           and cites_another_part(vault, c.item, record_id, part)]
    out += [Away(r.key, r.name, OVERRIDE_ROW if r.is_override else LEDGER_ROW, REMOVED, is_removal=True)
            for r in unagreed_removals(before, vault, rows, said)]
    return out


def elsewhere_problem(asked):
    """One grouped question for everything decided on the other machine: the lead hears names, `detail` the IDs."""
    if not asked:
        return []
    return [Problem(STILL_YES.format(names=say.names_said([a.name for a in asked])),
                    "decided elsewhere: " + ", ".join(a.id for a in asked), STILL_YES_CLEAR, kind=ELSEWHERE)]


def stray_problem(stray):
    if not stray:
        return []
    n, names = len(stray), [lead_path(p) for p in stray]
    shown = say.names_said(names[:3]) + (f" and {say.count_words(n - 3)} more" if n > 3 else "")
    said = (f"{shown} changed but isn't part of this session. Shall I leave it out, or is it yours to keep?" if n == 1
            else f"{shown} changed but aren't part of this session. Shall I leave them out, or are they yours to keep?")
    return [Problem(said, "left out: " + ", ".join(stray),
                    f"Committing, moving or deleting {_plural(n, 'it', 'them')} clears it.", kind=STRAY)]


def render_problem(stale, render_problems):
    if render_problems:
        return [Problem("Some generated tables are out of date, and render can't rewrite them yet.",
                        f"render cannot run: {render_problems} problems (run vela render to see them)",
                        "Fixing what render names, then running it, clears it.", kind=RENDER, audience=say.MODEL)]
    if stale:
        return [Problem("Some generated tables are out of date.", "render would still rewrite " + ", ".join(stale),
                        "Running vela render clears it.", kind=RENDER, audience=say.MODEL)]
    return []


def notes_of(seen):
    """What the lead hears that doesn't stop the close. The hooks line is informational on purpose: every rule a hook
    holds is also held by the command it guards, so a missing hook costs earlier feedback, never correctness (plan 1,
    the Silent Fallback row). Saying so plainly is what keeps "didn't run" from looking like "passed". The flow-check
    lines are a read-back for the lead (plan 2.1), not a gate: a slice that fails is the boundary session's to fix."""
    notes = []
    if seen.sync.listed:
        notes.append(Problem(seen.sync.plain, f"sync-main: {seen.sync.status}"))
    if seen.reader:
        notes.append(Problem("This is your copy, so I can't tell whether anything was deleted this session.",
                             "reader copy: no merge-base"))
    notes += [Problem(lead, line) for line, lead in seen.flow]
    if seen.flow_note:
        notes.append(Problem(seen.flow_note, seen.flow_note))
    if not seen.hooks_ran:
        notes.append(Problem("Hooks did not run in this session, so nothing stopped a wrong step early; this list "
                             "checked everything itself.", ".vela/hooks-active is missing", audience=say.MODEL))
    if seen.host:
        from vela.edge import hostprobe  # `stance` is pure: it reads only the host.json dict
        row, sentence = hostprobe.stance(seen.host)
        # A host that can do everything a session needs is not news to the lead; one that can't is.
        notes.append(Problem(sentence, f"host: {row}", audience=say.MODEL if row == "everything" else say.LEAD))
    return notes


# ------------------------------------------------------------------ the receipts this session wrote

NO_WORDS = "The decision on {name} has none of your words on record yet."
UNQUOTED = "{name}'s decision quotes someone who hasn't said yes to being quoted."


def _speaker_is_lead(who, lead):
    from vela.decisions import consent
    handle, names = lead
    return consent.same_handle(who, handle) or who.strip().casefold() in {n.casefold() for n in names}


def _may_quote(record, who, lead):
    """Whether `who`'s words may be on a committed page: they said something in this session and either they are the
    lead or they gave their own quote-yes (`consent.may_quote`)."""
    from vela.decisions import consent
    return any(consent.may_quote(c, record, lead) for c in record.captures.values()
               if consent.same_handle(c.origin, who))


def _new_bullets(vault, before):
    """(page, bullet) for every Decision and Dissent bullet this session added or reworded since `before`."""
    for page in vault.pages:
        old = before.page(page.name)
        was = {(b.label, b.value) for b in old.bullets} if old is not None else set()
        for bullet in page.bullets:
            if bullet.label in ("Decision", "Dissent") and not bullet.generated and (bullet.label, bullet.value) not in was:
                yield page, bullet


def _scope_name(vault, page, bullet):
    return vault.name_of(bullet.item) if bullet.item else str(page.meta.get("title") or page.name)


def receipt_problems(vault, before, record_id, part, record_text, lead):
    """The lead clause of E315, which `vela check` cannot judge because it does not know who the lead is. For the
    receipts on pages changed since `before` that cite this record and this part: a receipt whose who is the lead needs
    the lead's words; a receipt or Dissent that quotes someone else needs that person's own `quote-yes` in this
    session. A relayed yes has the lead as its origin, so it never counts for anyone else. With no known lead nothing
    is judged here."""
    from vela import receipts
    if lead is None or before is None:
        return []
    from vela.decisions import record as session_record
    held, out = session_record.from_text(record_id, "", record_text, part), []
    for page, bullet in _new_bullets(vault, before):
        name = _scope_name(vault, page, bullet)
        where = f"{bullet.item or page.id} at {page.path}:{bullet.line}"
        if bullet.label == "Decision":
            found = receipts.parse_decision(bullet.value)
            if found is None or found.record != record_id or found.ref is None or found.ref.part != part or not found.who:
                continue
            words, who = found.words, found.who
        else:
            found = receipts.parse_dissent(bullet.value)
            if found is None or found.see != record_id or not found.words:
                continue
            words, who = found.words, found.who
        if _speaker_is_lead(who, lead):
            if bullet.label == "Decision" and not words:
                out.append(Problem(NO_WORDS.format(name=name), f"{where}: the receipt names {who} and holds no words",
                                   "Quoting the lead's own words in the receipt clears it.", kind=RECEIPT))
        elif words and not _may_quote(held, who, lead):
            out.append(Problem(UNQUOTED.format(name=name), f"{where}: {who}'s words, with no quote-yes from {who}",
                               f"Asking {who}, in the session, whether they may be quoted clears it; so does taking "
                               "their words out of the line.", kind=RECEIPT))
    return out


READBACK_OWED = "I haven't read back the wording that goes on record in your name yet."


def readback_problems(vault, record_id, part, record_text, seen):
    """The lead has not read back the sentences that go on record in their name, or one changed after they did. Silent
    until there is a sentence to read: a session that put no words on a page owes no read-back."""
    from vela import closereadback
    found = closereadback.sentences(vault, record_id, part, record_text, seen.lead, seen.picked)
    if not found or closereadback.digest(found) == seen.readback:
        return []
    return [Problem(READBACK_OWED, f"{len(found)} sentence(s) to read back; `vela close readback` lists them, "
                    "`--done` records the lead's yes",
                    "Reading the sentences back to the lead, then vela close readback --done, clears it.",
                    kind=READBACK)]


def mark_target_problems(vault, record_text):
    """A capture marked `keep: [[page#heading|ID]]` whose page or heading is not in the plan. `vela check` cannot
    read the notes, so the gate is where a mark that points nowhere is stopped."""
    from vela import markrules
    out = []
    for capture in captures(record_text).values():
        mark = markrules.parse_mark(capture.mark)
        for target in (mark.targets if mark else ()):
            page = vault.page(target.page)
            if page is None:
                plain = f"Something you said was kept on {target.page}, and I can't find that page."
            elif not _heading_in(vault, page, target.heading):
                plain = f"Something you said was kept on {vault.name_of(page.id) if page.id else target.page}, under a heading that isn't there."
            else:
                continue
            out.append(Problem(plain, f"^c{capture.n} keeps into [[{target.page}#{target.heading}|{target.id}]], which is not in the plan",
                               "Pointing the mark at a page and heading that exist clears it.", kind=CHECK))
    return out


def _heading_in(vault, page, heading):
    row = vault.row_ids.get(heading)
    return heading in [h.text for h in page.headings] or (row is not None and row[0] is page)


def ready(vault, record_text, record_id, seen, part=1):
    """The whole gate, pure: a Readiness for one session record against what `seen` holds. `close gate` prints it and
    `close finish` refuses on it. The order is the order the lead fixes things in: main, decisions, filing, the tree."""
    rows, said = change_rows(record_text), captures(record_text)
    after = states(vault)
    if seen.before is None:
        changes = reader_changes(rows, after)
    else:
        changes = consent_changes(states(seen.before), after, vault)
    asked = away(vault, seen.before, rows, said, record_id, part)
    changes = [c for c in changes if c.item not in {a.id for a in asked}]
    problems, consent = judge(changes, record_text, record_id, vault, part)
    problems += elsewhere_problem(asked)
    if seen.sync.blocks:
        problems.insert(0, Problem(seen.sync.plain, f"sync-main: {seen.sync.status or 'not run'}",
                                   "Running vela close sync-main clears it.", kind=SYNC, audience=seen.sync.audience))
    problems += receipt_problems(vault, seen.before, record_id, part, record_text, seen.lead)
    problems += readback_problems(vault, record_id, part, record_text, seen)
    problems += unmarked_problem(record_text)
    problems += mark_target_problems(vault, record_text)
    problems += error_problems(seen.errors, vault)
    if seen.before is not None:
        problems += [r.problem for r in unagreed_removals(seen.before, vault, rows, said)
                     if r.key not in {a.id for a in asked}]
    problems += stray_problem(seen.stray)
    problems += render_problem(seen.stale, seen.render_problems)
    return Readiness(tuple(problems), tuple(notes_of(seen)), tuple(consent))
