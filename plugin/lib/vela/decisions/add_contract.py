"""`add contract`: `### CON-nnn <name>` with its required fact bullets under `## Contracts this app provides` on the
provider's building-blocks page (boundary section 4, allocate; CONVENTIONS "Fact bullets").

- **On the provider's page**, because a contract is stated once, by the app that owns it, and every consumer links it.
- **The required bullets** (`**Crosses the boundary:**`, `**Consumers:**`, `**Change policy:**`, `**Change:**`,
  `**State:**`) are all written, so the page passes the contract check from its first line. Consumers link each
  consumer's page, or say `none`.
- **Never `decided`**: only a grill decides a contract, so a new one is at most an `assumption`. The case table is
  the session's to read back with the lead, one open case at a time; it is not invented here.
- Numbered `CON-nnn` past every open branch. The capture gets the `## Changes` row and its keep mark.
"""
from vela.decisions import textedit
from vela.decisions.schema import Write

SECTION = "Contracts this app provides"
CHANGES = ("new", "changed", "new consumers", "unchanged")
STATES = ("inkling", "assumption", "fact")

FIELDS = {"provider": "the providing app's ID, APP-<slug>",
          "name": "the contract's short name for the heading: at most six words",
          "crosses": "what goes in and what comes out",
          "consumers": "the consuming apps' IDs; empty for none",
          "change_policy": "how it may change",
          "change": "new, changed, new consumers or unchanged",
          "state": "inkling or assumption (default); fact needs source",
          "source": "SRC-nn, for a fact",
          "capture": "the capture it was confirmed in",
          "id": "leave null: vela numbers it past every open branch"}
REQUIRED = ("provider", "name", "crosses", "change_policy", "change")
EXAMPLE = {"provider": "APP-stock", "name": "Stock reservation", "crosses": "an item and a count in; a hold out",
           "consumers": ["APP-shop"], "change_policy": "versioned, six months' notice", "change": "new",
           "capture": "^c12"}


def validate(item, vault, record):
    from vela.decisions import resolve  # the one rule for what a fact may cite
    found = textedit.capture_refusals(item, record)
    provider = textedit.find(vault, str(item["provider"]))
    if provider is None or provider[1] is not None:
        found.append(textedit.refusal("add-contract-provider", "I can't find the app that provides it.",
                                      f"provider {item['provider']!r} is no app page in this vault."))
    missing = [c for c in item.get("consumers") or [] if textedit.find(vault, str(c)) is None]
    if missing:
        found.append(textedit.refusal("add-contract-consumer", "One of its consumers isn't an app the vault holds.",
                                      f"consumers names {', '.join(map(str, missing))}."))
    if item["change"] not in CHANGES:
        found.append(textedit.refusal("add-contract-change", "I couldn't tell how the contract changes.",
                                      f"change is one of {', '.join(CHANGES)}."))
    state = item.get("state") or "assumption"
    if state not in STATES:
        found.append(textedit.refusal("add-contract-state", "A new contract isn't decided until a grill decides it.",
                                      f"state is one of {', '.join(STATES)}; decide it in a grill.",
                                      override="an override of grill on the item, then vela decide"))
    if state == "fact":
        refusal = resolve.fact_source_refusal(vault, item.get("source"))
        if refusal is not None:
            found.append(refusal)
    for refusal in (textedit.heading_refusal(item["name"]),
                    textedit.id_refusal(vault, item["id"], "CON") if item.get("id") else None):
        if refusal is not None:
            found.append(refusal)
    return found


def apply(item, vault, record):
    ident = textedit.new_id(item, vault, "CON")
    path = textedit.find(vault, str(item["provider"]))[0]
    consumers = ", ".join(textedit.link(vault, str(c)) for c in item.get("consumers") or []) or "none"
    state = item.get("state") or "assumption"
    lines = [f"### {ident} {item['name'].strip()}", "",
             f"- **Crosses the boundary:** {textedit.inline(item['crosses'])}", f"- **Consumers:** {consumers}",
             f"- **Change policy:** {textedit.inline(item['change_policy'])}", f"- **Change:** {item['change']}",
             f"- **State:** {state}"]
    if state == "fact":
        lines.append(f"- **Source:** {item['source']}")
    page = textedit.insert_block(vault.text(path), SECTION, lines, before=("Contracts this app consumes", "History"))
    rec = textedit.record_text(record, vault)
    if item.get("capture"):
        heading = f"{ident} {item['name'].strip()}"
        rec = textedit.add_change(rec, ident, "-", state, textedit.capture_link(record.id, item["capture"]))
        rec = textedit.mark_if_unmarked(rec, item["capture"], textedit.keep_mark(textedit.basename(path), heading,
                                                                                 ident, state))
    return [Write(path, page)] + textedit.record_writes(record, vault, rec)
