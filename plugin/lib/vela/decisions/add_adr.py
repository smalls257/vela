"""`add adr`: a decision record's skeleton, `09-decisions/ADR-nnnn-<slug>.md`, linked from `09-decisions.md` (close's "Write the items and the prose", grill's "File each decision as its branch closes").

The skeleton is code and the content is judgment: this writes the frontmatter (`type: decision`, `authored: authored`),
the four sections close fills (`## Context`, `## Decision`, `## Alternatives considered` with its
`| Alternative | Why rejected |` table, `## Consequences`) and `## History`, and the index line, so the record exists
to link to the moment a grill offers it. The prose is the model's to draft and the lead's to read back.

- Numbered `ADR-nnnn` past every open branch.
- `state` is `proposed` until it's settled; a record for a page decided this session may be written `decided`
  with `decision` naming the deciding session, which goes under `## History` as its `**Decision:**` bullet. That
  bullet is a receipt (`receipts.decision_value`): it needs `capture`, the yes it came from, and carries that person's
  words only when `consent.may_quote` lets them out. A bare `[[session]]` would be a Decision nobody can trace.
"""
from vela import privaterecord, receipts
from vela.decisions import consent, decide_writes, textedit
from vela.decisions.schema import Write

FOLDER = "09-decisions"
INDEX = "09-decisions"
STATES = ("proposed", "decided", "superseded", "rejected")

FIELDS = {"title": "what was decided, as a short sentence",
          "owner": "the handle that owns the record: the lead's",
          "state": "proposed (default) or decided",
          "decision": "for a decided record: the deciding session's ID (needs capture, the yes it came from)",
          "decides": "the ID of the page or item it records the decision for (optional; linked under Decision)",
          "capture": "the capture where the lead asked for or agreed to the record; a decided record's receipt cites it",
          "id": "leave null: vela numbers it past every open branch"}
REQUIRED = ("title", "owner")
EXAMPLE = {"title": "One booking app, not a shared library", "owner": "@priya", "decides": "APP-booking"}


def validate(item, vault, record):
    found = textedit.capture_refusals(item, record)
    if item.get("state") not in (None,) + STATES:
        found.append(textedit.refusal("add-state", "I couldn't tell where that decision stands.",
                                      f"state is one of {', '.join(STATES)}."))
    if item.get("state") == "decided" and not item.get("decision"):
        found.append(textedit.refusal("add-adr-decision", "A decided record needs the session that decided it.",
                                      "Give decision: the deciding session's ID.",
                                      override="leave state proposed until it's settled"))
    if item.get("decision") and not item.get("capture"):
        found.append(textedit.refusal("add-adr-capture", "I need the answer that decided it written down before I can "
                                                         "cite it.",
                                      "Give capture: the capture holding the yes that decided it.",
                                      override="leave the record proposed until there is a yes on record"))
    if item.get("decision") and item.get("capture"):
        found += receipt_refusals(item, vault, record)
    if item.get("decides") and textedit.find(vault, str(item["decides"])) is None:
        found.append(textedit.refusal("add-adr-decides", "I can't find what that decision is about.",
                                      f"decides names {item['decides']}, which the vault doesn't hold."))
    if item.get("id"):
        refusal = textedit.id_refusal(vault, item["id"], "ADR")
        if refusal is not None:
            found.append(refusal)
    return found


def receipt_refusals(item, vault, record):
    """The receipt names this session, the yes it came from and the lead: each must hold, or nothing is written."""
    if str(item["decision"]) != record.id:
        return [textedit.refusal("add-adr-session", "That decision was made in another session, so I can't cite a yes "
                                                    "from this one.",
                                 f"decision {item['decision']!r} is not the open session {record.id}; cite the yes "
                                 "from the session that decided it, or record it there.",
                                 override="leave the record proposed")]
    if getattr(vault, "lead", None) is None:
        return [decide_writes.lead_unknown()]
    missing = textedit.capture_refusals(item, record)
    yes = None if missing else consent.a_yes(item["capture"], record)
    return missing + ([yes] if yes else [])


def receipt(item, vault, record):
    """The `**Decision:**` value: the session, the capture of the yes and who said it, with their words when they may
    be quoted."""
    capture = record.capture(item["capture"])
    words = capture.quote if consent.may_quote(capture, record, getattr(vault, "lead", None)) else None
    return receipts.decision_value(item["decision"], privaterecord.Ref(record.part, int(capture.n)),
                                   decide_writes.speaker(capture, vault.lead), words)


def apply(item, vault, record):
    ident = textedit.new_id(item, vault, "ADR")
    title = str(item["title"]).strip()
    name = f"{ident}-{textedit.slug(title)}"
    path = f"{FOLDER}/{name}.md"
    decides = textedit.link(vault, str(item["decides"])) if item.get("decides") else ""
    lines = ["---", f"id: {ident}", "type: decision", f"title: {textedit.yaml_value(title)}", f"state: {item.get('state') or 'proposed'}",
             f'owner: "{item["owner"]}"', "authored: authored", f"sources: [{record.id}]", "---", "",
             f"# {ident} {title}", "", "## Context", "", "## Decision", ""]
    if decides:
        lines += [f"This records the decision on {decides}.", ""]
    lines += ["## Alternatives considered", "", "| Alternative | Why rejected |", "|---|---|", "",
              "## Consequences", "", "## History", ""]
    if item.get("decision"):
        lines += [f"- **Decision:** {receipt(item, vault, record)}", ""]
    writes = [Write(path, "\n".join(lines).rstrip("\n") + "\n")]
    index = textedit.page_path(vault, INDEX)
    if index is not None:
        text = vault.text(index).rstrip("\n") + "\n"
        bullet = f"- [[{name}|{textedit.inline(title)}]]"
        if not text.split("\n")[-2].startswith("- [["):
            text += "\n"
        writes.append(Write(index, text + bullet + "\n"))
    rec = textedit.record_text(record, vault)
    if item.get("capture"):
        state = item.get("state") or "proposed"
        rec = textedit.add_change(rec, ident, "-", state, textedit.capture_link(record.id, item["capture"]))
        rec = textedit.mark_if_unmarked(rec, item["capture"], textedit.keep_mark(name, f"{ident} {title}", ident, state))
    return writes + textedit.record_writes(record, vault, rec)
