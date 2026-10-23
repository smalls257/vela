"""`add constraint`: something the initiative cannot change (a date, a budget, a law, a contract term, a system it
must keep), as a row on `02-constraints.md` (close's "Write the items and the prose"):

    | CST-n | <the constraint> | <where it comes from, as a link on the words> | <what it forces> |

- The constraint is the lead's words, copied from the capture when `constraint` is left null, and escaped for a table
  cell (`textedit.cell`): a `|` in the lead's words would otherwise split the row, and the check would read a row with
  the wrong columns. A link's label pipe is written `\\|` there for the same reason.
- "Where it comes from" defaults to a link to the capture on the words "the lead's account", so the row can be traced
  to who said it without anyone being asked for bookkeeping.
- Numbered past every open branch, like every new ID.
- The capture, when given, gets its keep mark to the row, under the heading the table sits under.
"""
from vela.decisions import textedit
from vela.decisions.schema import Write

PAGE = "02-constraints"
HEADER = ("ID", "Constraint")

FIELDS = {"constraint": "what can't change, in the lead's words (leave null to take the capture's words)",
          "capture": "the capture it came from (\"^c12\")",
          "source": "where it comes from, as a link on the words (default: the capture, as the lead's account)",
          "forces": "what it forces the plan to do",
          "state": "the mark's state for the capture: assumption (default) or fact",
          "id": "leave null: vela numbers it past every open branch"}
REQUIRED = ("forces",)
EXAMPLE = {"capture": "^c12", "forces": "the till work lands before November"}


def words(item, record):
    return item.get("constraint") or textedit.quote(record, item.get("capture"))


def validate(item, vault, record):
    found = textedit.capture_refusals(item, record)
    if item.get("id"):
        refusal = textedit.id_refusal(vault, item["id"], "CST")
        if refusal is not None:
            found.append(refusal)
    if not found and not words(item, record):
        found.append(textedit.refusal("add-constraint", "I need the constraint itself before I can write it down.",
                                      "Give constraint, or a capture holding the lead's words."))
    path = textedit.page_path(vault, PAGE)
    if path is None or textedit.find_table(vault.text(path).split("\n"), HEADER) is None:
        found.append(textedit.refusal("add-constraint-page", "The constraints page has no table to add this to, so I "
                                                             "filed nothing.",
                                      "02-constraints.md needs its `| ID | Constraint | Where it comes from | What it "
                                      "forces |` table; run vela upgrade or add the header."))
    if item.get("state") not in (None, "assumption", "fact"):
        found.append(textedit.refusal("add-state", "I couldn't tell how sure that is.",
                                      "state is assumption or fact."))
    return found


def apply(item, vault, record):
    ident = textedit.new_id(item, vault, "CST")
    path = textedit.page_path(vault, PAGE)
    source = item.get("source") or (textedit.capture_ref(record, item["capture"]) if item.get("capture") else "")
    line = textedit.row(ident, textedit.cell(words(item, record)), textedit.cell(source), textedit.cell(item["forces"]))
    page = textedit.add_row(vault.text(path), HEADER, line)
    text = textedit.record_text(record, vault)
    heading = textedit.heading_above(page, HEADER)
    text = textedit.mark_if_unmarked(text, item.get("capture"),
                                     textedit.keep_mark(PAGE, heading, ident, item.get("state") or "assumption"))
    return [Write(path, page)] + textedit.record_writes(record, vault, text)
