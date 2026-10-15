"""`vela decide CAP-nnn.FRn@APP-<slug>`: one row of an app's `## Requirements allocated` set decided (grill section 4;
CONVENTIONS "Requirements and allocation"). Pure.

A Grill on an app page takes its allocated rows with it: each row is read back as part of the app's agenda and set
`decided` in its State cell when the lead confirms it. The Violation this kind exists to prevent is a Paper Tiger
share: a row marked decided that nobody heard read back with its app, so a team inherits a share of a requirement they
never agreed to carry. So:

- **The read-back names the app** (its title, its ID, or the row's `CAP-nnn.FRn@APP-<slug>`): a yes to "the requirement"
  heard without the app is a yes to the requirement, not to this app's share of it.
- **The app page's own `**Decision:**` answers for its rows**, as it does for goal rows, so a row is decided only on a
  page that carries one (decide the page first, in the same grill). No Decision or Why bullet is written for a row,
  and a `--why` is refused rather than dropped: the reason for the page's decision goes with the page.
- The grill gate (`gates.verdict`) judges IDs, and a row's subject is the pair, so none of its rules run on a row; the
  requirement and the app were each through the gate when they were decided.

The State cell is the row's last; nothing else in the row changes, so the lead's share sentence stays as written.
Reopened, the row goes back to `assumption`.
"""
import re

from vela import allocation, parse, schema as vault_schema
from vela.decisions import decide_writes, textedit

KIND = "allocation-row"
TO, REOPEN_TO, DECISION = "decided", "assumption", False
FIELDS = {}
ROW_ID = re.compile(r"^(?P<req>CAP-\d{3}\.FR\d+)@(?P<app>APP-[\w-]+)$")
LAST_CELL = re.compile(r"\|(?P<cell>[^|]*)\|\s*$")


def _parts(ident):
    found = ROW_ID.match(str(ident))
    return (found["req"], found["app"]) if found else (None, None)


def _row(lines, req):
    """(index, State cell) of the allocation row naming `req`, or (None, None)."""
    header = textedit.find_table(lines, vault_schema.ALLOCATION_HEADER)
    if header is None:
        return None, None
    for index in range(header + 2, textedit.table_rows_end(lines, header)):
        cells = parse.split_row(lines[index])
        found = allocation.REQUIREMENT_ID.search(cells[0]) if cells else None
        if found and found.group(0) == req:
            return index, cells[-1].strip() if len(cells) >= 4 else ""
    return None, None


def claims(view, ident):
    req, app = _parts(ident)
    return req is not None and bool(view.model.by_id.get(app))


def target(view, ident):
    req, app = _parts(ident)
    found = textedit.find(view, app)
    if found is None:
        return None
    path = found[0]
    index, state = _row(view.text(path).split("\n"), req)
    if index is None:
        return None
    app_name = textedit.name_of(view, app)
    share = f"{app_name}'s share of {textedit.name_of(view, req)}"
    return decide_writes.Target(KIND, ident, path, share, state, "", "Requirements allocated", app, "")


def refusals(item, view, record, found):
    out = []
    req, app = _parts(found.id)
    page = view.model.by_id[app][0]
    app_name = textedit.name_of(view, app)
    if not page.page_bullets("Decision") and "E303" not in decide_writes.rules_set_aside(item):
        out.append(decide_writes.refusal(
            "decide-row-needs-page-decision", f"{app_name} itself isn't decided yet, and its shares are decided with it.",
            f"Decide {app} first in this grill (its page's Decision answers for its rows), then the row.",
            override="--override E303 --reason-from <the lead's reason> --until <date>"))
    readback = record.capture(item.get("readback")) if item.get("readback") else None
    words = (readback.words if readback is not None else "").lower()
    if readback is not None and not any(w and w.lower() in words for w in (app_name, app, found.id)):
        out.append(decide_writes.refusal(
            "decide-row-readback", f"I read that share back without saying it's {app_name}'s, so I'll read it again.",
            f"Read the row back as {found.id} (or with the app's name), capture the read-back, then the lead's yes.",
            override="none: a row is read back with its app"))
    if item.get("why"):
        out.append(decide_writes.refusal(
            "decide-row-why", f"The reason goes with {app_name}'s own decision, not with one of its shares.",
            "Leave --why off the row; give it when deciding the app page.", override="none: drop --why for a row"))
    return out


def set_state(text, found, state):
    lines = text.rstrip("\n").split("\n")
    req, _ = _parts(found.id)
    index, _ = _row(lines, req)
    lines[index] = LAST_CELL.sub(f"| {state} |", lines[index].rstrip())
    return "\n".join(lines) + "\n"
