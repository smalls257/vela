"""`vela add TYPE --field VALUE ... [--vault V] [--today D] [--json|--for-lead]`: one new item, numbered and written in
one step (overhaul Task 15, plan 3.2). The same as `vela apply` of a decision file holding that one `add` item: the
flags build the item, `vela.decisions.plan` validates and writes it through the `add` kind, and the item is kept as an
applied decision file under `.vela/decisions/<session>/`, so what was filed can be read back like any other.

Types (`vela add TYPE --help` lists each one's fields, and `vela.decisions.add_<type>` says why each rule holds):
unknown, constraint, subject, adr, epic, slice, app-stub, contract, fr, source, cut.

Why a command and not only a file: grill's "File each decision as its branch closes" ("a new unknown mid-grill"), boundary, releases and requirements
write one item at a time while the lead is talking, and drafting a file for one item is a step a model skips. "New
IDs come from vela next-id, so an open session branch never hands out the same number twice": this command reads
`main` and every session branch (`edge/idgit.py`) and says the ID it took, so nothing is numbered by hand.

`vela add unknown --blocks X` also says which agenda items the unknown now holds up. They stay on the agenda; settling
one notes the open question.

A missing `--owner` is the lead's handle (`.vela/handle`, as `vela whoami` keeps it): never asked for.

Exit codes (plan 3.1):
0  added; the ID taken and the pages written are printed (`--json`: `id`, `wrote`, `now_blocks`, `notices`);
1  refused: every reason, plainly, and nothing written; also no session open;
2  the tool failed: the vault or git can't be read, or the disk refused a write (what landed is named);
3  several sessions are open: nothing written, the choices printed (`needs_lead`).

It runs no git that writes: committing is the checkpoint's and close's work. In a reader copy no git runs at all
(there are no branches to count), and it says nothing was committed.
"""
import argparse
import pathlib

from vela import commands, decisions, say
from vela.commands import apply as apply_command
from vela.decisions import add, add_fr, add_unknown, schema, textedit
from vela.edge import apply as disk
from vela.edge import atomic, idgit, sessiongit
from vela.edge.vaultgit import GitUnavailable

NAME = "add"
LISTS = ("blocks", "apps", "delivers", "consumes", "flows", "trace", "concerns", "after", "rejected", "consumers",
         "criteria", "traces")
SUMMARY = {"unknown": "an open question with an owner and what it blocks (an ask-by date only if the lead gave one)",
           "constraint": "a row on the constraints page: something the initiative can't change",
           "subject": "an outside party or value held for customers, with its required facts",
           "adr": "a decision record's skeleton, linked from the decisions page",
           "epic": "a new epic's skeleton, or a criterion added with the next AC number and its Trace line",
           "slice": "a slice page: one journey, proven end to end",
           "app-stub": "a stub page for a new or changed app of the picked cut",
           "contract": "a contract with its required bullets on the provider's page",
           "fr": "a functional requirement, numbered after the highest",
           "source": "a row in the sources register (a token in a repo URL is stripped)",
           "cut": "the picked cut, with its apps and Options considered"}
PREFIXES = {"unknown": "UNK", "constraint": "CST", "adr": "ADR", "epic": "EPC", "slice": "SLC", "contract": "CON",
            "source": "SRC"}


def register(sub):
    parser = sub.add_parser("add", help="add one new item (an unknown, a constraint, an app stub, ...): numbered past "
                                        "every open branch and written in the vault's grammar")
    each = parser.add_subparsers(dest="add_type", required=True, metavar="TYPE")
    for kind, module in add.TYPES.items():
        one = each.add_parser(kind, help=SUMMARY[kind], description=module.__doc__,
                              formatter_class=argparse.RawDescriptionHelpFormatter)
        one.add_argument("--vault", default=".", help="vault root or reader workspace (default: current directory)")
        one.add_argument("--today", help="the date written (Opened, and the day on a record line), YYYY-MM-DD (default: today)")
        for field, hint in module.FIELDS.items():
            flag = "--" + getattr(module, "FLAGS", {}).get(field, field.replace("_", "-"))
            if field in LISTS:
                one.add_argument(flag, dest=f"f_{field}", action="append", metavar=field.upper(),
                                 help=f"{hint} (repeat for each)".replace("%", "%%"))
            else:
                one.add_argument(flag, dest=f"f_{field}", metavar=field.upper(), help=hint.replace("%", "%%"))
        say.add_output_flags(one)
        one.set_defaults(func=run)


def item_from(args, root):
    module = add.TYPES[args.add_type]
    item = {"type": args.add_type}
    for field in module.FIELDS:
        value = getattr(args, f"f_{field}", None)
        if value is None:
            continue
        item[field] = [v.split(",") for v in value] if field == "traces" else value
    return with_owner(item, root)


def with_owner(item, root):
    """A missing owner is the lead's handle (`.vela/handle`), never asked for."""
    module = add.TYPES[item["type"]]
    if "owner" in module.FIELDS and not item.get("owner") and item["type"] != "subject":
        handle = sessiongit.read_handle(root)
        if handle:
            item["owner"] = "@" + handle.lstrip("@")
    return item


def new_ident(item, view):
    """The ID the item will take, worked out on the same view `apply` numbers from, so the two agree."""
    kind = item["type"]
    if item.get("id"):
        return item["id"]
    if kind == "subject":
        return textedit.next_id(view, item.get("subject_type") or "PTY")
    if kind == "app-stub":
        return f"APP-{item.get('slug')}"
    if kind == "fr":
        texts = list(textedit.texts(view).values()) + list(view.branch_texts or ())
        return f"{item.get('capability')}.FR{add_fr.highest(str(item.get('capability')), texts) + 1}"
    return textedit.next_id(view, PREFIXES[kind]) if kind in PREFIXES else None


def failed(text, plain):
    return say.Result(NAME, exit=say.FAILED, lines=[say.Line(f"vela add: {text}", plain=plain)])


def run(args, out):
    from vela import cli
    root = pathlib.Path(args.vault).resolve()
    try:
        today = cli.parse_today(args.today)[0]
        vault = cli.load_vault(root)
    except cli.ToolError as exc:
        return commands.emit(failed(str(exc), "I couldn't read the vault, so I added nothing."), args, out)
    result = file_new(root, today, vault, item_from(args, root))
    if args.add_type == "app-stub" and result.exit == say.DONE:
        from vela.commands import size
        result.lines += size.announce(root, cli.load_vault(root))  # a new app may be the one that grows the plan
    return commands.emit(result, args, out, say.Resolver(vault))


def file_new(root, today, vault, item):
    """Number `item` past every open branch and write it into the open session: the whole of `vela add` after its flags
    are read. `vela library add` calls it too, so a Library row is written by one path (no second copy of the rules)."""
    record, early = apply_command.find_record(root)
    if early is not None:
        return early
    reader = sessiongit.is_read_copy(root)
    try:
        staged = textedit.attach(decisions.Staged(vault, disk.reader(root)), today, idgit.branch_texts(root),
                               lead=apply_command.lead_of(root))
    except GitUnavailable as exc:
        return failed(f"couldn't read the other branches' numbers: {exc}",
                      "I couldn't check which numbers other sessions hold, so I added nothing.")
    return file_item(item, root, staged, record, reader)


def file_item(item, root, staged, record, reader):
    ident = new_ident(item, staged)
    before = textedit.record_text(record, staged)
    raw = {"version": schema.VERSION, "kind": "add", "session": record.id, "items": [item]}
    decision = decisions.Decision("add", record.id, [item], raw)
    folder = root / schema.FOLDER / record.id
    existing = sorted(p.name for p in folder.glob("*.json")) if folder.is_dir() else []
    path = root / schema.draft_path(record.id, existing, "add")
    try:
        writes, refusals = decisions.plan(decision, staged, record)
        if refusals:
            return say.Result(NAME, exit=say.REFUSED, refusals=refusals)
        filed = decisions.applied_text(decision, writes, decisions.record_after(record, staged))
        path.parent.mkdir(parents=True, exist_ok=True)
        written = disk.write_all(root, writes, {path: filed})
    except disk.OutsideVault as exc:
        return say.Result(NAME, exit=say.REFUSED, refusals=[say.Refusal(
            "apply-outside-vault", "That would have changed a file outside the vault, so I added nothing.",
            f"{exc}.", override="none: vela only writes inside the vault")])
    except atomic.WriteFailed as exc:
        landed = ", ".join(str(p) for p in exc.written) or "nothing"
        return failed(f"the disk refused a write ({exc}); written: {landed}",
                      "The disk refused part of that; I've listed which files changed.")
    blocks = add_unknown.now_blocks(dict(item, id=ident), before) if item["type"] == "unknown" else []
    return report(item, ident, written, blocks, staged, reader)


def report(item, ident, written, blocks, view, reader):
    kind = item["type"]
    name = textedit.name_of(view, ident) if ident and textedit.find(view, ident) else \
        (item.get("name") or item.get("title") or "")
    lines = [say.Line(f"added {kind} {ident or item.get('name', '')}: wrote {', '.join(written)}.",
                      plain=f"I've written down {_plain_name(kind, name)}.")]
    if kind == "unknown":
        ask_by = _fact(view, ident, "Ask by")
        lines.append(say.Line(f"ask by: {ask_by or 'no date set'}",
                              plain=f"I've set it to be asked by {ask_by}." if ask_by else
                              "There's no date to ask it by yet. Do you want one?"))
    if blocks:
        names = [textedit.name_of(view, b) for b in blocks]
        lines.append(say.Line(f"now blocks on the agenda: {', '.join(blocks)} (they stay on it; settling notes the question)",
                              plain=f"It holds up {apply_command.join(names)}. "
                                    f"{'It stays' if len(names) == 1 else 'They stay'} on the agenda, and settling "
                                    f"{'it' if len(names) == 1 else 'them'} notes the question as still open."))
    notices = add.notices(item)
    lines += [say.Line(n) for n in notices]
    if reader:
        lines.append(say.Line("read copy: nothing committed (no git runs here); the proposal carries the changes.",
                              plain="This is your copy, so nothing was committed; the changes go to the owner "
                                    "with your proposal."))
    return say.Result(NAME, lines=lines, wrote=written,
                      data={"id": ident, "type": kind, "now_blocks": blocks, "notices": notices, "reader": reader})


def _plain_name(kind, name):
    words = {"unknown": "the question", "constraint": "the constraint", "subject": "", "adr": "a decision record for",
             "epic": "the epic", "slice": "the slice", "app-stub": "a first page for", "contract": "the contract",
             "fr": "the requirement", "source": "the source", "cut": "the cut you picked,"}
    lead_in = words.get(kind, "")
    return f"{lead_in} {_quoted(name)}".strip()


def _quoted(name):
    return f"“{name}”" if name else "it"


def _fact(view, ident, label):
    found = textedit.find(view, ident)
    if found is None:
        return ""
    text = view.text(found[0])
    start = text.find(f"### {ident}")
    for line in text[start:].split("\n")[1:]:
        if line.startswith("#"):
            break
        if line.startswith(f"- **{label}:**"):
            return line.split(":**", 1)[1].strip()
    return ""

