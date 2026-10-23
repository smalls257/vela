"""Validate a whole decision file, then say every write it makes, or none (overhaul Task 4, plan 4.1). Pure.

The Violation this exists to prevent is a Silent Fallback across a batch: a file whose third item is refused, applied
one item at a time, leaves the first two pages looking decided while the rest was turned away, and nothing on the
page says the batch was cut short. So `plan` refuses or writes the whole file:

1. the file's shape (`load`): JSON, `version` 1, a known `kind`, `session`, a list of `items`;
2. the file was drafted for the open session (a file from another session would file its answers into this record);
3. the kind's module exists (`kind_module`). A kind in `schema.KINDS` with no module yet is refused plainly ("I can't
   file that kind of decision yet"), never skipped, because a skipped item looks filed to the model that wrote it;
4. every item: no field the kind doesn't take (a typo'd field ignored is a lost answer), every required field set,
   every capture the drafter sealed in `seen` unchanged, then the kind's own `validate`;
5. only when nothing at all was refused, each item's `apply` in order, each seeing the writes before it (`Staged`), so
   two items touching one page compose instead of the second clobbering the first. A kind may still raise `Refused`
   from `apply`; the whole file is then refused, nothing written.

All refusals are collected, not just the first, so the lead hears everything that stands in the way at once.

Writing is the edge's work (`edge/apply.py`, every file or none); this module only says what to write.
"""
import hashlib
import importlib
import json
from dataclasses import dataclass

from vela import say
from vela.decisions import consent, record as records, schema


class Refused(Exception):
    """A kind's `apply` found something `validate` could not: the whole file is refused."""

    def __init__(self, refusals):
        super().__init__("; ".join(r.plain for r in refusals))
        self.refusals = list(refusals)


@dataclass(frozen=True)
class Decision:
    kind: str
    session: str
    items: list
    raw: dict

    @property
    def applied(self):
        return self.raw.get("applied")


def _file_refusal(rule, plain, fix):
    return say.Refusal(rule, plain, fix, override="none: a file vela can't read can't be filed; draft it again "
                                                  "(or file by hand with the lead's words in the record)")


def load(text):
    """(Decision, []) for a well-formed file, else (None, [Refusal])."""
    try:
        raw = json.loads(text)
    except ValueError as exc:
        return None, [_file_refusal("decision-file-json", "The file with your answers is damaged, so I filed nothing.",
                                    f"Draft the file again; it isn't JSON ({exc}).")]
    if not isinstance(raw, dict):
        return None, [_file_refusal("decision-file-shape", "The file with your answers is damaged, so I filed nothing.",
                                    "Draft the file again; it must be one JSON object.")]
    if raw.get("version") != schema.VERSION:
        return None, [_file_refusal("decision-file-version",
                                    "That file was written by a newer or older vela than this one, so I filed nothing.",
                                    f"Draft it again with this vela; it says version {raw.get('version')!r}, "
                                    f"this vela reads {schema.VERSION}.")]
    problems = [name for name, kind in (("kind", str), ("session", str), ("items", list))
                if not isinstance(raw.get(name), kind)]
    if not problems and not all(isinstance(item, dict) for item in raw["items"]):
        problems.append("items")
    if problems:
        return None, [_file_refusal("decision-file-shape", "The file with your answers is damaged, so I filed nothing.",
                                    f"Draft the file again; these are missing or the wrong shape: "
                                    f"{', '.join(problems)}.")]
    return Decision(raw["kind"], raw["session"], raw["items"], raw), []


def kind_module(kind):
    """(module, None) for a kind with a module, else (None, Refusal). A module that exists but fails its own imports
    raises: that is a vela bug, not a kind that isn't built yet."""
    if kind not in schema.KINDS:
        return None, say.Refusal("decision-kind-unknown", "I don't know that kind of decision, so I filed nothing.",
                                 f"The file's kind {kind!r} is not one of: {', '.join(schema.KINDS)}. Draft it again.",
                                 override="none in a file: file it by hand, with the lead's words in the record")
    name = f"vela.decisions.{schema.module_name(kind)}"
    try:
        return importlib.import_module(name), None
    except ModuleNotFoundError as exc:
        if exc.name != name:
            raise
    return None, say.Refusal("decision-kind-not-built", "I can't file that kind of decision yet.",
                             f"vela has no module for {kind!r} decisions yet; file it by hand and tell the lead.",
                             override="none in a file: file it by hand, with the lead's words in the record")


def shape_refusals(kind_schema, item, index):
    """Refusals for item `index` (0-based) against what its kind takes."""
    found = []
    unknown = sorted(set(item) - set(kind_schema.fields) - set(schema.SHARED_KEYS))
    if unknown:
        found.append(say.Refusal("decision-unknown-field", "Part of what you told me went in the wrong place, so I "
                                                           "filed nothing.",
                                 f"Item {index + 1} has fields this kind doesn't take: {', '.join(unknown)}. "
                                 "See vela apply --schema.",
                                 override="none: rename the field to one the kind takes"))
    unfilled = [name for name in kind_schema.required if item.get(name) is None]
    if unfilled:
        found.append(say.Refusal("decision-unfilled", "I still need one of your answers before I can file these.",
                                 f"Item {index + 1} has no value yet for: {', '.join(unfilled)}. Ask the lead, "
                                 "capture the answer, point the field at it.",
                                 override="none: a required field can't be skipped; the lead may decline the item"))
    return found


def seen_refusals(item, record):
    found = []
    for ref, stored in sorted((item.get("seen") or {}).items()):
        capture = record.capture(ref)
        refusal = consent.exists(ref, record) if capture is None else consent.unchanged_since_draft(capture, stored)
        if refusal is not None:
            found.append(refusal)
    return found


class Staged:
    """The vault as the items see it: the vault model, plus every write earlier items made. `read(path)` gives a
    file's text from disk (or None), so a file that isn't a page (the record, a new file) can be read too."""

    def __init__(self, model, read):
        self.model, self._read, self.pending = model, read, {}

    def text(self, path):
        if path in self.pending:
            return self.pending[path]
        return self._read(path)

    def stage(self, writes):
        for write in writes:
            self.pending[write.path] = write.text

    @property
    def writes(self):
        return [schema.Write(path, text) for path, text in self.pending.items()]


def plan(decision, staged, record):
    """(writes, refusals). Refusals non-empty means write nothing."""
    if decision.session != record.id:
        return [], [say.Refusal("decision-session", "Those answers were written down in another session, so I filed "
                                                    "nothing here.",
                                f"The file is for {decision.session}; the open session is {record.id}. Apply it in "
                                "its own session, or draft it again here.",
                                override="none: draft the file again in this session")]
    module, refusal = kind_module(decision.kind)
    if refusal is not None:
        return [], [refusal]
    refusals = []
    for index, item in enumerate(decision.items):
        found = shape_refusals(module.SCHEMA, item, index) + seen_refusals(item, record)
        refusals += found or list(module.validate(item, staged, record))
    if refusals:
        return [], refusals
    try:
        for item in decision.items:
            staged.stage(module.apply(item, staged, record))
    except Refused as exc:
        return [], exc.refusals
    return staged.writes, []


def pages_hash(writes):
    """sha256 over every written path and text, in path order: what `applied.pages` holds. A content hash, not a commit,
    because a reader copy has no commits (plan 4.1)."""
    digest = hashlib.sha256()
    for write in sorted(writes, key=lambda w: w.path):
        digest.update(write.path.encode("utf-8") + b"\0" + write.text.encode("utf-8") + b"\0")
    return digest.hexdigest()


def applied_text(decision, writes, record_after):
    """The decision file's new text, with `applied` written back."""
    raw = dict(decision.raw)
    raw["applied"] = {"pages": pages_hash(writes), "captures": record_after.count}
    return json.dumps(raw, indent=2, ensure_ascii=False) + "\n"


def record_after(record, staged):
    """The record as it will be once the writes land (a kind may add lines to it)."""
    return records.from_text(record.id, record.path, staged.text(record.path) or record.text)
