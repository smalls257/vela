"""`vela size [show | set <band> [--because ^cN] | clear | announce]`: the plan's size, and the lead's say over it.

The Violation this exists to prevent is a Black Box. A plan sized without telling the lead treats a two-app plan
lightly with nobody having heard so; so the size is said once (`announce`, called at session start, on growth and at
close). `set` takes the lead's reason as a capture when they gave one, and records `reason not given` when they did
not: a size is never held up for a reason, and the record says plainly that none was given (not a made-up cite). The
lead may choose any band. A `--because` that names no capture in the open session is still a stop (exit 3, nothing
written): it is a mistaken reference, not a missing reason.

Exit codes: 0 done; 3 a named capture is not in the open session, or a size to clear is needed (nothing changed).
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


def reason_ref(root, because):
    """The committed citation for `because`, or the Result that says it is not a capture in the open session."""
    ask = "Which of your words was that? Say it again and I'll record it with your choice."
    try:
        record, _ = sessiongit.open_record(root)
    except sessiongit.PrivateMissing as exc:
        return needs_reason(str(exc), ask)
    if record is None or record.capture(because) is None:
        return needs_reason(f"{because} is not a capture in the open session's notes", ask)
    return privaterecord.citation(record.id, record.part, number_of(because))


def set_size(root, vault, args, today):
    if not args.band:
        raise SystemExit("vela size set: name a band: small, medium or large.")
    ref = reason_ref(root, args.because) if args.because else sizing.NO_REASON
    if isinstance(ref, say.Result):
        return ref
    choice = sizing.Choice(args.band, ref, today)
    text = (root / ".vela.yaml").read_text(encoding="utf-8")
    wrote = sessiongit.write_text(root, ".vela.yaml", sizing.config_with_choice(text, choice))
    return say.Result(NAME, wrote=[wrote], data={"band": args.band, "because": ref, "date": today}, lines=[say.Line(
        f"vela size: set {args.band}, because {ref}.",
        plain=f"I've set this as a {args.band} plan" + ("." if ref == sizing.NO_REASON else ", on your word."))])


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
