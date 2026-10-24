"""`vela reviewers prepare --checkpoint NAME --focus PAGE... [--rerun N --areas FIN,REG] [--team]`: everything a review
checkpoint needs before a reviewer runs (overhaul Task 20). Named `reviewers`, not `review`: `vela/review.py` is the
proposals reviewer.

What it does, in order, for a vault checkpoint:

1. finds the open session record (as `vela record add` does) and numbers the checkpoint from it
   (`reviewprep.checkpoint_number`); `--rerun N` makes it checkpoint `n+1` over only `--areas`, with finding IDs from
   `F<n+1>.1`, so earlier IDs never change;
2. reads what the session changed (the working tree against the branch point, or a reader copy's folder against its
   baseline) before it commits, so the line ranges are the session's own;
3. commits the record and every page the session changed, staged by exact path: a reviewer sees only what is
   written, and the commit is what a second machine resumes from. The message is `close stage --checkpoint`'s own,
   `Checkpoint <session id>`, so a session's commits keep one grammar (REVIEW once added the number; the record's
   `### <n>.` heading carries it);
4. writes one packet per reviewed area to `.vela/review/<n>/<AREA>.md`, with that area's owed questions beside it
   (`<AREA>-questions.json`), and clears `.vela/findings/<session id>/<n>/` for the replies, so no stale reply is
   read as fresh;
5. lists each skipped area with its reason, and prints the merge command to run once the replies are saved.

`--team` is the design checkpoint: five fixed reviewers over the focus pages (the design doc, CONTEXT.md, the ADRs,
the design's inputs), packets in `.vela/review/design/`. A design opens no session record, so nothing is numbered or
committed.

The Violation the shape prevents is a Silent Fallback: a page list missing a changed page, or a skipped area nobody
was told about, reads afterwards as "checked, none". So a skipped area is always listed with its reason, and a failure
to read the record or git is exit 2 with git's words, never an empty packet. A reader copy runs no git: it commits
nothing and says so.

Exit codes: 0 prepared; 1 no session is open; 2 the tool failed or an argument is wrong (a page that isn't there, a
re-run of a checkpoint the record lacks); 3 several sessions are open here (pick with `--record`).
"""
import datetime
import json
import pathlib
import shutil

from vela import commands, privaterecord, questions, reviewprep, say, sizing
from vela.commands import close_drafts, close_stage, record
from vela.edge import copies, flowstore, sessiongit, vaultgit

NAME = "reviewers prepare"
COUNT_WORDS = {1: "one", 2: "two", 3: "three", 4: "four", 5: "five", 6: "six"}


class Failed(Exception):
    """An argument or the disk that stops the checkpoint; said with its reason, exit 2."""


def register(sub):
    group = sub.add_parser("reviewers", help="review checkpoints: number one and write each reviewer's packet")
    verbs = group.add_subparsers(dest="reviewers_command", metavar="{prepare}")
    verbs.required = True
    prep = verbs.add_parser("prepare", help="number the checkpoint, commit the record, write one packet per area to "
                                            ".vela/review/<n>/, and list the areas skipped with the reason")
    prep.add_argument("--vault", default=".", help="vault root or reader workspace (default: current directory)")
    prep.add_argument("--checkpoint", required=True, help="the checkpoint and its focus, such as 'after the pre-mortem'")
    prep.add_argument("--focus", nargs="+", required=True, metavar="PAGE",
                      help="the pages this checkpoint's focus touches; every reviewer reads them")
    prep.add_argument("--rerun", type=int, metavar="N",
                      help="re-run areas of checkpoint N (or run ones it skipped): a new checkpoint n+1, with --areas")
    prep.add_argument("--areas", help="with --rerun: the area codes to run, comma-separated, such as FIN,REG")
    prep.add_argument("--team", action="store_true",
                      help="the design checkpoint: five reviewers (vendors, data, failure, security, operations) "
                           "over the focus pages; nothing numbered or committed")
    prep.add_argument("--record", default="", metavar="ID", help="the open record, when several are open")
    prep.add_argument("--today", help="the date for the checkpoint's heading, YYYY-MM-DD (default: today)")
    say.add_output_flags(prep)
    prep.set_defaults(func=cmd_prepare)


def cmd_prepare(args, out):
    from vela import cli  # the shell loads the vault
    root = pathlib.Path(args.vault).resolve()
    reader = sessiongit.is_read_copy(root)
    try:
        result = prepare_team(root, args) if args.team else prepare(root, args, reader, cli)
    except record.Stop as stop:
        result = stop.result
    except (Failed, cli.ToolError, vaultgit.GitUnavailable, copies.SourceUnreadable, ValueError, OSError) as exc:
        result = say.Result(NAME, exit=say.FAILED, lines=[
            say.Line(f"vela reviewers prepare: {exc}",  # the reason is the model's (flags, area codes, git's words)
                     plain="I couldn't start the review; I'll fix how I asked and try again.")])
    if say.mode_of(args) == "for-lead":
        return commands.emit(result, args, out, say.Resolver())
    return commands.emit(result, args, out)


def today_of(args):
    return args.today or datetime.date.today().isoformat()


def _check_args(args, codes):
    if args.areas and args.rerun is None:
        raise Failed("--areas goes with --rerun N: a first checkpoint decides its own areas, and lists any it skips.")
    if args.rerun is not None and not args.areas:
        raise Failed("--rerun N needs --areas, the area codes to run again, such as --areas FIN,REG.")
    if args.team and (args.rerun is not None or args.areas):
        raise Failed("--team is the design checkpoint's five reviewers; it takes no --rerun or --areas.")
    if args.areas is None:
        return None
    wanted = [w.strip().upper() for w in args.areas.split(",") if w.strip()]
    unknown = [w for w in wanted if w not in codes]
    if not wanted or unknown:
        raise Failed(f"--areas takes area codes of the catalog ({', '.join(codes)}); "
                     f"{', '.join(unknown) or 'it was empty'} {'is' if len(unknown) < 2 else 'are'} not one.")
    return tuple(c for c in codes if c in wanted)


def _focus_pages(root, focus, vault=None):
    """Each focus page as a vault-relative path; one that isn't there stops the checkpoint."""
    from vela import reviews
    found, missing = [], []
    for ref in focus:
        page = reviews.find_page(vault, ref) if vault is not None else None
        if page is not None:
            found.append(page.path)
        elif (root / ref).is_file():
            found.append(pathlib.PurePosixPath(ref).as_posix())
        else:
            missing.append(ref)
    if missing:
        raise Failed(f"--focus names {', '.join(missing)}, which {'is' if len(missing) == 1 else 'are'} not a page "
                     "here. Name the pages this checkpoint's focus touches, by their path.")
    return found


def _changes(root, reader, cli):
    """{vault page path: text before, or None when new}: what the session changed, before anything is committed."""
    changes = close_drafts.reader_changes(root) if reader else close_drafts.git_changes(root)
    return {p: t for p, t in changes.items() if p.endswith(".md") and cli.page_kind(p) == "page"}


def _commit(root, record_id, changes):
    """Commit the stub and each changed page that git still sees as uncommitted; the short hash, or None when
    everything was already committed. The private notes are never committed: they are untracked on purpose."""
    dirty = set(flowstore.changed_files(root))
    paths = sorted(p for p in {privaterecord.stub_path(record_id)} | set(changes) if p in dirty)
    if not paths:
        return None
    return sessiongit.commit(root, close_stage.MESSAGES["checkpoint"].format(id=record_id), paths)


def _clear(root, *folders):
    for rel in folders:
        path = root / rel
        if path.exists():
            shutil.rmtree(path)
        path.mkdir(parents=True)


def _prepared(root, record_id):
    """How many checkpoints this session has prepared that ran reviewers: findings folders `prepare` leaves behind.
    A checkpoint that skipped every area leaves none, so it never counts as this session's review."""
    folder = root / ".vela" / "findings" / record_id
    return sum(1 for child in folder.iterdir() if child.is_dir()) if folder.is_dir() else 0


def _state_path(record_id):
    return f".vela/review-state/{record_id}.json"


def _listings_at_last_run(root, record_id):
    """{area code: listing fingerprint} as the last checkpoint that ran reviewers left it; {} when none did."""
    path = root / _state_path(record_id)
    try:
        return json.loads(path.read_text(encoding="utf-8")) if path.is_file() else {}
    except ValueError:
        return {}


def prepare(root, args, reader, cli):
    vault = cli.load_vault(root)
    only = _check_args(args, vault.catalog.area_codes)
    focus = _focus_pages(root, args.focus, vault)
    state = sessiongit.read_json(root, sessiongit.STATE_FILE)
    rel, record_id = record.open_record(root, state, args.record)
    text = (root / rel).read_text(encoding="utf-8")
    n = reviewprep.checkpoint_number(text)
    if args.rerun is not None and args.rerun not in reviewprep.checkpoints(text):
        held = reviewprep.checkpoints(text)
        raise Failed(f"--rerun {args.rerun}: the record has no checkpoint {args.rerun} under ## Reviews"
                     + (f" (it has {', '.join(map(str, held))})." if held else " (it has none yet)."))
    earlier = args.rerun is None and reviewprep.earlier_checkpoint_covers(text, sizing.of(vault),
                                                                          _prepared(root, record_id))
    before = _listings_at_last_run(root, record_id) if earlier else {}
    changes = _changes(root, reader, cli)
    commit = None if reader else _commit(root, record_id, changes)
    now = {p.path: p.text for p in vault.pages}
    now[rel] = text
    changed = reviewprep.reviewed_changes(changes, now, rel)
    changed_arg = reviewprep.changed_arg(changed)
    folder, findings = f".vela/review/{n}", f".vela/findings/{record_id}/{n}"
    _clear(root, folder, findings)
    ledger = questions.ledger_page(vault)
    limit = reviewprep.ledger_limit(ledger.text) if ledger is not None else None
    standing = [p for p in reviewprep.STANDING_PAGES if vault.page(p[:-3]) is not None]
    base = reviewprep.base_pages(rel, changed, standing + ([ledger.path] if ledger is not None else []), focus)
    close = set(changed) | set(focus)
    prep = reviewprep.Prep(n, reviewprep.heading(n, args.checkpoint, today_of(args), args.rerun, only or ()),
                           folder, findings, changed_arg, rerun_of=args.rerun)
    files, listings = {}, {}
    for code, label in vault.catalog.areas:
        if only is not None and code not in only:
            continue
        answer = questions.listing(vault, code)
        listings[code] = reviewprep.listing_signature(answer)
        if only is not None:
            reason = ""
        elif earlier:
            reason = reviewprep.later_skip(answer, close, before.get(code, ""))
        else:
            reason = reviewprep.skip_reason(answer, close)
        if reason:
            prep.skipped.append(reviewprep.Skipped(code, label, reason))
            continue
        pages = reviewprep.reviewer_pages(base, reviewprep.pending_subject_pages(answer),
                                          ledger.path if ledger is not None else None, limit)
        qfile, ffile = f"{folder}/{code}-questions.json", f"{findings}/{code}.json"
        packet = f"{folder}/{code}.md"
        body = reviewprep.area_packet_text(code, label, args.checkpoint, pages, changed_arg, qfile, ffile, rel)
        prep.packets.append(reviewprep.Packet(code, label, tuple(pages), packet, qfile, ffile, body))
        files[qfile] = json.dumps(answer, indent=2, ensure_ascii=False) + "\n"
        files[packet] = body
    if prep.packets:
        files[_state_path(record_id)] = json.dumps({**before, **listings}, indent=2) + "\n"
    else:
        shutil.rmtree(root / findings)  # nothing ran, so this checkpoint is not the session's review
    wrote = [sessiongit.write_text(root, path, body) for path, body in files.items()]
    return said(prep, args, wrote, commit, reader, rel)


def prepare_team(root, args):
    _check_args(args, ())
    focus = _focus_pages(root, args.focus)
    prep = reviewprep.team_prep(args.checkpoint, focus, today_of(args))
    _clear(root, prep.folder, prep.findings_folder)
    wrote = [sessiongit.write_text(root, p.packet, p.text) for p in prep.packets]
    return said(prep, args, wrote, None, False, None)


def said(prep, args, wrote, commit, reader, rel):
    """The Result in the mode asked for: the lead hears one sentence, the default mode the paths and the merge."""
    lines = lead_lines(prep) if say.mode_of(args) == "for-lead" else default_lines(prep, commit, reader)
    return say.Result(NAME, wrote=wrote, lines=lines,
                      data={**prep.as_json(), "record": rel, "commit": commit, "reader_copy": reader})


def default_lines(prep, commit, reader):
    """What the default mode prints; `lead_lines` carries the lead's sentence, so each mode shows only its own."""
    which = f"checkpoint {prep.n}" if prep.n is not None else "the design checkpoint"
    lines = [f"vela reviewers prepare: {which}, {len(prep.packets)} packet{'' if len(prep.packets) == 1 else 's'} "
             f"in {prep.folder}/" + (f"; findings from {prep.first_finding}" if prep.n is not None else "") + "."]
    if prep.n is not None:
        lines.append("reader copy: no git ran and nothing was committed; the record reaches the owner in the proposal."
                     if reader else (f"committed {commit}." if commit else "nothing to commit: the record and the "
                                                                           "changed pages were already committed."))
    lines += [f"- {p.area} {p.label}: {p.packet}" for p in prep.packets]
    lines += [f"skipped {s.area} {s.label}: {s.reason}" for s in prep.skipped]
    if prep.n is not None and prep.packets:
        lines.append(f"Heading once merged: {prep.heading}")
        lines.append(f"Merge: {prep.merge_command()}")
    return [say.Line(text) for text in lines]


def lead_lines(prep):
    """The one sentence the lead hears while the reviewers run, with each skipped angle named by its label."""
    count = len(prep.packets)
    if not count and prep.skipped and all(s.reason == reviewprep.ONE_PER_SESSION for s in prep.skipped):
        words = ("I've already had this session checked, and at this size one check covers what changed. "
                 "Want me to run it again anyway?")
        return [say.Line(words, plain=words)]
    words = f"Checking this against {COUNT_WORDS.get(count, count)} angle{'' if count == 1 else 's'}, about a minute."
    if prep.skipped:
        names = ", ".join(s.label.lower() for s in prep.skipped)
        it = "it" if len(prep.skipped) == 1 else "them"
        # voice audit row 199: not "owed", ledger talk
        words += f" I skipped {names}: nothing there changed or is waiting on an answer. Want {it} checked anyway?"
    return [say.Line(words, plain=words)]
