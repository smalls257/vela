"""`vela voice settle`: close/VOICE-REVIEW.md's git dance, so a model never restores a page by hand (overhaul Task 19).

Two steps, one each side of the rewrite the skill writes (dispatching the reviewer and rewriting once stay in the skill):

- `voice settle --checkpoint PAGE...`, before rewriting: commits each page that differs from HEAD, alone, as
  `Checkpoint <id>`. Why: the working tree also holds section 2 and 3's uncommitted edits, and a failed rewrite is
  undone by restoring the page to HEAD; without the checkpoint that restore discards those edits too. The pages and the
  blob HEAD holds for each are noted in `.vela/close/<id>.voice-checkpoint.json`.
- `voice settle --rewrites PAGE... [--redundant PAGE "sentence"]... [--score]`, after rewriting: checks each page
  against HEAD with voicecheck, one page at a time, restores only the pages that fail (no other file), and commits the
  passes, by exact path, as `draft: voice rewrite for <id>`. Why each rule:
  - A rewrite may change words but not what they point at (IDs, numbers, dates, links, code, cells, negations), so a
    voicecheck failure keeps the earlier draft of that page whole.
  - A sentence the reviewer named as redundant may take its negation with it (`--redundant`, for that page only). A
    named sentence that is not in the draft or is still in the rewrite is voicecheck's "could not check": that page is
    restored too, because an unchecked rewrite is never committed.
  - `--score` adds the voicescore summary line. It is a hint, never a gate: it does not change the exit
    code and it never restores or keeps a page.
  The outcome goes to `.vela/close/<id>.voice.json` (the pull request body no longer reads it):
  `{"version": 1, "redundant": [{"page", "sentence"}], "restored": [{"page", "why"}], "kept": [page, ...]}`.

The Violations this shape prevents: the **Distributed Monolith** of a checkpoint in one prose step and a restore in
another, where one forgotten command loses an uncommitted section-3 edit. So `--rewrites` refuses a changed page that
was not checkpointed, or whose HEAD blob moved since (a later commit may already hold the rewrite, and voicecheck would
then compare the rewrite with itself and pass: a **Paper Tiger**). And a **Silent Fallback**: a git failure is exit 2
with git's words, never read as "no difference".

Exit codes (plan 3.1): 0 every rewrite kept (or nothing to check); 1 some pages restored, each listed with why, or the
run refused (nothing changed); 2 git or the disk failed; 3 the session is not clear (none open, or several): nothing ran.
A reader copy has no git, so nothing runs there, and it says so.
"""
import json
import pathlib

from vela import guard, say, voicecheck, voicescore
from vela.commands import close_stage
from vela.edge import atomic, settlegit, stagegit, vaultgit

COMMAND = "voice settle"
REWRITE_MESSAGE = "draft: voice rewrite for {id}"
CLOSE_DIR = ".vela/close"
OUTCOME_VERSION = 1
KIND_WORDS = {"link": "a link", "code": "a code span", "date": "a date", "version": "a version number", "id": "an ID",
              "number": "a number", "cell": "a table cell", "frontmatter": "a frontmatter line"}


def register_voice(each):
    parser = each.add_parser("settle", help="close's voice review: checkpoint pages before the rewrite; after it, "
                                            "voicecheck each against HEAD, restore failures, commit passes")
    which = parser.add_mutually_exclusive_group(required=True)
    which.add_argument("--checkpoint", nargs="+", metavar="PAGE",
                       help="before rewriting: commit each page that differs from HEAD as `Checkpoint <id>`, so a "
                            "restore keeps section 2 and 3's edits")
    which.add_argument("--rewrites", nargs="+", metavar="PAGE",
                       help="after rewriting: voicecheck each page against HEAD, restore the failures, commit the "
                            "passes as `draft: voice rewrite for <id>`")
    parser.add_argument("--redundant", nargs=2, action="append", default=[], metavar=("PAGE", "SENTENCE"),
                        help="a sentence the reviewer named as redundant on PAGE, exactly as it stood; repeatable")
    parser.add_argument("--score", action="store_true",
                        help="add the voicescore summary line (a hint, never a gate)")
    parser.add_argument("--session", help="the session id; default: the one record in sessions/ that says status: open")
    parser.add_argument("--vault", default=".", help="vault root (default: current directory)")
    say.add_output_flags(parser)
    parser.set_defaults(func=cmd_settle)


# --- pure: the verdict on one page, and the outcome -------------------------------------------------------------------

def verdict(before, after, sentences):
    """(kept, why, plain why). `sentences` are the ones named redundant on this page."""
    try:
        result = voicecheck.compare(before, after, sentences)
    except voicecheck.NotRedundant as exc:
        # voice audit row 206: the plain why follows "because the rewrite", so it has to be a verb phrase
        return False, f"voicecheck could not check it: {exc}", "didn't take out the sentence it was meant to"
    if result.same:
        return True, "", ""
    return False, "; ".join(voicecheck.describe(result)), "changed " + ", ".join(changed_kinds(result))


def changed_kinds(result):
    kinds = [t.kind for t in result.missing + result.added] + [x.kind for x, _ in result.moved]
    words = list(dict.fromkeys(KIND_WORDS.get(k, k) for k in kinds))
    return words + (["a negation"] if result.negation else [])


def outcome(kept, restored, redundant):
    """The record `close pr` reads. Only a kept page's redundant sentences are listed: a restored page has them back."""
    return {"version": OUTCOME_VERSION,
            "redundant": [{"page": p, "sentence": s} for p, s in redundant if p in kept],
            "restored": [{"page": p, "why": why} for p, why in restored],
            "kept": list(kept)}


# --- the command ------------------------------------------------------------------------------------------------------

def cmd_settle(args, out):
    from vela import commands
    return commands.emit(settle_result(args, pathlib.Path(args.vault).resolve()), args, out)


def refused(rule, plain, fix, override=""):
    return say.Result(COMMAND, exit=say.REFUSED, refusals=[say.Refusal(rule, plain, fix, override)])


def failed(text, plain):
    return say.Result(COMMAND, exit=say.FAILED, lines=[say.Line(text, plain)])


def settle_result(args, root):
    if close_stage.is_reader_copy(root):
        return refused("voice-settle-reader", f"{say.YOUR_COPY}, so there's nothing to save or put back here; the "
                       "rewrite reaches the owner as a proposal.", "This is a reader copy with no git to checkpoint or "
                       "restore with: skip the voice review's git steps here; nothing ran.")
    ident, problem = session_of(args, root)
    if problem is not None:
        return problem
    pages = [guard.normal(p) for p in (args.checkpoint or args.rewrites)]
    problem = page_problem(root, pages, ident) or flag_problem(args, pages)
    if problem is not None:
        return problem
    try:
        if args.checkpoint:
            return checkpoint(root, ident, pages)
        return settle(root, ident, pages, [(guard.normal(p), s) for p, s in args.redundant], args.score,
                      say.mode_of(args))
    except vaultgit.GitUnavailable as exc:
        return failed(f"vela voice settle: {exc}", "Something went wrong saving the rewrites, partway through. "
                                                   "I'll tell you which pages are safe.")  # voice audit row 210
    except (OSError, atomic.WriteFailed) as exc:
        return failed(f"vela voice settle: the disk refused a write: {exc}",
                      "I couldn't save a change to disk, so I stopped.")


def session_of(args, root):
    """(id, None), or (None, the Result). The same record rule `close stage` uses, so both name one session."""
    if args.session:
        if "/" in args.session or "\\" in args.session or args.session.endswith(".md"):
            return None, refused("voice-session-form", "That session name isn't in the form I need.",
                                 "Give --session the record's file name without .md.")
        return args.session, None
    found = close_stage.open_records(root)
    if len(found) == 1:
        return found[0], None
    if found:
        return None, say.Result(COMMAND, exit=say.NEEDS_LEAD, needs_lead=found, lines=[say.Line(
            f"vela voice settle: {len(found)} records are open: {', '.join(found)}. Run again with --session <id>. "
            "Nothing ran.", "More than one session is open here, so I need to know which one this review is for.")])
    return None, say.Result(COMMAND, exit=say.NEEDS_LEAD, needs_lead=["--session <id>"], lines=[say.Line(
        "vela voice settle: no record in sessions/ says status: open. Run again with --session <id>. Nothing ran.",
        "I couldn't find an open session here, so nothing ran.")])


def page_problem(root, pages, ident):
    """A refusal when a page is not one a close commits (the same allow-list as `close stage`), or is not on disk."""
    plan = guard.plan(pages, close_stage.vault_pages(pages), ident)
    outside = [p for p in pages if p not in plan.stage or not (root / p).is_file()]
    if not outside:
        return None
    return refused("voice-not-a-page", "Only the session's own pages go through the voice review; I ran nothing.",
                   f"Name pages of this vault that are on disk; not one: {', '.join(outside)}.")


def flag_problem(args, pages):
    if args.checkpoint and (args.redundant or args.score):
        return refused("voice-settle-flags", "Redundant sentences and the score belong to the step after the rewrite.",
                       "Run --checkpoint alone, rewrite, then --rewrites with --redundant and --score.")
    stray = sorted({p for p, _ in args.redundant if guard.normal(p) not in pages})
    if stray:
        return refused("voice-redundant-page", "A redundant sentence was named on a page that wasn't rewritten.",
                       f"Give --redundant only for pages in --rewrites; not one: {', '.join(stray)}.")
    return None


def notes_path(root, ident):
    return root / CLOSE_DIR / f"{ident}.voice-checkpoint.json"


def outcome_rel(ident):
    return f"{CLOSE_DIR}/{ident}.voice.json"


def write_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    atomic.write_atomic(path, json.dumps(data, indent=2, ensure_ascii=False) + "\n")


def read_notes(root, ident):
    """{page: blob} from the checkpoint notes. Unreadable notes are a disk failure, never an empty set (that would
    refuse every page with the wrong reason)."""
    path = notes_path(root, ident)
    if not path.is_file():
        return {}
    try:
        return dict(json.loads(path.read_text(encoding="utf-8"))["pages"])
    except (ValueError, KeyError, TypeError) as exc:
        raise OSError(f"{path.relative_to(root)} cannot be read ({exc}); run voice settle --checkpoint again") from exc


def checkpoint(root, ident, pages):
    differing = [p for p in pages if settlegit.differs_from_head(root, p)]
    result = say.Result(COMMAND, data={"session": ident, "checkpointed": differing, "pages": pages})
    if differing:
        message = close_stage.MESSAGES["checkpoint"].format(id=ident)
        stagegit.stage(root, differing)
        sha = stagegit.commit(root, message, differing)
        result.wrote = list(differing)
        result.lines.append(say.Line(f"committed {sha}: {message} ({', '.join(differing)})",
                                     "I've saved the pages' current edits, so a failed rewrite can be undone safely."))
    else:
        result.lines.append(say.Line("every page equals HEAD: nothing to checkpoint",
                                     "The pages had no unsaved edits, so there was nothing to save first."))
    notes = read_notes(root, ident)
    notes.update({p: settlegit.head_blob(root, p) for p in pages})
    write_json(notes_path(root, ident), {"version": OUTCOME_VERSION, "pages": notes})
    result.lines.append(say.Line("now rewrite, then run vela voice settle --rewrites with the same pages",
                                 "Ready for the rewrite."))
    return result


def unchecked_refusal(root, ident, pages, changed):
    """A refusal when a changed page has no checkpoint, or when HEAD moved under a checkpointed page since (checked for
    unchanged pages too: a rewrite committed by hand makes the page equal HEAD and would otherwise pass unchecked);
    None when every page is safe."""
    notes = read_notes(root, ident)
    missing = [p for p in changed if p not in notes]
    if missing:
        return refused("voice-not-checkpointed", "I didn't save the page before it was rewritten, so putting it back "
                       "could lose other edits. I've stopped.",  # voice audit row 209
                       f"Not checkpointed: {', '.join(missing)}. Before the next rewrite run vela voice settle "
                       "--checkpoint on those pages.",
                       "you may accept that a failed rewrite takes the page's other unsaved edits with it; then the "
                       "page is checked by hand")
    moved = [p for p in pages if p in notes and notes[p] != settlegit.head_blob(root, p)]
    if moved:
        return refused("voice-checkpoint-moved", "A commit since the checkpoint changed a rewritten page, so I can't "
                       "tell the rewrite from the draft; I ran nothing.",
                       f"Changed since the checkpoint: {', '.join(moved)}. Compare it by hand with vela voicecheck "
                       "against the checkpoint commit.")
    return None


def settle(root, ident, pages, redundant, score, mode):
    changed = [p for p in pages if settlegit.differs_from_head(root, p)]
    problem = unchecked_refusal(root, ident, pages, changed)
    if problem is not None:
        return problem
    result = say.Result(COMMAND)
    kept, restored = [], []
    for page in pages:
        if page not in changed:
            result.lines.append(say.Line(f"{page}: equals HEAD, nothing to check",
                                         f"{close_stage.lead_name(page)} had no rewrite to check."))
            continue
        before = settlegit.head_text(root, page) or ""
        after = (root / page).read_text(encoding="utf-8") if (root / page).is_file() else ""
        ok, why, plain = verdict(before, after, [s for p, s in redundant if p == page])
        if ok:
            kept.append(page)
            result.lines.append(say.Line(f"kept {page}: voicecheck passed",
                                         f"I kept the rewrite of {close_stage.lead_name(page)}."))
            continue
        settlegit.restore(root, page)
        restored.append((page, why))
        result.wrote.append(page)
        result.lines.append(say.Line(f"restored {page}: {why}", f"I put back the earlier draft of "
                                     f"{close_stage.lead_name(page)}, because the rewrite {plain}."))
    commit_rewrites(root, ident, kept, result)
    record = outcome(kept, restored, redundant)
    if score:
        record["voicescore"] = score_line(root, pages)
        result.lines.append(say.Line(record["voicescore"], lead_score(record["voicescore"])))
    write_json(root / outcome_rel(ident), record)
    if mode != "for-lead":
        result.lines.append(say.Line(f"outcome: {outcome_rel(ident)}"))
    result.data = dict(record, session=ident, outcome=outcome_rel(ident))
    result.exit = say.REFUSED if restored else say.DONE
    return result


def commit_rewrites(root, ident, kept, result):
    if not kept:
        return
    message = REWRITE_MESSAGE.format(id=ident)
    stagegit.stage(root, kept)
    sha = stagegit.commit(root, message, kept)
    notes = read_notes(root, ident)  # this commit was checked, so a later settle measures from it
    notes.update({p: settlegit.head_blob(root, p) for p in kept})
    write_json(notes_path(root, ident), {"version": OUTCOME_VERSION, "pages": notes})
    result.wrote += kept
    result.lines.append(say.Line(f"committed {sha}: {message}", "I've committed the rewrites that passed."))


def score_line(root, pages):
    """The voicescore summary over the pages' prose as they now stand, or "voicescore: not run (<reason>)"."""
    from vela import cli
    texts = [(root / p).read_text(encoding="utf-8") for p in pages if (root / p).is_file()]
    prose = "\n\n".join(par.text for text in texts for par in voicescore.paragraphs(text))
    try:
        cli.require_dependencies()
        cli.require_model()
        ref = cli.voicescore_reference(root, "owner")
        if ref.warning:
            return f"voicescore: not run (fewer than {voicescore.MIN_RELIABLE} owner examples)"
        embed, _ = cli.voicescore_embedder(root)
        return voicescore.summary(voicescore.score(prose, ref, embed), ref.range_name)
    except (cli.VoiceScoreUnavailable, voicescore.NotScorable, cli.ToolError) as exc:
        return f"voicescore: not run ({exc})"


def lead_score(line):
    if line.startswith("voicescore: not run"):
        return "The style reading didn't run."
    inside, total = line.split(": ", 1)[1].split(" paragraphs", 1)[0].split(" of ")
    return f"The style reading puts {inside} of {total} paragraphs inside your range; it's a hint, not a verdict."
