"""`vela record add --origin O --tag T [--mark M] "text"`: one capture line in the open session record, numbered in
code (overhaul Task 6b). Named `record`, not `capture`: `vela capture` is the vault's counts, which the session
simulator reads (`tests/sim/run.py`), so that name and its output stay as they are.

The Violation the shape prevents is a Silent Fallback inside the record: a number reused after a delete, or a line
just off the grammar, still looks like a capture, and every consent check that cites it then reads the wrong words or
none. So the number is one more than any the record has ever used (its text now, the high-water mark in
`.vela/session.json`, and the record's git history; see `vela/records.py`), and the line is built from its parts and
refused when it would not read back.

Origins, as START defines them: the lead's (or another person's) name, role or handle for their own words, quoted
verbatim; `claude` for Claude's own idea; `claude, from <name>` for Claude's restatement of what someone said or a
recommendation the lead accepted. A mode whose skill marks its captures at once (Grill, Discover, Boundary,
Requirements, Allocate, Releases) passes `--mark`.

Which record: `.vela/session.json` (written by `session start`) while it names an open record, else the one open
record in the working tree's `sessions/`. Exit codes: 0 added (the number is printed); 1 no open record, or a line
that would not parse; 2 the record or git failed; 3 several open records in this folder (pick with `--record`).

A reader copy writes in place and runs no git: the history is not read there, and the record's text and the
session file still hold every number this copy used.
"""
import pathlib

from vela import commands, records, say, sessions
from vela.edge import sessiongit
from vela.edge.vaultgit import GitUnavailable

NAME = "record add"
NO_RECORD = "No session is open, so there's no record to add the note to."


def register(sub):
    record = sub.add_parser("record", help="the open session record: add a capture, numbered so no number is reused")
    verbs = record.add_subparsers(dest="record_command", metavar="{add}")
    verbs.required = True
    adder = verbs.add_parser("add", help="append one capture line with the next ^cNN, and print the number")
    adder.add_argument("--vault", default=".", help="vault root or reader workspace (default: current directory)")
    adder.add_argument("--origin", required=True,
                       help="whose words: a name, role or handle (quoted verbatim), claude, or 'claude, from <name>'")
    adder.add_argument("--tag", required=True, help="idea, thought, unknown, wild or worry (or the mode's own tag)")
    adder.add_argument("--mark", default="", help="a mark written at once, for the modes that mark as they go")
    adder.add_argument("--record", default="", metavar="ID", help="the open record to add to, when several are open")
    adder.add_argument("text", help="the words of the capture")
    say.add_output_flags(adder)
    adder.set_defaults(func=cmd_add)


class Stop(Exception):
    def __init__(self, result):
        super().__init__(result.command)
        self.result = result


def cmd_add(args, out):
    root = pathlib.Path(args.vault).resolve()
    try:
        result = add(root, args, sessiongit.is_read_copy(root))
    except Stop as stop:
        result = stop.result
    except (GitUnavailable, ValueError, OSError) as exc:
        result = say.Result(NAME, exit=say.FAILED, lines=[
            say.Line(f"vela: {exc}", plain=f"I couldn't add the note to the record: {exc}")])
    return commands.emit(result, args, out)


def open_record(root, state, wanted):
    """(path, record id) of the record to write to, or Stop (exit 1 none, 3 several)."""
    if not wanted and state and state.get("path"):
        path = root / str(state["path"])
        if path.is_file():
            record, _ = sessions.read("", str(state["path"]), path.read_text(encoding="utf-8"))
            if record is not None and record.status == "open":
                return str(state["path"]), record.id
    found, _ = sessions.find_open(sessiongit.folder_records(root))
    if wanted:
        found = sessions.pick(found, wanted)
    if not found:
        raise Stop(say.Result(NAME, exit=say.REFUSED, lines=[say.Line(NO_RECORD)]))
    if len(found) > 1:
        raise Stop(say.Result(NAME, exit=say.NEEDS_LEAD, needs_lead=[{"ask": "record", "id": r.id} for r in found],
                              lines=[say.Line(f"{len(found)} records are open here; nothing changed. Run again with "
                                              "--record <id>:", plain="More than one session is open here, so I "
                                                                      "haven't picked one.")]
                              + [say.Line(f"- {r.id}", plain=f"- {r.title}") for r in found]))
    return found[0].path, found[0].id


def add(root, args, reader):
    state = sessiongit.read_json(root, sessiongit.STATE_FILE)
    rel, record_id = open_record(root, state, args.record)
    path = root / rel
    text = path.read_text(encoding="utf-8")
    remembered = {int(state.get("last_capture") or 0)} if state and state.get("id") == record_id else set()
    history = set() if reader else records.numbers_in(sessiongit.history_text(root, rel))
    number = records.next_number(records.numbers_in(text), remembered, history)
    try:
        line = records.capture_line(args.tag, args.origin, args.text, number, args.mark)
        new_text = records.append(text, line)
    except records.CaptureRefused as exc:
        raise Stop(say.Result(NAME, exit=say.REFUSED, refusals=[say.Refusal(
            "capture grammar", f"I didn't add the note: {exc}.", "change that part and run it again")])) from exc
    wrote = [sessiongit.write_text(root, rel, new_text)]
    kept = dict(state) if state and state.get("id") == record_id else {"id": record_id, "path": rel}
    kept["last_capture"] = number
    wrote.append(sessiongit.write_state(root, kept))
    label = records.label(number)
    return say.Result(NAME, wrote=wrote, data={"number": label, "line": line, "record": rel},
                      lines=[say.Line(label, plain="Noted in the session record.")])
