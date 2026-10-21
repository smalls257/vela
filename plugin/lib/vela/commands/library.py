"""`vela library add <path-or-url> --title T [...]` and `vela library list [--type T] [--json]`: the Library, one place
for everything outside the plan (provider specs, Figma mocks, Confluence pages, Jira, documents).

Why a command and not "copy the file, then add a row": a model that does both by hand forgets one of them, or
commits the whole folder (`git add library/`), or keeps a file the owner never agreed to. This command is the only
way a file gets into `library/`, and it is built to prevent one Violation: **Silent Fallback on consent**. A file
copied into the vault is company material that will be committed with the plan and read by everyone who has the plan,
so keeping it without the lead's yes is the quiet failure; here no yes means exit 3 and nothing written.

- A URL becomes a link row. Vela never opens it; the type is guessed from the address (`library.type_of_url`) and
  `--type` overrides the guess.
- A local file is kept (copied to `library/<folder>/<name>`) only with `--keep-file --yes ^cN`, where ^cN is a capture
  in the open session holding the lead's yes (the same check `vela decide --yes` runs: a person's words, not a bare
  "ok"). A file in `.inbox/` may be kept this way: the copy is committed, the inbox original stays ignored.
- A file over 20 MB asks for a link instead (exit 3); `--force-large` keeps it anyway.
- Nothing is overwritten. A name clash, the same bytes already kept, or the same link already registered is refused
  and the existing item is named.
- A spec file's version is read from its `info.version` unless `--version` says otherwise.
- The row is written by `vela add source` (one path for the register's rules, token stripping included). The commit
  holds exactly the new file and sources.md, staged by exact path through `stagegit`, never a folder.

Exit codes: 0 added (and committed); 1 refused, nothing written; 2 git or the disk failed (what landed is named);
3 the lead's yes (or a choice about a large file) is needed first: nothing was written.

`vela library list` prints the rows grouped by type (spec, design, document, wiki, tracker, link); `--json` shape:
{"command": "library list", "exit": 0, "count": N, "groups": [{"type": "spec", "items": [{"id", "title", "owner",
"date", "kind", "type", "relates": [IDs], "version", "newer", "stored", "location"}]}]}, a type with no rows omitted.
"""
import argparse
import hashlib
import pathlib

from vela import commands, library, say, sourcerows
from vela.commands import add as add_command
from vela.commands import apply as apply_command
from vela.decisions import add_source, consent
from vela.edge import sessiongit, stagegit, vaultgit
from vela.edge.vaultgit import GitUnavailable

NAME = "library"
PLURAL = {"spec": "specs", "design": "designs", "document": "documents", "wiki": "wiki pages", "tracker": "tracker items",
          "link": "links"}


def register(sub):
    top = sub.add_parser("library", help="the Library: add a link or a file, or list what it holds")
    each = top.add_subparsers(dest="library_command", required=True, metavar="COMMAND")
    add = each.add_parser("add", help="add a link, or keep a file in library/ (with the lead's yes), and commit it",
                          description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    add.add_argument("source", help="a URL (a link row) or a path to a local file")
    add.add_argument("--vault", default=".", help="vault root (default: current directory)")
    add.add_argument("--today", help="the date written, YYYY-MM-DD (default: today)")
    add.add_argument("--title", required=True, help="what the lead calls it")
    add.add_argument("--type", dest="source_type", choices=sourcerows.TYPES,
                     help="override the guess (spec, design, document, wiki, tracker, link)")
    add.add_argument("--relates", help="IDs of the items it relates to, separated by spaces")
    add.add_argument("--version", help="a spec's version (a local spec file gives its own info.version)")
    add.add_argument("--owner", help="who owns it (default: the lead's handle)")
    add.add_argument("--date", help="the document's date, YYYY-MM-DD (default: today)")
    add.add_argument("--kind", default="exists", choices=("exists", "intends", "repo"),
                     help="exists (describes what runs today, default), intends (a plan) or repo")
    add.add_argument("--keep-file", action="store_true",
                     help="copy a local file into library/; needs --yes, the lead's yes on record")
    add.add_argument("--yes", metavar="^cN", help="the capture holding the lead's yes to keeping the file")
    add.add_argument("--force-large", action="store_true", help="keep a file over 20 MB anyway")
    say.add_output_flags(add)
    add.set_defaults(func=run_add)
    listing = each.add_parser("list", help="the Library's rows, grouped by type")
    listing.add_argument("--vault", default=".", help="vault root (default: current directory)")
    listing.add_argument("--type", dest="only", choices=sourcerows.TYPES, help="only this type")
    say.add_output_flags(listing)
    listing.set_defaults(func=run_list)


# ------------------------------------------------------------------ list

def run_list(args, out):
    root = pathlib.Path(args.vault).resolve()
    register_path = root / "sources.md"
    if not register_path.is_file():
        return commands.emit(say.Result("library list", exit=say.REFUSED, refusals=[say.Refusal(
            "library-no-register", "There's no Library page in this folder.",
            "Run it from the vault's root, or pass --vault.", override="none: there is nothing to list")]), args, out)
    found = library.rows(register_path.read_text(encoding="utf-8"))
    groups = library.grouped(found, args.only)
    result = say.Result("library list", data={
        "count": sum(len(rows) for _, rows in groups),
        "groups": [{"type": kind, "items": [library.row_json(r) for r in rows]} for kind, rows in groups]})
    if not groups:
        result.lines.append(say.Line("the library is empty.", plain="The library is empty."))
    for kind, rows in groups:
        result.lines.append(say.Line(f"{kind} ({len(rows)})", plain=f"{say.count_words(len(rows), capital=True)} "
                                     f"{PLURAL[kind] if len(rows) != 1 else kind}: " + say.names_said([r.title for r in rows]) + "."))
        result.lines += [say.Line(f"  {r.id}  {r.title}  {r.version or '-'}  {r.stored or r.location}", plain="")
                         for r in rows]
    return commands.emit(result, args, out)


# ------------------------------------------------------------------ add

def refuse(rule, plain, fix, override="none: vela never overwrites a library file"):
    return say.Result("library add", exit=say.REFUSED, refusals=[say.Refusal(rule, plain, fix, override=override)])


def needs_lead(command, plain, text, choices):
    return say.Result("library add", exit=say.NEEDS_LEAD, needs_lead=choices, lines=[say.Line(text, plain=plain)])


class Plan:
    """What `add` has worked out before touching anything: the row's fields and, for a kept file, where it goes."""
    def __init__(self, item, source=None, stored=None, data=b""):
        self.item, self.source, self.stored, self.data = item, source, stored, data


def digest(data):
    return hashlib.sha256(data).hexdigest()


def kept_files(root):
    folder = root / sourcerows.LIBRARY
    return sorted(p for p in folder.rglob("*") if p.is_file()) if folder.is_dir() else []


def clash(root, stored, data):
    """The library file this one would collide with (same path, or the same bytes under another name), or None."""
    target = root / stored
    if target.exists():
        return stored
    size = len(data)
    for path in kept_files(root):
        if path.stat().st_size == size and digest(path.read_bytes()) == digest(data):
            return path.relative_to(root).as_posix()
    return None


def registered_link(root, location):
    """The ID of the register row that already holds this address, or None."""
    wanted = add_source.stripped(location).rstrip("/")
    for row in library.rows((root / "sources.md").read_text(encoding="utf-8")):
        if row.location.rstrip("/") == wanted:
            return row.id
    return None


def item_of(args, source_type, version, stored, location):
    item = {"type": "source", "title": args.title, "kind": args.kind, "source_type": source_type}
    for key, value in (("owner", args.owner), ("date", args.date), ("relates", args.relates), ("version", version),
                       ("stored", stored), ("location", location)):
        if value:
            item[key] = value
    return item


def link_plan(root, args):
    """(Plan, None) for a URL, or (None, the refusal)."""
    existing = registered_link(root, args.source)
    if existing:
        return None, refuse("library-duplicate", "That link is already in the library.",
                            f"{existing} holds {add_source.stripped(args.source)}; nothing was added.",
                            override="none: add it under another address if it is a different page")
    source_type = args.source_type or library.type_of_url(args.source)
    return Plan(item_of(args, source_type, args.version, "", args.source)), None


def file_plan(root, args):
    """(Plan, None) for a local file, (None, a Result) to stop before any write."""
    path = pathlib.Path(args.source).expanduser()
    if not path.is_file():
        return None, refuse("library-no-file", "I couldn't find that file.", f"{args.source} is not a file on this machine.",
                            override="none: nothing to add")
    data = path.read_bytes()
    text = data.decode("utf-8", "replace") if len(data) < library.MAX_BYTES else ""
    found_type, found_version = library.type_of_file(path.name, text)
    source_type = args.source_type or found_type
    version = args.version or (library.version_cell(found_version) if source_type == "spec" else "")
    name = library.stored_name(source_type, args.title, path.name)
    stored = f"{sourcerows.LIBRARY}/{sourcerows.folder_for(source_type)}/{name}"
    where = clash(root, stored, data)
    if where:
        return None, refuse("library-clash", f"That is already in the library as {where}.",
                            f"{where} is there already (same name or same contents), so nothing was kept. Rename the "
                            "title, or leave the existing file.")
    return Plan(item_of(args, source_type, version, stored, ""), path, stored, data), None


def large_choice(plan, size):
    mb = size / (1024 * 1024)
    return needs_lead("library add", f"That file is about {mb:.0f} megabytes, which is a lot to keep in the plan's folder. "
                      "A link to where it lives is usually better. Link it, or keep the file anyway?",
                      f"vela library add: {plan.source} is {size} bytes, over the 20 MB limit. Add it as a link "
                      "(drop --keep-file and pass its URL), or pass --force-large to keep it.",
                      [{"choice": "link", "plain": "add a link instead"},
                       {"choice": "keep", "command": "--force-large", "plain": "keep the file anyway"}])


def yes_ask(plan):
    return needs_lead("library add", f"“{plan.item['title']}” is company material. Keeping it means it's saved into the plan "
                      "and goes wherever the plan goes, to everyone who has it. Is it all right to keep it?",
                      f"vela library add: {plan.source} is company material; keeping it copies it to {plan.stored} and commits it with the plan. "
                      "Ask the lead; when they say yes, capture it and run again with --keep-file --yes ^cN. "
                      "To register it without keeping the file: vela add source --location 'local only'.",
                      [{"choice": "keep", "command": "--keep-file --yes ^cN", "plain": "keep the file in the plan"},
                       {"choice": "skip", "plain": "leave it out of the plan"}])


def check_yes(root, args):
    """None when the lead's yes is on record in the open session, else the Result that stops the add."""
    record, early = apply_command.find_record(root)
    if early is not None:
        return early
    found = consent.a_yes(args.yes, record)
    if found is None:
        return None
    return say.Result("library add", exit=say.REFUSED, refusals=[found])


def copy_in(root, plan):
    """Create the file exclusively: a file that appears between the check and now is a clash, never overwritten."""
    target = root / plan.stored
    target.parent.mkdir(parents=True, exist_ok=True)
    with open(target, "xb") as handle:
        handle.write(plan.data)
    return target


def run_add(args, out):
    from vela import cli
    root = pathlib.Path(args.vault).resolve()
    try:
        today = cli.parse_today(args.today)[0]
        vault = cli.load_vault(root)
    except cli.ToolError as exc:
        return commands.emit(add_command.failed(str(exc), "I couldn't read the vault, so I added nothing."), args, out)
    result = add_to_library(root, today, vault, args)
    return commands.emit(result, args, out, say.Resolver(vault))


def add_to_library(root, today, vault, args):
    local = not library.is_url(args.source)
    plan, stop = file_plan(root, args) if local else link_plan(root, args)
    if stop is not None:
        return stop
    if local:
        stop = consent_stop(root, args, plan)
        if stop is not None:
            return stop
    reader = sessiongit.is_read_copy(root)
    if local and reader:
        return refuse("library-reader", "This is your copy, so I can't keep a file in it.",
                      "A read copy has no git; add a link instead, or keep the file in the owner's vault.",
                      override="none: files are kept in the owner's vault")
    if not reader:
        stop = dirty_register(root)
        if stop is not None:
            return stop
    return write_and_commit(root, today, vault, plan, reader)


def consent_stop(root, args, plan):
    if len(plan.data) > library.MAX_BYTES and not args.force_large:
        return large_choice(plan, len(plan.data))
    if not (args.keep_file and args.yes):
        return yes_ask(plan)
    return check_yes(root, args)


def dirty_register(root):
    """sources.md edited and not yet saved would ride into this commit; stop and say so."""
    try:
        dirty = vaultgit.status_paths(root, pathspec=("sources.md",))
    except GitUnavailable as exc:
        return add_command.failed(f"git can't answer: {exc}", "I couldn't check the plan's saved state, so I added nothing.")
    if dirty:
        return refuse("library-register-unsaved", "The Library page has changes that aren't saved yet, so I haven't added anything.",
                      "sources.md has uncommitted edits, and this commit would carry them. Save the session's work "
                      "(vela close stage --checkpoint), then add again.", override="none: the commit holds only this item")


def write_and_commit(root, today, vault, plan, reader):
    copied = copy_in(root, plan) if plan.stored else None
    added = add_command.file_new(root, today, vault, add_command.with_owner(dict(plan.item), root))
    added.command = "library add"
    if added.exit != say.DONE:
        if copied is not None:
            copied.unlink()  # we created it a moment ago; leaving it would be a file with no row
        return added
    paths = ["sources.md"] + ([plan.stored] if plan.stored else [])
    data = dict(added.data, stored=plan.stored or "", location=plan.item.get("location", ""),
                title=plan.item["title"], commit=None)
    result = say.Result("library add", wrote=paths, data=data, lines=list(added.lines))
    if reader:
        result.lines.append(say.Line("read copy: nothing committed.", plain="This is your copy, so I haven't saved it with git."))
        return result
    message = f"Add to the library: {plan.item['title']}"
    try:
        stagegit.stage(root, paths)
        data["commit"] = stagegit.commit(root, message, paths)
    except GitUnavailable as exc:
        return add_command.failed(f"the row and file are written ({', '.join(paths)}) but git would not commit: {exc}",
                                  "I added it, but couldn't save it with git; the files are in place.")
    kept = "kept the file and " if plan.stored else ""
    result.lines.append(say.Line(f"committed {data['commit']}: {message}",
                                 plain=f"I've {kept}added “{plan.item['title']}” to the library and saved it."))
    return result
