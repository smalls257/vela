"""The `agenda` apply kind: grill's `## Agenda` lines in the session record, written and updated (overhaul Task 15,
plan 2.2). Pure.

The Violation this exists to prevent is a Leaky Narrative in the record START resumes from. Grill section 2 held the
grammar in prose,

    - <ID>: GATE-3 confirmed yes|no, status open|decided|off-agenda: GATE-n[, override: GATE-n]

and START's resume rule reads it back, so a line typed slightly wrong is an item a resumed grill silently skips. Here
the line is written from fields and read back by the same pattern (`LINE`). Why each part:

- `GATE-3 confirmed yes` only on a yes on record: the capture `yes` passes the consent checks (a person's words, not a
  bare "ok", after the read-back of the agenda), because GATE-3 is the lead's explicit yes to the agenda, and a yes
  nobody can point at is no yes. Without `yes` the line says `no`.
- `off-agenda: GATE-n` names the gate the item failed, so the resumed grill knows what to ask before it comes back on.
  An open question under an item never takes it off the agenda: settling notes it (`Decided with open`).
- `override: GATE-n` is the lead deciding it anyway; the item stays on the agenda with a status. The override bullet
  itself is the `override` kind's to write, on the item, where check reads it.

An item already on the agenda has its line replaced, never a second line added.
"""
import re

from vela.decisions import consent, schema, textedit

HEADING = "Agenda"
STATUS = re.compile(r"^(?:open|decided|off-agenda: GATE-\d)$")
GATE = re.compile(r"^GATE-\d$")
LINE = re.compile(r"^- (?P<id>[^\s:]+): GATE-3 confirmed (?P<yes>yes|no), status (?P<status>open|decided|off-agenda: "
                  r"GATE-\d)(?:, override: (?P<override>GATE-\d(?:, GATE-\d)*))?\s*$")

SCHEMA = schema.KindSchema(
    fields={"id": "the item's ID, as the gate named it",
            "status": "open, decided or off-agenda: GATE-n",
            "readback": "the capture where the agenda was read back",
            "yes": "the capture holding the lead's yes to the agenda (GATE-3); null when there is none yet",
            "override": "the gates the lead chose to decide it anyway, such as [\"GATE-5\"]"},
    judgment=("yes",), required=("id", "status"),
    example={"id": "CON-003", "status": "open", "readback": "^c30", "yes": "^c31", "override": ["GATE-5"]})


def format_line(ident, yes, status, override=()):
    tail = f", override: {', '.join(override)}" if override else ""
    return f"- {ident}: GATE-3 confirmed {'yes' if yes else 'no'}, status {status}{tail}"


def entries(record_text):
    """{ID: the line's match} for every agenda line in the record."""
    found, inside = {}, False
    for line in record_text.split("\n"):
        if line.startswith("## "):
            inside = line[3:].strip() == HEADING
            continue
        match = LINE.match(line.strip()) if inside else None
        if match:
            found[match["id"]] = match
    return found


def set_line(record_text, ident, line):
    """The record with the agenda line for `ident` replaced by `line`, or added; the section made before `## Captures`
    when the record has none."""
    lines = record_text.rstrip("\n").split("\n")
    start = textedit.find_heading(lines, HEADING, 2)
    if start is not None:
        end = textedit.section_end(lines, start, 2)
        for index in range(start + 1, end):
            found = LINE.match(lines[index].strip())
            if found and found["id"] == ident:
                lines[index] = line
                return "\n".join(lines) + "\n"
        last = end
        while last > start + 1 and not lines[last - 1].strip():
            last -= 1
        gap = [""] if last == start + 1 else []
        return "\n".join(lines[:last] + gap + [line] + lines[last:]) + "\n"
    return textedit.insert_block(record_text, HEADING, [line], before=("Captures", "Changes"))


def validate(item, vault, record):
    found = textedit.context_refusals(vault)
    if textedit.find(vault, str(item["id"])) is None:
        found.append(textedit.refusal("agenda-item", "I can't find that item in the vault, so I didn't put it on the "
                                                     "agenda.",
                                      f"{item['id']} is no item or page ID in this vault; use the ID the gate named.",
                                      override="none: an agenda line names an item that exists"))
    if not STATUS.match(str(item.get("status") or "")):
        found.append(textedit.refusal("agenda-status", "I couldn't tell where that item stands on the agenda.",
                                      f"status {item.get('status')!r} must be open, decided or "
                                      "off-agenda: GATE-n.", override="none: pick one of the three"))
    bad = [g for g in (item.get("override") or []) if not GATE.match(str(g))]
    if bad:
        found.append(textedit.refusal("agenda-override", "I couldn't tell which check you chose to set aside.",
                                      f"override names {', '.join(map(str, bad))}; give gates as GATE-n.",
                                      override="none: name the gate"))
    if item.get("yes"):
        # The agenda is read back in the chat, then both are captured together; capture order says when the model
        # wrote them down, not when the lead spoke, so only the read-back's existence is checked, not its order.
        refusal = consent.a_yes(item["yes"], record)
        if refusal is None and item.get("readback"):
            refusal = consent.exists(item["readback"], record)
        if refusal is not None:
            found.append(refusal)
    return found


def apply(item, vault, record):
    text = textedit.record_text(record, vault)
    line = format_line(item["id"], bool(item.get("yes")), item["status"], tuple(item.get("override") or ()))
    return textedit.record_writes(record, vault, set_line(text, item["id"], line))
