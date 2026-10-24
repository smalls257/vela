"""The `decide` apply kind: one decision filed, sent to the module of its target kind (overhaul Task 16, plan 4.3; grill's
"File each decision as its branch closes"). Pure.

**A dispatcher, and only that** (review S1, Shield). Grill section 4 is nine writes per decision; the seven every target
shares live in `decide_writes`, and what is a target's own (where its state lives, what else it needs before it is
decided) lives in its kind's module, `decide_<kind>.py`, tried in `KINDS` order, most specific first, because an epic and
a slice are pages too:

    allocation_row  CAP-nnn.FRn@APP-<slug>   a row of an app's Requirements allocated, read back with its app
    slice           SLC-nnn                  planned, not decided; only on a passed flow check
    epic            EPC-nnn                  a yes for every criterion group
    contract        CON-nnn                  where the provider stands on record
    fr              CAP-nnn.FRn              a functional requirement
    release         "<release heading>"      a section of 04b-releases.md, named by its heading
    page            any page id with state:  the fallback

Without this split one function would know every target's rules, and a new kind would be an edit to it: a God Method
with a branch per kind. Here a kind adds a file and a name in `KINDS`, and a flag one kind takes is refused on any
other (`field_refusals`), never ignored, because an ignored answer looks filed.

An item:

    {"id": "CON-003", "to": "decided", "readback": "^c30", "yes": "^c31", "why": "^c33", "dissent": null,
     "overrides": [{"rules": ["GATE-4"], "reason": "^c35", "until": "2026-11-30"}], "on_behalf_of": null,
     "by": "@lead", "reader": false}

`by` (the lead's handle) and `reader` (whether this is a reader copy) are computed by the drafter, never asked;
`vela decide` fills them from `.vela/handle` and the role. A change of mind is `{"id": ..., "reopen": true, "why":
"^cN", "by": ...}`: the state goes back (to `assumption`, or `reopened` for an epic) and the Changes row records it,
citing the lead's reason, which `close gate` then reads like any other change out of `decided`.

What is refused, plainly, and nothing written: the target isn't in the vault; it is already where the decision would
put it (`vela decide` turns that into exit 3, "already decided; reopen?"); the yes isn't a yes, or comes before the
read-back (`consent`); the gate failed and the lead set none of its reasons aside (`gates.verdict`); and what the
target kind adds. The grill gate needs the flow check's standings for a slice or a flow: the shell attaches them to the
view as `flows`; a view without them reads as "not checked", never as a pass.
"""
import importlib
import re

from vela import say

from vela.decisions import consent, decide_writes, schema, textedit

KINDS = ("allocation_row", "slice", "epic", "contract", "fr", "release", "page")
SHARED = {"id": "the item's ID (a release by its heading, an allocation row as CAP-nnn.FRn@APP-<slug>)",
          "to": "where it goes: decided (planned for a slice); computed, leave it as drafted",
          "readback": "the capture where the final wording was read back",
          "yes": "the capture holding the lead's yes to that read-back, after it",
          "why": "the capture holding the lead's reason, in their words (null when they gave none)",
          "dissent": "the capture holding a disagreement, in the dissenter's words",
          "overrides": "the rules the lead set aside: [{\"rules\": [\"GATE-4\"], \"reason\": \"^c35\", \"until\": "
                       "\"YYYY-MM-DD\"}]; until only for a standing rule",
          "on_behalf_of": "the owner's handle when the lead decides for an owner who isn't here (with GATE-5)",
          "by": "the lead's handle; computed",
          "reader": "true in a reader copy; computed",
          "reopen": "true to reopen a decided item (a change of mind), with why",
          "stated_in": "the source (SRC-nn) that states the decision, when an import confirms it: no options needed",
          "picked": "the option the lead picked and the capture where they picked it: \"<option>=^cP\"",
          "rejected": "each option set aside: [\"<option>=^cR\"] (the capture holding the lead's reason) or "
                      "[\"<option>=declined\"]"}
JUDGMENT = ("readback", "yes", "why", "dissent", "overrides", "on_behalf_of", "picked", "rejected")


def kind_module(kind):
    return importlib.import_module(f"vela.decisions.decide_{kind}")


def kind_fields():
    """{field: (kind, hint)} for every field a target kind adds."""
    out = {}
    for kind in KINDS:
        for name, hint in kind_module(kind).FIELDS.items():
            out[name] = (kind, hint)
    return out


def _schema():
    fields = dict(SHARED)
    fields.update({name: f"({kind} only) {hint}" for name, (kind, hint) in kind_fields().items()})
    judgment = JUDGMENT + tuple(kind_fields())
    example = {"id": "CON-003", "to": "decided", "readback": "^c30", "yes": "^c31", "why": "^c33",
               "provider": "^c32", "overrides": [{"rules": ["GATE-4"], "reason": "^c35", "until": "2026-11-30"}],
               "by": "@lead", "reader": False}
    return schema.KindSchema(fields=fields, judgment=judgment, required=("id", "by"), example=example)


SCHEMA = _schema()


def locate(view, ident):
    """(module, Target) for an ID: the first kind in `KINDS` that claims it. (None, None) when none does, and
    (module, None) when a kind claims it but can't find where it lives."""
    for kind in KINDS:
        module = kind_module(kind)
        if module.claims(view, str(ident)):
            return module, module.target(view, str(ident))
    return None, None


def already(view, ident):
    """The Target when the item already stands where a decision would put it, else None."""
    module, found = locate(view, ident)
    return found if module is not None and found is not None and found.state == module.TO else None


def missing(ident):
    return decide_writes.refusal("decide-missing", "I can't find that in the plan, so I decided nothing.",
                                 f"{ident!r} is no page, item, release heading or allocation row in this vault; use "
                                 "the ID the gate named.", override="none: a decision names something that exists")


def field_refusals(item, module):
    found = []
    for name, (kind, _) in kind_fields().items():
        if item.get(name) is not None and name not in module.FIELDS:
            found.append(decide_writes.refusal(
                "decide-field-not-for-kind", "Part of what you told me goes with a different kind of decision, so I "
                                             "filed nothing.",
                f"{name} is for a {kind.replace('_', ' ')} decision; this is a {module.KIND}. Leave it off.",
                override="none: drop the field"))
    if item.get("to") and not item.get("reopen") and item["to"] != module.TO:
        found.append(decide_writes.refusal("decide-to", "That kind of item doesn't go where the file says.",
                                           f"to {item['to']!r}: a {module.KIND} goes to {module.TO}.",
                                           override="none: leave to as drafted"))
    return found


def reopen_refusals(item, view, record, module, found):
    out = []
    if module.REOPEN_TO is None:
        return [decide_writes.refusal("decide-reopen-not-here", f"{found.name} is the team's to move on from here, so "
                                                                "I left it as it is.",
                                      f"A planned {module.KIND} is never reopened by a grill; change it with its owner.",
                                      override="none from decide: the owner edits it, with the lead")]
    if found.state != module.TO:
        out.append(decide_writes.refusal("decide-reopen-not-decided", f"{found.name} isn't decided, so there's nothing "
                                                                      "to reopen.",
                                         f"It is {found.state or 'without a state'}; decide it instead.",
                                         override="none: only a decided item is reopened"))
    if not item.get("why"):
        return out + [decide_writes.refusal("decide-reopen-why", "I need your reason for changing your mind, in your "
                                                                 "words.",
                                            "Capture why the lead reopens it, then give it as --why.",
                                            override="none: a change of mind is recorded with its reason")]
    why = consent.why_in_their_words(item["why"], record, getattr(view, "lead", None))
    capture = record.capture(item["why"])
    why = why or consent.not_bare_non_yes(capture)
    return out + ([why] if why else [])


def stated_refusals(item, view):
    """A decision confirmed from a document names a source that is in the register, so the reviewer can open it."""
    ident = item.get("stated_in")
    if not ident or (re.fullmatch(r"SRC-\d+", str(ident)) and str(ident) in view.model.row_ids):
        return []
    return [decide_writes.refusal("decide-stated-in", "I can't find the document that says this was decided, so I "
                                                      "filed nothing.",
                                  f"--stated-in {ident!r} is no row of sources.md; register it with vela add source "
                                  "first.", override="none: a decision from a document cites that document",
                                  audience=say.MODEL)]


def validate(item, view, record):
    found = textedit.context_refusals(view)
    if found:
        return found
    module, target = locate(view, item["id"])
    if module is None or target is None:
        return [missing(item["id"])]
    found = field_refusals(item, module)
    if item.get("reopen"):
        return found + reopen_refusals(item, view, record, module, target) + decide_writes.by_refusals(item)
    if target.state == module.TO:
        return found + [decide_writes.refusal("decide-already", f"{target.name} is already {module.TO}.",
                                              f"Reopen it only if the lead wants to change it: vela decide --reopen "
                                              f"{target.id} --why <their reason>.",
                                              override="none: reopening is the route, and it records the change")]
    found += stated_refusals(item, view)
    found += decide_writes.yes_refusals(item, record)
    found += decide_writes.words_refusals(item, view, record)
    found += decide_writes.options_refusals(item, view, record, target)
    found += decide_writes.override_refusals(item, view, record, target)
    found += decide_writes.gate_refusals(item, view, record, target)
    return found + list(module.refusals(item, view, record, target))


def apply(item, view, record):
    module, target = locate(view, item["id"])
    text = view.text(target.path)
    if item.get("reopen"):
        page = module.set_state(text, target, module.REOPEN_TO)
        rec = decide_writes.record_after(item, view, record, target, module.TO, module.REOPEN_TO, item["why"])
        return decide_writes.writes(target, page, rec, view, record)
    page = module.set_state(text, target, module.TO)
    bullets = decide_writes.history_bullets(item, view, record, target, module.DECISION)
    page = decide_writes.add_history(page, bullets, target)
    if hasattr(module, "extra"):
        page = module.extra(item, view, record, target, page)
    cite = item.get("yes") or item["overrides"][0]["reason"]  # an override of the quoted-yes rule cites its reason
    rec = decide_writes.record_after(item, view, record, target, target.state, module.TO, cite)
    return decide_writes.writes(target, page, rec, view, record)


def new_state(item, view):
    """Where the item goes: what `vela decide` says it did and names its commit by."""
    module, _ = locate(view, item["id"])
    return module.REOPEN_TO if item.get("reopen") else module.TO
