"""Close section 2's default marks, as one table: every capture gets its mark without asking, and only what the
defaults can't settle goes to the lead, ranked by what it holds up (overhaul Task 14). Pure: record text and a
`Context` in, a `Plan` out; no disk, git or clock.

The Violation this shape prevents is a God Method in prose. Close section 2 held about twenty rules the model applied
at once (wild -> park, claude -> park, PTY/SV -> subject, copy IDs -> ledger row, never `fact`, ...), and every one of
them was a place to slip. Here each rule is one row of `RULES`: a name, the reason the skill sentence gave (S8: the
why moves with the rule), when it applies and what it proposes. The first row that applies wins, and the order is the
skill's own precedence ("this rule wins over the park default for claude lines"). Adding or retiring a rule is one row,
and `tests/test_markrules.py` has one case per row, so a deleted rule fails by name.

"Filing is the tool's work, not the lead's." So nothing here asks for bookkeeping: the owner of a new unknown is the
lead's handle (else the handle the capture was said by), it gets no ask-by date (the lead gives or agrees one, never the
tool), and the ledger rows for
`## Reviews` findings the lead didn't take are drafted with their checkpoint cited. What reaches the lead (`leftovers`)
is only what the rules say a person must choose: Claude's own unknown or deferral (keep or drop; Claude never decides
an unknown alone), and a line someone other than the lead said that would be copied word for word.

What the rules can't read from the words alone (which page an inkling belongs on, a ledger row's state when the words
don't say it, a tag no rule covers) is left `null` with a hint for the model, and listed in `for_model`: never guessed,
and never sent to the lead as if it were theirs to settle.

A capture that already has a mark keeps it: a grill's `(decided)`, a Discover's `(fact)`, a Boundary's `(assumption)`
were written by the mode that settled them, and re-marking them would overwrite a decision with a default. A
`claude` line among them is still listed (`promoted_on_a_nod`) for the PR body.

`plan` never proposes `fact`: a capture becomes a fact only when the lead names its source in this turn and the source
has a row in `sources.md`. That is a judgment on what the lead said, so no default makes it; `_never_fact` raises (a
vela bug) if a row ever tried.

The drafted items follow Task 4's decision-file format (`vela.decisions.schema`); `draft_files` seals each item's
capture in `seen`, so `apply` refuses an answer whose words changed after this ran.
"""
import dataclasses
import re
from dataclasses import dataclass, field

from vela import closegate, deferrals, parse
from vela.decisions import schema

UNKNOWNS_PAGE = "11-unknowns-and-risks"
LEDGER_HEADING = "Question ledger"
REVIEWS_HEADING = "Reviews"

_COPY = r"Q-[A-Z]{3}-\d{2}@[\w*.-]*[\w*]"
_FINDING = r"F\d+\.\d+"
_REVIEWER = r"R-[A-Z]{3}-\d{2,}"
_LEDGER_ID = re.compile(rf"\b(?:{_COPY}|{_FINDING}|{_REVIEWER})")
# One ID or a leading list of them ("F1.8, F1.9: ..."): the words start with what they answer.
_STARTS_WITH_LEDGER_ID = re.compile(rf"^\W*(?:{_COPY}|{_FINDING}|{_REVIEWER})(?:\s*(?:,|and)\s*(?:{_COPY}|{_FINDING}|{_REVIEWER}))*")
_WAITS_ON = re.compile(r"^\W*waits on (?P<unknown>UNK-\d{3})\s*:\s*(?P<ids>[^()]*)")
_TYPED = re.compile(r"\btype at close:\s*(?P<type>PTY|SV)\b")
_SUBJECT_ID = re.compile(r"\b(?:PTY|SV)-\d+\b")
_ITEM_ID = re.compile(r"\b(?:(?:UNK|CAP|CON|EPC|FLO|SLC|ADR|ENT|PTY|SV|CST|R)-\d[\w.]*|(?:APP|RUN)-[a-z][\w-]*)")
_NOT_APPLICABLE = re.compile(r"\b(?:not applicable|n/a|does not apply|doesn't apply)\b", re.IGNORECASE)
_SOURCE = re.compile(r"\bSRC-\d+\b")
_PICK = re.compile(r"\b(?:pick|picks|picked|go with|going with|went with|choose|chose|chosen)\b", re.IGNORECASE)
LEAD_WORDS = ("lead", "the lead", "solution lead")  # how records name the lead when they don't use the handle
PAGE_TAGS = ("idea", "thought", "decision")  # the tags whose words end up on a page as content
UNKNOWN_TAGS = ("unknown", "worry")

_TARGET_SHAPE = r"\[\[[^\]#|]+#[^\]|]+\|[^\]]+\]\] \([\w-]+\)"
_TARGET_RE = re.compile(r"\[\[(?P<page>[^\]#|]+)#(?P<heading>[^\]|]+)\|(?P<id>[^\]]+)\]\] \((?P<state>[\w-]+)\)")
_KEEP_RE = re.compile(rf"^keep: {_TARGET_SHAPE}(?:; {_TARGET_SHAPE})*$")


# --- reading the record ---------------------------------------------------------------------------------------------

@dataclass(frozen=True)
class Note:
    """One capture line: `ref` is `^cNN` as written; `mark` the existing mark, or None."""
    n: str
    tag: str
    origin: str
    words: str
    mark: object

    @property
    def ref(self):
        return f"^c{self.n}"

    @property
    def is_claude(self):
        return self.origin.strip().lower().startswith("claude")

    @property
    def quote(self):
        found = closegate.QUOTE_RE.search(self.words)
        return found.group("q").strip() if found else ""


def notes(record_text):
    """Every capture under `## Captures`, in record order."""
    found, section = [], None
    for line in record_text.split("\n"):
        if line.startswith("## "):
            section = line[3:].strip()
            continue
        if section != "Captures":
            continue
        match = closegate.CAPTURE_RE.match(line.strip())
        if match:
            found.append(Note(match["n"], match["tag"], match["origin"], match["words"].strip(), match["mark"]))
    return found


@dataclass(frozen=True)
class ReviewRow:
    """One kept finding of a `## Reviews` table, with the `### <n>. <checkpoint>, <date>` heading it sits under."""
    checkpoint: str
    finding: str
    area: str
    severity: str
    copy: str
    question: str
    quote: str


def review_rows(record_text):
    """Every finding row under `## Reviews` (CONVENTIONS "Sessions")."""
    found, section, checkpoint, header = [], None, "", None
    for line in record_text.split("\n"):
        if line.startswith("## "):
            section, header = line[3:].strip(), None
            continue
        if section != REVIEWS_HEADING:
            continue
        if line.startswith("### "):
            checkpoint, header = line[4:].strip(), None
            continue
        if not line.startswith("|"):
            header = None if not line.strip() else header
            continue
        cells = [c.strip() for c in parse.split_row(line)]
        if header is None:
            header = cells
            continue
        if set("".join(cells)) <= set("-: ") or len(cells) < 6 or not re.fullmatch(_FINDING, cells[0]):
            continue
        found.append(ReviewRow(checkpoint, *cells[:6]))
    return found


# --- marks, as CONVENTIONS "Sessions" writes them -------------------------------------------------------------------

@dataclass(frozen=True)
class Target:
    page: str
    heading: str
    id: str
    state: str


@dataclass(frozen=True)
class Mark:
    kind: str  # "keep" | "park" | "drop"
    targets: tuple = ()
    reason: str = ""


def parse_mark(text):
    """The Mark a capture line carries, or None when the text isn't one: `keep: [[<page>#<heading>|<ID>]] (<state>)`
    (several targets joined by "; " when one capture keeps several ledger rows), `park`, or `drop: <reason>`."""
    text = (text or "").strip()
    if text == "park":
        return Mark("park")
    if text.startswith("drop:"):
        reason = text[len("drop:"):].strip()
        return Mark("drop", reason=reason) if reason else None
    if not _KEEP_RE.match(text):
        return None
    return Mark("keep", tuple(Target(m["page"], m["heading"], m["id"], m["state"]) for m in _TARGET_RE.finditer(text)))


def format_mark(mark):
    """The text of a Mark, for the capture line (before its `^cNN`)."""
    if mark.kind == "park":
        return "park"
    if mark.kind == "drop":
        return f"drop: {mark.reason}"
    return "keep: " + "; ".join(f"[[{t.page}#{t.heading}|{t.id}]] ({t.state})" for t in mark.targets)


# --- what the rules read besides the capture ------------------------------------------------------------------------

@dataclass(frozen=True)
class Context:
    """What the defaults need beyond the record. `lead` is the lead's handle ("@sam", or "" when none is kept);
    `open_items` the IDs of items not yet decided
    (what a leftover can hold up); `ledger_copies` the Copy cells the question ledger already has."""
    record_id: str
    modes: tuple
    today: str
    lead: str = ""
    open_items: frozenset = frozenset()
    ledger_copies: frozenset = frozenset()
    reviews: tuple = ()
    lead_names: frozenset = frozenset()  # the lead's display names, lower-cased

    def is_lead(self, origin):
        said = origin.strip().lower().lstrip("@")
        return bool(said) and (said == self.lead.strip().lower().lstrip("@") or said in LEAD_WORDS
                               or origin.strip().casefold() in self.lead_names)

    def owner_for(self, note):
        """The lead chasing a new unknown: the kept handle, else the handle the capture was said by. Never asked."""
        if self.lead:
            return self.lead
        origin = note.origin.strip()
        return origin if origin.startswith("@") else None


def blocks(note, ctx):
    """The open items a capture names: what a leftover holds up, the order the lead hears them in."""
    return sorted({m.group(0) for m in _ITEM_ID.finditer(note.words)} & set(ctx.open_items))


# --- the rules ------------------------------------------------------------------------------------------------------

@dataclass(frozen=True)
class Rule:
    """One default. `applies(note, ctx)` says when; `propose(note, ctx)` the item's fields. `leftover` names the
    choices when the lead must answer (the rule then proposes the recommendation, not the mark)."""
    name: str
    reason: str
    applies: object
    propose: object
    leftover: tuple = ()
    plain: str = ""  # what the lead hears this leftover called


def _keep(to, state, **more):
    return dict(mark="keep", to=to, state=state, **more)


def _new_unknown(note, ctx, **more):
    return _keep("unknown", "open", id=None, owner=ctx.owner_for(note), blocks=blocks(note, ctx), **more)


def _is_deferral(note):
    return bool(deferrals.DEFERS.search(note.words))


def _ledger_ids(note):
    waits = _WAITS_ON.match(note.words)
    if waits:
        return [m.group(0) for m in _LEDGER_ID.finditer(waits["ids"])], waits["unknown"]
    first = _STARTS_WITH_LEDGER_ID.match(note.words)
    return ([m.group(0) for m in _LEDGER_ID.finditer(first.group(0))] if first else []), None


def _ledger_state(note, unknown):
    if unknown:
        return "unknown"
    if _NOT_APPLICABLE.search(note.words):
        return "not-applicable"
    if _SOURCE.search(note.words):
        return "answered"
    return None  # the words don't say: the model reads them, and asks the lead only if it can't tell


def _resolve(ident, ctx):
    """A finding ID stands for the copy or `R-` id its `## Reviews` row names; a `new` one has no id yet (the ledger
    kind numbers it past every open branch)."""
    if not re.fullmatch(_FINDING, ident):
        return ident
    row = next((r for r in ctx.reviews if r.finding == ident), None)
    if row is None or row.copy == "new":
        return None
    return row.copy


def _copy_ledger(note, ctx):
    ids, unknown = _ledger_ids(note)
    more = {"unknown": unknown} if unknown else {}
    return _keep("ledger", _ledger_state(note, unknown), id=[_resolve(i, ctx) for i in ids], **more)


def _typed_subject(note, ctx):
    named = _SUBJECT_ID.search(note.words)
    return _keep("subject", "subject", id=named.group(0) if named else None,
                 subject_type=_TYPED.search(note.words)["type"])


def _default_without(name):
    """What the rest of the table proposes, for a rule that only adds a question on top of it."""
    def propose(note, ctx):
        rule = next(r for r in RULES if r.name != name and not r.leftover and r.applies(note, ctx))
        return dict(rule.propose(note, ctx), rule=rule.name)
    return propose


def _is_shape_pick(note, ctx):
    return ("shape" in ctx.modes and "epics" not in ctx.modes and note.tag in PAGE_TAGS
            and bool(_PICK.search(note.words)))


def _lifted_from_someone_else(note, ctx):
    return (not note.is_claude and not ctx.is_lead(note.origin) and bool(note.quote)
            and note.tag in PAGE_TAGS)


RULES = (
    Rule("typed-subject",
         "A capture saying `type at close: PTY` or `SV` names a subject the lead said exists; a party or stored value "
         "carries no state, so its one mark is to the subject.",
         lambda n, c: bool(_TYPED.search(n.words)), _typed_subject),
    Rule("copy-ledger",
         "A capture that starts with a copy ID or a finding ID, or says what they wait on, is kept as its question-"
         "ledger row, so the owed question is disposed of in the one table the check reads.",
         lambda n, c: bool(_ledger_ids(n)[0]), _copy_ledger),
    Rule("claude-unknown",
         "An unknown Claude raised, or a deferral Claude wrote, is never Claude's to keep or drop alone: the lead "
         "chooses, kept as a question with an owner, or dropped with a reason. This wins over the "
         "park default for claude lines.",
         lambda n, c: n.is_claude and (n.tag == "unknown" or _is_deferral(n)),
         lambda n, c: _new_unknown(n, c), leftover=("keep", "drop"),
         plain="A question I raised myself, which only you can keep or drop"),
    Rule("claude-park",
         "A claude line is parked unless the lead picks it; that covers every origin starting with claude, including "
         "claude, from someone, because Claude's summary is not the person's word.",
         lambda n, c: n.is_claude, lambda n, c: dict(mark="park", to=None, state=None, id=None)),
    Rule("lifted-line",
         "A line copied word for word onto a page that someone other than the lead said is confirmed with the lead "
         "before it is copied, because a page quoting a person is read as that person's settled word.",
         _lifted_from_someone_else, _default_without("lifted-line"), leftover=("copy", "leave out"),
         plain="Words someone else said, which I'd copy onto a page as written"),
    Rule("wild-park",
         "A person's wild line is parked, never dropped: it was said on purpose as a what-if, and a later session "
         "may want it back.",
         lambda n, c: n.tag == "wild", lambda n, c: dict(mark="park", to=None, state=None, id=None)),
    Rule("deferral-unknown",
         "A capture saying something is left for a grill becomes an open unknown with an owner and what it "
         "blocks, so the record says who will answer; prose that defers with no open question draws W389.",
         lambda n, c: _is_deferral(n), lambda n, c: _new_unknown(n, c, deferral=True)),
    Rule("person-unknown",
         "A person's unknown or worry is kept as an unknown (an unknown is never parked), owned by the lead who is "
         "chasing it, with no ask-by date unless the lead gives one; the model may make it a concern cell instead.",
         lambda n, c: n.tag in UNKNOWN_TAGS, lambda n, c: _new_unknown(n, c)),
    Rule("shape-pick",
         "In a shape session the picked option is kept as an assumption with its options considered, never an "
         "inkling, so the next step reads it as ready for a grill.",
         _is_shape_pick, lambda n, c: _keep("assumption", "assumption", id=None, options_considered=None)),
    Rule("person-inkling",
         "A person's idea or thought is kept as an inkling on the page it belongs to: it was said, and nothing yet "
         "makes it more certain than that.",
         lambda n, c: n.tag in ("idea", "thought"), lambda n, c: _keep("inkling", "inkling", id=None, page=None)),
    Rule("no-default",
         "A capture no rule above covers gets no default mark: the model reads it and marks it from what the lead "
         "said, rather than a rule guessing.",
         lambda n, c: True, lambda n, c: dict(mark=None, to=None, state=None, id=None)),
)

LEFTOVER_ORDER = tuple(r.name for r in RULES if r.leftover)
MODEL_HINTS = {
    "mark": "keep, park or drop, from the lead's answer",
    "lead_answer": "the capture holding the lead's answer (\"^c31\"), never their words",
    "page": "the page the inkling belongs on",
    "options_considered": "the options the session weighed, each rejected one with its reason",
    "owner": "the lead's handle: run vela whoami",
    "state": "the ledger row's state from the lead's words; ask them only if the words leave it unclear",
    "to": "where it goes: an item, an unknown, a constraint or a concern cell",
}


# --- the plan -------------------------------------------------------------------------------------------------------

@dataclass
class Plan:
    items: list = field(default_factory=list)  # marks items, in capture order
    ledger: list = field(default_factory=list)  # ledger items
    leftovers: list = field(default_factory=list)  # ranked: most blocking first
    left_alone: list = field(default_factory=list)
    for_model: list = field(default_factory=list)

    @property
    def counts(self):
        marks = [i["mark"] for i in self.items]
        return {"kept": marks.count("keep"), "parked": marks.count("park"), "dropped": marks.count("drop"),
                "needs_lead": len(self.leftovers), "for_model": len(self.for_model),
                "left_alone": len(self.left_alone)}


def _never_fact(item, rule):
    if item.get("state") == "fact":
        raise ValueError(f"vela bug: the default rule {rule.name!r} proposed `fact`; no default may")
    return item


def _null_hints(item, names):
    hints = dict(item.get("hints") or {})
    for name in names:
        if name in item and item[name] is None:
            hints[name] = MODEL_HINTS.get(name, "")
    if hints:
        item["hints"] = hints
    return item


def mark_item(note, ctx):
    """(rule, item) for one unmarked capture: the first rule that applies."""
    rule = next(r for r in RULES if r.applies(note, ctx))
    proposed = _never_fact(dict(rule.propose(note, ctx)), rule)
    item = {"capture": note.ref, "rule": rule.name, "reason": rule.reason, "needs_lead": bool(rule.leftover),
            "lifted": bool(note.quote) and not note.is_claude and ctx.is_lead(note.origin)}
    if rule.leftover:
        item.update(mark=None, to=None, state=None, id=None, lead_answer=None)
        item["recommend"] = proposed
        item["hints"] = {"mark": MODEL_HINTS["mark"], "lead_answer": MODEL_HINTS["lead_answer"]}
        return rule, item
    item.update(proposed)
    if proposed.get("rule"):  # a question added on top of another default carries that default's name
        item["rule"] = proposed["rule"]
    return rule, _null_hints(item, ("mark", "page", "options_considered", "owner", "state", "to"))


def leftover_entry(note, rule, item, ctx):
    return {"capture": note.ref, "rule": rule.name, "why": rule.plain, "words": note.words,
            "choices": list(rule.leftover), "recommend": item["recommend"], "blocks": blocks(note, ctx)}


def _ranked(entries):
    return sorted(entries, key=lambda e: (-len(e["blocks"]), LEFTOVER_ORDER.index(e["rule"]),
                                          int(e["capture"][2:])))


def taken(row, captured):
    """A finding the lead took: some capture names its finding ID, or the `R-` id it stands for."""
    return row.finding in captured or (row.copy != "new" and row.copy in captured)


def _ledger_rows_from(note, item, ctx):
    """One ledger item per ID a copy-ledger capture keeps (a waits-on group is one row per ID)."""
    ids, unknown = _ledger_ids(note)
    rows = []
    for ident, copy in zip(ids, item["id"]):
        if copy is not None and copy in ctx.ledger_copies and not unknown:
            continue  # an earlier session wrote the row; only a waits-on group changes it in place
        review = next((r for r in ctx.reviews if r.finding == ident), None)
        rows.append(_ledger_row(copy, review, item["state"], ctx, capture=note.ref, unknown=unknown,
                                existing=copy in ctx.ledger_copies))
    return rows


def _ledger_row(copy, review, state, ctx, capture=None, unknown=None, existing=False, cite=None):
    row = {"copy": copy, "finding": review.finding if review else None, "area": review.area if review else None,
           "state": state, "unknown": unknown, "capture": capture, "existing": existing,
           "cite": cite or (f"[[{ctx.record_id}#{capture}]]" if capture else None),
           "question": review.question if review else None, "quote": review.quote if review else None,
           "severity": review.severity if review else None}
    return _null_hints(row, ("state",))


def _subject_ledger_row(note, ctx):
    """The existence question's copy, answered by the lead's yes: one row, unless an earlier session wrote it."""
    first = _STARTS_WITH_LEDGER_ID.match(note.words)
    copy = _LEDGER_ID.search(first.group(0)).group(0) if first else None
    if copy is None or not copy.startswith("Q-") or copy in ctx.ledger_copies:
        return []
    row = _ledger_row(copy, None, "answered", ctx, capture=note.ref)
    row["item"] = None
    row["hints"] = dict(row.get("hints") or {}, item="the subject's ID once it is written")
    return [row]


def _untaken_review_rows(found, ctx):
    """A ledger row for each `## Reviews` finding the lead didn't take that a new or unrecorded reviewer question
    stands for, citing its checkpoint heading, because there is no capture to cite. A finding about an owed copy the
    lead didn't take adds no row: the copy stays undisposed, and the undisposed-questions block shows it."""
    captured = {m.group(0) for n in found for m in _LEDGER_ID.finditer(n.words)}
    rows = []
    for review in ctx.reviews:
        if taken(review, captured) or review.copy.startswith("Q-"):
            continue
        if review.copy != "new" and review.copy in ctx.ledger_copies:
            continue
        rows.append(_ledger_row(None if review.copy == "new" else review.copy, review, "open", ctx,
                                cite=f"[[{ctx.record_id}#{review.checkpoint}]]"))
    return rows


def plan(record_text, ctx):
    """Every default applied to the record's captures. `ctx.reviews` is read from the record when not given."""
    if not ctx.reviews:
        ctx = dataclasses.replace(ctx, reviews=tuple(review_rows(record_text)))
    found = notes(record_text)
    result = Plan()
    for note in found:
        if note.mark is not None:
            result.left_alone.append({"capture": note.ref, "mark": note.mark, "promoted_on_a_nod": note.is_claude})
            continue
        rule, item = mark_item(note, ctx)
        result.items.append(item)
        if rule.leftover:
            result.leftovers.append(leftover_entry(note, rule, item, ctx))
        elif item["mark"] is None or (item.get("to") == "ledger" and item.get("state") is None):
            result.for_model.append({"capture": note.ref, "rule": item["rule"], "words": note.words})
        if item.get("to") == "ledger":
            result.ledger += _ledger_rows_from(note, item, ctx)
        elif item.get("to") == "subject":
            result.ledger += _subject_ledger_row(note, ctx)
    result.ledger += _untaken_review_rows(found, ctx)
    result.leftovers = _ranked(result.leftovers)
    return result


def draft_files(result, session, record):
    """{kind: decision-file dict} in Task 4's format, each item's capture sealed in `seen` so `apply` refuses an answer
    whose words changed after the draft. No ledger file when there is no ledger row to write."""
    files = {"marks": {"version": schema.VERSION, "kind": "marks", "session": session,
                       "items": [schema.seal(item, record, [item["capture"]]) for item in result.items]}}
    if result.ledger:
        files["ledger"] = {"version": schema.VERSION, "kind": "ledger", "session": session,
                           "items": [schema.seal(row, record, [row["capture"]] if row["capture"] else [])
                                     for row in result.ledger]}
    return files


SETTLED_STATES = ("decided", "fact", "resolved", "closed", "not-applicable", "retired")


def open_items(vault):
    """IDs of the vault's items not yet settled: what a leftover can hold up."""
    return frozenset(ident for ident, found in vault.items.items()
                     if found and found[0].fact("State") not in SETTLED_STATES)
