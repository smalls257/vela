"""The `ledger` apply kind: question-ledger rows, one per copy, written and numbered by code (overhaul Task 17; close
/LEDGER.md "The question ledger"; CONVENTIONS "Questions and the ledger"). Pure.

    | Copy | State | Evidence | By | Date |          (under `## Question ledger` on 11-unknowns-and-risks.md)

The Violation this exists to prevent is a Distributed Monolith over one table. The rows were written by the model from
a 1,500-word state table, and the numbering of a new reviewer question (`R-<AREA>-nn`) depended on the model reading
the ledger on this branch, on `origin/main` and on every other `session/*` branch: two sessions that each counted only
what they could see took the same number, and the merge then held two rows for one ID (E801). Here one module writes
every row (Shield), and the number comes from what the shell reads from git (`edge/idgit.py`, attached by
`textedit.attach`), so no session's row depends on what another session happened to look at.

The rules, each with the reason the skill gave:

- **One row per copy.** A waits-on group (`waits on UNK-nnn: <IDs>`) is drafted by `vela marks plan` as one item per
  ID, and each becomes its own `unknown` row, because the check reads one Copy cell per row. A copy or `R-` id that
  already has a row keeps its one row, changed in place (two rows for one copy is E801), with a reviewer question's
  `question:`, `quote:` and `severity:` kept from it; the old state's evidence goes, because a key of another state is
  E802.
- **`R-` ids are numbered past every open branch** (`next_reviewer_id`), with the first area's code when a merged
  finding lists several, because the merge folded one question from each area and it is one row, never one per area.
  The number is never reused: a gap is left as it is.
- **Evidence follows the state** (the CONVENTIONS state table):
  - `answered` needs `item:` (the item the answer was written into, linked) and `source:`. A source is one `SRC-nn`
    that `sources.md` holds (the lead's first-hand row counts; vela never invents one), or one page quote. A page quote
    may cite only words that were on the page before this close, or that sit under an item at `fact` or `decided`:
    words this close copied from the lead onto the page would make the lead's own answer its own evidence, which is
    no evidence at all (`quote_refusal`). With no such source the row is `assumed`, not `answered`.
  - `assumed` needs `load-bearing: yes|no` and a `signpost:` from what the lead said would show it wrong, so the gate
    can tell which assumptions the plan rests on.
  - `unknown` names an `UNK-nnn` that is open and owned by a handle: an unknown nobody chases asks nobody.
  - `not-applicable` needs a reason that rules the question out; one that defers it ("for now", "pending") is refused,
    because not-applicable takes the question off every gate and "not yet" must stay on them.
  - `asked` links the capture where it was asked.
- **By and Date.** By is the handle of whoever said it (the capture's origin, or `by`), Date is today. An `open` row
  may leave both empty: a reviewer question the lead didn't take has nobody who decided it.
- **A `## Changes` row for every row written**, `| <copy> | <old state or -> | <state> | <cite> |`, citing the capture,
  or for a reviewer question the lead didn't take (it has no capture) its checkpoint heading in `## Reviews`, which
  `marks plan` drafts as `cite`.

The lead's words in a cell are escaped (`textedit.cell`), and a `;` in free text is quoted so it can't split the
Evidence cell. Every row is parsed back with the check's own parser (`vela.ledger.parse_row`) before it is returned,
so a row check would call malformed (E801) is never written.

Numbering against `edge/idgit.branch_texts`: that reader prints ID-shaped tokens, `[A-Z]{1,4}-[0-9]+`, and so reads
`R-FIN-07` on another branch as the token `FIN-07`. A bare `<AREA>-nn` token there is counted as an `R-<AREA>-nn`
number. That over-counts (a catalog entry `Q-FIN-07` reads as `FIN-07` too), which can leave a gap in the numbers
but never hands out a number another branch holds; a collision is the failure this module exists to prevent.
"""
import re

from vela import firsthand, ledger, parse, questions, receipts, schema as vault_schema
from vela.decisions import consent, schema, textedit
from vela.decisions.resolve import source_row

PAGE = "11-unknowns-and-risks"
HEADING = ledger.HEADING
GENERATED = "undisposed-questions"
HANDLE = re.compile(rf"^{vault_schema.HANDLE}$")
AREA = re.compile(r"\b[A-Z]{3}\b")
SOURCE_ID = re.compile(r"^SRC-\d+$")
STATE_OF_ITEM = re.compile(r"^- \*\*State:\*\*\s*(?P<state>\S+)", re.M)
ITEM_HEADING = re.compile(r"^(?P<hashes>#{2,4}) [A-Z]+-\S+")
# The IDs a capture starts with ("Q-DAT-03@INI-900: ...", "F1.2, F1.3: ..."), left off the words a row quotes.
LEADING_IDS = re.compile(r"^\W*(?:(?:Q-[A-Z]{3}-\d{2}@[\w*.-]*[\w*]|F\d+\.\d+|R-[A-Z]{3}-\d{2,})"
                         r"(?:\s*(?:,|and)\s*)?)+\s*:\s*")
REVIEWER_WIDTH = 2  # R-<AREA>-nn

SCHEMA = schema.KindSchema(
    fields={"copy": "the Copy cell: a copy ID (Q-DAT-02@APP-booking), a wildcard (Q-OPS-01@APP-*) or an R- id; null "
                    "for a new reviewer question, numbered here",
            "state": "the row's state from the lead's words: open, asked, answered, assumed, unknown or "
                     "not-applicable; ask the lead only if the words leave it unclear",
            "capture": "drafted: the capture the row comes from (\"^c12\"); null for a reviewer question not taken",
            "cite": "drafted: what the ## Changes row cites (the capture, or the checkpoint heading in ## Reviews)",
            "finding": "drafted: the ## Reviews finding the row stands for",
            "area": "drafted: the finding's area codes; a new R- id takes the first",
            "existing": "drafted: the copy already has a row, changed in place",
            "question": "drafted: a reviewer question's question",
            "quote": "drafted: a reviewer question's quote, \"<the words>\" in [[<page>]]",
            "severity": "drafted: a reviewer question's severity, high or normal",
            "unknown": "unknown: the open UNK-nnn the row waits on",
            "item": "answered: the ID of the item the answer was written into",
            "source": "answered: one SRC-nn from sources.md (a first-hand row counts), or one page quote "
                      "\"<the words>\" in [[<page>]] of words on the page before this close",
            "answer": "answered: the capture holding the answer (\"^c31\"); default the row's capture",
            "belief": "assumed: the capture holding what is believed; default the row's capture",
            "load_bearing": "assumed: yes when the captures show the plan resting on it, no otherwise",
            "signpost": "assumed: the capture holding what the lead said would show it wrong",
            "reason": "not-applicable: the capture holding why it doesn't apply; default the row's capture",
            "covers": "an initiative row's scope: what level it answers (app, contract, capability, ...)",
            "by": "the handle who said it; default the capture's origin"},
    judgment=("state", "item", "source", "answer", "belief", "load_bearing", "signpost", "reason"),
    required=("state",),
    example={"copy": "Q-DAT-03@INI-001", "state": "answered", "capture": "^c12", "item": "CON-002",
             "source": "SRC-03"})


# --- reading what the item names ------------------------------------------------------------------------------------

def words(record, ref):
    """The words a capture quotes, without the copy IDs it starts with, or None."""
    said = textedit.quote(record, ref)
    return LEADING_IDS.sub("", said, count=1).strip() if said else None


def by_of(item, record):
    if item.get("by"):
        return str(item["by"]).strip()
    capture = record.capture(item.get("capture")) if item.get("capture") else None
    origin = capture.origin.strip() if capture is not None else ""
    return origin if HANDLE.match(origin) else None


def first_area(item):
    found = AREA.findall(str(item.get("area") or ""))
    return found[0] if found else None


def ledger_page(view):
    return textedit.page_path(view, PAGE)


def existing_rows(text):
    """{copy: (line index, ledger.Row)} of the page's ledger table."""
    lines = text.rstrip("\n").split("\n")
    header = textedit.find_table(lines, ledger.HEADER)
    if header is None:
        return {}
    found = {}
    for index in range(header + 2, textedit.table_rows_end(lines, header)):
        cells = [c.strip() for c in parse.split_row(lines[index])]
        row = ledger.parse_row("", index, cells)
        found.setdefault(row.copy, (index, row))
    return found


# --- numbering ------------------------------------------------------------------------------------------------------

def next_reviewer_id(view, area):
    """`R-<area>-nn`, one past every number this vault (as staged) and every other branch holds for that area."""
    exact = re.compile(rf"(?<![A-Za-z0-9-])R-{area}-(\d+)(?!\d)")
    token = re.compile(rf"^{area}-(\d+)$", re.M)  # idgit's token for R-<area>-nn (see the module docstring)
    branches = list(getattr(view, "branch_texts", None) or ())
    numbers, width = set(), REVIEWER_WIDTH
    for text in list(textedit.texts(view).values()) + branches:
        for found in exact.findall(text):
            numbers.add(int(found))
            width = max(width, len(found))
    for text in branches:
        numbers.update(int(found) for found in token.findall(text))
    return f"R-{area}-{(max(numbers) + 1 if numbers else 1):0{width}d}"


# --- page quotes ----------------------------------------------------------------------------------------------------

def quotable(text):
    """A page's hand-written text: no frontmatter, no generated block or comment, and not the ledger section (a row
    can't be evidenced by itself)."""
    _, start, _ = parse.split_frontmatter(text)
    lines = text.split("\n")[start or 0:]
    kept, skipping = [], False
    for line in lines:
        if line.startswith("## "):
            skipping = line[3:].strip() == HEADING
        if not skipping:
            kept.append(line)
    return re.sub(r"<!--.*?-->", " ", "\n".join(kept), flags=re.S)


def under_settled_item(text, said):
    """True when the words sit under an item whose State is fact or decided."""
    lines = text.split("\n")
    for index, line in enumerate(lines):
        found = ITEM_HEADING.match(line)
        if not found:
            continue
        end = textedit.section_end(lines, index, len(found["hashes"]))
        section = "\n".join(lines[index:end])
        state = STATE_OF_ITEM.search(section)
        if said in questions.normal_text(section) and state and state["state"] in ("fact", "decided"):
            return True
    return False


def written_this_close(record, said):
    """True when the quoted words are the lead's words from this session's captures: what close copies onto pages."""
    for capture in record.captures.values():
        for text in (capture.words, capture.quote):
            heard = questions.normal_text(text)
            if said in heard or (len(heard.split()) >= questions.MIN_QUOTE_WORDS and heard in said):
                return True
    return False


def quote_refusal(view, record, value):
    match = questions.QUOTE_RE.match(value)
    if not match:
        return textedit.refusal("ledger-answered-source", "I can only write that as answered with the source it "
                                                          "comes from.",
                                f"source {value!r} must be exactly one SRC-nn, or one quote \"<the words>\" in "
                                "[[<page>]].", override="write the row as assumed instead")
    path = textedit.page_path(view, match["page"].strip())
    said = questions.normal_text(match["text"])
    text = view.text(path) if path else None
    if text is None or len(said.split()) < questions.MIN_QUOTE_WORDS or said not in questions.normal_text(
            quotable(text)):
        return textedit.refusal("ledger-quote-not-on-page", "I couldn't find those words on that page, so I filed "
                                                            "nothing.",
                                f"The quote {value!r} must be at least {questions.MIN_QUOTE_WORDS} words of the "
                                "page's hand-written text, outside the ledger.",
                                override="cite an SRC-nn instead, or write the row as assumed")
    if written_this_close(record, said) and not under_settled_item(text, said):
        return textedit.refusal("ledger-quote-this-close", "Those words are your own answer, which this close wrote "
                                                           "onto the page, so they can't be its evidence too.",
                                "Cite a source the answer comes from: an SRC-nn, or the lead's first-hand row in "
                                "sources.md (vela add source), or quote words that were on the page before this close.",
                                override="write the row as assumed, with a signpost")
    return None


# --- validate -------------------------------------------------------------------------------------------------------

def validate(item, vault, record):
    found = textedit.context_refusals(vault) + textedit.capture_refusals(item, record)
    state = item["state"]
    if state not in ledger.STATES:
        return found + [textedit.refusal("ledger-state", "I couldn't tell how that question ended, so I filed nothing.",
                                         f"state {state!r} is not one of {', '.join(ledger.STATES)}.",
                                         override="none: pick the state from the lead's words")]
    if ledger_page(vault) is None:
        found.append(textedit.refusal("ledger-page", "I can't find the page the question ledger lives on.",
                                      f"The vault has no {PAGE}.md."))
    found += copy_refusals(item)
    if not item.get("capture") and not item.get("cite"):
        found.append(textedit.refusal("ledger-cite", "I can't tell where that answer was said, so I filed nothing.",
                                      "Give capture (the capture it comes from) or cite (a reviewer question's "
                                      "checkpoint heading)."))
    if state != "open" and by_of(item, record) is None:
        found.append(textedit.refusal("ledger-by", "I need to know who said that, so the row says who decided it.",
                                      "Give by: the handle of whoever recorded or decided it (vela whoami for the "
                                      "lead's).", override="none: a row that isn't open names who decided it"))
    return found + STATE_CHECKS[state](item, vault, record) + pointer_refusals(item, vault, record)


def copy_refusals(item):
    copy = item.get("copy")
    if copy:
        if not ledger.parse_copy(str(copy))[0]:
            return [textedit.refusal("ledger-copy", "I don't recognize that question's number, so I filed nothing.",
                                     f"copy {copy!r} is not a copy ID (Q-DAT-02@APP-booking), a wildcard "
                                     "(Q-OPS-01@APP-*) or a reviewer question (R-FIN-01).")]
        return []
    found = []
    if first_area(item) is None:
        found.append(textedit.refusal("ledger-area", "I can't number that reviewer's question without its area.",
                                      "A new reviewer question needs area: the finding's area code, such as FIN."))
    if not item.get("question") or not item.get("quote"):
        found.append(textedit.refusal("ledger-reviewer", "That reviewer's question is missing its words, so I filed "
                                                         "nothing.",
                                      "A new reviewer question needs question and quote from its ## Reviews row."))
    if item.get("severity") and item["severity"] not in ("high", "normal"):
        found.append(textedit.refusal("ledger-reviewer", "That reviewer's question has a severity I don't know.",
                                      f"severity {item['severity']!r} is high or normal."))
    return found


def _answered(item, vault, record):
    found = []
    if not item.get("item"):
        found.append(textedit.refusal("ledger-answered-item", "I can only write that as answered once the answer is "
                                                              "written into an item.",
                                      "Give item: the ID of the item holding the answer.",
                                      override="write the row as assumed instead"))
    elif textedit.find(vault, str(item["item"])) is None:
        found.append(textedit.refusal("ledger-answered-item", "I can't find the item that answer went into.",
                                      f"{item['item']} is no item in this vault; add it first, then point item at it."))
    if not words(record, item.get("answer") or item.get("capture")):
        found.append(textedit.refusal("ledger-answered-answer", "I need the capture holding the answer.",
                                      "Give answer: the capture holding the lead's answer (\"^c31\")."))
    source = str(item.get("source") or "").strip()
    if not source:
        found.append(textedit.refusal("ledger-answered-source", "I can only write that as answered with the source it "
                                                                "comes from.",
                                      "Give source: an SRC-nn (a first-hand answer gets its own row in sources.md "
                                      "first, vela add source), or a quote of words on the page before this close.",
                                      override="write the row as assumed instead"))
    elif SOURCE_ID.match(source):
        if source_row(vault, source) is None:
            found.append(textedit.refusal("ledger-source-unregistered", "That source isn't in the register yet, so I "
                                                                        "filed nothing.",
                                          f"{source} has no row in sources.md; add it with vela add source first.",
                                          override="write the row as assumed instead"))
    else:
        refusal = quote_refusal(vault, record, source)
        found += [refusal] if refusal else []
    return found


def _assumed(item, vault, record):
    missing = []
    if str(item.get("load_bearing") or "") not in ("yes", "no"):
        missing.append("load_bearing (yes or no)")
    if not words(record, item.get("signpost")):
        missing.append("signpost (the capture saying what would show it wrong)")
    if not words(record, item.get("belief") or item.get("capture")):
        missing.append("belief (the capture holding what is believed)")
    if not missing:
        return []
    return [textedit.refusal("ledger-assumed", "I need a little more before I can write that as an assumption.",
                             f"An assumed row needs {', '.join(missing)}.",
                             override="none: the gate reads which assumptions the plan rests on")]


def _unknown(item, vault, record):
    ident = str(item.get("unknown") or "")
    located = textedit.find(vault, ident) if re.fullmatch(r"UNK-\d{3}", ident) else None
    if located is not None:
        from vela.decisions.resolve import state_of, unknown_block
        text = vault.text(located[0])
        start, end = unknown_block(text, ident)
        block = text.split("\n")[start:end]
        owner = next((l.split(":**", 1)[1].strip() for l in block if l.startswith("- **Owner:**")), "")
        if state_of(block) == "open" and vault_schema.OWNER_BULLET_RE.match(owner):
            return []
    return [textedit.refusal("ledger-unknown", "That question waits on an unknown nobody is chasing, so I filed "
                                               "nothing.",
                             f"unknown {ident or '(none)'} must be an open UNK-nnn whose Owner is a handle; add or fix "
                             "the unknown first (vela add unknown).",
                             override="write the row as assumed or open instead")]


def _not_applicable(item, vault, record):
    reason = words(record, item.get("reason") or item.get("capture"))
    if not reason:
        return [textedit.refusal("ledger-not-applicable", "I need the reason that question doesn't apply.",
                                 "Give reason: the capture saying why it doesn't apply.")]
    cue = questions.deferral_cue(reason)
    if cue:
        return [textedit.refusal("ledger-not-applicable-defers", "That reason says not yet, rather than never, so "
                                                                 "I'd keep the question open.",
                                 f"The reason defers the question ({cue!r}); write the row as unknown (with an open "
                                 "UNK-nnn) or assumed.", override="none: not-applicable takes it off every gate")]
    return []


def _asked(item, vault, record):
    if item.get("capture"):
        return []
    return [textedit.refusal("ledger-asked", "I need the capture where that was asked.",
                             "An asked row needs capture: the capture where it was asked.")]


STATE_CHECKS = {"open": lambda i, v, r: [], "asked": _asked, "answered": _answered, "assumed": _assumed,
                "unknown": _unknown, "not-applicable": _not_applicable}


# --- whose words may leave the machine -------------------------------------------------------------------------------

def free_text_refs(item):
    """The captures whose words this row copies into a free-text cell (answer, belief, signpost, reason)."""
    capture = item.get("capture")
    state = item["state"]
    if state == "answered":
        return [item.get("answer") or capture]
    if state == "assumed":
        return [item.get("belief") or capture, item.get("signpost")]
    if state == "not-applicable":
        return [item.get("reason") or capture]
    return []


def kept_in_notes(record, ref, lead):
    """The capture behind `ref` when a person's words in it may not be written to a page (their own quote-yes is
    missing, and they are not the lead), else None. Claude's own captures are no one's words to hold back."""
    capture = record.capture(ref) if ref else None
    if capture is None or not capture.is_person or consent.may_quote(capture, record, lead):
        return None
    return capture


def pointer_refusals(item, vault, record):
    """A row can point at a person's first-hand source only when it knows who they are: a handle, and a lead to tell
    them apart from. Otherwise the words would be copied (Silent Fallback) or the pointer would name no one."""
    lead = getattr(vault, "lead", None)
    out = []
    for ref in free_text_refs(item):
        capture = kept_in_notes(record, ref, lead)
        if capture is None:
            continue
        if lead is None:
            out.append(textedit.refusal("ledger-lead-unknown", "I don't know your GitHub handle yet, so I can't tell "
                                        "whose words may go on the page.",
                                        "Ask the lead once, run vela whoami --set <handle>, then file it again.",
                                        override="none: whose words go on a page is checked against the lead's handle"))
            return out
        if not receipts.is_handle(capture.origin):
            out.append(textedit.refusal("ledger-speaker-not-handle", f"I don't have a handle for {capture.origin.strip()}, "
                                        "so I can't point at their first-hand source.",
                                        f"Re-capture ^c{capture.n} with their handle (like @raj) as origin, then file "
                                        "it again.", override="leave the row's words out"))
    return out


def first_hand_pointers(item, vault, record):
    """({ref: "see SRC-nn"}, [Write]) for the cells that hold a person's words back. The first-hand row is the one
    already in sources.md, or a new one added here (as the split does), numbered past every open branch."""
    lead = getattr(vault, "lead", None)
    path = textedit.page_path(vault, "sources")
    text, cites, writes = (vault.text(path) if path else ""), {}, []
    for ref in free_text_refs(item):
        capture = kept_in_notes(record, ref, lead)
        if capture is None or ref in cites:
            continue
        handle = receipts.handle_ref(capture.origin)
        ident = firsthand.row_id(text, handle)
        if ident is None:
            ident = textedit.next_id(vault, "SRC")
            text = firsthand.with_row(text, ident, handle, textedit.today(vault))
            writes = [schema.Write(path, text)]
        cites[ref] = f"see {ident}"
    return cites, writes


# --- writing --------------------------------------------------------------------------------------------------------

def free_text(said):
    """The words as one Evidence value: a `;` in them is quoted so it can't split the cell."""
    said = textedit.inline(said)
    if ";" in said:
        said = '"' + said.replace('"', "'") + '"'
    return textedit.cell(said)


def evidence(item, vault, record, old, cites=None):
    state = item["state"]
    cites = cites or {}

    def said(ref):
        return cites[ref] if ref in cites else free_text(words(record, ref))

    pairs = []
    if state == "asked":
        pairs.append(("capture", textedit.capture_ref(record, item["capture"])))
    elif state == "answered":
        pairs += [("item", textedit.link(vault, str(item["item"]), cell_link=True)),
                  ("answer", said(item.get("answer") or item["capture"])),
                  ("source", textedit.cell(str(item["source"]).strip()))]
    elif state == "assumed":
        pairs += [("belief", said(item.get("belief") or item["capture"])),
                  ("load-bearing", str(item["load_bearing"])),
                  ("signpost", said(item["signpost"]))]
    elif state == "unknown":
        pairs.append(("unknown", textedit.link(vault, str(item["unknown"]), cell_link=True)))
    elif state == "not-applicable":
        pairs.append(("reason", said(item.get("reason") or item["capture"])))
    if item.get("covers"):
        pairs.append(("covers", textedit.cell(item["covers"])))
    copy = item.get("copy")
    if not copy or ledger.parse_copy(str(copy))[0] == "reviewer":
        kept = dict(old.evidence) if old is not None else {}
        for key in ledger.REVIEWER_KEYS:
            value = item.get(key) or kept.get(key)
            if value:
                pairs.append((key, free_text(value) if key == "question" else textedit.cell(value)))
    return "; ".join(f"{key}: {value}" for key, value in pairs)


def ensure_ledger(text):
    """The page with a `## Question ledger` table: the section made after `## Risks` when it is missing, with the
    empty `undisposed-questions` block render fills, as close/LEDGER.md asks."""
    lines = text.rstrip("\n").split("\n")
    if textedit.find_table(lines, ledger.HEADER) is not None:
        return text
    block = []
    if f"generated:{GENERATED}" not in text:
        block += [f"<!-- generated:{GENERATED} sha=00000000: {parse.MARKER_TEXT} -->", f"<!-- /generated:{GENERATED} -->",
                  ""]
    block += ["| " + " | ".join(ledger.HEADER) + " |", "|" + "---|" * len(ledger.HEADER)]
    risks = textedit.find_heading(lines, "Risks", 2)
    before = ["History"]
    if risks is not None:
        after = textedit.section_end(lines, risks, 2)
        if after < len(lines):
            before = [lines[after][3:].strip()]
    return textedit.insert_block(text, HEADING, block, before=before)


def row_line(item, vault, record, copy, old, cites=None):
    by = by_of(item, record) or ""
    date = textedit.today(vault) if by else ""
    return textedit.row(copy, item["state"], evidence(item, vault, record, old, cites), by, date)


def parsed_back(line, copy):
    from vela.decisions import Refused  # the core's whole-file refusal, raised on a vela bug only
    row = ledger.parse_row("", 0, [c.strip() for c in parse.split_row(line)])
    if row.problems or row.copy != copy:
        raise Refused([textedit.refusal("ledger-grammar", "Something went wrong on my side, so I filed nothing.",
                                        f"vela bug: the ledger row would not parse ({'; '.join(row.problems)}): "
                                        f"{line}", override="none: this is a fault in vela, not a rule")])


def apply(item, vault, record):
    path = ledger_page(vault)
    text = ensure_ledger(vault.text(path))
    copy = str(item.get("copy") or next_reviewer_id(vault, first_area(item)))
    rows = existing_rows(text)
    index, old = rows.get(copy, (None, None))
    cites, sources = first_hand_pointers(item, vault, record)
    line = row_line(item, vault, record, copy, old, cites)
    parsed_back(line, copy)
    if index is None:
        page = textedit.add_row(text, ledger.HEADER, line)
    else:
        lines = text.rstrip("\n").split("\n")
        if lines[index] == line:
            return sources  # this row is already written as it would be
        lines[index] = line
        page = "\n".join(lines) + "\n"
    cite = item.get("cite") or textedit.capture_link(record.id, item["capture"])
    rec = textedit.add_change(textedit.record_text(record, vault), copy, old.state if old else "-", item["state"], cite)
    return [schema.Write(path, page)] + sources + textedit.record_writes(record, vault, rec)
