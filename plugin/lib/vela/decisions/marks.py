"""The `marks` apply kind: each capture's mark written into its line (close section 3, "Write the marks"). Pure. The
items are the ones `vela marks plan` drafts (Task 14, `vela.markrules`), with the model's and the lead's answers
filled in.

    - [<tag>] (<origin>) <words> → keep: [[<page>#<heading>|<ID>]] (<state>) ^cNN
    - [<tag>] (<origin>) <words> → park ^cNN
    - [<tag>] (<origin>) <words> → drop: <reason> ^cNN

The Violation this exists to prevent is a Leaky Narrative between the rules and the record: the mark grammar lived in
close's prose, and a mark typed by hand that `markrules.parse_mark` can't read is a capture the gate counts as
unmarked, or a keep that links a heading that doesn't exist. Here the text comes from `markrules.format_mark`, the
same module that parses it, and every keep target is looked up in the vault as staged, so the link resolves.

The rules, with their reasons:

- **Before the block ID.** The `^cNN` stays the last token on the line, because links to the capture use it
  (CONVENTIONS "Sessions"); a mark after it would break every `[[<record>#^cNN]]`.
- **A capture keeps the mark it has.** A grill's `(decided)`, a Discover's `(fact)`, a Boundary's `(assumption)` were
  written by the mode that settled them; marking over them would overwrite a decision with a default. So an item for a
  capture that already carries a mark is refused, not applied twice.
- **A leftover is the lead's** (`needs_lead`: Claude's own unknown or deferral, words someone else said): it is
  filed only on a capture of the lead's answer whose origin is a person, because "Claude never decides it alone".
- **An unknown is kept or dropped, never parked**, and a drop carries its reason (from `drop_reason`, else the lead's
  answer in their words).
- **A new unknown is written as it is marked**: a keep to an unknown with no `id` yet is numbered and written by `add
  unknown` (with the owner and ask-by date `marks plan` worked out), then the mark links it, so no mark links a
  heading that doesn't exist. Every other new item is added first (`vela add`), and its ID goes in `id`.
- **Never a fact from a plan**: a keep at `fact` names its `source`, a registered source whose Kind is `exists` or
  `repo` (`resolve.fact_source_refusal`): a capture becomes a fact only when the lead named its source and it has a
  row in `sources.md`.

- **A lead's yes kept at `assumption` is listed as ready to decide.** A shape, boundary or requirements session can't
  set `decided`, and the rule "run `vela decide` on a plain yes" was skipped in the paid runs (E81), so the yes was
  recorded and forgotten (a Silent Fallback of consent). The keep names the item and the state, so this kind lists it
  under `## Ready to decide` itself (`ready.from_keep`); the next grill opens with it.

Fields the drafter writes for the record and the PR body (`rule`, `reason`, `lifted`, `recommend`, `deferral`, ...)
are taken and not written: they say why the default was chosen.
"""
from vela import markrules, say
from vela.decisions import add_unknown, consent, ready, resolve, schema, textedit

LEDGER_PAGE = "11-unknowns-and-risks"
LEDGER_HEADING = "Question ledger"
MARKS = ("keep", "park", "drop")

SCHEMA = schema.KindSchema(
    fields={"capture": "the capture to mark (\"^c12\")",
            "mark": "keep, park or drop",
            "to": "where a keep goes: unknown, ledger, subject, inkling, assumption, contract, constraint, ...",
            "id": "the kept item's ID (a list of copy IDs for a ledger keep); null for a new unknown, numbered here",
            "state": "the kept item's state: inkling, assumption, fact, decided, open, resolved, subject, or the "
                     "ledger row's state",
            "page": "for an inkling with no ID of its own: the ID of the page it sits on",
            "heading": "the heading a keep links, when it isn't the item's own heading or the page's title",
            "source": "for a keep at fact: the SRC-nn row it comes from",
            "drop_reason": "why it is dropped, when the lead's answer doesn't say it in words to copy",
            "name": "for a new unknown: its short name",
            "owner": "for a new unknown: the lead chasing it",
            "ask": "for a new unknown: who would actually know",
            "ask_by": "for a new unknown: the date the lead gave or said yes to (never one the tool works out)",
            "blocks": "for a new unknown: the IDs it blocks",
            "lead_answer": "for a leftover: the capture holding the lead's answer (\"^c31\"), never their words",
            "needs_lead": "drafted by marks plan: true when only the lead can settle it",
            "rule": "drafted by marks plan: the default that proposed it", "reason": "drafted: that default's reason",
            "lifted": "drafted: a line the lead said, copied word for word", "recommend": "drafted: the default "
            "proposed to the lead", "subject_type": "drafted: PTY or SV for a typed subject",
            "unknown": "drafted: the unknown a ledger row waits on", "options_considered": "drafted: for a shape "
            "pick, the options weighed", "deferral": "drafted: true when the capture defers to a grill"},
    judgment=("mark", "lead_answer"), required=("capture", "mark"),
    example={"capture": "^c12", "mark": "keep", "to": "unknown", "id": "UNK-004", "state": "open"})


def ids_of(item):
    value = item.get("id")
    return [str(v) for v in value] if isinstance(value, list) else ([str(value)] if value else [])


def new_unknown(item):
    """The `add unknown` item a keep to a not-yet-numbered unknown writes, or None."""
    if item.get("mark") != "keep" or item.get("to") != "unknown" or ids_of(item):
        return None
    return {"name": item.get("name"), "capture": item["capture"], "owner": item.get("owner"), "ask": item.get("ask"),
            "ask_by": item.get("ask_by"), "blocks": item.get("blocks") or []}


def validate(item, vault, record):
    found = textedit.context_refusals(vault)
    missing = consent.exists(item["capture"], record)
    if missing is not None:
        return found + [missing]
    _, line = textedit.capture_line(textedit.record_text(record, vault), item["capture"])
    if line is not None and textedit.existing_mark(line) is not None:
        found.append(textedit.refusal("marks-already-marked", "That note already has its place, so I left it.",
                                      f"{item['capture']} is marked ({textedit.existing_mark(line)}); a mode that "
                                      "settled it wrote that mark. Take the item out of the file.",
                                      override="none: an earlier mode's mark is never overwritten"))
    if item["mark"] not in MARKS:
        return found + [textedit.refusal("marks-mark", "I couldn't tell where that note goes.",
                                         f"mark {item['mark']!r} is keep, park or drop.")]
    found += _lead_refusals(item, record)
    if item["mark"] == "park" and record.capture(item["capture"]).tag == "unknown":
        found.append(textedit.refusal("marks-unknown-parked", "A question is kept or dropped, never set aside.",
                                      "Keep it as an unknown (with an owner and an ask-by date) or drop it with a "
                                      "reason.", override="none: an unknown is never parked"))
    if item["mark"] == "drop" and not (item.get("drop_reason") or item.get("lead_answer")):
        found.append(textedit.refusal("marks-drop-reason", "I need the reason that note is dropped.",
                                      "Give drop_reason, or the lead_answer capture saying why."))
    if item["mark"] == "keep":
        found += _keep_refusals(item, vault, record)
    return found


def _lead_refusals(item, record):
    if not item.get("needs_lead"):
        return []
    if not item.get("lead_answer"):
        return [textedit.refusal("marks-needs-lead", "Only you can settle that one, and I don't have your answer yet.",
                                 f"{item['capture']} is a leftover: ask the lead, capture their answer, set "
                                 "lead_answer.", override=consent.OVERRIDE_YES)]
    refusal = consent.exists(item["lead_answer"], record) or consent.from_a_person(record.capture(item["lead_answer"]))
    return [refusal] if refusal else []


def _keep_refusals(item, vault, record):
    found = []
    if not item.get("state"):
        found.append(textedit.refusal("decision-unfilled", "I still need one of your answers before I can file these.",
                                      f"{item['capture']}: a keep needs state.", audience=say.MODEL))
    if item.get("state") == "fact":
        refusal = resolve.fact_source_refusal(vault, item.get("source"))
        if refusal is not None:
            found.append(refusal)
    unknown = new_unknown(item)
    if unknown is not None:
        if not unknown["name"]:
            return found + [textedit.refusal("decision-unfilled", "I still need one of your answers before I can file "
                                                                  "these.",
                                             f"{item['capture']}: a new unknown needs name, its short heading.",
                                             audience=say.MODEL)]
        return found + add_unknown.validate(unknown, vault, record)
    if item.get("to") == "ledger":
        if not ids_of(item) or None in (item.get("id") or [None]):
            found.append(textedit.refusal("marks-ledger-id", "That reviewer's question has no number yet.",
                                          "Apply the ledger file first; it numbers new reviewer questions, then put "
                                          "the R- ID in id."))
        return found
    target = item.get("page") if not ids_of(item) else None
    for ident in ids_of(item) or ([str(target)] if target else []):
        if textedit.find(vault, ident) is None:
            found.append(textedit.refusal("marks-target", "I can't find where that note was meant to go.",
                                          f"{ident} is not in the vault; add the item first (vela add), then point "
                                          "id at it."))
    if not ids_of(item) and not target:
        found.append(textedit.refusal("decision-unfilled", "I still need one of your answers before I can file these.",
                                      f"{item['capture']}: a keep needs id (or page, for an inkling).",
                                      audience=say.MODEL))
    return found


def targets(item, vault):
    state = item["state"]
    if item.get("to") == "ledger":
        return [markrules.Target(LEDGER_PAGE, LEDGER_HEADING, ident, state) for ident in ids_of(item)]
    found = []
    for ident in ids_of(item) or [str(item["page"])]:
        path, heading = textedit.find(vault, ident)
        heading = item.get("heading") or heading or textedit.title_heading(vault.text(path))
        found.append(markrules.Target(textedit.basename(path), heading, ident, state))
    return found


def mark_text(item, vault, record):
    if item["mark"] == "park":
        return markrules.format_mark(markrules.Mark("park"))
    if item["mark"] == "drop":
        reason = item.get("drop_reason") or textedit.quote(record, item["lead_answer"])
        return markrules.format_mark(markrules.Mark("drop", reason=textedit.inline(reason)))
    return markrules.format_mark(markrules.Mark("keep", tuple(targets(item, vault))))


def apply(item, vault, record):
    unknown = new_unknown(item)
    if unknown is not None:
        return add_unknown.apply(unknown, vault, record)  # writes the unknown and marks the capture
    text = textedit.write_mark(textedit.record_text(record, vault), item["capture"], mark_text(item, vault, record))
    if item["mark"] == "keep":
        # the header is read only for a keep that could be a ready-to-decide yes (from_keep ignores the rest)
        stub = textedit.stub_text(record, vault) if item["state"] == ready.KEPT_AT else ""
        for ident in ids_of(item):
            text = ready.from_keep(text, record.id, record.capture(item["capture"]), ident, item["state"],
                                   getattr(vault, "lead", None), stub)
    return textedit.record_writes(record, vault, text)
