"""What this session is about, what it decided, what's still open and what's next. Pure.

The Violation this exists to prevent is a Distributed Monolith of meaning: if the terminal pane, the one-line band and
the Cowork artifact each decided for themselves what "decided" is, they would drift. So one dict is built here and
every surface draws it (the renders are `companionrender.py`). A second Violation is a Silent Fallback: a panel that
says "nothing decided" when the notes could not be read. `unreadable` is its own shape, with every list null, so no
surface can draw it as an empty session.

Inputs are plain values: the disk, git and the clock are the edge's (`edge/companionstore.py`), so a panel is built
the same offline and in a test.
"""
import datetime
from dataclasses import dataclass

from vela import closegate, pageindex, privaterecord, say
from vela.decisions import agenda

VERSION = 2  # 2: the JSON carries `blocks`; a file without them is a version-1 file
PLACEHOLDER_SUMMARY = "In progress."  # what privaterecord.new_private writes: read as no summary
FOLDER = ".vela/companion"
FILES = {"json": FOLDER + "/session.json", "md": FOLDER + "/session.md", "html": FOLDER + "/session.html"}


@dataclass(frozen=True)
class Inputs:
    stub: dict         # the open stub's frontmatter (privaterecord.stub_meta)
    notes: str         # the private notes' text
    index: dict        # companionstore.page_index
    touched: object    # tuple of vault-relative pages changed since the session began, or None when git could not say
    map_next: str      # the topic map's first move in words, "" when none
    plan_next: tuple   # (text, made date) from the digest, ("", "") when there is no digest
    today: str         # YYYY-MM-DD
    now: str           # HH:MM


def as_of(today, now):
    return f"{today}T{now}"


def session_of(stub):
    return {"id": str(stub.get("id", "")), "title": str(stub.get("title", "")),
            "modes": [str(m) for m in (stub.get("modes") or [])], "opened": str(stub.get("date", "")),
            "branch": str(stub.get("branch", "")), "start_commit": str(stub.get("start_commit", ""))}


def highest_capture(notes):
    """The highest ^cNN in the notes, 0 when there is none: the number the staleness line compares."""
    return max((int(n) for n in closegate.captures(notes)), default=0)


def behind(published, notes):
    """The line for Claude when the published panel shows fewer captures than the notes hold, "" when it is current.
    It is for Claude, so the command words are allowed."""
    if notes <= published:
        return ""
    gap = notes - published
    word = "1 capture" if gap == 1 else f"{gap} captures"
    return (f"The session companion is {word} behind; run `sh ${{CLAUDE_PLUGIN_ROOT}}/scripts/run-vela companion session "
            "--html` in the same Bash call as your next vela write and publish the file to the same artifact.")


def unreadable(stub, why, today, now):
    """The panel for a session whose notes can't be read: every list is null, never empty, and the warning says why."""
    return {"version": VERSION, "kind": "session", "as_of": as_of(today, now), "capture": 0, "notes": "unreadable",
            "session": session_of(stub), "about": "", "decided": None, "said_yes": None, "open": None, "agenda": None,
            "next": None, "touched": None, "diagram": None, "band": "", "files": dict(FILES), "vault": "",
            "warnings": [why]}


def date_in_words(value, today):
    return say.date_words(value, datetime.date.fromisoformat(today))


def _day_count(opened, today):
    try:
        return max(0, (datetime.date.fromisoformat(today) - datetime.date.fromisoformat(opened)).days)
    except ValueError:
        return 0


def _name(names, ident):
    found = names.get(ident)
    return found.name if found else ident


def _capture_of(row):
    return int(row.capture_number) if row.capture_number else 0


def folded(rows):
    """{item: (first row, last row)} in table order. A reopened item is no longer decided and a resolved question is no
    longer open, so every list reads the item's last row; reading each row alone is how a panel lists a decision twice
    or keeps one the lead took back (Paper Tiger)."""
    found = {}
    for row in rows:
        found[row.item] = (found[row.item][0] if row.item in found else row, row)
    return found


def decided_rows(rows, names):
    return [{"id": item, "name": _name(names, item), "from": last.before, "to": last.after,
             "capture": _capture_of(last), "page": names[item].page if item in names else ""}
            for item, (_, last) in folded(rows).items() if last.after == "decided" and not last.reconfirmed]
            # a reconfirmed item was decided on another machine; close's "You settled" leaves it out too


def said_yes_rows(notes, index, names):
    found = []
    for ident in privaterecord.lists_of(notes)["ready"]:
        holders = pageindex.blocking(index, ident)
        found.append({"id": ident, "name": _name(names, ident),
                      "blocked_by": _name(names, holders[0]) if holders else "",
                      "who": pageindex.who(index, holders[0]) if holders else ""})
    return found


def agenda_rows(notes, names):
    return [{"id": ident, "name": _name(names, ident), "status": match["status"].split(":")[0]}
            for ident, match in agenda.entries(notes).items()]


def _open_entry(index, names, ident, new, today):
    opened = ""
    for entry in index.get("pages", {}).values():
        if ident in entry["items"]:
            opened = entry["items"][ident]["opened"]
    return {"id": ident, "name": _name(names, ident), "who": pageindex.who(index, ident), "new_this_session": new,
            "open_days": _day_count(opened, today) if opened else 0}


def open_rows(rows, agenda_list, index, names, today):
    found = [_open_entry(index, names, item, True, today) for item, (first, last) in folded(rows).items()
             if item.startswith("UNK-") and first.before == "-" and last.after == "open"]
    seen = {entry["id"] for entry in found}
    for item in agenda_list:
        if item["status"] == "decided":
            continue
        for ident in pageindex.blocking(index, item["id"]):
            if ident not in seen:
                seen.add(ident)
                found.append(_open_entry(index, names, ident, False, today))
    return found


def next_move(agenda_list, map_next, plan_next, today):
    open_items = [item for item in agenda_list if item["status"] == "open"]
    if open_items:
        first = open_items[0]
        return {"text": first["name"], "id": first["id"], "source": "agenda", "left_after": len(open_items) - 1}
    if map_next:
        return {"text": map_next, "id": "", "source": "map", "left_after": 0}
    text, made = plan_next
    if text:
        return {"text": f"{text} (vela's suggestion as of {date_in_words(made, today)})", "id": "", "source": "vela",
                "left_after": 0}
    return {"text": "", "id": "", "source": "none", "left_after": 0}


def _change_of(rows, index, page):
    ids = set(index["pages"][page]["items"]) | {index["pages"][page]["page"]["id"]}
    mine = [(first, last) for item, (first, last) in folded(rows).items() if item in ids]
    if any(last.after == "decided" for _, last in mine):
        return "decided"
    if any(first.before == "-" and last.after == "open" for first, last in mine):
        return "new question"
    return "changed"


def touched_rows(touched, rows, index):
    found = []
    for page in touched:
        entry = index["pages"].get(page)
        if entry is None or entry["page"]["type"] == "session":
            continue
        found.append({"page": page, "name": entry["page"]["title"], "change": _change_of(rows, index, page)})
    return found


def diagram_of(decided, touched, index, names):
    """The last decided flow, else the first touched flow page, else None: the one picture worth drawing."""
    for row in reversed(decided):
        if row["id"].startswith("FLO-") and row["page"] in index["pages"]:
            return _diagram(row["id"], row["name"], index["pages"][row["page"]]["steps"])
    for row in touched or ():
        entry = index["pages"].get(row["page"])
        if entry and entry["page"]["type"] == "flow":
            return _diagram(entry["page"]["id"], entry["page"]["title"], entry["steps"])
    return None


def _diagram(ident, name, steps):
    return {"kind": "sequence", "of": ident, "name": name, "steps": steps, "svg": ""}


def build(inputs):
    """The session JSON (version 2). Raises ValueError when the notes' header can't be read: the caller turns that
    into `unreadable`, never into an empty panel."""
    notes, index, today = inputs.notes, inputs.index, inputs.today
    names = pageindex.names(index)
    rows = closegate.change_rows(notes)
    summary = privaterecord.summary_of(notes)
    agenda_list = agenda_rows(notes, names)
    decided = decided_rows(rows, names)
    touched = touched_rows(inputs.touched, rows, index) if inputs.touched is not None else None
    warnings = []
    if inputs.touched is None:
        warnings.append("I couldn't tell which pages this session changed.")
    return {"version": VERSION, "kind": "session", "as_of": as_of(today, inputs.now), "capture": highest_capture(notes),
            "notes": "read", "session": session_of(inputs.stub),
            "about": "" if summary == PLACEHOLDER_SUMMARY else summary,
            "decided": decided, "said_yes": said_yes_rows(notes, index, names),
            "open": open_rows(rows, agenda_list, index, names, today), "agenda": agenda_list,
            "next": next_move(agenda_list, inputs.map_next, inputs.plan_next, today), "touched": touched,
            "diagram": diagram_of(decided, touched, index, names), "band": "", "files": dict(FILES), "vault": "",
            "warnings": warnings}
