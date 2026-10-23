"""`vela close reconfirm --yes ^cNN ID [ID ...] [--json|--for-lead]`: the lead's "Still yes?" for what the other
machine decided.

The Violation this command's shape prevents is a Silent Fallback in the record: a later part of a session cannot
read the first part's notes, so a decision made there would reach the pull request under a yes nobody on this machine
heard. The gate asks once (`closegate.ELSEWHERE`); the lead answers here, in a capture of this part, and then the
receipt names this part's yes (`[[<id>]] 2.c03, @lead: "..."`) and the Changes table holds the row for it. Nothing is
decided by this command: it files the lead's yes the gate then judges as it judges any other. A no is captured and
files nothing, so the gate keeps asking and the skill offers to reopen the item.

Close order (controller ruling C7): this runs before the read-back, so the read-back digest covers the new words.

Exit codes: 0 filed; 1 refused (said in plain words, nothing written); 2 the tool failed; 3 several sessions are open.
"""
import pathlib

from vela import closegate, privaterecord, receipts, say
from vela.decisions import consent, textedit
from vela.edge import flowstore, mergegit, sessiongit, vaultgit

NAME = "close reconfirm"
NOT_ASKED = "{ids} wasn't something the other machine decided, so I haven't filed anything."


def register_close(steps):
    p = steps.add_parser("reconfirm", help="the lead's yes, in this part, to what the other machine decided: "
                                           "re-points each receipt here and records the yes in the Changes table")
    p.add_argument("--vault", default=".", help="vault root (default: current directory)")
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
    refusal = _yes_refusal(args.yes, record, lead)
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
    notes, pages = record.text, {}
    for ident in dict.fromkeys(args.ids):
        notes = textedit.add_change(notes, ident, asked[ident].before, asked[ident].after, source)
        _repoint(vault, root, pages, ident, record, lead, yes)
    wrote = [sessiongit.write_text(root, rel, text) for rel, text in pages.items()]
    wrote.append(sessiongit.write_text(root, record.path, notes))
    names = say.names_said([asked[i].name for i in dict.fromkeys(args.ids)])
    return say.Result(NAME, exit=say.DONE, wrote=wrote, lines=[say.Line(
        f"close reconfirm: {len(set(args.ids))} item(s) reconfirmed in part {record.part} by {args.yes}.",
        plain=f"Thank you. {names[0].upper() + names[1:]} stands as your yes today.")])


def _yes_refusal(ref, record, lead):
    first = consent.a_yes(ref, record)
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
