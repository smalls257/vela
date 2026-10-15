"""The decision file's shape and the kinds it may carry (overhaul Task 4, plan 4.1 and 4.2). Pure.

The Violation this exists to prevent is a Leaky Narrative between the model and the vault. Without a file the CLI
drafts, the model types the vault's grammar itself (the Changes row, the Override bullet, the mark on a capture),
and every sentence of that grammar in a skill is a place to get it wrong. So the CLI drafts the file with every
computable field filled and every judgment field `null` with a hint; the model only points each judgment field at
the capture that carries the lead's words (`"yes": "^c31"`), never at the words themselves.

    {"version": 1, "kind": "decide", "session": "<record id>", "items": [{...}, ...]}

An item may carry two keys every kind shares: `hints` (field -> what to fill in, written by the drafter) and `seen`
(capture -> hash of its quoted words when the drafter read it, so `apply` can refuse an answer that changed since:
plan 9.1). After a successful apply the file also carries `applied`.

Kinds are a closed list for version 1 (`KINDS`). Each kind is its own module, `vela.decisions.<module>`, so no single
applier knows every kind (Shield): a later task adds a kind by adding its module file, never by editing this file or
`decisions/__init__.py`. A kind module offers:

- `SCHEMA`: a `KindSchema` (its fields with a hint each, which of them are judgment fields, which are required, and
  one example item);
- `validate(item, vault, record) -> list[say.Refusal]`;
- `apply(item, vault, record) -> list[Write]`.

`vault` is a `decisions.Staged` view (the vault model plus the writes earlier items made), `record` a
`decisions.record.OpenRecord`.
"""
import hashlib
import re
from dataclasses import dataclass, field

VERSION = 1
FOLDER = ".vela/decisions"
KINDS = ("marks", "add", "ledger", "decide", "agenda", "override", "defer", "resolve", "allocate", "release", "handoff",
         "challenge")
# A kind whose module name differs from the kind: `vela.decisions.ledger` would shadow nothing today, but the ledger
# parser is `vela.ledger`, and two modules named `ledger` is a reader's trap.
MODULE_NAMES = {"ledger": "ledger_rows"}
# What the lead hears a kind's items called, for "what was filed", one and many. In the lead's words, not the
# builder's (voice audit row 90): "notes from today", never "marks on the record" or "ledger rows".
KIND_WORDS = {"marks": ("note from today", "notes from today"), "add": ("new item", "new items"),
              "ledger": ("answer to the standard questions", "answers to the standard questions"),
              "decide": ("decision", "decisions"), "agenda": ("change to the agenda", "changes to the agenda"),
              "override": ("rule set aside", "rules set aside"), "defer": ("question put off", "questions put off"),
              "resolve": ("answered question", "answered questions"),
              "allocate": ("line of who builds what", "lines of who builds what"),
              "release": ("change to a release", "changes to the releases"),
              "handoff": ("change to what's handed to a team", "changes to what's handed to the teams"),
              "challenge": ("challenge", "challenges")}
SHARED_KEYS = ("hints", "seen")
_SEQ = re.compile(r"^(\d+)-")


@dataclass(frozen=True)
class Write:
    """One file a kind wants written: `path` relative to the vault root, `text` its whole new contents."""
    path: str
    text: str


@dataclass(frozen=True)
class KindSchema:
    """What a kind takes. `fields` maps each field to the hint a drafter writes for it; `judgment` are the fields only
    the lead's answer can fill; `required` must be set (not null) before apply; `example` is one filled item."""
    fields: dict
    judgment: tuple = ()
    required: tuple = ()
    example: dict = field(default_factory=dict)

    def as_json(self):
        return {"fields": dict(self.fields), "judgment": list(self.judgment), "required": list(self.required),
                "example": self.example}


def module_name(kind):
    return MODULE_NAMES.get(kind, kind)


def quote_hash(capture):
    """The hash `seen` keeps for a capture: of its quoted words, so a re-marked capture (`→ filed`) still matches."""
    return hashlib.sha256(capture.quote.encode("utf-8")).hexdigest()


def draft_item(kind_schema, computed):
    """An item as a drafter writes it: the computed fields as given, each judgment field null with its hint."""
    item = dict(computed)
    hints = {}
    for name in kind_schema.judgment:
        if item.get(name) is None:
            item[name] = None
            hints[name] = kind_schema.fields.get(name, "")
    if hints:
        item["hints"] = hints
    return item


def seal(item, record, refs):
    """`item` with `seen` holding the quoted words' hash of each capture in `refs`, as the drafter read them. A ref the
    record does not hold is left out, so `apply` refuses it as missing rather than as changed."""
    seen = dict(item.get("seen") or {})
    for ref in refs:
        capture = record.capture(ref)
        if capture is not None:
            seen[ref] = quote_hash(capture)
    return {**item, "seen": seen}


def draft_path(session, existing, kind):
    """`.vela/decisions/<session>/<seq>-<kind>.json`, numbered one past the highest of `existing` file names."""
    numbers = [int(m.group(1)) for m in map(_SEQ.match, existing) if m]
    return f"{FOLDER}/{session}/{max(numbers, default=0) + 1:02d}-{kind}.json"
