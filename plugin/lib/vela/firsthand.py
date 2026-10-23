"""The first-hand `sources.md` row for a person: where a pointer goes when that person's words stay in the notes.

The Violation this exists to prevent is a Leaky Narrative of the owner's rule: a person's words leave the machine only
with that person's own yes. A ledger cell that says `see SRC-07` keeps the claim traceable to who knew it without
carrying what they said. The split and the ledger writer both point there, so the row has one shape in one place.
Pure: text in, text out."""
from vela import parse, receipts, sourcerows
from vela.decisions import textedit


def row_id(text, handle):
    """The SRC-nn of the register's first-hand row for `handle`, or None. `text` is sources.md."""
    lines = text.split("\n")
    index = textedit.find_table(lines, sourcerows.CORE)
    if index is None:
        return None
    header = parse.split_row(lines[index])
    for line in lines[index + 2:]:
        if not line.lstrip().startswith("|"):
            break
        row = sourcerows.read(header, parse.split_row(line))
        if row.kind == "exists" and row.location.casefold() == f"first-hand: {handle}".casefold():
            return row.id
    return None


def with_row(text, ident, handle, today):
    """`text` (sources.md) with the first-hand row for `handle` added as `ident`. Raises ValueError when sources.md
    has no register table to hold it."""
    lines = text.split("\n")
    index = textedit.find_table(lines, sourcerows.CORE)
    if index is None:
        raise ValueError("sources.md has no register table (ID | Title | Owner | Date | Kind ...), so the "
                         "first-hand source that stands in for someone's words has nowhere to go.")
    header = parse.split_row(lines[index])
    values = {"ID": ident, "Title": f"First-hand knowledge of {receipts.handle_ref(handle)[1:]}", "Owner": handle,
              "Date": today, "Kind": "exists", "Location": f"first-hand: {handle}"}
    row = textedit.row(*[values.get(name, "") for name in header])
    return textedit.add_row(text, sourcerows.CORE, row)
