"""`vela grill owner <ID> [--owner @handle] [--join @handle ...] | --clear`: who runs the grill on an item, and who is
asked to join it. The dashboard's Grills waiting view reads this.

Why a command and not a hand edit: the answer lives in `.vela.yaml`'s `grills:` block, keyed by the item's ID (an
item of any shape: a heading, a table row, a whole page). A model or a person typing that block by hand gets the
indentation, the quotes or the @ wrong, and the grill then belongs to nobody without anything saying so (Silent
Fallback). Here the handles are checked against the one handle pattern, the ID is checked against the plan, and
the block is rewritten whole through an atomic write.

- With no grill owner the grill belongs to the item's own owner. `--owner` replaces that for this grill only.
- `--join` lists everyone asked to take part and replaces the earlier list; it does not add to it. They see the
  grill under their own filter. `--owner` alone keeps the list; `--join` alone keeps the owner.
- `--clear` removes both, so the grill goes back to the item's owner and nobody is asked.
- The command writes the file and runs no git; the change is committed with the plan like any other edit.

Exit codes: 0 written (or already so); 1 refused, nothing written; 2 the file could not be written.
"""
import pathlib

from vela import commands, grillowners, say
from vela.commands.check import is_reader_copy
from vela.edge import atomic

NAME = "grill owner"


def register(sub):
    top = sub.add_parser("grill", help="who runs a grill, and who is asked to join it")
    each = top.add_subparsers(dest="grill_command", required=True, metavar="COMMAND")
    owner = each.add_parser("owner", help="set the owner of the grill on an item, and who is asked to join",
                            description=__doc__, formatter_class=__import__("argparse").RawDescriptionHelpFormatter)
    owner.add_argument("item", metavar="ID", help="the item's ID (a contract, requirement, epic, app, or a page's ID)")
    owner.add_argument("--vault", default=".", help="vault root (default: current directory)")
    owner.add_argument("--owner", metavar="HANDLE", help="who runs the grill (default: the item's own owner)")
    owner.add_argument("--join", metavar="HANDLE", action="append", help="someone asked to join; repeat for each (replaces the earlier list)")
    owner.add_argument("--clear", action="store_true", help="go back to the item's own owner and ask nobody")
    say.add_output_flags(owner)
    owner.set_defaults(func=run_owner)


def refuse(rule, plain, fix):
    return say.Result(NAME, exit=say.REFUSED, refusals=[say.Refusal(rule, plain, fix, override="none: nothing was written")])


def problem(args, vault, root):
    """A Result refusing the call, or None."""
    if is_reader_copy(root):
        return refuse("grill-reader-copy", "This is a reader copy, so I can't change who runs a grill here.",
                      "Ask the plan's owner to set it, or send it as a proposal.")
    if args.clear and (args.owner or args.join):
        return refuse("grill-clear", "Clearing and setting an owner are two different asks.", "Use --clear alone, or --owner and --join.")
    if not (args.clear or args.owner or args.join):
        return refuse("grill-nothing", "Tell me who runs it or who is asked to join.", "Add --owner <handle>, --join <handle>, or --clear.")
    if args.item not in vault.known_ids():
        return refuse("grill-item", f"I can't find {args.item} in this plan.", "Use the item's ID, such as CON-022 or EPC-036.")
    for value in ([args.owner] if args.owner else []) + list(args.join or []):
        why = grillowners.handle_problem(value)
        if why:
            return refuse("grill-handle", why, "Write a GitHub handle, such as @sam-hadley.")
    return None


def next_entry(args, before):
    owner = grillowners.handle(args.owner) if args.owner else before.owner
    join = [grillowners.handle(j) for j in args.join] if args.join else list(before.join)
    join = [j for j in dict.fromkeys(join) if j != owner]
    return grillowners.Entry("" if args.clear else owner, () if args.clear else join)


def run_owner(args, out):
    from vela import cli
    root = pathlib.Path(args.vault).resolve()
    vault = cli.load_vault(root)
    refused = problem(args, vault, root)
    if refused is not None:
        return commands.emit(refused, args, out, say.Resolver(vault))
    existing, _ = grillowners.read(vault.config)
    entry = next_entry(args, existing.get(args.item, grillowners.Entry()))
    path = root / ".vela.yaml"
    text = path.read_text(encoding="utf-8")
    new = grillowners.with_entry(text, args.item, entry)
    result = say.Result(NAME, data={"id": args.item, "owner": entry.owner, "join": list(entry.join)})
    name = say.Resolver(vault).name(args.item)
    if new != text:
        try:
            atomic.write_atomic(path, new)
        except atomic.WriteFailed as exc:
            return commands.emit(say.Result(NAME, exit=say.FAILED, lines=[say.Line(f"vela grill owner: could not write: {exc}",
                                 plain=f"I couldn't save that ({exc}), so nothing changed.")]), args, out)
        result.wrote = [".vela.yaml"]
    result.lines = [say.Line(f"{args.item}: {describe(entry, plain=False)}", plain=f"{name}: {describe(entry, plain=True)}")]
    return commands.emit(result, args, out, say.Resolver(vault))


def describe(entry, plain):
    said = (lambda h: say.person_words(h)) if plain else (lambda h: h)
    if not entry.owner and not entry.join:
        return "back to the item's own owner, and nobody is asked to join." if plain else "owner: the item's own; join: none"
    owner = f"{said(entry.owner)} runs the grill" if entry.owner else "the item's own owner runs the grill"
    join = f", with {say.names_said([said(j) for j in entry.join])} asked to join" if entry.join else ""
    if plain:
        return f"{owner}{join}."
    own, asked = entry.owner or "the item's own", ", ".join(entry.join) or "none"
    return f"owner: {own}; join: {asked}"
