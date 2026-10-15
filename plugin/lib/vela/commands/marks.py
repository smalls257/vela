"""`vela marks plan [--vault V] [--today D] [--json|--for-lead]`: close section 2's default marks (overhaul Task 14).

"Filing is the tool's work, not the lead's." The rules live in `vela.markrules`, one table row each with its reason;
this module only reads what they need and writes the drafts. It drafts `.vela/decisions/<session>/<seq>-marks.json`
in Task 4's decision-file format with every default applied, and `<seq>-ledger.json` when there are question-ledger
rows to write (copy-ID captures, and every `## Reviews` finding the lead didn't take, citing its checkpoint). What the
defaults can't settle is the `needs_lead` list, ranked by what each item holds up, so the skill asks the few that
matter (at most three at a time) and fills the draft's judgment fields with the captures holding the answers. The
`marks` apply kind (Task 15) writes the marks; this command writes no page and no record line.

Nothing here asks for bookkeeping: the lead's handle is `.vela/handle` (else the capture's own handle), and ask-by
dates come from the fixed rule in `markrules.ask_by`, said back so the lead can correct one.

A re-run replaces the latest draft of each kind that hasn't been applied yet, so a stale draft never sits beside the
fresh one for the model to pick by mistake; an applied draft is never touched.

Exit codes (plan 3.1):
0  every capture has a default (or already had a mark); the draft is written;
1  refused: no session is open;
2  the tool failed: the vault or the record can't be read, or the disk refused the draft;
3  needs the lead: leftovers to ask (`needs_lead`), or several sessions are open (pick one). The draft is written
   for the leftovers, since it is scratch under `.vela/` that nothing commits; the vault and the record are
   unchanged, which is what exit 3 promises, so the draft is reported in `drafts`, not `wrote`.

It runs no git in either role. In a reader copy it says so: the draft is filed into the proposal later.
"""
import json
import pathlib

from vela import commands, ledger, markrules, parse, say
from vela.decisions import record as records, schema
from vela.edge import atomic, sessiongit

NAME = "marks plan"


def register(sub):
    marks = sub.add_parser("marks", help="close's default marks: draft them, and say what only the lead can settle")
    each = marks.add_subparsers(dest="marks_step", required=True)
    parser = each.add_parser("plan", help="apply every default mark and draft the decision file; list the leftovers "
                                          "for the lead, most blocking first")
    parser.add_argument("--vault", default=".", help="vault root or reader workspace (default: current directory)")
    parser.add_argument("--today", help="the date ask-by defaults count from, YYYY-MM-DD (default: today)")
    say.add_output_flags(parser)
    parser.set_defaults(func=cmd_plan)


def cmd_plan(args, out):
    from vela import cli  # the shell loads the vault and parses the date; this module wires it
    root = pathlib.Path(args.vault).resolve()
    try:
        today = cli.parse_today(args.today)[0]
        vault = cli.load_vault(root)
    except cli.ToolError as exc:
        return commands.emit(failed(str(exc), "I couldn't read the vault, so I haven't worked out any marks."),
                             args, out)
    resolver = say.Resolver(vault)
    record, early = find_record(root)
    if early is not None:
        return commands.emit(early, args, out, resolver)
    reader = sessiongit.is_read_copy(root)
    ctx = context(root, vault, record, today)
    result = markrules.plan(record.text, ctx)
    try:
        written = write_drafts(root, record.id, markrules.draft_files(result, record.id, record)) if result.items \
            or result.ledger else []
    except OSError as exc:  # atomic.WriteFailed among them
        return commands.emit(failed(f"couldn't write the draft: {exc}", "I couldn't save the marks I worked out."),
                             args, out, resolver)
    return commands.emit(report(result, written, reader, resolver), args, out, resolver)


def failed(text, plain):
    return say.Result(NAME, exit=say.FAILED, lines=[say.Line(f"vela marks plan: {text}", plain=plain)])


def find_record(root):
    """(OpenRecord, None), or (None, the Result to print instead). Read from the working tree, so no git runs."""
    try:
        rec, opened = records.open_record(sessiongit.folder_records(root))
    except (OSError, UnicodeDecodeError) as exc:
        return None, failed(f"can't read the session records: {exc}", "I couldn't read the session records.")
    if rec is not None:
        return rec, None
    if not opened.several:
        why = f" ({'; '.join(opened.problems)})" if opened.problems else ""
        return None, say.Result(NAME, exit=say.FAILED if opened.problems else say.REFUSED, lines=[say.Line(
            f"No session is open, so there is nothing to mark{why}.",
            plain="No session is open, so there are no notes to file.")])
    choices = [{"id": r.id, "topic": r.title, "date": r.date} for r in opened.records]
    return None, say.Result(NAME, exit=say.NEEDS_LEAD, needs_lead=choices, lines=[say.Line(
        f"{len(choices)} sessions are open in this folder; nothing drafted. Run it on the branch of the one closing.",
        plain=f"{len(choices)} sessions are open here, so I haven't filed anything. Which one are we closing?")])


def context(root, vault, record, today):
    meta = parse.split_frontmatter(record.text)[0]
    modes = meta.get("modes") or ()
    handle = sessiongit.read_handle(root)
    copies = frozenset(row.copy for page in vault.pages for row in ledger.rows(page))
    return markrules.Context(record_id=record.id, modes=tuple(modes) if isinstance(modes, (list, tuple)) else (modes,),
                             today=today, lead=("@" + handle.lstrip("@")) if handle else "",
                             hard_dates=markrules.hard_dates(vault), open_items=markrules.open_items(vault),
                             ledger_copies=copies)


def unapplied(path):
    try:
        return "applied" not in json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return False  # a draft that can't be read is left as it is, and a fresh one is numbered past it


def write_drafts(root, session, files):
    """Write each kind's draft (atomically, every file or none) and return their vault-relative paths."""
    folder = root / schema.FOLDER / session
    folder.mkdir(parents=True, exist_ok=True)
    existing = sorted(p.name for p in folder.glob("*.json"))
    targets = {}
    for kind, content in files.items():
        mine = [name for name in existing if name.endswith(f"-{kind}.json")]
        if mine and unapplied(folder / mine[-1]):
            rel = f"{schema.FOLDER}/{session}/{mine[-1]}"
        else:
            rel = schema.draft_path(session, existing, kind)
            existing.append(pathlib.PurePosixPath(rel).name)
        targets[rel] = json.dumps(content, indent=2, ensure_ascii=False) + "\n"
    atomic.write_all_atomic({root / rel: text for rel, text in targets.items()})
    return list(targets)


def report(result, written, reader, resolver):
    counts = result.counts
    done = counts["kept"] + counts["parked"] + counts["dropped"]
    lines = [say.Line(f"marks plan: {done} by default (kept {counts['kept']}, parked {counts['parked']}, dropped "
                      f"{counts['dropped']}); {counts['needs_lead']} for the lead; {counts['for_model']} for the "
                      f"model; {counts['left_alone']} already marked; {len(result.ledger)} ledger rows drafted.",
                      plain=f"I've worked out where {done} of your notes go by default: kept {counts['kept']}, "
                            f"parked {counts['parked']}.")]
    if result.leftovers:
        lines.append(say.Line(f"{len(result.leftovers)} need the lead, most blocking first:",
                              plain=f"{len(result.leftovers)} need your word, the ones holding up the most first:"))
        lines += [say.Line(f"- {lo['capture']} {lo['rule']}: {lo['words']}"
                           + (f" (blocks {', '.join(lo['blocks'])})" if lo["blocks"] else ""),
                           plain=f"- {lo['why']}: {resolver.plain(lo['words'])}") for lo in result.leftovers]
    if result.for_model:
        lines.append(say.Line(f"{len(result.for_model)} have no default; read the record and fill the draft's hints: "
                              + ", ".join(f["capture"] for f in result.for_model),
                              plain=f"{len(result.for_model)} more I'll settle from what you said this session."))
    lines.append(say.Line("draft: " + ", ".join(written) if written else "nothing to draft: every note has its mark.",
                          plain="I've written that down, ready to file." if written
                          else "Every note already has its place."))
    if reader:
        lines.append(say.Line("read copy: no git runs here; the draft is filed into the proposal.",
                              plain="This is a read copy, so nothing is committed; your notes go to the owner with "
                                    "your proposal."))
    data = {"drafts": written, "counts": counts, "for_model": result.for_model, "left_alone": result.left_alone,
            "reader": reader}
    return say.Result(NAME, exit=say.NEEDS_LEAD if result.leftovers else say.DONE, lines=lines,
                      needs_lead=result.leftovers, data=data)
