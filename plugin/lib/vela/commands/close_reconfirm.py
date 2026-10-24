"""`vela close reconfirm --yes ^cNN ID [ID ...] [--json|--for-lead]`: the lead's "Still yes?" for what the other
machine decided.

The Violation this command's shape prevents is a Silent Fallback in the record: a later part of a session cannot
read the first part's notes, so a decision made there would reach the pull request under a yes nobody on this machine
heard. The gate asks once (`closegate.ELSEWHERE`); the lead answers here, in a capture of this part, and then the
receipt names this part's yes (`[[<id>]] 2.c03, @lead: "..."`) and the Changes table holds the row for it. Nothing is
decided by this command: it files the lead's yes the gate then judges as it judges any other. The "Still yes?" question is the read-back of this
part (the first read-back happened on the other machine, in notes this machine cannot read), so `--readback ^cQ` names
the captured question, and it and the yes are marked `keep ... (decided)` the way `vela decide` marks its own, or the
gate would ask "I never read it back" at every two-machine close. A no is captured and
files nothing, so the gate keeps asking and the skill offers to reopen the item.

Close order (controller ruling C7): this runs before the read-back, so the read-back digest covers the new words.

Exit codes: 0 filed; 1 refused (said in plain words, nothing written); 2 the tool failed; 3 several sessions are open.
"""
import pathlib

from vela import closegate, closereadback, privaterecord, receipts, say
from vela.decisions import consent, decide, textedit
from vela.edge import apply as disk, flowstore, mergegit, sessiongit, vaultgit

NAME = "close reconfirm"
REOPENED = "I've changed a line you already read back, so read it back again."
NOT_ASKED = "{ids} wasn't something the other machine decided, so I haven't filed anything."


def register_close(steps):
    p = steps.add_parser("reconfirm", help="the lead's yes, in this part, to what the other machine decided: "
                                           "re-points each receipt here and records the yes in the Changes table")
    p.add_argument("--vault", default=".", help="vault root (default: current directory)")
    p.add_argument("--readback", required=True, metavar="^cQ",
                   help="the capture of your \"Still yes?\" question, made before the lead's answer")
    p.add_argument("--yes", required=True, metavar="^cNN", help="the lead's capture of this part saying yes")
    p.add_argument("ids", nargs="+", metavar="ID", help="what the gate asked about: item or page IDs, ledger copies")
    say.add_output_flags(p)
    p.set_defaults(func=run)


def _refused(text, plain=None):
    return say.Result(NAME, exit=say.REFUSED, lines=[say.Line(text, plain=plain or text)])


def run(args, out):
    from vela import cli, commands
    from vela.commands import apply, close_gate
    root = pathlib.Path(args.vault).resolve()
    try:
        record, early = apply.find_record(root)
        if early is not None:
            return commands.emit(early, args, out)
        vault = cli.load_vault(root)
        lead = apply.lead_of(root)
        if mergegit.is_reader_copy(root):
            result = _refused("a reader copy has no branch point, so nothing was decided elsewhere.",
                              "This is your copy, so there's nothing here to ask again.")
        else:
            changed = flowstore.changed_files(root, since=close_gate.branch_point(root))
            result = reconfirm(args, root, vault, close_gate.vault_before(vault, changed), record, lead)
    except (ValueError, OSError, cli.ToolError, vaultgit.GitUnavailable) as exc:
        return commands.emit(say.Result(NAME, exit=say.FAILED, lines=[say.Line(
            f"vela close reconfirm: {exc}", plain="I couldn't file your yes; something on disk didn't answer.")]),
            args, out)
    return commands.emit(result, args, out, say.Resolver(vault))


def reconfirm(args, root, vault, before, record, lead):
    refusal = _yes_refusal(args.yes, args.readback, record, lead)
    if refusal is not None:
        return say.Result(NAME, exit=say.REFUSED, refusals=[refusal])
    rows, said = closegate.change_rows(record.text), closegate.captures(record.text)
    asked = {a.id: a for a in closegate.away(vault, before, rows, said, record.id, record.part)}
    missing = [i for i in args.ids if i not in asked]
    if missing:
        return _refused(NOT_ASKED.format(ids=", ".join(missing)),
                        "I didn't ask about one of those, so I haven't filed anything.")
    yes = record.capture(args.yes)
    source = textedit.capture_link(record.id, args.yes)
    was_read_back = _read_back(root, vault, record, lead)
    notes, pages = record.text, {}
    for ident in dict.fromkeys(args.ids):
        notes = textedit.add_change(notes, ident, asked[ident].before, asked[ident].after,
                                    f"{source} {closegate.RECONFIRMED}")
        _repoint(vault, root, pages, ident, record, lead, yes)
    notes = _marked(notes, vault, root, [asked[i] for i in dict.fromkeys(args.ids)], args)
    wrote = [sessiongit.write_text(root, rel, text) for rel, text in pages.items()]
    wrote.append(sessiongit.write_text(root, record.path, notes))
    names = say.names_said([asked[i].name for i in dict.fromkeys(args.ids)])
    lines = [say.Line(
        f"close reconfirm: {len(set(args.ids))} item(s) reconfirmed in part {record.part} by {args.yes}.",
        plain=f"Thank you. {names[0].upper() + names[1:]} stands as your yes today.")]
    if was_read_back and not _read_back(root, _reloaded(root), record, lead):
        lines.append(say.Line("close reconfirm: the read-back digest changed; run close readback again.", plain=REOPENED))
    return say.Result(NAME, exit=say.DONE, wrote=wrote, lines=lines)


def _reloaded(root):
    from vela import cli
    return cli.load_vault(root)


def _read_back(root, vault, record, lead):
    """Whether the lead's finished read-back still matches the sentences as they stand."""
    from vela.commands import close_gate
    stored = close_gate.read_back_digest(root, record.id)
    if stored is None:
        return False
    found = closereadback.sentences(vault, record.id, record.part, record.text, lead,
                                    close_gate.read_picked(root, record.id))
    return closereadback.digest(found) == stored


def _marked(notes, vault, root, asked, args):
    """`notes` with the question and the yes kept on every item reconfirmed as decided: the read-back the gate looks
    for (`closegate.read_back_before`). A removal has no item to keep, so those captures are left for close's marks."""
    from vela import decisions
    staged = textedit.attach(decisions.Staged(vault, disk.reader(root)), "", [])
    kept = []
    for away in asked:
        target = None if away.is_removal else decide.locate(staged, away.id)[1]
        if target is not None and away.after == closegate.CONSENT_STATE:
            kept.append(textedit.keep_mark(textedit.basename(target.path), target.anchor, target.id, away.after))
    if not kept:
        return notes
    mark = "keep: " + "; ".join(k[len("keep: "):] for k in kept)
    for ref in (args.readback, args.yes):
        notes = textedit.mark_if_unmarked(notes, ref, mark)
    return notes


def _yes_refusal(ref, readback, record, lead):
    first = consent.a_yes(ref, record, readback=readback)
    if first is not None:
        return first
    handle, names = lead if lead else ("", ())
    return consent.from_the_lead(record.capture(ref), handle, names)


def _repoint(vault, root, pages, ident, record, lead, yes):
    """Point the item's receipt at this part's yes, in `pages` ({path: new text}); a removal has no receipt."""
    if not closegate.cites_another_part(vault, ident, record.id, record.part):
        return
    page, bullet = closegate.decision_bullets(vault, ident)[0]
    path = page.path
    old = receipts.parse_decision(bullet.value)
    value = receipts.decision_value(record.id, privaterecord.Ref(record.part, int(yes.n)), lead[0], yes.quote,
                                    old.stated_in)
    lines = (pages.get(path) or (pathlib.Path(root) / path).read_text(encoding="utf-8")).split("\n")
    index = bullet.line - 1
    if not lines[index].startswith("- **Decision:** "):
        raise ValueError(f"the decision line for {ident} is not at {path}:{bullet.line}")
    lines[index] = f"- **Decision:** {value}"
    pages[path] = "\n".join(lines)
