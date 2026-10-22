"""`vela close drafts [--json|--for-lead]`: the paragraphs this session owes before it closes (overhaul Task 21a).

Close section 4 used to be a list the model walked by memory, so a skipped paragraph was invisible (Black Box). This
command prints the checklist; the skill drafts each paragraph on it (Filter). What it reads, and why:

- the pages changed since this session began (`git diff` against the `start_commit` its record holds, so a second
  session on a reused branch owes only its own paragraphs; a record without one, or whose commit is no longer in this
  branch's history, falls back to the merge-base with main), plus untracked pages, or,
  in a reader copy, the folder against its `.vela/baseline`, so a reader copy runs no git at all;
- the vault as it is now, which `closedrafts` asks `query refs` of for each item resolved or decided this session;
- the open session record, for its modes (an epics session owes each epic's own sections).

`closedrafts.py` holds the rules and the why of each. Read-only: it writes nothing and runs no subcommand.

Exit codes: 0 the checklist (even an empty one); 1 no session is open, so nothing is owed; 2 the tool failed (git or
the baseline could not be read, said with the reason, never an empty checklist); 3 several sessions are open here.
"""
import pathlib
import re

from vela import closedrafts, opening, say, sessions
from vela.edge import copies, flowstore, mergegit, sessiongit, vaultgit

PLAIN_WHY = {
    "opening": "its opening should say what is true now",
    "strategy": "its Strategy paragraph should still match the cells this session changed",
    "item": "it needs an opening sentence before its bullets",
    "adr": "it was decided and shapes the whole design, so it needs a decision record",
    "epic": "an epics session owes this part of each epic it drafted",
}
LEADING_ID = re.compile(r"^(\S+-\S+)\s+\S")


def register_close(steps):
    drafts = steps.add_parser("drafts", help="the paragraphs this session owes: changed pages, sentences naming what "
                                             "it resolved or decided, Strategy paragraphs, decision records, lists "
                                             "over seven, and whether to ask about splitting the PR")
    drafts.add_argument("--vault", default=".", help="vault root (default: current directory)")
    say.add_output_flags(drafts)
    drafts.set_defaults(func=run)


def open_record(root):
    """(record, None) for the one open record here, or (None, Result) to print instead."""
    found, problems = sessions.find_open(sessiongit.folder_records(root))
    if len(found) == 1:
        return found[0], None
    if not found:
        line = "No session is open, so no paragraph is owed." + (f" ({'; '.join(problems)})" if problems else "")
        return None, say.Result("close drafts", exit=say.REFUSED, lines=[say.Line(line)])
    choices = [{"id": r.id, "topic": r.title, "date": r.date} for r in found]
    plain = f"{len(found)} sessions are open here, so I haven't listed what either owes. Which one are we closing?"
    lines = [say.Line(f"{len(found)} sessions are open in this folder; run close drafts on the branch of the one you "
                      "are closing.", plain=plain)]
    return None, say.Result("close drafts", exit=say.NEEDS_LEAD, lines=lines, needs_lead=choices)


def branch_point(root):
    """The commit this branch left main at: merge-base with origin/main, else with main."""
    for ref in ("origin/main", "main"):
        code, out, _ = vaultgit.run_git(root, "merge-base", "HEAD", ref)
        if code == 0 and out:
            return out
    raise vaultgit.GitUnavailable("this branch shares no commit with main or origin/main")


def session_start(root, record):
    """The commit to count changes from: the one the record began at, else the branch point."""
    began = sessions.start_commit_of((root / record.path).read_text(encoding="utf-8"))
    if began and sessiongit.ref_exists(root, began) and mergegit.is_ancestor(root, began, "HEAD"):
        return began
    return branch_point(root)


def git_changes(root, record=None):
    """The changed pages since the session began, or, with no record (a reviewer's whole-branch read), since the branch point."""
    return flowstore.changed_files(root, since=session_start(root, record) if record else branch_point(root))


def reader_changes(root):
    """{path: text before or None} from the baseline the copy was opened with. No git runs here."""
    baseline = root / copies.BASELINE
    if not baseline.is_dir():
        raise copies.SourceUnreadable(f"this reader copy has no baseline at {copies.BASELINE}, so I can't tell what "
                                      "changed")
    before = copies.read_tree(baseline, skip_published=True)
    now = copies.read_tree(root, skip_published=True)
    changed = {}
    for path in sorted(set(before) | set(now)):
        if before.get(path) != now.get(path):
            old = before.get(path)
            changed[path] = None if old is None else old.decode("utf-8", "replace")
    return changed


def page_changes(changes, page_kind):
    """Only Markdown pages count; a deleted page owes no paragraph."""
    return {path: text for path, text in changes.items() if path.endswith(".md") and page_kind(path) == "page"}


def run(args, out):
    """List what the open session owes; git or a baseline that can't answer is a tool failure, never "nothing owed"."""
    from vela import cli  # the shell loads the vault; this module wires it
    try:
        return list_owed(args, out, cli)
    except (vaultgit.GitUnavailable, copies.SourceUnreadable, opening.OpenError, cli.ToolError) as exc:
        print(f"vela close drafts: could not list what the session owes: {exc}", file=out)
        return say.FAILED


def list_owed(args, out, cli):
    from vela import commands
    root = pathlib.Path(args.vault).resolve()
    reader = mergegit.is_reader_copy(root)
    record, early = open_record(root)
    if early is not None:
        return commands.emit(early, args, out)
    after = cli.load_vault(root)
    changes = page_changes(reader_changes(root) if reader else git_changes(root, record), cli.page_kind)
    changes = {p: t for p, t in changes.items() if (root / p).is_file()}
    found = closedrafts.owed(closedrafts.vault_before(after, changes), after, changes, record.modes)
    resolver = say.Resolver(after)
    lines = default_lines(found, record.id, reader) if say.mode_of(args) != "for-lead" else lead_lines(found, after, resolver)
    result = say.Result("close drafts", exit=say.DONE, lines=lines, data=as_data(found, record.id, reader))
    return commands.emit(result, args, out, resolver)


def as_data(found, record_id, reader):
    return {"record": record_id, "reader_copy": reader, "count": found.count,
            "paragraphs": [p.as_json() for p in found.paragraphs],
            "readback": [r.__dict__ for r in found.readback],
            "long_lists": [x.as_json() for x in found.long_lists],
            "split": found.split.as_json() if found.split else None,
            "judgment": list(found.judgment), "kept_wording": list(found.kept)}


def default_lines(found, record_id, reader):
    since = "its baseline" if reader else "the session began"
    n = found.count
    out = [say.Line(f"close drafts: {n} paragraph{'' if n == 1 else 's'} owed for {record_id} (changes since {since}).")]
    for p in found.paragraphs:
        items = f" ({', '.join(p.items)})" if p.items else ""
        out.append(say.Line(f"- {p.page} > {p.heading} [{p.kind}]{items}: {p.why}"))
    for r in found.readback:
        out.append(say.Line(f"read back: {r.item} {r.name} ({r.before} -> decided), {r.page} > {r.heading}"))
    for x in found.long_lists:
        out.append(say.Line(f"list over seven: {x.page} > {x.heading}: {x.count} entries; the few that matter first, "
                            "the rest under ## Also open (n)"))
    if found.split:
        groups = ", ".join(f"{g}: {c}" for g, c in found.split.groups.items())
        out.append(say.Line(f"size: ask the lead: \"{found.split.question}\" ({found.split.pages} pages; by group: "
                            f"{groups})"))
    out += [say.Line(f"kept wording: {page}: the documents' words, as the lead chose; no voiced prose owed")
            for page in found.kept]
    out += [say.Line(f"judgment: {j}") for j in found.judgment]
    return out


def place(owed, vault, resolver):
    """Where on the page a paragraph is, in words: an item heading by the item's name, never its ID."""
    if owed.heading == closedrafts.OPENING:
        return "the opening"
    lead = LEADING_ID.match(owed.heading)
    if lead and vault.item(lead.group(1)) is not None:
        return vault.name_of(lead.group(1))
    return f"under {resolver.plain(owed.heading)}"


def plain_why(owed, resolver):
    said = []
    if owed.mentions:
        names = ", ".join(resolver.name(i) for i in owed.mentions)
        verbs = " or ".join(sorted(set(owed.mentions.values())))
        said.append(f"it mentions {names}, which this session {verbs}")
    if owed.kind != "ref" or owed.whys:
        said.append(PLAIN_WHY[owed.kind])
    return "; ".join(said)


def lead_lines(found, vault, resolver):
    n = found.count
    head = (f"{say.count_words(n, capital=True)} paragraph{' is' if n == 1 else 's are'} to write up."
            if n else "Nothing needs writing up this time.")  # voice audit row 151: not "owes"
    out = [say.Line(head, plain=head)]
    for p in found.paragraphs:
        text = resolver.plain(f"{p.title}, {place(p, vault, resolver)}: {plain_why(p, resolver)}.")
        out.append(say.Line(text, plain=text))
    for r in found.readback:
        text = f"I'll read {r.name} back to its owner, since it was decided today."
        out.append(say.Line(text, plain=text))
    for x in found.long_lists:
        text = resolver.plain(f"{x.title} lists {x.count} things under {x.heading}; I'll put the few that matter "
                              "first and fold the rest.")
        out.append(say.Line(text, plain=text))
    if found.split:
        out.append(say.Line(found.split.question, plain=found.split.question))
    # the model's reminder, not news to the lead on every close (voice audit row 159)
    out.append(say.Line("Also: a glossary entry for each term a newcomer to the initiative wouldn't know.",
                        audience=say.MODEL))
    return out
