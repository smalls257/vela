"""The `add` apply kind: a new structured item, numbered and written in the vault's grammar in one step (overhaul
Task 15, plan 2.1 section 3 and 2.13). Pure. `vela add TYPE --field ...` is the same thing for one item.

The Violation this exists to prevent is a Leaky Narrative at every skill that writes an item: close (constraint rows,
unknowns, subjects, decision records), grill (a new unknown mid-grill), epics (the skeleton and AC numbers), boundary
(app stubs, contracts, the picked cut), releases (slices), requirements (FR headings) and discover (sources) each held
the grammar in prose, and each copy was a place to slip and to drift from the others (a Distributed Monolith). Here
each type is its own module, `add_<type>.py`, with its fields, its reasons and its writes; this module only
dispatches, so no single function knows every item (Shield) and a new type is a new file plus one line in `TYPES`.

"New IDs come from vela next-id, so an open session branch never hands out the same number twice." Every type numbers
through `textedit.next_id`, which counts this tree, the writes earlier items in the file made, and the IDs on `main` and
every session branch. An item may carry its own `id`; it is refused when anything already uses it.

An item's `type` names the type; the other fields are the type's own (`vela apply --schema add` lists them all, and
`vela add TYPE --help` one type's). A field another type takes is refused like a typo, because a field that is
silently ignored is a lost answer.
"""
from vela import say
from vela.decisions import (add_adr, add_app_stub, add_constraint, add_contract, add_cut, add_epic, add_fr, add_slice,
                            add_source, add_subject, add_unknown, schema, textedit)

TYPES = {"unknown": add_unknown, "constraint": add_constraint, "subject": add_subject, "adr": add_adr,
         "epic": add_epic, "slice": add_slice, "app-stub": add_app_stub, "contract": add_contract, "fr": add_fr,
         "source": add_source, "cut": add_cut}


def _fields():
    fields = {"type": f"what to add: one of {', '.join(TYPES)}"}
    for module in TYPES.values():
        for name, hint in module.FIELDS.items():
            fields.setdefault(name, hint)
    return fields


SCHEMA = schema.KindSchema(fields=_fields(), required=("type",),
                           example=dict(add_unknown.EXAMPLE, type="unknown"))


def type_module(item):
    return TYPES.get(item.get("type"))


def validate(item, vault, record):
    found = textedit.context_refusals(vault)
    if found:
        return found
    module = type_module(item)
    if module is None:
        return [say.Refusal("add-type", "I don't know how to add that kind of item, so I filed nothing.",
                            f"type {item.get('type')!r} is not one of: {', '.join(TYPES)}.",
                            override="none: add it by hand, in the grammar vela conventions prints")]
    extra = sorted(set(item) - set(module.FIELDS) - {"type"} - set(schema.SHARED_KEYS))
    if extra:
        return [say.Refusal("decision-unknown-field", "Part of what you told me went in the wrong place, so I filed "
                                                      "nothing.",
                            f"A {item['type']} doesn't take: {', '.join(extra)}. See vela add {item['type']} --help.",
                            override="none: rename the field to one the type takes")]
    unfilled = [name for name in module.REQUIRED if item.get(name) in (None, "", [])]
    if unfilled:
        return [say.Refusal("decision-unfilled", "I still need one of your answers before I can file these.",
                            f"The {item['type']} has no value yet for: {', '.join(unfilled)}.",
                            override="none: a required field can't be skipped; the lead may decline the item")]
    return list(module.validate(item, vault, record))


def apply(item, vault, record):
    return type_module(item).apply(item, vault, record)


def notices(item):
    """Lines the CLI says after filing that the writes themselves can't carry (a token stripped from a URL)."""
    module = type_module(item)
    return list(module.notices(item)) if module is not None and hasattr(module, "notices") else []
