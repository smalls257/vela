"""`vela voice <step>`: the voice examples' mechanics, so a skill asks the owner and the CLI does the files (Task 18).

- `voice examples --type T | --page P`: the example paths a draft reads, in house-voice's fixed order.
- `voice plan --type T --place committed|local [--source S] [--adding N] [--from FILE]`: what retires before a save.
- `voice save --from FILE --type T --place committed|local --consent ^cN [--commit-consent ^cM] --author H
  (--where TEXT | --page P --harvested-from SHA) [--retire-consent ^cK]`: the passage, byte for byte, with its
  frontmatter, compared after writing; then the planned retirements.
- `voice harvest list`: the owner's edits to merged session drafts, offered as candidates with draft and merged text.
- `voice harvest decline PR PAGE HASH`: the bare decline line under the record's `## Captures`.

The Violations this shape prevents: a **Silent Fallback** in harvest (a `gh` failure read as "no edits found": here it
is exit 2 with gh's words, and a run that hit the PR limit says older PRs were not checked), and a **God Method**: each
step is its own small function, and a later step (Task 19's `voice settle`) is one more name in `STEPS`, a module with
`register_voice(steps)`, without touching this file's steps or `cli.py`.

Consent (voice-seed, HARVEST): a passage is stored only on the owner's yes to "Did you write this yourself?"
(`--consent`), and a committed one also on a second, separate yes that everyone with access to the repository may
read it (`--commit-consent`): committed text is pushed in a PR. Both are captures in the open session record, checked
by `decisions.consent.a_yes`. A retirement the cap forces needs the owner's yes too (`--retire-consent`), because the
owner may refuse one; without it the save exits 3 and changes nothing. A reader copy has no git and no PR, so only
the local place is open there.

Exit codes (plan 3.1): 0 done; 1 refused (the cap, a missing yes, a reader copy's committed save), with the reason;
2 the tool failed (`gh`, git, the disk, or a store that differs from its passage, which is never repaired);
3 needs the owner (a cap retirement, or several sessions open): nothing changed.
"""
import datetime
import importlib
import pathlib
import re

from vela import commands, privaterecord, say, voiceplan
from vela.decisions import consent, record as records
from vela.edge import atomic, sessiongit, voicegit
from vela.edge.vaultgit import GitUnavailable

STEPS = ("voice_settle",)  # modules with `register_voice(steps)`
NAME = "voice"
_SHA = re.compile(r"^[0-9a-f]{40}$")
_HASH = re.compile(r"^[0-9a-f]{12}$")


def register(sub):
    voice = sub.add_parser("voice", help="the voice examples: reading order, retire plan, verbatim save, harvest")
    each = voice.add_subparsers(dest="voice_step", required=True)
    for add in (add_examples, add_plan, add_save, add_harvest):
        add(each)
    for name in STEPS:
        importlib.import_module(f"vela.commands.{name}").register_voice(each)


def common(parser):
    parser.add_argument("--vault", default=".", help="vault root (default: current directory)")
    say.add_output_flags(parser)


def add_examples(each):
    parser = each.add_parser("examples", help="the example files a draft reads, in house-voice's fixed order")
    which = parser.add_mutually_exclusive_group(required=True)
    which.add_argument("--type", choices=voiceplan.VOICE_TYPES, help="a voice type")
    which.add_argument("--page", help="a page; its voice type comes from house-voice's page-type table")
    common(parser)
    parser.set_defaults(func=cmd_examples)


def add_plan(each):
    parser = each.add_parser("plan", help="what retires when examples are added: folder-local seed rule, cap of 5")
    place_and_type(parser)
    parser.add_argument("--source", choices=voiceplan.OWNER_SOURCES, default="owner",
                        help="owner (voice-seed) or owner-edit (harvest); default owner")
    parser.add_argument("--adding", type=int, default=1, help="how many examples of the type are about to be stored")
    parser.add_argument("--from", dest="source_file", help="a passage file: also report its --- and generated lines "
                                                           "and its word count, so the owner is asked first")
    common(parser)
    parser.set_defaults(func=cmd_plan)


def add_save(each):
    parser = each.add_parser("save", help="store a passage byte for byte with its frontmatter, then compare")
    parser.add_argument("--from", dest="source_file", required=True, help="the passage file, stored exactly")
    place_and_type(parser)
    parser.add_argument("--consent", required=True, help="the capture of the owner's yes that they wrote it (^cN)")
    parser.add_argument("--commit-consent", help="committed only: a second capture, the yes to committing it (^cM)")
    parser.add_argument("--retire-consent", help="the capture of the owner's yes to the retirements the cap forces")
    parser.add_argument("--author", required=True, help="the owner's handle, with or without @")
    parser.add_argument("--where", help="an owner passage: where it comes from, in a few words (`from`)")
    parser.add_argument("--page", help="a harvested paragraph: the page it came from")
    parser.add_argument("--harvested-from", help="a harvested paragraph: the full hash of the draft commit")
    parser.add_argument("--today", help="the `added` date, YYYY-MM-DD (default: today)")
    common(parser)
    parser.set_defaults(func=cmd_save)


def add_harvest(each):
    harvest = each.add_parser("harvest", help="the owner's edits to merged session drafts")
    steps = harvest.add_subparsers(dest="harvest_step", required=True)
    listing = steps.add_parser("list", help="candidates from the last merged session PRs, draft and merged text")
    common(listing)
    listing.set_defaults(func=cmd_harvest_list)
    decline = steps.add_parser("decline", help="record a declined paragraph, so it is not offered again")
    decline.add_argument("pr", type=int)
    decline.add_argument("page")
    decline.add_argument("hash")
    common(decline)
    decline.set_defaults(func=cmd_harvest_decline)


def place_and_type(parser):
    parser.add_argument("--type", required=True, choices=voiceplan.VOICE_TYPES)
    parser.add_argument("--place", required=True, choices=tuple(voiceplan.FOLDERS))


def root_of(args):
    return pathlib.Path(args.vault).resolve()


def refused(command, rule, plain, fix, override="", data=None):
    return say.Result(command, exit=say.REFUSED, refusals=[say.Refusal(rule, plain, fix, override)], data=data or {})


def failed(command, text, plain, data=None):
    return say.Result(command, exit=say.FAILED, lines=[say.Line(text, plain)], data=data or {})


# --- examples ---------------------------------------------------------------------------------------------------------

def cmd_examples(args, out):
    return commands.emit(examples_result(root_of(args), args.type, args.page), args, out)


def examples_result(root, voice_type, page):
    command = "voice examples"
    if page is not None:
        rel = pathlib.Path(page)
        if not (root / rel).is_file():
            return refused(command, "voice-page-missing", "I couldn't find that page.", f"No file {page} in the vault.")
        meta = voicegit.page_meta(root, rel)
        voice_type = voiceplan.voice_type_of(meta or {})
        if voice_type is None:
            kind = (meta or {}).get("type", "no type")
            return refused(command, "voice-type-unknown", "I don't know which voice that page is written in.",
                           f"{page} has type {kind!r}, which house-voice's page-type table does not list; pick the "
                           "voice type from that table and run with --type.")
        if voice_type == voiceplan.STRUCTURED:
            return say.Result(command, lines=[say.Line(f"{page} is structured: it holds no voiced prose.",
                                                       "That page holds tables and lists, so it has no voice.")],
                              data={"voice_type": voice_type, "examples": []})
    chosen = voiceplan.reading_order(voicegit.examples(root), voice_type)
    lines = [say.Line(e.path, plain="") for e in chosen]  # files for the model to read; nothing for the lead
    if len(chosen) < 2:
        lines.append(say.Line(f"{voice_type} has fewer than 2 active examples: say \"No examples for {voice_type}: "
                              "drafted without examples\" in the PR body.",
                              ""))  # thin examples go in the PR body, never to the lead (CONVERSATION-VOICE)
    return say.Result(command, lines=lines, data={"voice_type": voice_type, "examples": [e.path for e in chosen]})


# --- plan -------------------------------------------------------------------------------------------------------------

def cmd_plan(args, out):
    root = root_of(args)
    notes = []
    if args.source_file:
        body, problem = read_passage(args.source_file, "voice plan")
        if problem is not None:
            return commands.emit(problem, args, out)
        notes = voiceplan.body_notes(body, args.type)
    plan = voiceplan.plan(voicegit.examples(root), args.type, args.place, args.adding, args.source)
    return commands.emit(plan_result(plan, notes), args, out)


def retire_line(example, why):
    reason = "the cap of 5 forces it" if why == "cap" else "its folder now holds 2 of the owner's examples"
    # voice audit row 201: not "retire" and "cap", and the date in words
    added = say.date_words(example.added)
    plain = (f"Saving this pushes out your oldest example, from {added}, because I keep five at most." if why == "cap"
             else f"Saving this puts away the starter example from {added}, now that two of yours take its place.")
    return say.Line(f"retire {example.path} ({example.source}, added {example.added}): {reason}", plain)


def plan_result(plan, notes, command="voice plan"):
    data = dict(plan.as_json(), notes=notes)
    note_lines = [say.Line(f"note: {n}", plain=f"Before saving: {n}.") for n in notes]
    if plan.blocked:
        return refused(command, "voice-cap", plan.reason, "Store nothing for this type, or pick the other place.",
                       "the owner may retire an example by hand first", data=data)
    lines = note_lines + [retire_line(e, "seed") for e in plan.seed_retires] \
        + [retire_line(e, "cap") for e in plan.cap_retires]
    if not plan.retires:
        lines.append(say.Line(f"{plan.voice_type}: room for {plan.adding} more in {plan.place}; nothing retires.",
                              "There's room for it; nothing has to retire."))
    if plan.cap_retires:
        return say.Result(command, exit=say.NEEDS_LEAD, lines=lines, data=data,
                          needs_lead=[{"retire": e.id, "path": e.path, "source": e.source} for e in plan.cap_retires])
    return say.Result(command, lines=lines, data=data)


# --- save -------------------------------------------------------------------------------------------------------------

def read_passage(path, command):
    """(text, None), or (None, the exit-2 Result). Read as bytes and decoded strictly, so nothing is altered."""
    try:
        return pathlib.Path(path).read_bytes().decode("utf-8"), None
    except (OSError, UnicodeDecodeError) as exc:
        return None, failed(command, f"vela voice: can't read {path}: {exc}", "I couldn't read the passage file.")


def cmd_save(args, out):
    return commands.emit(save_result(args, root_of(args)), args, out)


def field_problem(args):
    """A refusal for the frontmatter values, or None."""
    command = "voice save"
    harvested = args.page is not None or args.harvested_from is not None
    if harvested and not (args.page and args.harvested_from and _SHA.match(args.harvested_from)):
        return refused(command, "voice-harvest-fields", "I need the page and the draft it came from.",
                       "Give --page and --harvested-from with the full 40-character hash of the draft commit.")
    if not harvested and not args.where:
        return refused(command, "voice-from-missing", "I need a few words on where the passage comes from.",
                       "Give --where (the `from` field), or --page and --harvested-from for a harvested paragraph.",
                       "the owner may leave it out: pass --where with the words they agree to record")
    for value in (args.where, args.page, args.author):
        if value and ("\n" in value or "\r" in value):
            return refused(command, "voice-field-newline", "A field held a line break, so I stored nothing.",
                           "Give each field on one line.")
    if args.today is not None and not re.match(r"^\d{4}-\d{2}-\d{2}$", args.today):
        return refused(command, "voice-date", "That date isn't YYYY-MM-DD.", "Give --today as YYYY-MM-DD.")
    return None


def save_result(args, root):
    command = "voice save"
    problem = field_problem(args)
    if problem is not None:
        return problem
    if args.place == "committed" and sessiongit.is_read_copy(root):
        return refused(command, "voice-reader-committed", "In your copy I can only keep it on this machine.",
                       "Store it with --place local; a reader copy has no git, so nothing is committed or pushed.")
    body, problem = read_passage(args.source_file, command)
    if problem is not None:
        return problem
    record, problem = open_record(root, command)
    if problem is not None:
        return problem
    problem = yes_problem(args, record)
    if problem is not None:
        return problem
    found = voicegit.examples(root)
    source = "owner-edit" if args.page else "owner"
    plan = voiceplan.plan(found, args.type, args.place, 1, source)
    if plan.blocked or (plan.cap_retires and not args.retire_consent):
        return plan_result(plan, voiceplan.body_notes(body, args.type), command)
    if plan.cap_retires:
        refusal = consent.a_yes(args.retire_consent, record)
        if refusal is not None:
            return say.Result(command, exit=say.REFUSED, refusals=[refusal])
    return store(root, found, plan, args, body)


def open_record(root, command):
    """(OpenRecord, None), or (None, the Result): the yeses are read from the one open session record."""
    rec, opened = records.open_record(sessiongit.folder_records(root))
    if rec is not None:
        return rec, None
    if opened.several:
        choices = [{"id": r.id, "topic": r.title} for r in opened.records]
        return None, say.Result(command, exit=say.NEEDS_LEAD, needs_lead=choices, lines=[say.Line(
            f"{len(choices)} sessions are open; nothing done. Run on the branch of the one that holds the yes.",
            f"{len(choices)} sessions are open here, so I don't know which one holds your yes.")])
    return None, refused(command, "voice-no-record", "No session is open, so I have nowhere to read your yes from.",
                         "Open a session and capture the owner's yes in its record, then pass that capture.")


def yes_problem(args, record):
    command = "voice save"
    refusal = consent.a_yes(args.consent, record)
    if refusal is not None:
        return say.Result(command, exit=say.REFUSED, refusals=[refusal])
    if args.place != "committed":
        return None
    if not args.commit_consent:
        return refused(command, "voice-commit-consent", "I need your yes to commit it, where everyone with access to "
                       "the repository can read it.",
                       "Ask \"May this text be committed to the vault?\", capture the yes, pass --commit-consent; or "
                       "store it with --place local.")
    if records.number_of(args.commit_consent) == records.number_of(args.consent):
        return refused(command, "voice-one-yes-for-two", "Writing it and committing it are two questions, so I need "
                       "two answers.", "Capture the yes to committing it separately and pass that capture.")
    refusal = consent.a_yes(args.commit_consent, record)
    return say.Result(command, exit=say.REFUSED, refusals=[refusal]) if refusal is not None else None


def store(root, found, plan, args, body):
    command = "voice save"
    ident = voiceplan.next_id(found, args.type)
    rel = f"{voiceplan.FOLDERS[args.place]}/{args.type}/{ident}.md"
    today = args.today or datetime.date.today().isoformat()
    fields = voiceplan.example_fields(ident, args.type, args.author, today, args.where, args.page, args.harvested_from)
    try:
        written = voicegit.write_example(root, rel, voiceplan.file_text(fields, body))
    except (OSError, atomic.WriteFailed) as exc:
        return failed(command, f"vela voice: the disk refused {rel}: {exc}",
                      "I couldn't save it to disk, so nothing changed.")  # voice audit row 207
    if voiceplan.stored_body(written.decode("utf-8")) != body:
        return failed(command, f"vela voice: {rel} does not hold the passage exactly; it was not repaired",
                      "The saved file doesn't match your passage, so I stopped and left it as it is.",
                      {"wrote": [rel]})
    problem = frontmatter_problem(written.decode("utf-8"), dict(fields), rel)
    if problem is not None:
        return problem
    retiring = {e.path: voiceplan.retired((root / e.path).read_text(encoding="utf-8")) for e in plan.retires}
    try:
        voicegit.write_files(root, retiring)
    except atomic.WriteFailed as exc:
        return failed(command, f"vela voice: saved {rel}, but a retirement failed: {exc}",
                      "I saved it, but I couldn't put away the older example it replaces.", {"wrote": [rel]})
    lines = [say.Line(f"wrote {rel}; the stored text equals the passage", "I've saved it word for word.")]
    lines += [say.Line(f"note: {n}", plain=f"Note: {n}.") for n in voiceplan.body_notes(body, args.type)]
    lines += [retire_line(e, "seed") for e in plan.seed_retires] + [retire_line(e, "cap") for e in plan.cap_retires]
    if args.place == "committed":
        lines.append(say.Line("committed place: it reaches the repository only through a PR",
                              "It goes to everyone with access to the repository once the PR is merged."))
    result = say.Result(command, lines=lines, wrote=[rel] + list(retiring),
                        data={"id": ident, "path": rel, "retired": [e.id for e in plan.retires]})
    if sessiongit.is_read_copy(root):
        result.lines.append(say.Line("reader copy: no git ran", f"{say.YOUR_COPY}, so it's saved on this machine "
                                     "only."))  # voice audit row 215
    return result


def frontmatter_problem(text, fields, rel):
    """Re-read the frontmatter and confirm it parses and holds the values given (WRITE.md's last move)."""
    from vela import parse
    meta, _, error = parse.split_frontmatter(text)
    expect = {"page": fields.get("page"), "harvested_from": fields.get("harvested_from"), "from": fields.get("from")}
    wrong = [key for key, value in expect.items() if value is not None and str(meta.get(key)) != value[1:-1].replace("''", "'")]
    if error is None and not wrong:
        return None
    return failed("voice save", f"vela voice: {rel}'s frontmatter does not read back as given ({error or wrong})",
                  "The saved file's header didn't read back as written, so I stopped.", {"wrote": [rel]})


# --- harvest ----------------------------------------------------------------------------------------------------------

def cmd_harvest_list(args, out):
    return commands.emit(harvest_result(root_of(args)), args, out, vault_resolver(root_of(args)))


def vault_resolver(root):
    """A resolver over the vault when it loads, so a page is said by its title; else the plain kind words."""
    from vela import cli
    try:
        return say.Resolver(cli.load_vault(root))
    except cli.ToolError:
        return say.Resolver()


def harvest_result(root):
    command = "voice harvest list"
    if sessiongit.is_read_copy(root):
        return refused(command, "voice-harvest-reader", HARVEST_OWNER_ONLY, "Skip harvest here: a reader copy has no "
                       "git, and harvest runs in the owner's clone.")
    found = voicegit.examples(root)
    owners = voiceplan.owner_handles(found)
    if not owners:
        return say.Result(command, lines=[say.Line(
            "No owner examples yet, so nothing to harvest. `/vela:voice-seed` adds them.")], data={"candidates": []})
    try:
        handle = voicegit.login(root)
    except voicegit.GhFailed as exc:
        return failed(command, f"gh could not read your handle, so nothing was harvested. ({exc})",
                      NO_GITHUB, {"candidates": []})
    if handle.lstrip("@") not in owners:
        return refused(command, "voice-harvest-owner", HARVEST_OWNER_ONLY, "Skip harvest. Harvest is owner-only.",
                       data={"candidates": []})
    try:
        prs = voicegit.merged_session_prs(root)
    except voicegit.GhFailed as exc:
        return failed(command, f"gh could not list merged PRs, so nothing was harvested. ({exc})",
                      NO_GITHUB, {"candidates": []})
    return collect(root, found, prs)


# voice audit rows 203 and 204: no "harvest", "clone" or gh's words, and no raw exception in what the lead hears
HARVEST_OWNER_ONLY = "Only the plan's owner can collect their edits as examples, and only on their own machine."
NO_GITHUB = "I couldn't reach GitHub, so I haven't looked for your edits."
UNCHECKED_PR = "I couldn't read one of your merged changes on GitHub, so its edits weren't checked."


def collect(root, found, prs):
    lines, failures, candidates = [], [], []
    if len(prs) >= voicegit.PR_LIMIT:
        lines.append(say.Line(f"{len(prs)} merged PRs came back, so older PRs were not checked."))
    voicegit.clear_harvest(root)
    declined = voiceplan.declined(voicegit.record_metas(root))
    for pr in prs:
        number = int(pr["number"])
        for offer in pr_offers(root, number, failures):
            key = (number, offer["page"], offer["hash"])
            if key in declined or voiceplan.already_saved(found, offer["page"], offer["baseline"], offer["merged"]):
                continue
            offer["file"] = voicegit.write_paragraph(root, number, len(candidates) + 1, offer["merged"])
            candidates.append(offer)
    lines += [say.Line(f, UNCHECKED_PR) for f in failures]
    lines += [say.Line(f"PR {c['pr']} {c['page']} {c['hash']}: {c['file']} ({c['voice_type'] or 'voice type unknown'})",
                       f"An edit you made to {page_stem(c['page'])}, in PR {c['pr']}.") for c in candidates]
    if not candidates and not failures:
        word = "PR" if len(prs) == 1 else "PRs"
        mine = ("Your last merged PR had no edits of yours to keep." if len(prs) == 1
                else f"None of your last {say.count_words(len(prs))} merged PRs had edits of yours to keep.")
        lines.append(say.Line(f"No edits found in the {len(prs)} merged {word} checked.", mine))  # row 208
    return say.Result("voice harvest list", exit=say.FAILED if failures else say.DONE, lines=lines,
                      data={"candidates": candidates, "unchecked": failures})


def page_stem(path):
    """'06-runtime/heron-runtime.md' -> 'heron-runtime': the page's name, which the resolver says as its title."""
    stem = str(path).replace("\\", "/").rsplit("/", 1)[-1]
    return stem[:-3] if stem.endswith(".md") else stem


def pr_offers(root, number, failures):
    """The owner's edited paragraphs of one PR. A failure goes in `failures` with what it left unchecked."""
    try:
        commits = voicegit.pr_commits(root, number)
    except voicegit.GhFailed as exc:
        failures.append(f"gh could not read the commits of PR {number}, so its edits were not checked. ({exc})")
        return []
    try:
        tip = voicegit.fetch_pr(root, number)
    except GitUnavailable as exc:
        failures.append(f"git could not fetch PR {number}, so it was not checked. ({exc})")
        return []
    try:
        return list(offers_in(root, number, commits, tip))
    except GitUnavailable as exc:
        failures.append(f"git failed while reading PR {number}, so its edits were not all checked. ({exc})")
        return []


def baselines(root, commits):
    """{page: the last draft commit in the PR's list that touched it}."""
    found = {}
    for commit in commits:
        if commit.get("messageHeadline", "").startswith("draft: "):
            for page in voicegit.pages_of(root, commit["oid"]):
                found[page] = commit["oid"]
    return found


def offers_in(root, number, commits, tip):
    listed = {c["oid"]: c for c in commits}
    for page, base in baselines(root, commits).items():
        owner = [oid for oid in voicegit.commits_touching(root, base, tip, page) if oid in listed
                 and not voiceplan.is_tool_commit(listed[oid].get("messageHeadline", ""),
                                                  listed[oid].get("messageBody", ""))]
        merged_text = voicegit.show(root, tip, page) if owner and page.endswith(".md") else None
        if merged_text is None:
            continue
        from vela import parse
        meta, _, _ = parse.split_frontmatter(merged_text)
        voice_type = voiceplan.voice_type_of(meta)
        if voice_type == voiceplan.STRUCTURED:
            continue
        yield from page_offers(root, number, page, base, list(reversed(owner)), merged_text, voice_type)


def page_offers(root, number, page, base, owner, merged_text, voice_type):
    tip_lines, seen = merged_text.split("\n"), set()
    for oid in owner:
        before = (voicegit.show(root, f"{oid}^", page) or "").split("\n")
        for old_start, added in voiceplan.added_hunks(voicegit.diff_u0(root, oid, page)):
            index = voiceplan.find_line(tip_lines, added[0], old_start - 1)
            span = voiceplan.paragraph_span(tip_lines, index) if index is not None else None
            if span is None or span in seen:
                continue
            seen.add(span)
            draft_span = voiceplan.paragraph_span(before, old_start - 1) or voiceplan.paragraph_span(before, old_start - 2)
            merged = voiceplan.paragraph_text(tip_lines, span)
            yield {"pr": number, "page": page, "baseline": base, "commit": oid, "voice_type": voice_type,
                   "lines": [span[0] + 1, span[1] + 1], "hash": voiceplan.harvest_hash(merged), "merged": merged,
                   "draft": voiceplan.paragraph_text(before, draft_span) if draft_span else ""}


def cmd_harvest_decline(args, out):
    return commands.emit(decline_result(root_of(args), args.pr, args.page, args.hash), args, out)


def decline_result(root, pr, page, digest):
    command = "voice harvest decline"
    if not _HASH.match(digest) or not page.strip() or "\n" in page:
        return refused(command, "voice-decline-form", "That decline isn't in the record's form, so I wrote nothing.",
                       "Give the PR number, the page path and the paragraph's 12-character hash from harvest list.")
    record, problem = open_record(root, command)
    if problem is not None:
        return problem
    line = voiceplan.decline_line(pr, page, digest)
    if (pr, page, digest) in voiceplan.declined([privaterecord.stub_meta(record.text)]):
        return say.Result(command, lines=[say.Line(f"already declined: {line}", "That one was already declined.")])
    text = voiceplan.with_decline(record.text, line)
    text = None if text is None else privaterecord.synced_stub(text, text)
    if text is None:
        return refused(command, "voice-no-captures", "The session record has no captures section to write it under.",
                       f"Add a `## Captures` heading to {record.path}, then decline again.")
    try:
        atomic.write_atomic(root / record.path, text)
    except atomic.WriteFailed as exc:
        return failed(command, f"vela voice: the disk refused {record.path}: {exc}", "The disk refused the record.")
    return say.Result(command, lines=[say.Line(f"wrote under ## Captures in {record.path}: {line}",
                                               "I've noted that you declined it, so it won't come up again.")],
                      wrote=[record.path])
