"""`vela apply <file> [--vault V] [--json|--for-lead]` and `vela apply --schema KIND` (overhaul Task 4, plan 4).

The model never writes the vault's grammar. The CLI drafts a decision file (`.vela/decisions/<session>/<seq>-<kind>.json`)
with every computable field filled and every judgment field null with a hint; the skill asks the lead; the model
points each judgment field at the capture holding the lead's words; `apply` validates the whole file and then writes
every file or none. "Filing is the tool's work, not the lead's": a page half-filed by hand is a Leaky Narrative the
lead ends up reading, and a batch that half-applied is a Silent Fallback (`vela/decisions/__init__.py` says how the
core prevents it). The consent checks are a Sensor on what the record says, not proof the lead said it
(`vela/decisions/consent.py`).

Exit codes (plan 3.1):
0  applied; or already applied (the file carries `applied`; nothing is written again); or `--schema` printed;
1  refused: every reason, plainly, and nothing written. `--json` gives each as {refused, rule, plain, fix, override};
   `--for-lead` prints only what the lead hears. Also: no session open, or a write outside the vault;
2  the tool failed: the file can't be read, the vault can't be loaded, or the disk refused a write (what landed is
   named);
3  several sessions are open: nothing judged, the choices printed (`needs_lead`).

After a successful apply the file gets `"applied": {"pages": <sha256 of what was written>, "captures": <the record's
capture count>}`. A content hash, not a commit, because a reader copy has no commits. `apply` runs no git in either
role (committing is the checkpoint's and close's work); in a reader copy it says nothing was committed.
"""
import json
import pathlib

from vela import commands, decisions, say
from vela.decisions import record as records, schema
from vela.edge import apply as disk
from vela.edge import atomic, sessiongit

NAME = "apply"


def register(sub):
    parser = sub.add_parser("apply", help="file a decision file the CLI drafted: every write or none")
    parser.add_argument("file", nargs="?", help="the decision file (.vela/decisions/<session>/<seq>-<kind>.json)")
    parser.add_argument("--schema", metavar="KIND", help="print the fields KIND takes, with one example, and stop")
    parser.add_argument("--vault", default=".", help="vault root or reader workspace (default: current directory)")
    say.add_output_flags(parser)
    parser.set_defaults(func=run)


def run(args, out):
    if args.schema:
        return commands.emit(schema_result(args.schema, say.mode_of(args) == "for-lead"), args, out)
    if not args.file:
        return commands.emit(failed("give a decision file, or --schema KIND",
                                    "I wasn't told which file to file."), args, out)
    return apply_file(pathlib.Path(args.file), pathlib.Path(args.vault).resolve(), args, out)


def schema_result(kind, for_lead=False):
    """The fields KIND takes and one example. The schema is for the model, not the lead, so `--for-lead` says only
    that."""
    module, refusal = decisions.kind_module(kind)
    if refusal is not None:
        return say.Result(NAME, exit=say.REFUSED, refusals=[refusal])
    shape = module.SCHEMA
    lines = [say.Line(f"{kind}: the fields one item takes (* = judgment, from the lead's answer; ! = required)",
                      plain="These are the fields that kind of decision takes; they're for me to fill in.")]
    if for_lead:
        return say.Result(NAME, lines=lines, data={"kind": kind, "schema": shape.as_json()})
    for name, hint in shape.fields.items():
        marks = ("*" if name in shape.judgment else " ") + ("!" if name in shape.required else " ")
        lines.append(say.Line(f"  {marks} {name}: {hint}"))
    lines.append(say.Line("judgment fields point at captures (\"^c31\"), never at the lead's words. Example item:"))
    lines.append(say.Line(json.dumps(shape.example, indent=2, ensure_ascii=False)))
    return say.Result(NAME, lines=lines, data={"kind": kind, "schema": shape.as_json()})


def failed(text, plain):
    return say.Result(NAME, exit=say.FAILED, lines=[say.Line(f"vela apply: {text}", plain=plain)])


def refused(refusals, data=None):
    return say.Result(NAME, exit=say.REFUSED, refusals=list(refusals), data=data or {})


def apply_file(path, root, args, out):
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        return commands.emit(failed(f"can't read {path}: {exc}", "I couldn't read the file with your answers."),
                             args, out)
    decision, problems = decisions.load(text)
    if problems:
        return commands.emit(refused(problems), args, out)
    if decision.applied:
        return commands.emit(say.Result(NAME, lines=[say.Line(
            f"already applied: {path.name} was filed before; nothing written.",
            plain="Those were already filed, so I left everything as it was.")], data={"applied": decision.applied}),
            args, out)
    reader = sessiongit.is_read_copy(root)
    record, early = find_record(root)
    if early is not None:
        return commands.emit(early, args, out)
    from vela import cli  # the shell loads the vault; this module wires it
    try:
        vault = cli.load_vault(root)
    except cli.ToolError as exc:
        return commands.emit(failed(str(exc), "I couldn't read the vault, so I filed nothing."), args, out)
    result = file_decision(decision, path, root, vault, record, reader)
    return commands.emit(result, args, out, say.Resolver(vault))


def find_record(root):
    """(OpenRecord, None), or (None, the Result to print instead). Read from the working tree, so no git runs."""
    rec, opened = records.open_record(sessiongit.folder_records(root))
    if rec is not None:
        return rec, None
    if not opened.several:
        why = f" ({'; '.join(opened.problems)})" if opened.problems else ""
        return None, say.Result(NAME, exit=say.FAILED if opened.problems else say.REFUSED, lines=[say.Line(
            f"No session is open, so there is nothing to file into{why}.",
            plain="No session is open, so there's nowhere to file your answers.")])
    choices = [{"id": r.id, "topic": r.title, "date": r.date} for r in opened.records]
    return None, say.Result(NAME, exit=say.NEEDS_LEAD, needs_lead=choices, lines=[say.Line(
        f"{len(choices)} sessions are open in this folder; nothing filed. Apply on the branch of the one it is for.",
        plain=f"{len(choices)} sessions are open here, so I haven't filed anything. Which one is this for?")])


def file_decision(decision, path, root, vault, record, reader):
    staged = decisions.Staged(vault, disk.reader(root))
    try:
        writes, refusals = decisions.plan(decision, staged, record)
        if refusals:
            return refused(refusals)
        new_file = decisions.applied_text(decision, writes, decisions.record_after(record, staged))
        written = disk.write_all(root, writes, {path.resolve(): new_file})
    except disk.OutsideVault as exc:
        return refused([say.Refusal("apply-outside-vault", "One of those would have changed a file outside the vault, "
                                                           "so I filed nothing.",
                                    f"{exc}. Point the item at a page inside the vault.",
                                    override="none: vela only writes inside the vault")])
    except atomic.WriteFailed as exc:
        landed = ", ".join(str(p) for p in exc.written) or "nothing"
        return failed(f"the disk refused a write ({exc}); written: {landed}; not written: "
                      f"{', '.join(str(p) for p in exc.unwritten)}",
                      "The disk refused part of the filing; I've listed which files changed.")
    return filed_result(decision, written, vault, record, reader)


def name_of(path, vault, record):
    if path == record.path:
        return "the session record"
    for page in vault.pages:
        if page.path == path:
            return str(page.meta.get("title") or pathlib.PurePosixPath(path).stem.replace("-", " "))
    return pathlib.PurePosixPath(path).stem.replace("-", " ")


def filed_result(decision, written, vault, record, reader):
    count = len(decision.items)
    words = schema.KIND_WORDS.get(decision.kind, f"{decision.kind} items")
    names = [name_of(p, vault, record) for p in written]
    lines = [say.Line(f"applied: {count} {decision.kind} item{'' if count == 1 else 's'}; wrote "
                      f"{', '.join(written) or 'nothing'}.",
                      plain=f"I've filed {count} {words}" + (f", in {join(names)}." if names else "."))]
    if reader:
        lines.append(say.Line("read copy: nothing committed (no git runs here); the proposal carries the changes.",
                              plain="This is a read copy, so nothing was committed; the changes go to the owner "
                                    "with your proposal."))
    return say.Result(NAME, lines=lines, wrote=written, data={"applied": True, "reader": reader, "kind": decision.kind})


def join(names):
    return names[0] if len(names) == 1 else ", ".join(names[:-1]) + " and " + names[-1]
