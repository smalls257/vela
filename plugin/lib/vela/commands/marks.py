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
0  the draft is written and listed in `wrote` (and `drafts`): every capture has a default, or the leftovers the lead
   must settle are in `needs_lead`, most blocking first. The draft is written for those leftovers, so the command
   changed something, and exit 3 ("nothing changed") would be a false promise: the 14 October voice audit found it
   exiting 3 with the draft hidden from `wrote`, which `say.check_contract` could then never see (Silent Fallback);
1  refused: no session is open;
2  the tool failed: the vault or the record can't be read, or the disk refused the draft;
3  needs the lead, nothing written: several sessions are open (pick one).

It runs no git in either role. In a reader copy it says so: the draft is filed into the proposal later.
"""
import datetime
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
    resolver = say.Resolver(vault, today=datetime.date.fromisoformat(today))
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
                      plain=sorted_words(counts) if done else "")]
    n = len(result.leftovers)
    answer = ("" if not n else "One of today's notes needs your call:" if n == 1
              else f"{say.count_words(n, capital=True)} of today's notes need your call, most urgent first:")
    if result.leftovers:
        lines.append(say.Line(f"{n} need the lead, most blocking first:", plain=""))
        lines += [say.Line(f"- {lo['capture']} {lo['rule']}: {lo['words']}"
                           + (f" (blocks {', '.join(lo['blocks'])})" if lo["blocks"] else ""),
                           plain=leftover_words(lo, resolver)) for lo in result.leftovers]
    if result.for_model:
        lines.append(say.Line(f"{len(result.for_model)} have no default; read the record and fill the draft's hints: "
                              + ", ".join(f["capture"] for f in result.for_model),
                              plain=f"{say.count_words(len(result.for_model), capital=True)} more I'll settle from "
                                    "what you said this session."))
    lines.append(say.Line("draft: " + ", ".join(written) if written else "nothing to draft: every note has its mark.",
                          plain="" if written else "Every note already has its place."))
    if reader:
        lines.append(say.Line("read copy: no git runs here; the draft is filed into the proposal.",
                              plain="This is a read copy, so nothing is committed; your notes go to the owner with "
                                    "your proposal."))
    data = {"drafts": written, "counts": counts, "for_model": result.for_model, "left_alone": result.left_alone,
            "reader": reader}
    return say.Result(NAME, exit=say.DONE, lines=lines, needs_lead=result.leftovers, wrote=list(written), data=data,
                      answer=answer)


def sorted_words(counts):
    """'Of today's notes, two become pages or open questions and two are set aside for later.' Every count that
    isn't zero is said, so the numbers add up (conversation voice rule 4)."""
    parts = [f"{say.count_words(counts['kept'])} {'becomes a page or an open question' if counts['kept'] == 1 else 'become pages or open questions'}"
             if counts["kept"] else "",
             f"{say.count_words(counts['parked'])} {'is' if counts['parked'] == 1 else 'are'} set aside for later"
             if counts["parked"] else "",
             f"{say.count_words(counts['dropped'])} {'is' if counts['dropped'] == 1 else 'are'} dropped"
             if counts["dropped"] else ""]
    return f"Of today's notes, {say.names_said([p for p in parts if p])}."


def leftover_words(lo, resolver):
    """One leftover as a question with my recommendation (conversation voice rule 2)."""
    words = resolver.plain(lo["words"]).strip().rstrip(".")
    recommend = lo.get("recommend") or {}
    if lo["rule"] == "claude-unknown":
        by = f" for you to chase by {resolver.plain(recommend['ask_by'])}" if recommend.get("ask_by") else ""
        return f"I raised '{words}' myself. I'd keep it as an open question{by}. Keep it, or drop it?"
    if lo["rule"] == "lifted-line":
        return f"Someone else said '{words}'. I'd copy that onto its page word for word. Fine?"
    choices = " or ".join(lo.get("choices") or ())
    return f"{lo['why']}: '{words}'." + (f" {choices[0].upper()}{choices[1:]}?" if choices else "")
