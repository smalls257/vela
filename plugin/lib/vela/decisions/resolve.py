"""The `resolve` apply kind: an open unknown answered, written resolved (MODES "Unknowns", discover step 6, grill's
answer path, close's "Write the items and the prose"). Pure.

The Violation this exists to prevent is a Silent Fallback in the register of what nobody knows: an answer heard in a
session but never written back leaves the question open (and its owner chasing it), while one written back without its
source turns a guess into a settled answer nobody can check. So, in one write:

- `**State:** resolved`, an `**Outcome:**` that says the answer with its source linked on the words, `**Resolved in:**`
  linking this session, and no `**Ask by:**` (a resolved question has nobody to chase);
- the `## Changes` row `| UNK-nnn | open | resolved | [[<record>#^cNN]] |` and the answer capture's keep mark.

What it refuses, and why:

- **No source, no resolution.** An answer comes from a source the session read or from the lead first-hand, and a
  first-hand answer needs its own row in `sources.md` first (`Kind: exists`, Location `first-hand: <handle>`), so the
  Outcome always cites something a reviewer can open.
- **Never a fact from a plan** (`fact_source_refusal`, shared with `marks` and `add contract`): a document stating
  intent gives an assumption, however sure it sounds ("ready in Q4" in a deck is a plan). An unknown a plan speaks to
  stays open, with what the plan says in its `**Notes:**`.
- **Only an open unknown** is resolved; one already resolved keeps its Outcome.

What it blocked is not changed here: a grill decides, and Discover writes the fact, each in its own mode.
"""
import re

from vela import parse, sourcerows
from vela.decisions import consent, schema, textedit

PAGE = "11-unknowns-and-risks"
SOURCE_ID = re.compile(r"^SRC-\d+$")

SCHEMA = schema.KindSchema(
    fields={"id": "the open unknown's ID, UNK-nnn",
            "answer": "the capture holding the answer (\"^c31\")",
            "source": "the SRC-nn row the answer comes from (a first-hand answer gets its own row first)",
            "outcome": "the answer as it goes on the page; leave null to take the capture's words"},
    judgment=("answer",), required=("id", "answer", "source"),
    example={"id": "UNK-004", "answer": "^c31", "source": "SRC-03"})


def source_row(vault, source_id):
    """{"title", "kind", "location"} of a sources.md row, or None. Read by the register's own header names, so a
    six-column register and a Library register both answer."""
    path = textedit.page_path(vault, "sources")
    if path is None:
        return None
    header = None
    for line in vault.text(path).split("\n"):
        if not line.lstrip().startswith("|"):
            header = None
            continue
        cells = parse.split_row(line)
        if sourcerows.is_register(cells):
            header = cells
        elif header is not None and cells and cells[0] == source_id:
            row = sourcerows.read(header, cells)
            return {"title": row.title, "kind": row.kind, "location": row.location}
    return None


def fact_source_refusal(vault, source_id):
    """None when `source_id` is a registered source whose Kind can give a fact (`exists` or `repo`); else why not."""
    if not source_id or not SOURCE_ID.match(str(source_id)):
        return textedit.refusal("fact-needs-source", "I can only write that as known with the source it comes from.",
                                "Give source: the SRC-nn row (a first-hand answer gets its own row in sources.md "
                                "first, Kind exists, Location first-hand: <handle>).",
                                override="write it as an assumption instead")
    row = source_row(vault, str(source_id))
    if row is None:
        return textedit.refusal("fact-needs-source", "That source isn't in the register yet, so I filed nothing.",
                                f"{source_id} has no row in sources.md; add it with vela add source first.",
                                override="write it as an assumption instead")
    if row["kind"] == "intends":
        return textedit.refusal("fact-from-intends", "That document is a plan, so what it says is what someone "
                                                     "expects, not what is so; I'd write it as assumed.",
                                f"{source_id} is Kind intends; a fact needs an exists or repo source, or the lead's "
                                "first-hand row.",
                                override="write it as an assumption (state assumption), or the lead confirms the "
                                         "Kind is exists and the row changes first")
    return None


def unknown_block(text, ident):
    """(start, end) line indexes of `### <ident> ...` and its bullets, or None."""
    lines = text.split("\n")
    start = next((i for i, l in enumerate(lines) if re.match(rf"^### {re.escape(ident)}(?: |$)", l)), None)
    if start is None:
        return None
    return start, textedit.section_end(lines, start, 3)


def state_of(lines):
    for line in lines:
        found = re.match(r"^- \*\*State:\*\*\s*(\S+)", line)
        if found:
            return found.group(1)
    return None


def validate(item, vault, record):
    found = textedit.context_refusals(vault)
    missing = consent.exists(item["answer"], record)
    if missing is not None:
        found.append(missing)
    located = textedit.find(vault, str(item["id"]))
    if located is None or not str(item["id"]).startswith("UNK-"):
        found.append(textedit.refusal("resolve-missing", "I can't find that question, so I resolved nothing.",
                                      f"{item['id']} is no unknown in this vault."))
    else:
        text = vault.text(located[0])
        start, end = unknown_block(text, item["id"])
        if state_of(text.split("\n")[start:end]) != "open":
            found.append(textedit.refusal("resolve-not-open", "That question was already answered, so I left it as "
                                                              "it is.",
                                          f"{item['id']} is not open; its Outcome stands.",
                                          override="none: reopen it as a new unknown if the answer changed"))
    refusal = fact_source_refusal(vault, item.get("source"))
    return found + ([refusal] if refusal else [])


def outcome(item, vault, record):
    words = item.get("outcome") or textedit.quote(record, item["answer"])
    row = source_row(vault, item["source"])
    return f"{textedit.inline(words).rstrip('.')}, as [[sources#{item['source']}|{textedit.inline(row['title'])}]] says."


def apply(item, vault, record):
    path = textedit.find(vault, item["id"])[0]
    text = vault.text(path)
    lines = text.rstrip("\n").split("\n")
    start, end = unknown_block(text, item["id"])
    body = [l for l in lines[start:end] if not re.match(r"^- \*\*(?:Ask by|Outcome|Resolved in):\*\*", l)]
    at = next(i for i, l in enumerate(body) if l.startswith("- **State:**"))
    body[at] = "- **State:** resolved"
    body[at + 1:at + 1] = [f"- **Outcome:** {outcome(item, vault, record)}", f"- **Resolved in:** [[{record.id}]]"]
    page = "\n".join(lines[:start] + body + lines[end:]) + "\n"
    heading = lines[start][4:].strip()
    rec = textedit.add_change(textedit.record_text(record, vault), item["id"], "open", "resolved",
                              textedit.capture_link(record.id, item["answer"]))
    rec = textedit.mark_if_unmarked(rec, item["answer"], textedit.keep_mark(PAGE, heading, item["id"], "resolved"))
    return [schema.Write(path, page)] + textedit.record_writes(record, vault, rec)
