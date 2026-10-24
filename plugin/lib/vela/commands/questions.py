"""`vela questions`: the parser, moved out of cli.py (Task 2). The command itself is `cli.cmd_questions`, except
`--digest --session ID` (overhaul Task 20), which lives here.

`--digest --session ID` is the digest a lead hears in one turn: the next three lines, high and blocking first, without
any line already shown this session or one a capture this session already took, answered or ruled out (REVIEW
section 5, "never twice, never ruled out"). What it showed is written to the record as one bare line under
`## Reviews`, `Digest shown: <copy id>, <copy id>, ...`, and read back next time. The Violation that shape prevents is
a Silent Fallback in memory: "shown once" kept in a model's head is lost on a resume or a second machine, and the
lead is asked the same question again with nothing to show it was asked before. In the record it is committed with
the session (Sensor), and in a reader copy it reaches the owner in the proposal; no git runs here either way.

Without `--session` the digest is exactly what it was: a session's memory never filters the plain digest.

`--digest --session ID --for-lead` is the same three lines as the lead hears them, through say: the answer first, each
question by its area's name with every ID inside it said by name, and no copy codes, catalog version, record path or
command tail (the October 14 voice audit, rows 174 and 175).
"""
import json
import pathlib

from vela import privaterecord, questions, reviewprep, say
from vela.edge import sessiongit


def register(sub):
    from vela import cli  # cli builds the parser, so it is loaded by the time this runs
    ques = sub.add_parser("questions", help="the questions the catalog says this vault owes, and where each stands")
    ques.add_argument("--vault", default=".", help="vault root (default: current directory)")
    ques.add_argument("--json", action="store_true", help="print JSON instead of text")
    ques.add_argument("--for-lead", action="store_true",
                      help="with --digest --session: the lines as the lead hears them, by name, with no codes")
    ques.add_argument("--area", help="only this area of the catalog, such as FIN")
    ques.add_argument("--open", action="store_true", help="list only copies with no row, an open row, an invalid row or an asked row")
    ques.add_argument("--subject", help="only copies about this subject, such as APP-booking")
    view_of = ques.add_mutually_exclusive_group()
    view_of.add_argument("--digest", action="store_true",
                         help="the undisposed and asked copies grouped by entry and ranked, high and blocking first")
    ques.add_argument("--all", action="store_true",
                      help="with --digest: every line in full, not only the high and blocking ones")
    ques.add_argument("--session", metavar="ID",
                      help="with --digest: the next three lines for this session's lead, never one already shown or "
                           "taken this session; what it shows is written under the record's ## Reviews")
    view_of.add_argument("--existence", action="store_true",
                         help="the six existence questions as one numbered read-back, a no recommended only on the plan's evidence")
    view_of.add_argument("--stats", action="store_true", help="how often each entry ends not-applicable in this vault")
    ques.set_defaults(func=cmd_questions)


def cmd_questions(args, out):
    from vela import cli
    if args.existence:
        return existence(args, out)
    if args.for_lead and (args.session is None or not args.digest or args.json):
        raise cli.ToolError("--for-lead goes with --digest --session ID, and not with --json.")
    if args.session is None:
        return cli.cmd_questions(args, out)
    if not args.digest:
        raise cli.ToolError("--session goes with --digest: it shows the next lines of the digest for that session.")
    if args.all:
        raise cli.ToolError("--session shows three lines at a time, so it takes no --all. Run it again for the next "
                            "three, or leave out --session for every line.")
    root = pathlib.Path(args.vault).resolve()
    vault = cli.load_vault(root)
    if args.area is not None and args.area not in vault.catalog.area_codes:
        raise cli.ToolError(f"--area {args.area} is not an area of catalog v{vault.catalog.version}. "
                            f"Use one of: {', '.join(vault.catalog.area_codes)}.")
    rel = privaterecord.private_path(args.session)
    path = root / rel
    if not path.is_file():
        raise cli.ToolError(f"--session {args.session}: there are no session notes {rel} on this machine. Give the "
                            "session's id, its record's file name without .md.")
    text = path.read_text(encoding="utf-8")
    answer = questions.digest(vault, args.area, args.subject)
    every = [c for g in answer["groups"] for c in g["copies"]]
    named = reviewprep.taken_in_captures(text)
    seen = set(reviewprep.digest_shown(text)) | {c for c in every if reviewprep.covered(c, named)}
    shown, held = questions.unseen(answer, seen)
    ids = [c for g in shown for c in g["copies"]]
    if ids:
        sessiongit.write_text(root, rel, reviewprep.with_digest_shown(text, ids))
    reader = sessiongit.is_read_copy(root)
    answer = dict(answer, groups=shown, held=len(held), session=args.session, record=rel, shown=ids,
                  reader_copy=reader)
    if args.json:
        print(json.dumps(answer, indent=2, ensure_ascii=False), file=out)
        return 0
    if args.for_lead:
        from vela import commands
        return commands.emit(lead_digest(answer, dict(vault.catalog.areas)), args, out, say.Resolver(vault))
    print_session_digest(answer, out, dict(vault.catalog.areas), cli)
    return 0


def existence(args, out):
    from vela import cli, commands
    if args.session is not None or args.area or args.subject or args.open or args.all:
        raise cli.ToolError("--existence reads back the six existence questions together, so it takes no --session, "
                            "--area, --subject, --open or --all.")
    vault = cli.load_vault(pathlib.Path(args.vault).resolve())
    found = questions.existence_lines(vault)
    if args.json:
        print(json.dumps({"lines": [{"copy": l.copy, "question": l.question, "recommend": l.recommend, "why": l.why}
                                    for l in found]}, indent=2, ensure_ascii=False), file=out)
        return 0
    if args.for_lead:
        # A named exception to DIGEST_AT_A_TIME and say.LEAD_LIMIT: the existence read-back is one turn of six yes-or-no
        # lines; each answer is its own capture, so the lead's reason is their own for every one.
        args.more = True
        return commands.emit(lead_existence(found), args, out, say.Resolver(vault))
    print(f"vela questions --existence: {len(found)} existence question{'' if len(found) == 1 else 's'} still to answer.", file=out)
    for n, line in enumerate(found, start=1):
        extra = f" (I'd say no: {line.why})" if line.recommend else ""
        print(f"{n}. {line.copy}: {line.question}{extra}", file=out)
    return 0


def lead_existence(found):
    """The six as the lead hears them, in one turn: numbered yes-or-no lines, then which ones vela would say no to."""
    if not found:
        return say.Result("questions --existence", answer="Every existence question has an answer already.")
    lines = [say.Line("", plain=f"{n}. {line.question.strip()}") for n, line in enumerate(found, start=1)]
    head = "These decide what else I'll ask. Answer yes or no to each:"
    closing = "Which are yes?" + recommended_noes(found)
    return say.Result("questions --existence", answer=head, lines=lines, closing=closing,
                      data={"lines": len(found)})


def recommended_noes(found):
    """" I'd say no to 1 and 2: <reason>." with each recommended no under its own reason, so a stored value and a party
    never share the other's evidence; "" when none is recommended."""
    by_reason = {}
    for n, line in enumerate(found, start=1):
        if line.recommend:
            by_reason.setdefault(line.why, []).append(str(n))
    parts = [f"{say.names_said(numbers)}: {reason}" for reason, numbers in by_reason.items()]
    if len(parts) <= 1:
        return f" I'd say no to {parts[0]}." if parts else ""
    return " I'd say no to " + "; and to ".join(parts) + "."


def lead_digest(answer, area_names):
    """The session digest as the lead hears it: the answer, each question by its area, then how many wait."""
    count = len(answer["groups"])
    if not count:
        return say.Result("questions --digest --session",
                          answer="That's every question for this session; the rest are listed if you want them.")
    lines = []
    for group in answer["groups"]:
        area = area_names.get(group["area"], "Another area")
        read = group.get("on_page_copies", [])
        if read and len(read) == len(group["copies"]):
            lines.append(say.Line("", plain=f"{area}: the runtime pages already say what happens when these fail: "
                                            f"{say.names_said([c.split('@', 1)[1] for c in read])}. Is that the answer?"))
            continue
        said = f"{area}: {group['question'].strip()}"
        if group["blocks"]:
            said += f" It holds up {say.names_said(group['blocks'][:3])}" + (
                f" and {say.count_words(len(group['blocks']) - 3)} more." if len(group["blocks"]) > 3 else ".")
        if len(group["copies"]) > 1:
            said += f" It comes up in {say.count_words(len(group['copies']))} places; one answer for all?"
        if read:
            said += (" The runtime pages already say what happens for "
                     f"{say.names_said([c.split('@', 1)[1] for c in read])}; is that the answer there?")
        lines.append(say.Line("", plain=said))
    held = answer["held"]
    head = ("One question for today:" if count == 1 else
            f"{say.count_words(count, capital=True)} questions for today, most important first:")
    closing = (f"{say.count_words(held, capital=True)} more {'is' if held == 1 else 'are'} waiting for later."
               if held else "")
    return say.Result("questions --digest --session", answer=head, lines=lines, closing=closing,
                      data={"shown": answer["shown"], "held": held})


def print_session_digest(answer, out, area_names, cli):
    count = len(answer["groups"])
    if not count:
        print(f"vela questions --digest --session {answer['session']}: nothing left to show this session; every "
              "pending line was shown once or taken in a capture. Every line: vela questions --open --digest --all",
              file=out)
        return
    print(f"vela questions --digest --session {answer['session']}: {cli.said_coverage(answer)}. The next {count}, "
          f"most important first; written to {answer['record']} as shown"
          + (" (a reader copy: nothing else ran; the line reaches the owner in the proposal)."
             if answer["reader_copy"] else "."), file=out)
    for n, group in enumerate(answer["groups"], start=1):
        cli.print_digest_line(n, group, out, area_names)
    if answer["held"]:
        held = answer["held"]
        print(f"{held} more {'is' if held == 1 else 'are'} written down; run the same command for the next "
              f"{questions.DIGEST_AT_A_TIME}.", file=out)
