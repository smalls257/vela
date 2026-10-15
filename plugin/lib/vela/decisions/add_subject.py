"""`add subject`: a party (`### PTY-nn <name>`, under `## Outside parties`) or a stored value (`### SV-nn <name>`, under
`## Value held for customers`) on `03-context-and-scope.md` (CONVENTIONS "Fact bullets"; close LEDGER, discover 5).

- **Every required fact, or nothing** (E808): a party needs `**Relationship:**` and `**Agreements:**`, a stored value
  `**Holder:**` and `**Owner:**`. The question catalog fires on these facts, so a subject written without one is a
  question nobody will ever be owed. The facts come from the lead; the model fills them from what was said and this
  type refuses a missing one rather than writing a gap.
- **Relationship** is one of the four the check knows (E105), in any case.
- A subject carries no state, so its capture's mark says `(subject)`.
"""
from vela import schema as vault_schema
from vela.decisions import textedit
from vela.decisions.schema import Write

PAGE = "03-context-and-scope"
SECTIONS = {"PTY": "Outside parties", "SV": "Value held for customers"}
FACTS = {"PTY": ("relationship", "agreements"), "SV": ("holder", "owner")}
LABELS = {"relationship": "Relationship", "agreements": "Agreements", "holder": "Holder", "owner": "Owner",
          "links": "Links"}

FIELDS = {"subject_type": "PTY for an outside party, SV for value held for customers",
          "name": "the short name for the heading: at most six words",
          "relationship": "a party's relationship: partner, supplier, regulator or customer group",
          "agreements": "the agreements a party is in, with their SRC-nn where registered, or `none known`",
          "holder": "the app or party that holds a stored value's balances",
          "owner": "who carries the balances as money owed to customers, or `not known yet` with the unknown",
          "links": "a party's API spec, docs or portal (optional)",
          "capture": "the capture the lead said it in (\"^c12\")",
          "id": "leave null: vela numbers it past every open branch"}
REQUIRED = ("subject_type", "name")
EXAMPLE = {"subject_type": "PTY", "name": "Card acquirer", "relationship": "supplier", "agreements": "none known",
           "capture": "^c12"}


def validate(item, vault, record):
    found = textedit.capture_refusals(item, record)
    kind = item.get("subject_type")
    if kind not in SECTIONS:
        return found + [textedit.refusal("add-subject-type", "I couldn't tell whether that's a party or value held for "
                                                             "customers.", "subject_type is PTY or SV.")]
    missing = [LABELS[f] for f in FACTS[kind] if not str(item.get(f) or "").strip()]
    if missing:
        found.append(textedit.refusal("E808", "I need a bit more about it before I can write it down, or the "
                                              "questions it raises would never be asked.",
                                      f"A {kind} needs {', '.join(missing)}; ask the lead, then fill the field.",
                                      override="none: write the item as an unknown instead until the lead knows"))
    if kind == "PTY" and item.get("relationship") and \
            str(item["relationship"]).strip().lower() not in vault_schema.PARTY_RELATIONSHIPS:
        found.append(textedit.refusal("E105", "I couldn't tell how they relate to us.",
                                      f"relationship is one of {', '.join(vault_schema.PARTY_RELATIONSHIPS)}."))
    if kind == "SV" and item.get("links"):
        found.append(textedit.refusal("add-subject-links", "Links belong on a party, not on value held.",
                                      "Leave links out for a stored value."))
    for refusal in (textedit.heading_refusal(item["name"]),
                    textedit.id_refusal(vault, item["id"], kind) if item.get("id") else None):
        if refusal is not None:
            found.append(refusal)
    if textedit.page_path(vault, PAGE) is None:
        found.append(textedit.refusal("add-subject-page", "The context and scope page is missing, so I filed nothing.",
                                      "03-context-and-scope.md is the one home of parties and stored value."))
    return found


def apply(item, vault, record):
    kind = item["subject_type"]
    ident = textedit.new_id(item, vault, kind)
    path = textedit.page_path(vault, PAGE)
    lines = [f"### {ident} {item['name'].strip()}", ""]
    lines += [f"- **{LABELS[f]}:** {textedit.inline(item[f])}" for f in FACTS[kind] + ("links",) if item.get(f)]
    page = textedit.insert_block(vault.text(path), SECTIONS[kind], lines)
    text = textedit.mark_if_unmarked(textedit.record_text(record, vault), item.get("capture"),
                                     textedit.keep_mark(PAGE, f"{ident} {item['name'].strip()}", ident, "subject"))
    return [Write(path, page)] + textedit.record_writes(record, vault, text)
