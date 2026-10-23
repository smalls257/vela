"""`vela records verify <id>`, `vela records seal <id>` and `vela records backup --to <place>`: a session's private notes.

The Violation these exist to prevent is a Black Box in the record: the notes never leave their machine, so the plan
can't show whether the file on disk is the one the close fingerprinted. `verify` answers that for this machine's part
and nothing else (`parts(meta)[part_of(private)]`); another machine's part is its own to check. `seal` is the repair
for a part the close never fingerprinted (a session that ended without `close finish`): it fills this machine's own
pending key, refuses to overwrite a different fingerprint (that would hide an edit), and commits only the stub.

`backup` is the one sanctioned copy of the notes off this machine, to a place the lead picks. The notes live nowhere
else, so a lost laptop would lose the plan's reasoning (a Silent Fallback of its own: nothing would say so until it
mattered). It refuses a target inside the plan or its git repo before writing anything, since the copy would be
committed, and it never overwrites: a taken name gets -2, -3.

Exit codes: 0 the part matches (or was sealed, or was already); 1 it changed since, isn't fingerprinted yet (verify),
or holds a different fingerprint (seal); 2 no private file here, no stub, or git failed.
"""
import pathlib

from vela import commands, privaterecord, publish, say
from vela.edge import plans, sessiongit, vaultgit

VERIFY, SEAL, BACKUP = "records verify", "records seal", "records backup"
INSIDE_THE_PLAN = "That folder is inside the plan, so the copy would be committed. Pick a folder outside it."
NOTHING_TO_BACK_UP = "There are no session notes here to back up."


def register(sub):
    top = sub.add_parser("records", help="a session's private notes: check or fill this machine's fingerprint")
    verbs = top.add_subparsers(dest="records_command", required=True, metavar="COMMAND")
    for name, helps, func in (("verify", "check that this machine's notes are the ones the close fingerprinted",
                               cmd_verify),
                              ("seal", "fingerprint this machine's notes in the stub, when the close never did",
                               cmd_seal)):
        each = verbs.add_parser(name, help=helps)
        each.add_argument("id", metavar="ID", help="the session's id (its file name without .md)")
        each.add_argument("--vault", default=".", help="vault root (default: current directory)")
        say.add_output_flags(each)
        each.set_defaults(func=func)
    backup = verbs.add_parser("backup", help="copy every session's notes to a folder or .zip outside the plan")
    backup.add_argument("--to", required=True, help="a folder to copy into, or a .zip to write; it must be outside the plan")
    backup.add_argument("--vault", default=".", help="vault root (default: current directory)")
    backup.add_argument("--today", help="the date in the copy's name, YYYY-MM-DD (default: today)")
    say.add_output_flags(backup)
    backup.set_defaults(func=cmd_backup)


def failed(command, text, plain=None):
    return say.Result(command, exit=say.FAILED, lines=[say.Line(f"vela: {text}", plain=plain or text)])


def load(command, root, record_id):
    """(notes, stub, None), or (None, None, the Result that says why not)."""
    notes = sessiongit.private_text(root, record_id)
    if notes is None:
        words = str(sessiongit.PrivateMissing(record_id))
        return None, None, failed(command, words)
    try:
        stub = (root / privaterecord.stub_path(record_id)).read_text(encoding="utf-8")
    except FileNotFoundError:
        return None, None, failed(command, f"there is no committed record for {record_id} in this plan.",
                                  "This plan has no record of that session.")
    return notes, stub, None


def committed_on(root, record_id, stub):
    """The day the stub last changed, as 'October 22, 2026'. A reader copy runs no git, so it uses the stub's date."""
    if sessiongit.is_read_copy(root):
        day = str(privaterecord.stub_meta(stub).get("date", ""))
    else:
        day = vaultgit.git_out(root, "log", "-1", "--format=%cs", "--", privaterecord.stub_path(record_id))
    return say.date_words(day)


def cmd_verify(args, out):
    root = pathlib.Path(args.vault).resolve()
    try:
        result = verify(root, args.id)
    except (ValueError, vaultgit.GitUnavailable) as exc:
        result = failed(VERIFY, str(exc))
    return commands.emit(result, args, out)


def verify(root, record_id):
    notes, stub, early = load(VERIFY, root, record_id)
    if early is not None:
        return early
    part = privaterecord.part_of(notes)
    held = privaterecord.parts(privaterecord.stub_meta(stub)).get(part, privaterecord.PENDING)
    if held == privaterecord.PENDING:
        text = f"Part {part} isn't fingerprinted yet."
        return say.Result(VERIFY, exit=say.REFUSED, lines=[say.Line(f"vela records verify: {text}", plain=text)],
                          data={"id": record_id, "part": part, "matches": False})
    if held != privaterecord.fingerprint(notes):
        text = f"Part {part} changed since it was committed."
        return say.Result(VERIFY, exit=say.REFUSED, lines=[say.Line(f"vela records verify: {text}", plain=text)],
                          data={"id": record_id, "part": part, "matches": False})
    text = f"Part {part} matches what was committed on {committed_on(root, record_id, stub)}."
    return say.Result(VERIFY, lines=[say.Line(text)], data={"id": record_id, "part": part, "matches": True})


def cmd_seal(args, out):
    root = pathlib.Path(args.vault).resolve()
    try:
        result = seal(root, args.id)
    except (ValueError, OSError, vaultgit.GitUnavailable) as exc:
        result = failed(SEAL, str(exc))
    return commands.emit(result, args, out)


def seal(root, record_id):
    notes, stub, early = load(SEAL, root, record_id)
    if early is not None:
        return early
    part, fingerprint = privaterecord.part_of(notes), privaterecord.fingerprint(notes)
    held = privaterecord.parts(privaterecord.stub_meta(stub)).get(part, privaterecord.PENDING)
    data = {"id": record_id, "part": part}
    if held == fingerprint:
        text = f"Part {part} is already fingerprinted, so nothing changed."
        return say.Result(SEAL, lines=[say.Line(text)], data=data)
    if held != privaterecord.PENDING:
        text = (f"Part {part} already has a different fingerprint, so I haven't replaced it: the notes changed after "
                "they were committed.")
        return say.Result(SEAL, exit=say.REFUSED, lines=[say.Line(f"vela records seal: {text}", plain=text)], data=data)
    rel = privaterecord.stub_path(record_id)
    sessiongit.write_text(root, rel, privaterecord.with_part(stub, part, fingerprint))
    if not sessiongit.is_read_copy(root):
        sessiongit.commit(root, f"Seal part {part} of {record_id}", [rel])
    return say.Result(SEAL, lines=[say.Line(f"Part {part} is fingerprinted now.")], wrote=[rel], data=data)


def cmd_backup(args, out):
    from vela import cli  # lazy: cli imports the command modules
    root = pathlib.Path(args.vault).resolve()
    try:
        today = cli.parse_today(args.today)[0]
        result = backup(root, pathlib.Path(args.to).expanduser(), today, cli.load_config(root))
    except (cli.ToolError, OSError) as exc:
        result = failed(BACKUP, str(exc))
    return commands.emit(result, args, out)


def refused(text):
    return say.Result(BACKUP, exit=say.REFUSED, lines=[say.Line(f"vela records backup: {text}", plain=text)])


def inside(target, folder):
    return target == folder or folder in target.parents


def backup(root, to, today, config):
    """Copy `sessions/private/*.md` into `<to>/vela-sessions-<initiative>-<today>/`, or into a zip when `to` ends in
    .zip. Nothing is written until the target is known to be outside the plan and its repo."""
    target = to.resolve()
    top = plans.repo_root(root)
    if inside(target, root) or (top is not None and inside(target, top)):
        return refused(INSIDE_THE_PLAN)
    notes = {path.name: path.read_bytes() for path in sorted((root / privaterecord.PRIVATE_DIR).glob("*.md"))
             if path.is_file() and not path.is_symlink()}
    if not notes:
        return refused(NOTHING_TO_BACK_UP)
    name = f"vela-sessions-{publish.slug(str(config.get('title') or config['initiative']))}-{today}"
    if target.suffix.lower() == ".zip":
        placed = write_zip(target, name, notes)
    else:
        placed = write_folder(target, name, notes)
    count = len(notes)
    text = f"Copied {count} session note{'s' if count != 1 else ''} to {placed}."
    return say.Result(BACKUP, lines=[say.Line(text)], data={"count": count, "to": str(placed)})


def claimed(make):
    """True when `make()` created its file or folder; False when the name was already taken. The creation is the claim,
    so two backups at once cannot choose the same name."""
    try:
        make()
    except FileExistsError:
        return False
    return True


def write_folder(parent, name, notes):
    """The new folder `parent/name`, or `name-2`, `name-3` when that is taken."""
    parent.mkdir(parents=True, exist_ok=True)
    for n in range(1, 10000):
        folder = parent / (name if n == 1 else f"{name}-{n}")
        if claimed(folder.mkdir):
            for filename, data in notes.items():
                (folder / filename).write_bytes(data)
            return folder
    raise OSError(f"every name from {name} to {name}-9999 is taken in {parent}")


def write_zip(wanted, name, notes):
    """The zip `wanted`, or `<stem>-2.zip`, `<stem>-3.zip` when that exists. Exclusive create, so it never overwrites."""
    wanted.parent.mkdir(parents=True, exist_ok=True)
    data = publish.zip_bytes(notes, name)
    for n in range(1, 10000):
        path = wanted if n == 1 else wanted.with_name(f"{wanted.stem}-{n}{wanted.suffix}")
        if claimed(lambda: path.open("xb").close()):
            path.write_bytes(data)
            return path
    raise OSError(f"every name from {wanted.stem} to {wanted.stem}-9999 is taken in {wanted.parent}")
