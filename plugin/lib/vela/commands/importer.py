"""`vela import`: the open session's import queue, which the import skill works through in batches of about four.

    vela import add --type decision|clash|stale "what the documents say" --source SRC-nn [--source SRC-mm]
                    --propose "the answer I'd give" --why "why"            queue one thing for the lead
    vela import next [--for-lead]                                        the next batch, each with its proposal
    vela import close N --as OUTCOME [--how "..."]                        settle one item with the lead's answer
    vela import show [--for-lead]                                        the read-back: settled, asked, waiting
    vela import wording --as keep|split|voice --yes ^cN [--source SRC-nn]  the lead's answer to the voice question
    vela import page PAGE --source SRC-nn [--source ...]                  stamp a page with the wording it takes

The core is `vela/importqueue.py`; this module finds the open record, keeps the queue in `.vela/import/<session>.json`
through the topic map's own store (commands/map.py `Store`), and prints through `say`. The queue is never staged
(guard.py's tool-state rule).

Two writes reach the plan, and both refuse rather than guess:

- `wording` takes the capture of the lead's words and refuses one that is Claude's, missing, or a bare "ok"
  (closegate's own test of a yes): voicing a document's prose is the lead's call, never the session's.
- `page` writes `source-wording:` (and `source-wording-yes:`, the capture link) into the page's frontmatter, from
  that answer. With no answer it writes `keep`: the documents' words stay as written. Close and the voice checks read
  the field (closedrafts, voicecheck, voicescore), so a kept page is never handed to the voice redraft.

Exit codes: 0 done; 1 no open session, or input the queue refuses (the model's to fix); 2 the queue file, the vault
or a page can't be read or written; 3 several open sessions here (pick with `--record`).
"""
import pathlib
import re

from vela import closegate, commands, importqueue, privaterecord, say
from vela.commands import map as topic
from vela.edge import sessiongit

NAME = "import"
NO_SESSION = "No session is open, so there's no import queue to keep."
STORE = topic.Store(importqueue.FOLDER, importqueue.new_state, importqueue.parse, importqueue.dumps, "queue",
                    "import queue", "The import queue didn't take that: {exc}.",
                    "I couldn't read or save the import's list of things to ask you.", needs_kinds=False,
                    nothing=NO_SESSION)
WORDING_KEY, WORDING_YES_KEY = importqueue.WORDING_KEY, importqueue.WORDING_YES_KEY
CAPTURE_REF = re.compile(r"^\^?c?(?P<n>\d+)$")


def register(sub):
    top = sub.add_parser("import", help="the import's queue: stated decisions, clashes and stale facts, about four "
                                        "at a time, each with a proposed answer")
    verbs = top.add_subparsers(dest="import_command", metavar="{add,next,close,show,wording,page}")
    verbs.required = True

    add = verbs.add_parser("add", help="queue one thing the documents say that only the lead can settle")
    add.add_argument("text", help="what the documents say, in plain words")
    add.add_argument("--type", required=True, choices=importqueue.TYPES, dest="item_type")
    add.add_argument("--source", action="append", default=[], help="the source it rests on (SRC-nn); twice for a clash")
    add.add_argument("--propose", required=True, help="the answer you'd give, in a line")
    add.add_argument("--why", required=True, help="why you'd give it, in a line")
    add_record_flags(add, cmd_add)

    add_record_flags(verbs.add_parser("next", help="the next batch of about four, or the open batch again"), cmd_next)

    closer = verbs.add_parser("close", help="settle one item with the lead's answer")
    closer.add_argument("number", type=int, help="the item's number, as add printed it")
    closer.add_argument("--as", dest="outcome", required=True,
                        choices=sorted({o for outs in importqueue.OUTCOMES.values() for o in outs}))
    closer.add_argument("--how", default="", help="how it ended, in a line")
    add_record_flags(closer, cmd_close)

    add_record_flags(verbs.add_parser("show", help="the read-back: what's settled, what's asked, what waits"), cmd_show)

    wording = verbs.add_parser("wording", help="the lead's answer to the voice question, for every source or one")
    wording.add_argument("--as", dest="choice", required=True, choices=importqueue.WORDINGS,
                         help="keep: every word as written; split: the documents' terms quoted, the explaining "
                              "sentences voiced; voice: all of it in the plan's voice")
    wording.add_argument("--yes", required=True, metavar="^cN", help="the capture of the lead's answer")
    wording.add_argument("--source", default=importqueue.ALL_SOURCES, help="one source (SRC-nn); default every source")
    add_record_flags(wording, cmd_wording)

    page = verbs.add_parser("page", help="stamp a page with the wording its sources take")
    page.add_argument("page", help="the page's path in the vault")
    page.add_argument("--source", action="append", default=[], help="a source the page draws on (SRC-nn); repeat")
    add_record_flags(page, cmd_page)


def add_record_flags(parser, func):
    parser.add_argument("--vault", default=".", help="vault root (default: current directory)")
    parser.add_argument("--record", default="", metavar="ID", help="the open record, when several are open")
    say.add_output_flags(parser)
    parser.set_defaults(func=func)


def name_of(args):
    return f"import {args.import_command}"


def run(args, out, change):
    """map.run over the import's store: one way of keeping a session's working file."""
    return topic.run(args, out, change, store=STORE, name=name_of(args))


def model_line(text, plain=""):
    return say.Line(text, plain=plain, audience=say.MODEL if not plain else say.LEAD)


# --- the vault, read only for the names the lead hears --------------------------------------------------------------

def source_titles(root):
    """{SRC-nn: title} from the sources register."""
    path = pathlib.Path(root) / "sources.md"
    if not path.is_file():
        return {}
    out = {}
    for line in path.read_text(encoding="utf-8").split("\n"):
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) >= 2 and re.fullmatch(r"SRC-\d+", cells[0]):
            out[cells[0]] = cells[1]
    return out


def names(item, titles):
    return [titles.get(s, "a document") for s in item["sources"]]


def unknown_sources(sources, titles):
    return [s for s in sources if s not in titles]


# --- the subcommands ------------------------------------------------------------------------------------------------

def cmd_add(args, out):
    def change(state, where):
        root, _ = where
        missing = unknown_sources(args.source, source_titles(root))
        if missing:
            raise importqueue.QueueRefused(f"{', '.join(missing)} isn't in the sources register; add it first")
        item = importqueue.add(state, args.item_type, args.text, args.source, args.propose, args.why)
        return [model_line(f"#{item['n']} queued ({item['type']})")], {"item": item,
                                                                        "waiting": len(importqueue.waiting(state))}, "", ""
    return run(args, out, change)


def batch_lines(batch, titles):
    return [say.Line(f"#{i['n']} [{i['type']}] {i['text']} | proposed: {i['proposal']} ({i['why']})",
                     plain=importqueue.said(i, names(i, titles))) for i in batch]


def cmd_next(args, out):
    def change(state, where):
        root, _ = where
        batch, reopened = importqueue.next_batch(state)
        titles = source_titles(root)
        left = len(importqueue.waiting(state))
        if not batch:
            return ([model_line("nothing waits on the import queue")],
                    {"batch": [], "reopened": False, "waiting": 0}, "Nothing from the documents is waiting for you.", "")
        count = say.count_words(len(batch))
        if len(batch) == 1:
            answer = ("This one is still waiting for your answer." if reopened else
                      "One thing from the documents to settle, with what I'd do.")
        else:
            answer = (f"These {count} are still waiting for your answer." if reopened else
                      f"{count.capitalize()} things from the documents to settle, each with what I'd do.")
        lines = [model_line(f"batch {batch[0]['batch']}{' (still open: close these before the next)' if reopened else ''}"
                            f"; {left} more waiting after it")]
        lines += batch_lines(batch, titles)
        return lines, {"batch": batch, "reopened": reopened, "waiting": left}, answer, \
            "Yes to these, or which would you change?"
    return run(args, out, change)


def cmd_close(args, out):
    def change(state, where):
        item = importqueue.close(state, args.number, args.outcome, args.how)
        still = len(importqueue.open_batch(state))
        tail = f"; {still} left in this batch" if still else "; batch done: import next for more"
        return [model_line(f"#{item['n']} {item['state']}{tail}")], {"item": item, "open": still}, "", ""
    return run(args, out, change)


def cmd_show(args, out):
    def change(state, where):
        root, _ = where
        counts = importqueue.counts(state)
        asked, waiting, done = (importqueue.open_batch(state), importqueue.waiting(state), importqueue.settled(state))
        if not state["items"]:
            return [model_line("the import queue is empty")], {"counts": counts}, "Nothing from the documents is queued yet.", ""
        answer = (f"From the documents: {say.count_words(len(done))} settled, {say.count_words(len(asked))} with you "
                  f"now, {say.count_words(len(waiting))} still to ask.")
        lines = [model_line("; ".join(f"{t}: {c['settled']} settled, {c['asked']} asked, {c['waiting']} waiting"
                                      for t, c in counts.items()))]
        lines += batch_lines(asked, source_titles(root))
        wording = state["wording"]
        lines.append(model_line("wording: " + (", ".join(f"{s} {w['as']} ({w['yes']})" for s, w in wording.items())
                                               if wording else "not asked yet; pages keep the documents' words")))
        return lines, {"counts": counts, "asked": asked, "wording": wording}, answer, \
            "Which of these is wrong?" if asked else ""
    return run(args, out, change)


def record_captures(root, session):
    path = pathlib.Path(root) / privaterecord.private_path(session)
    return closegate.captures(path.read_text(encoding="utf-8")) if path.is_file() else {}


def capture_number(ref):
    found = CAPTURE_REF.match(str(ref).strip())
    if not found:
        raise importqueue.QueueRefused(f"--yes {ref!r} isn't a capture; give it as ^cN")
    return found["n"]


def lead_yes(root, session, ref):
    """The capture number of the lead's answer, or QueueRefused: missing, Claude's own, or a bare "ok", the same test
    close's gate puts every decision's yes to."""
    number = capture_number(ref)
    said = record_captures(root, session)
    capture = next((c for n, c in said.items() if int(n) == int(number)), None)
    if capture is None:
        raise importqueue.QueueRefused(f"capture ^c{number} isn't in this session's record; capture the lead's answer first")
    if not capture.is_person:
        raise importqueue.QueueRefused(f"capture ^c{capture.n} is Claude's (origin {capture.origin!r}), not the lead's "
                                       "answer; ask the lead")
    if capture.unverified:
        raise importqueue.QueueRefused(f"capture ^c{capture.n} is unverified (nothing could check the lead typed it); "
                                       "ask the lead, then run `vela record confirm`")
    if capture.is_bare_non_yes:
        raise importqueue.QueueRefused(f"capture ^c{capture.n} says only {capture.quote!r}; ask the lead which they mean")
    return f"^c{capture.n}"


def cmd_wording(args, out):
    def change(state, where):
        root, session = where
        if args.source != importqueue.ALL_SOURCES and unknown_sources([args.source], source_titles(root)):
            raise importqueue.QueueRefused(f"{args.source} isn't in the sources register")
        yes = lead_yes(root, session, args.yes)
        notes = (pathlib.Path(root) / privaterecord.private_path(session)).read_text(encoding="utf-8")  # lead_yes read it
        cite = privaterecord.citation(session, privaterecord.part_of(notes), int(capture_number(yes)))
        answer = importqueue.set_wording(state, args.choice, yes, args.source, cite)
        scope = "every source" if args.source == importqueue.ALL_SOURCES else args.source
        return [model_line(f"wording for {scope}: {answer['as']} ({answer['yes']})")], {"wording": state["wording"]}, "", ""
    return run(args, out, change)


def set_frontmatter(text, values):
    """`text` with each key of `values` set in its frontmatter (replaced in place, else added before the closing
    fence), or a key removed when its value is None. QueueRefused when the page has no frontmatter."""
    lines = text.split("\n")
    if not lines or lines[0].strip() != "---":
        raise importqueue.QueueRefused("the page has no frontmatter to record its wording in")
    end = next((i for i in range(1, len(lines)) if lines[i].strip() == "---"), None)
    if end is None:
        raise importqueue.QueueRefused("the page's frontmatter never closes")
    for key, value in values.items():
        pattern = re.compile(rf"^{re.escape(key)}:")
        at = next((i for i in range(1, end) if pattern.match(lines[i])), None)
        if value is None:
            if at is not None:
                del lines[at]
                end -= 1
            continue
        line = f'{key}: "{value}"' if any(c in value for c in ":[]#^") else f"{key}: {value}"
        if at is None:
            lines.insert(end, line)
            end += 1
        else:
            lines[at] = line
    return "\n".join(lines)


def cmd_page(args, out):
    def change(state, where):
        root, session = where
        rel = pathlib.PurePosixPath(args.page.replace("\\", "/")).as_posix().lstrip("./")
        path = (pathlib.Path(root) / rel).resolve()
        if not path.is_file() or pathlib.Path(root).resolve() not in path.parents or not rel.endswith(".md"):
            raise importqueue.QueueRefused(f"{args.page} isn't a page in this vault")
        missing = unknown_sources(args.source, source_titles(root))
        if not args.source or missing:
            raise importqueue.QueueRefused("give every source the page draws on (--source SRC-nn), each in the register"
                                           + (f"; {', '.join(missing)} isn't" if missing else ""))
        choice, yes, link = importqueue.wording_for(state, args.source)
        text = path.read_text(encoding="utf-8")
        after = set_frontmatter(text, {WORDING_KEY: choice, WORDING_YES_KEY: link or None})
        wrote = [sessiongit.write_text(root, rel, after)] if after != text else []
        said = {importqueue.KEEP: "keeps the documents' words as written",
                importqueue.SPLIT: "quotes the documents' terms and voices its own sentences",
                importqueue.VOICE: "is written in the plan's voice"}[choice]
        lines = [model_line(f"{rel}: {WORDING_KEY} {choice}" + (f" ({yes})" if yes else " (no answer yet: kept)")
                            + (f"; wrote {rel}" if wrote else "; unchanged"))]
        return lines, {"page": rel, "wording": choice, "yes": yes, "_wrote": wrote}, f"That page {said}.", ""
    return run(args, out, change)
