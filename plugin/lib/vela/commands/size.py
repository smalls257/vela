"""`vela size [show | set <band> --because ^cN | clear | announce]`: the plan's size, and the lead's say over it.

The Violation this exists to prevent is a Black Box, then a Silent Fallback. A plan sized without telling the lead
treats a two-app plan lightly with nobody having heard so; a size recorded with no reason on record is a choice
nobody can trace. So the size is said once (`announce`, called at session start, on growth and at close), and `set`
asks for the lead's reason as a capture first. Asking is never refusing: the lead may choose any band, and it goes on
record with their words (exit 3 means the reason is wanted and nothing was written).

Exit codes: 0 done; 3 the lead's reason, or a size to clear, is needed (nothing changed).
"""
import pathlib

from vela import commands, privaterecord, say, schema, sizing
from vela.decisions.record import number_of
from vela.edge import sessiongit

NAME = "size"


def register(sub):
    parser = sub.add_parser("size", help="the plan's size: show it, set it with your reason, clear it, or say it once")
    parser.add_argument("action", nargs="?", default="show", choices=("show", "set", "clear", "announce"))
    parser.add_argument("band", nargs="?", choices=schema.SIZE_BANDS, help="with set: small, medium or large")
    parser.add_argument("--because", default="", metavar="^cN", help="with set: the capture holding the lead's reason")
    parser.add_argument("--vault", default=".", help="vault root (default: current directory)")
    parser.add_argument("--today", default=None, help="YYYY-MM-DD for the date the choice is recorded (default: today)")
    say.add_output_flags(parser)
    parser.set_defaults(func=cmd_size)


def cmd_size(args, out):
    from vela import cli
    root = pathlib.Path(args.vault).resolve()
    vault = cli.load_vault(root)
    if args.action == "set":
        result = set_size(root, vault, args, cli.parse_today(args.today)[0])
    elif args.action == "clear":
        result = clear_size(root)
    elif args.action == "announce":
        result = say.Result(NAME, lines=announce(root, vault))
    else:
        result = show(vault)
    return commands.emit(result, args, out, say.Resolver(vault))


def counts_words(sized):
    return ", ".join(s.words for s in sized.signals[:-1]) + f" and {sized.signals[-1].words}"


def show(vault):
    sized = sizing.of(vault)
    text = f"vela size: {sized.band} (measured {sized.measured}; {sized.counts_text()})"
    plain = f"This is a {sized.band} plan: {counts_words(sized)}."
    if sized.ratcheted():
        text += f"; an earlier session read it {sized.recorded}"
    if sized.chosen:
        text += f"; set by the lead on {sized.chosen.date}, {sized.chosen.because}"
        plain = f"This is a {sized.band} plan, as you set it: {counts_words(sized)}."
    return say.Result(NAME, data=sized.as_json(), lines=[say.Line(text, plain=plain)])


def needs_reason(why, question):
    return say.Result(NAME, exit=say.NEEDS_LEAD, needs_lead=[{"ask": "the reason for the size", "question": question}],
                      lines=[say.Line(f"vela size: {why}; nothing was written.", plain=question)])


def set_size(root, vault, args, today):
    ask = "What's your reason for that size? Say it and I'll record it with your choice."
    if not args.band:
        raise SystemExit("vela size set: name a band: small, medium or large.")
    if not args.because:
        return needs_reason("the lead's reason is not on record (--because ^cN)", ask)
    try:
        record, _ = sessiongit.open_record(root)
    except sessiongit.PrivateMissing as exc:
        return needs_reason(str(exc), ask)
    if record is None or record.capture(args.because) is None:
        return needs_reason(f"{args.because} is not a capture in the open session's notes", ask)
    ref = privaterecord.citation(record.id, record.part, number_of(args.because))
    choice = sizing.Choice(args.band, ref, today)
    text = (root / ".vela.yaml").read_text(encoding="utf-8")
    wrote = sessiongit.write_text(root, ".vela.yaml", sizing.config_with_choice(text, choice))
    return say.Result(NAME, wrote=[wrote], data={"band": args.band, "because": ref, "date": today}, lines=[say.Line(
        f"vela size: set {args.band}, because {ref}.", plain=f"I've set this as a {args.band} plan, on your word.")])


def clear_size(root):
    text = (root / ".vela.yaml").read_text(encoding="utf-8")
    cleared = sizing.config_without_choice(text)
    if cleared == text:
        return say.Result(NAME, exit=say.NEEDS_LEAD, needs_lead=[{"ask": "no size is set", "question": "No size is set, so there is nothing to clear."}],
                          lines=[say.Line("vela size: there's no size set; nothing changed.", plain="No size is set, so there is nothing to clear.")])
    wrote = sessiongit.write_text(root, ".vela.yaml", cleared)
    return say.Result(NAME, wrote=[wrote], lines=[say.Line("vela size: cleared; the plan is sized from its pages again.",
                                                           plain="I'll size the plan from its pages again.")])


def due(vault):
    """(the size line, the size to record, the kept band to record) when a line is due, else None. Reads the vault
    only; the caller writes the stub, so a session's start carries it in its opening commit."""
    sized = sizing.of(vault)
    said = sizing.announcement(sized)
    if said is None:
        return None
    return say.Line(said.text, plain=said.plain), sized.stub_value(), sized.shape if said.kind == "kept" else ""


def announce(root, vault):
    """[say.Line] for the size line that is due, recorded on the open session's stub so it is said once. [] when none
    is due, or no session is open (there is nothing to record it on, so nothing is said)."""
    try:
        record, _ = sessiongit.open_record(root)
    except sessiongit.PrivateMissing:
        return []
    found = due(vault) if record is not None else None
    if found is None:
        return []
    line, value, kept = found
    stub = pathlib.Path(root) / record.stub
    sessiongit.write_text(root, record.stub, privaterecord.with_size(stub.read_text(encoding="utf-8"), size=value, kept=kept))
    return [line]
