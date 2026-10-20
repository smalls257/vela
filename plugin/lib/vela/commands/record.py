"""`vela record add [--origin O] --tag T [--mark M] "text"`: one capture line in the open session record, numbered in
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

With no `--origin` the words are the lead's, written `@<handle>` from `vela whoami` (the cache, then gh): the consent
checks compare a yes's origin with that handle, so a capture written without `--origin` still counts as the lead's
yes. When nobody knows the handle, nothing is written and the exit is 3 with whoami's question (ask once, then
`vela whoami --set`): writing the line under a guessed or empty origin would be a yes no consent check can trust.

Every loose spelling of the lead (`lead`, `@lead`, `the lead`, the handle with or without `@`) is written as
`@<handle>`, so `vela decide` and the override check never refuse on how the lead was named.

A person's words are checked against what they typed (`vela/said.py`, the log `vela hook said` keeps in
`.vela/said/`): words that are not an excerpt of one typed message are refused with exit 3 and nothing written, and
`--origin claude` is the home of the model's own words. Where no log exists (a host whose hooks don't fire) nothing can
be checked, so the capture is written with `, unverified` after its origin, and the close gate and `vela team commit`
ask the lead to confirm it by name before it counts; `vela record confirm` takes the mark off once they have.

Which record: `.vela/session.json` (written by `session start`) while it names an open record, else the one open
record in the working tree's `sessions/`. Exit codes: 0 added (the number is printed); 1 no open record, or a line
that would not parse; 2 the record or git failed; 3 several open records in this folder (pick with `--record`).

A reader copy writes in place and runs no git: the history is not read there, and the record's text and the
session file still hold every number this copy used.
"""
import datetime
import pathlib

from vela import closegate, commands, records, said, say, sessions
from vela.commands import whoami
from vela.edge import saidlog, sessiongit
from vela.edge import vaultgit
from vela.edge.vaultgit import GitUnavailable

NAME = "record add"
NO_RECORD = "No session is open, so there's no record to add the note to."


def register(sub):
    record = sub.add_parser("record", help="the open session record: add a capture, numbered so no number is reused")
    verbs = record.add_subparsers(dest="record_command", metavar="{add,confirm}")
    verbs.required = True
    adder = verbs.add_parser("add", help="append one capture line with the next ^cNN, and print the number")
    adder.add_argument("--vault", default=".", help="vault root or reader workspace (default: current directory)")
    adder.add_argument("--origin", default="",
                       help="whose words: a name, role or handle (quoted verbatim), claude, or 'claude, from <name>'. "
                            "Default: the lead, as @<handle> from vela whoami, so the consent checks read the "
                            "line as the lead's own yes; exit 3 when the handle isn't known yet")
    adder.add_argument("--tag", required=True, help="idea, thought, unknown, wild or worry (or the mode's own tag)")
    adder.add_argument("--mark", default="", help="a mark written at once, for the modes that mark as they go")
    adder.add_argument("--record", default="", metavar="ID", help="the open record to add to, when several are open")
    adder.add_argument("text", help="the words of the capture")
    say.add_output_flags(adder)
    adder.set_defaults(func=cmd_add)
    confirm_parser = verbs.add_parser("confirm", help="take 'unverified' off a capture once the person says the words were theirs")
    confirm_parser.add_argument("--vault", default=".", help="vault root or reader workspace (default: current directory)")
    confirm_parser.add_argument("--record", default="", metavar="ID", help="the open record, when several are open")
    confirm_parser.add_argument("number", help="the capture, as printed by record add (^c07 or 7)")
    say.add_output_flags(confirm_parser)
    confirm_parser.set_defaults(func=cmd_confirm)


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
    if not found and not wanted:
        design = design_record(root)
        if design:
            return design
    if not found:
        raise Stop(say.Result(NAME, exit=say.REFUSED, lines=[say.Line(NO_RECORD)]))
    if len(found) > 1:
        raise Stop(say.Result(NAME, exit=say.NEEDS_LEAD, needs_lead=[{"ask": "record", "id": r.id} for r in found],
                              lines=[say.Line(f"{len(found)} records are open here; nothing changed. Run again with "
                                              "--record <id>:", plain="More than one session is open here, so I "
                                                                      "haven't picked one.")]
                              + [say.Line(f"- {r.id}", plain=f"- {r.title}") for r in found]))
    return found[0].path, found[0].id


DESIGN_RECORDS = ".vela/design"


def design_record_path(branch):
    """The vault-relative path of the yes record for a `design/<slug>` branch, or "" for any other branch."""
    slug = branch[len("design/"):].strip("/") if branch.startswith("design/") else ""
    return f"{DESIGN_RECORDS}/{slug.replace('/', '-')}.md" if slug else ""


def design_record(root):
    """(path, id) of the design branch's own record of the senior's yes, made on first use. A design session opens no
    session record, yet its choices need a place for the yes (`vela team commit` reads it). It lives in `.vela/`, the
    tool's local state, so it never rides the design commit or shows up as a stray file; None off a design branch."""
    try:
        rel = design_record_path(vaultgit.current_branch(root))
    except GitUnavailable:
        return None
    if not rel:
        return None
    path = root / rel
    record_id = path.stem
    if not path.is_file():
        today = datetime.date.today().isoformat()
        sessiongit.write_text(root, rel, sessions.record_text(record_id, f"Design: {record_id}", today, ["design"]))
    return rel, record_id


def lead_origin(root):
    """(`@<handle>`, what whoami wrote) for a capture with no --origin, or Stop with whoami's exit 3 (ask the lead
    once). gh's answer is cached by whoami, so that write is listed too."""
    found = whoami.find_handle(root)
    if found.exit != say.DONE:
        raise Stop(say.Result(NAME, exit=found.exit, needs_lead=found.needs_lead, lines=found.lines))
    return "@" + found.data["handle"], list(found.wrote)


LEAD_WORDS = ("lead", "@lead", "the lead", "the @lead")


def spells_the_lead(root, origin):
    """Whether an origin is one of the loose ways to say "the lead": `lead`, `@lead`, `the lead`, or the lead's own
    handle with or without its `@`. The consent checks accept one spelling only (`@<handle>`), so every other
    spelling costs a refused `vela decide` later (a Distributed Monolith of spellings: the check and the writer
    must agree). Write the handle once, here, and the checks never see a variant. A role or another person's name
    is not the lead's spelling and is left alone."""
    word = origin.strip().casefold()
    if word in LEAD_WORDS:
        return True
    if word in sessiongit.lead_names(root):
        return True  # the lead's display name ("Jo Smith"), from git or `vela whoami --name`
    handle = sessiongit.read_handle(root).lstrip("@").casefold()
    return bool(handle) and word.lstrip("@") == handle


def add(root, args, reader):
    state = sessiongit.read_json(root, sessiongit.STATE_FILE)
    rel, record_id = open_record(root, state, args.record)
    origin, wrote = (args.origin.strip(), []) if args.origin.strip() else lead_origin(root)
    if spells_the_lead(root, origin):
        origin, wrote = lead_origin(root)
    origin, unverified = checked_origin(root, origin, args.text)
    path = root / rel
    text = path.read_text(encoding="utf-8")
    remembered = {int(state.get("last_capture") or 0)} if state and state.get("id") == record_id else set()
    history = set() if reader else records.numbers_in(sessiongit.history_text(root, rel))
    number = records.next_number(records.numbers_in(text), remembered, history)
    try:
        line = records.capture_line(args.tag, origin, args.text, number, args.mark)
        new_text = records.append(text, line)
    except records.CaptureRefused as exc:
        raise Stop(say.Result(NAME, exit=say.REFUSED, refusals=[say.Refusal(
            "capture grammar", f"I didn't add the note: {exc}.", "change that part and run it again")])) from exc
    wrote.append(sessiongit.write_text(root, rel, new_text))
    kept = dict(state) if state and state.get("id") == record_id else {"id": record_id, "path": rel}
    kept["last_capture"] = number
    wrote.append(sessiongit.write_state(root, kept))
    label = records.label(number)
    lines = [say.Line(label, plain="Noted in the session record.")]
    if unverified:
        lines.append(say.Line(UNVERIFIED_LINE))
    return say.Result(NAME, wrote=wrote, data={"number": label, "line": line, "record": rel, "unverified": unverified},
                      lines=lines)


NOT_TYPED = "Those aren't words the person typed. Quote what they said, or record it as your own note."
UNVERIFIED_LINE = "I couldn't check those words against what was typed here, so the note is marked unverified."


def checked_origin(root, origin, words):
    """(origin to write, whether it is unverified). A person's origin needs words they typed; Claude's own origin is
    never checked. Stop (exit 3, nothing written) when a log exists and the words are not in it."""
    if origin.strip().lower().startswith("claude"):
        return origin, False
    logs = saidlog.read_all(root)
    if logs is None:
        return said.mark_unverified(origin), True
    if said.typed(words, said.messages(logs)):
        return origin, False
    raise Stop(say.Result(NAME, exit=say.NEEDS_LEAD, needs_lead=[{"ask": "quote", "words": words}],
                          lines=[say.Line(NOT_TYPED)]))


def cmd_confirm(args, out):
    root = pathlib.Path(args.vault).resolve()
    try:
        result = confirm(root, args)
    except Stop as stop:
        result = stop.result
    except (GitUnavailable, ValueError, OSError) as exc:
        result = say.Result("record confirm", exit=say.FAILED, lines=[
            say.Line(f"vela: {exc}", plain=f"I couldn't confirm the note: {exc}")])
    return commands.emit(result, args, out)


def confirm(root, args):
    """Take `, unverified` off one capture. The lead's own say-so is the only reason to run this, so the skills ask
    first; this changes the one line and nothing else."""
    state = sessiongit.read_json(root, sessiongit.STATE_FILE)
    rel, _ = open_record(root, state, args.record)
    number = args.number.strip().lstrip("^c").lstrip("0") or "0"
    lines = (root / rel).read_text(encoding="utf-8").split("\n")
    for i, line in enumerate(lines):
        found = closegate.CAPTURE_RE.match(line.strip())
        if found and found["n"].lstrip("0") == number and said.is_unverified(found["origin"]):
            lines[i] = line.replace(f"({found['origin']})", f"({said.confirmed(found['origin'])})", 1)
            return say.Result("record confirm", wrote=[sessiongit.write_text(root, rel, "\n".join(lines))],
                              lines=[say.Line(f"^c{found['n']} confirmed", plain="Marked as theirs.")])
    raise Stop(say.Result("record confirm", exit=say.REFUSED, lines=[
        say.Line(f"No unverified capture ^c{number} in this record; nothing changed.",
                 plain="I couldn't find an unconfirmed note with that number, so nothing changed.")]))
