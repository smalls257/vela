"""`vela records verify <id>`, `seal <id>` and `split`: the committed fingerprint of a session's private notes, and
moving an older plan over to private notes.

The Violation these exist to prevent is a Black Box in the record: the notes never leave their machine, so the plan
can't show whether the file on disk is the one the close fingerprinted. `verify` answers that for this machine's part
and nothing else (`parts(meta)[part_of(private)]`); another machine's part is its own to check. `seal` is the repair
for a part the close never fingerprinted (a session that ended without `close finish`): it fills this machine's own
pending key, refuses to overwrite a different fingerprint (that would hide an edit), and commits only the stub.

Exit codes: 0 the part matches (or was sealed, or was already); 1 it changed since, isn't fingerprinted yet (verify),
or holds a different fingerprint (seal); 2 no private file here, no stub, or git failed.

`split` exists to prevent a Silent Fallback in the migration: moving the record files while a person's words stay on
committed pages. Its dry run (the default) runs the same `split_folder` on a temporary copy, so what it lists is what
`--apply` writes, and it exits 3 asking for the lead's yes. `--apply` refuses a dirty tree, works on its own branch,
stages named paths only (never the private notes) and commits once. `split_folder` writes in place and runs no git.
"""
import dataclasses
import pathlib
import shutil
import tempfile

from vela import commands, handoff, planscope, privaterecord, receipts, recordsplit, say, schema
from vela.edge import idgit, sessiongit, vaultgit

VERIFY, SEAL, SPLIT = "records verify", "records seal", "records split"
SPLIT_BRANCH = "records-split"
SPLIT_COMMIT = "Split session records: the notes stay on this machine"
REPUBLISH = "Once it's merged, I'll republish the read copy."


def register(sub):
    top = sub.add_parser("records", help="a session's private notes: check or fill this machine's fingerprint, or move "
                                         "an older plan over to them")
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
    split = verbs.add_parser("split", help="move an older plan's session records to private notes (dry run first)")
    split.add_argument("--vault", default=".", help="vault root (default: current directory)")
    split.add_argument("--apply", action="store_true",
                       help="do it, on a branch of its own, after the lead said yes to the dry run")
    split.add_argument("--today", help="the date written (records_split, new sources), YYYY-MM-DD")
    say.add_output_flags(split)
    split.set_defaults(func=cmd_split)


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


# ---- split -------------------------------------------------------------------------------------------------------

def plan_files(root):
    """{vault-relative path: text} of every Markdown file the split may read or rewrite, plus `.vela.yaml` and
    `.gitignore`. Hidden folders and the private notes are left out, as the vault loader leaves them."""
    from vela import cli
    files = {}
    for path in sorted(root.rglob("*.md")):
        rel = path.relative_to(root)
        if any(part.startswith(".") for part in rel.parts) or cli.page_kind(rel.as_posix()) == "ignored":
            continue
        files[rel.as_posix()] = path.read_text(encoding="utf-8")
    for name in (".vela.yaml", ".gitignore"):
        if (root / name).is_file():
            files[name] = (root / name).read_text(encoding="utf-8")
    return files


def read_manifests(root):
    """[(vault-relative path, text, [Entry])] for each handoff manifest, read before anything is written, so a
    manifest damaged by hand stops the split before it changes a file."""
    folder = root / schema.HANDOFF_DIR
    found = []
    for path in sorted(folder.glob("*.md")) if folder.is_dir() else ():
        rel = path.relative_to(root).as_posix()
        text = path.read_text(encoding="utf-8")
        try:
            found.append((rel, text, handoff.read(text)[1]))
        except handoff.ManifestError as exc:
            raise ValueError(f"{rel} can't be read as a handoff record ({exc}), so I haven't changed anything.") from exc
    return found


def hashes(vault, entries):
    """{id: hash} for the entries the vault still holds."""
    now = {entry.id: handoff.lookup(vault, entry) for entry in entries}
    return {ident: found.hash for ident, found in now.items() if found is not None}


def split_folder(root, lead, today, branch_texts=()):
    """Move a plan's whole records to stubs and private notes, in place, and return the `recordsplit.Report`. Runs no
    git. The handoff manifests are re-hashed by loading the vault before and after, because only the loaded vault
    knows which text each item's hash covers."""
    from vela import cli
    root = pathlib.Path(root)
    report = recordsplit.plan(plan_files(root), lead, today, branch_texts)
    manifests = read_manifests(root)
    before = cli.load_vault(root) if manifests and report.records else None
    for rel, text in report.writes.items():
        sessiongit.write_text(root, rel, text)
    if before is None:
        return report
    after = cli.load_vault(root)
    writes, rows = dict(report.writes), []
    for rel, text, entries in manifests:
        old, new = hashes(before, entries), hashes(after, entries)
        moved, ids = recordsplit.updated_manifest(text, old, new)
        if ids:
            sessiongit.write_text(root, rel, moved)
            writes[rel] = moved
            rows += [f"{rel}: {ident}" for ident in ids]
    return dataclasses.replace(report, writes=writes, handoff_rows=rows)


def lead_handle(root):
    """The lead's handle from the cache `vela whoami` keeps, or "" when there is none. It never calls gh or writes
    the cache, so the dry run changes nothing; an unknown lead keeps no one's words, which is the safe side."""
    return receipts.handle_ref(sessiongit.read_handle(root))


def cmd_split(args, out):
    from vela import cli
    root = pathlib.Path(args.vault).resolve()
    try:
        today, _ = cli.parse_today(args.today)
        result = split(root, args.apply, today)
    except (ValueError, OSError, vaultgit.GitUnavailable, cli.ToolError) as exc:
        result = failed(SPLIT, str(exc))
    return commands.emit(result, args, out)


def split(root, apply, today):
    if sessiongit.is_read_copy(root):
        return failed(SPLIT, "this is a read copy, and the records live in the owner's plan.",
                      "Splitting the records is done in the owner's plan, not in a read copy.")
    lead = lead_handle(root)
    branch_texts = idgit.branch_texts(root)
    if not apply:
        return dry_run(root, lead, today, branch_texts)
    return apply_split(root, lead, today, branch_texts)


def dry_run(root, lead, today, branch_texts):
    with tempfile.TemporaryDirectory() as folder:
        copy = pathlib.Path(folder) / "plan"
        shutil.copytree(root, copy, symlinks=True, ignore=shutil.ignore_patterns(".git"))
        report = split_folder(copy, lead, today, branch_texts)
    if not report.writes:
        return nothing_to_split(report)
    if report.left:
        return say.Result(SPLIT, exit=say.REFUSED, lines=dry_run_lines(report, lead), data=split_data(report))
    ask = "Want me to go ahead?"
    return say.Result(SPLIT, exit=say.NEEDS_LEAD, lines=dry_run_lines(report, lead), data=split_data(report),
                      needs_lead=[{"ask": "split", "question": ask, "answer_with": "--apply"}])


def nothing_to_split(report):
    return say.Result(SPLIT, data=split_data(report), lines=[say.Line(
        "Nothing to split: every session record is already a stub.",
        plain="Nothing to split: every session record is already kept private.")])


def split_data(report):
    return {"records": report.records, "links": report.links, "sources_added": report.sources_added,
            "split_date": report.split_date, "handoff_rows": report.handoff_rows,
            "left": [{"path": item.path, "line": item.line, "what": item.what} for item in report.left],
            "stripped": [{"path": s.path, "line": s.line, "what": s.what, "words": s.words}
                         for s in report.stripped]}


STRIP_WORDS = {recordsplit.DISSENT: "what someone disagreed with, keeping their name and the date",
               recordsplit.RECEIPT: "the words quoted from someone else, keeping who said yes",
               recordsplit.ANSWERED_QUOTE: "the quote from a session, and point that answer at a first-hand source"}


def page_name(path):
    stem = path.rsplit("/", 1)[-1][:-3]
    return stem.split("-", 1)[1].replace("-", " ") if stem[:2].isdigit() and "-" in stem else stem.replace("-", " ")


def plural(n, one, many):
    return f"{say.count_words(n)} {one if n == 1 else many}"


def dry_run_lines(report, lead):
    n = len(report.records)
    lines = [say.Line(f"{n} records move to private notes; {report.links} links are rewritten; split date {report.split_date}",
                      plain=f"I'd move {plural(n, 'session record', 'session records')} over so the notes stay on "
                            f"this machine, and point {plural(report.links, 'link', 'links')} at the stub instead.")]
    if not lead:
        lines.append(say.Line("the lead's handle is unknown, so every receipt's words are taken out",
                              plain="I don't know your GitHub handle yet, so I'd take the words out of every "
                                    "receipt, yours too."))
    for s in report.stripped:
        lines.append(say.Line(f'{s.path}:{s.line}: {s.what} words removed: "{s.words}"',
                              plain=f"On the {page_name(s.path)} page, I'd take out {STRIP_WORDS[s.what]}."))
    for item in report.left:
        lines.append(say.Line(f"{item.path}:{item.line}: a {item.what} line I can't read, so I can't tell whether it "
                              "holds someone's words",
                              plain=f"On the {page_name(item.path)} page, there's a line about a {item.what} I can't "
                                    "read, so I can't tell whether it holds someone's words. Fix it by hand first, "
                                    "then I'll split."))
    if report.sources_added:
        lines.append(say.Line(f"sources added: {', '.join(report.sources_added)}",
                              plain=f"I'd add {plural(len(report.sources_added), 'first-hand source', 'first-hand sources')} "
                                    "to the sources list."))
    if report.handoff_rows:
        lines.append(say.Line("handoff rows updated: " + ", ".join(report.handoff_rows),
                              plain=f"I'd update {plural(len(report.handoff_rows), 'handoff row', 'handoff rows')} where "
                                    "the split was the only change."))
    return lines


def apply_split(root, lead, today, branch_texts):
    from vela import cli
    dirty = vaultgit.uncommitted(root)
    if dirty:
        text = "This plan has changes that aren't committed, and the split edits many pages. Commit or set them aside first."
        return failed_refused(SPLIT, text, {"uncommitted": dirty})
    if not lead:
        return say.Result(SPLIT, exit=say.REFUSED, data={"lead": ""}, lines=[say.Line(
            "vela records split: no handle is cached, so --apply would strip your own words too. Run vela whoami "
            "first, so I keep your own words.",
            plain="I don't know who you are yet, and splitting now would take out your own words too. I'll find "
                  "out first, so I keep them.")])
    planned = recordsplit.plan(plan_files(root), lead, today, branch_texts)  # refuses before any branch is made
    if planned.left:
        text = (f"{plural(len(planned.left), 'line', 'lines')} I can't read, so I can't tell whether they hold "
                "someone's words. Fix them by hand first, then split again.")
        return say.Result(SPLIT, exit=say.REFUSED, data=split_data(planned), lines=[
            say.Line(f"vela records split: {text}", plain=text)] + dry_run_lines(planned, lead)[1:])
    if not planned.writes:
        return nothing_to_split(planned)
    scope = vaultgit.plan_scope(root)
    branch = planscope.session_branch(scope, SPLIT_BRANCH) if scope else SPLIT_BRANCH
    if sessiongit.branch_taken(root, branch):
        return failed_refused(SPLIT, f"The branch {branch} already exists. Merge or delete it, then split again.",
                              {"branch": branch})
    original = sessiongit.current_branch(root)
    made, words = sessiongit.create_branch(root, branch)
    if not made:
        return failed(SPLIT, f"couldn't start the branch {branch}: {words}")
    try:
        report = split_folder(root, lead, today, branch_texts)
        shared = sorted(rel for rel in report.writes if not privaterecord.is_private(rel))
        commit = sessiongit.commit(root, SPLIT_COMMIT, shared)
    except (ValueError, OSError, vaultgit.GitUnavailable, cli.ToolError) as exc:
        return failed(SPLIT, f"{exc} {put_back(root, original, branch, planned)}")
    data = {**split_data(report), "branch": branch, "commit": commit}
    n = len(report.records)
    return say.Result(SPLIT, wrote=shared, data=data, lines=[
        say.Line(f"Split {n} records on {branch}, committed {commit}.",
                 plain=f"Done. I moved {plural(n, 'session record', 'session records')} to private notes and committed "
                       "it on a branch of its own, for review."),
        say.Line(recordsplit.HISTORY_TELL, plain=recordsplit.HISTORY_TELL.replace(" (W720)", "")),
        say.Line(REPUBLISH)])


def put_back(root, original, branch, planned):
    """Undo a split that failed after the branch was made: restore the tracked files, remove the files the split
    created (the private notes are untracked and ignored, so git would leave them), go back to the starting branch
    and delete the split branch. Returns the sentence that says what state is left."""
    try:
        tracked = set(vaultgit.tracked_paths(root))
        vaultgit.run_git(root, "restore", "--source=HEAD", "--staged", "--worktree", "--", ".")
        for rel in planned.writes:
            if rel not in tracked or privaterecord.is_private(rel):
                (root / rel).unlink(missing_ok=True)
        if original:
            sessiongit.switch(root, original, False)
            vaultgit.run_git(root, "branch", "-D", branch)
    except (OSError, vaultgit.GitUnavailable) as exc:
        return (f"I couldn't put the plan back either ({exc}). The branch {branch} may hold a half-done split: "
                "check it with git status before doing anything else.")
    return f"I put the plan back as it was and removed the branch {branch}, so nothing is half-done."


def failed_refused(command, text, data):
    return say.Result(command, exit=say.REFUSED, lines=[say.Line(f"vela records split: {text}", plain=text)],
                      data=data)
