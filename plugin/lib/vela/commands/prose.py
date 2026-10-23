"""`vela prose replace --page P --line N`: keep a merged paragraph word for word before rewriting it (overhaul Task 21d).

Why: when a session makes a merged paragraph wrong as a whole, house-voice says to rewrite it and to keep the old one
word for word in the session record under `## Replaced prose`, with the page and the date, so whoever wrote it can
find it. A model asked to copy tidies; this copies the bytes (the rules are in `vela/prosereplace.py`). Run it before
editing the paragraph: it reads the page as it is on disk and never changes the page.

The record is the one open session record in the vault's `sessions/` folder, read from the disk (no git), or the one
`--record <id>` names. The Violation this refuses is the Silent Fallback of picking a record: with several open, a
guess files one session's replaced prose into another's record, so it exits 3 and lists them.

Exit codes:
0  copied; the record was written;
1  no paragraph at that line (a blank line, a heading, the frontmatter, past the end), or the line is in a generated
   block (vela's lines, not anyone's prose); or no session is open, or `--record` names no open one. Nothing written;
2  the page or the record can't be read or written, or the page is outside the vault;
3  several sessions are open and `--record` was not given. Nothing written; `--json` carries them as `needs_lead`.

It runs no git in any copy: the close skill commits the record with the rest of the session. In a reader copy it says
so.
"""
import datetime
import pathlib

from vela import commands, privaterecord, prosereplace, rules, say, sessions
from vela.edge import atomic, sessiongit

NAME = "prose replace"


def register(sub):
    prose = sub.add_parser("prose", help="merged prose: keep the old paragraph word for word before rewriting it")
    verbs = prose.add_subparsers(dest="prose_command", metavar="{replace}")
    verbs.required = True
    replace = verbs.add_parser("replace", help="copy the paragraph at a line, byte for byte, under `## Replaced prose` "
                                               "in the open session record")
    replace.add_argument("--vault", default=".", help="vault root or reader workspace (default: current directory)")
    replace.add_argument("--page", required=True, help="the page, relative to the vault, like 05-building-blocks/till.md")
    replace.add_argument("--line", required=True, type=int, help="any line of the paragraph (1-based, as an editor counts)")
    replace.add_argument("--record", default="", help="the open session record's id, when several are open (after an exit 3)")
    replace.add_argument("--today", default=None, help="the date written with the entry (default: today), YYYY-MM-DD")
    say.add_output_flags(replace)
    replace.set_defaults(func=cmd_replace)


def cmd_replace(args, out):
    root = pathlib.Path(args.vault).resolve()
    result = replace(root, args.page, args.line, args.record, args.today)
    return commands.emit(result, args, out)


def replace(root, page, line, wanted, today):
    if today is not None and not rules.is_date(today):
        return failed(f"--today '{today}' is not a YYYY-MM-DD date.", "The date given isn't a date.")
    page_path = (root / page).resolve()
    if root not in page_path.parents:
        return failed(f"{page} is outside the vault {root}.", "That page isn't in this vault.")
    try:
        page_text = page_path.read_bytes().decode("utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        return failed(f"cannot read {page}: {exc}", "I couldn't read that page.")
    found = prosereplace.paragraph_at(page_text, line)
    if isinstance(found, prosereplace.Miss):
        return refused(found)
    record, why_not = open_record(root, wanted)
    if record is None:
        return why_not
    record_rel = privaterecord.private_path(record.id)
    record_path = root / record_rel
    if not record_path.is_file():
        missing = sessiongit.PrivateMissing(record.id)
        return failed(str(missing), str(missing))
    try:
        record_text = record_path.read_bytes().decode("utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        return failed(f"cannot read {record_rel}: {exc}", "I couldn't read the session record.")
    date = today or datetime.date.today().isoformat()
    shown = page_path.relative_to(root).as_posix()
    try:
        atomic.write_atomic(record_path, prosereplace.with_entry(record_text, shown, date, found.text))
    except atomic.WriteFailed as exc:
        return failed(f"cannot write {record_rel}: {exc}", "I couldn't write the session record, so nothing changed.")
    result = say.Result(NAME, wrote=[record_rel], data={
        "page": shown, "first": found.first, "last": found.last, "record": record_rel, "date": date,
        "paragraph": found.text})
    result.lines.append(say.Line(f"copied {shown} lines {found.first}-{found.last} under {prosereplace.HEADING} "
                                 f"in {record_rel}.",
                                 plain="I kept the old paragraph word for word in the session record, so I can "
                                       "rewrite it and you can still see the old one."))  # voice audit row 225
    if sessiongit.is_read_copy(root):
        result.lines.append(say.Line("read copy: wrote the file, ran no git.",
                                     plain=f"{say.YOUR_COPY}, so the record changed on this machine only."))
    return result


def open_record(root, wanted):
    """(the open session record, None), or (None, the Result that says why not)."""
    try:
        records, problems = sessions.find_open(sessiongit.folder_records(root))
    except (OSError, UnicodeDecodeError) as exc:
        return None, failed(f"cannot read the session records: {exc}", "I couldn't read the session records.")
    chosen = sessions.pick(records, pathlib.Path(wanted).stem) if wanted else records
    if wanted and not chosen:
        return None, say.Result(NAME, exit=say.REFUSED, lines=[
            say.Line(f"No open session has the id {wanted}.", plain="The session you picked isn't open.")])
    if not chosen:
        if problems:  # a record that can't be read may be the open one: never say "none open" over it
            return None, failed(f"no session is open that can be read; unreadable: {'; '.join(problems)}",
                                "A session record can't be read, so I can't tell which session is open.")
        return None, say.Result(NAME, exit=say.REFUSED, lines=[say.Line("No session is open.")])
    if len(chosen) > 1:
        choices = [{"id": r.id, "topic": r.title, "path": r.path, "date": r.date} for r in chosen]
        lines = [say.Line(f"{len(chosen)} sessions are open; nothing written. Run again with --record <id>:",
                          plain=f"{len(chosen)} sessions are open, so I haven't picked one. Which is this?")]
        lines += [say.Line(f"- {r.id} ({r.path})", plain=f"- {r.title}.") for r in chosen]
        return None, say.Result(NAME, exit=say.NEEDS_LEAD, lines=lines, needs_lead=choices)
    return chosen[0], None


def refused(miss):
    """A line that holds no paragraph is the model's pick, so its line number and "frontmatter" are the model's to
    read; the lead hears only that I'll fix it (voice audit row 224). A generated block is said in words."""
    fix = ("Give a line of the paragraph itself." if miss.rule == "no paragraph"
           else "Rewrite the prose around the block; vela render rewrites the block itself.")
    audience = say.MODEL if miss.rule == "no paragraph" else say.LEAD
    plain = miss.plain if audience == say.MODEL else "That's not a paragraph anyone wrote, so there's nothing to keep."
    return say.Result(NAME, exit=say.REFUSED, data={"rule": miss.rule, "why": miss.plain}, refusals=[say.Refusal(
        rule=miss.rule, plain=plain, fix=f"{miss.plain} {fix}" if audience == say.LEAD else fix, audience=audience,
        override="copy the paragraph by hand under ## Replaced prose in the session record", waiver="")])


def failed(text, plain):
    return say.Result(NAME, exit=say.FAILED, lines=[say.Line(f"vela: {text}", plain=plain)])
