"""`vela map`: the open session's running topic map, which Dump, Discover and Grill call as the lead talks.

    vela map add --kind K "what the lead said" [--topic T]           tag a thing to a kind
    vela map add --group G                                          a group the lead named, on the roster now
    vela map add --group G --topic T --position P [--reason R] [--basis stated|guess]
    vela map open --type gap|conflict|belief|fact "text" [--kind K] [--topic T]
    vela map close N [--as settled|recorded|set-aside] [--how "..."]
    vela map next                                                    what to raise next, best first
    vela map show --for-lead                                         the read-back, about four at a time

The core is `vela/topicmap.py`; this module only finds the open record, reads and writes the map file, and prints
through `say`. The map lives in `.vela/map/<session>.json`, so it survives a long session and a restart and anyone can
open it; it is never only in the model's memory, and never staged (guard.py's tool-state rule). Exit codes: 0 done;
1 no open session, or input the map refuses (the model's to fix); 2 the map file or the catalog can't be read or
written; 3 several open sessions here (pick with `--record`).
"""
import pathlib
from dataclasses import dataclass
from typing import Callable

from vela import commands, say, topicmap
from vela.commands import record
from vela.edge import sessiongit

NO_SESSION = "No session is open, so there's no topic map to keep."
# Section 7.1, rule 13: the read-back asks which is wrong, since a summary is what draws the corrections out.
CLOSING = "Which of these is wrong?"


def register(sub):
    top = sub.add_parser("map", help="the open session's running topic map: what's covered, what's empty, what waits")
    verbs = top.add_subparsers(dest="map_command", metavar="{add,open,close,next,show}")
    verbs.required = True

    add = verbs.add_parser("add", help="tag something the lead said to a kind, name a group, or record its position")
    add.add_argument("text", nargs="?", default="", help="what the lead said, in their words (with --kind)")
    add.add_argument("--kind", default="", help="the kind it belongs to: one of the catalog's kinds")
    add.add_argument("--group", default="", help="a group the lead named; with --position, the group that holds it")
    add.add_argument("--topic", default="", help="the topic it is about; becomes the current topic")
    add.add_argument("--position", default="", help="where the group stands on --topic")
    add.add_argument("--reason", default="", help="why the group wants it, when the lead said")
    add.add_argument("--basis", default=topicmap.STATED, choices=topicmap.BASES,
                     help="stated: the group's own view as the lead reports it; guess: the lead's guess at it")
    common(add, cmd_add)

    opener = verbs.add_parser("open", help="a waiting item to raise later: a gap, conflict, belief or fact")
    opener.add_argument("text", help="the item, in the lead's words")
    opener.add_argument("--type", required=True, choices=topicmap.TYPES, dest="item_type")
    opener.add_argument("--kind", default="", help="the kind it belongs to")
    opener.add_argument("--topic", default="", help="the topic; a conflict on a topic marks its pair as raised")
    common(opener, cmd_open)

    closer = verbs.add_parser("close", help="settle a waiting item")
    closer.add_argument("number", type=int, help="the item's number, as open printed it")
    closer.add_argument("--as", dest="outcome", default=topicmap.SETTLED, choices=topicmap.OUTCOMES,
                        help="settled in the talk; recorded in the plan as open; set-aside by the lead")
    closer.add_argument("--how", default="", help="how it ended, in a line")
    common(closer, cmd_close)

    common(verbs.add_parser("next", help="what to raise next: summarize, a pair side by side, a group, or a kind"),
           cmd_next)
    common(verbs.add_parser("show", help="the read-back: covered, empty, and what waits"), cmd_show)


def common(parser, func):
    parser.add_argument("--vault", default=".", help="vault root (default: current directory)")
    parser.add_argument("--record", default="", metavar="ID", help="the open record, when several are open")
    say.add_output_flags(parser)
    parser.set_defaults(func=func)


class Stop(Exception):
    def __init__(self, result):
        super().__init__(result.command)
        self.result = result


def name_of(args):
    return f"map {args.map_command}"


def session_of(root, args, name=None, nothing=NO_SESSION):
    """The open record's id, or Stop: exit 1 with none open, 3 with several."""
    name = name or name_of(args)
    try:
        _, record_id = record.open_record(root, sessiongit.read_json(root, sessiongit.STATE_FILE), args.record)
    except record.Stop as stop:
        if stop.result.exit == say.REFUSED:
            raise Stop(say.Result(name, exit=say.REFUSED, lines=[say.Line(nothing)])) from stop
        found = stop.result
        raise Stop(say.Result(name, exit=found.exit, needs_lead=found.needs_lead, lines=found.lines)) from stop
    return record_id


@dataclass(frozen=True)
class Store:
    """A session's working file under `.vela/`: the topic map, or the import queue (commands/importer.py), which
    shares this one way of finding the open session, reading the file, writing it back only when it changed, and
    saying every refusal and failure. One copy, so the two queues can't drift in how they keep their state."""
    folder: str
    new: Callable
    parse: Callable
    dumps: Callable
    key: str  # the --json field naming the file
    rule: str  # the refusal's rule name
    refused: str  # the refusal's words, with {exc}
    failed: str  # what the lead hears when the file can't be read or written
    needs_kinds: bool = True  # the map's changes take the catalog's kinds; the import's take (root, session)
    nothing: str = NO_SESSION  # what the lead hears when no session is open

    def path(self, session):
        return f"{self.folder}/{session}.json"

    def load(self, root, session):
        path = root / self.path(session)
        if not path.is_file():
            return self.new(session)
        return self.parse(path.read_text(encoding="utf-8"))


MAP = Store(topicmap.FOLDER, topicmap.new_state, topicmap.parse, topicmap.dumps, "map", "topic map",
            "The map didn't take that: {exc}.", "I couldn't read or save the session's topic map.")


def map_path(session):
    return MAP.path(session)


def load(root, session):
    return MAP.load(root, session)


def run(args, out, change, store=MAP, name=None):
    """Find the session, load its file, apply `change(state, kinds)` -> (lines, data, answer, closing) and write the
    file back when the change altered it. Every refusal and failure is said, never read as an empty file."""
    from vela import cli  # the catalog's kinds; imported here as every command module does
    root = pathlib.Path(args.vault).resolve()
    name = name or name_of(args)
    try:
        session = session_of(root, args, name, store.nothing)
        kinds = cli.load_catalog().kinds if store.needs_kinds else ()
        if store.needs_kinds and not kinds:
            raise cli.ToolError("the question catalog lists no kinds, so the topic map has nothing to tag to")
        state = store.load(root, session)
        before = store.dumps(state)
        lines, data, answer, closing = change(state, kinds if store.needs_kinds else (root, session))
        wrote = list(data.pop("_wrote", []))  # a page the change wrote itself (vela import page)
        if store.dumps(state) != before:
            wrote.append(sessiongit.write_text(root, store.path(session), store.dumps(state)))
        result = say.Result(name, lines=lines, data={store.key: store.path(session), **data}, wrote=wrote, answer=answer,
                            closing=closing)
    except Stop as stop:
        result = stop.result
    except topicmap.MapRefused as exc:
        result = say.Result(name, exit=say.REFUSED, refusals=[say.Refusal(
            store.rule, store.refused.format(exc=exc), "fix that part and run it again",
            "nothing to override: the map only records", audience=say.MODEL)])
    except (topicmap.MapUnreadable, cli.ToolError, ValueError, OSError) as exc:
        result = say.Result(name, exit=say.FAILED, lines=[
            say.Line(f"vela: {exc}", plain=store.failed)])
    return commands.emit(result, args, out)


def model_line(text):
    return say.Line(text, plain="", audience=say.MODEL)


def cmd_add(args, out):
    def change(state, kinds):
        if args.text and not args.kind:
            raise topicmap.MapRefused("the words need a --kind to go under")
        if not (args.kind or args.group or args.topic):
            raise topicmap.MapRefused("give --kind with the lead's words, --group, or --topic")
        if args.position and not (args.group and args.topic):
            raise topicmap.MapRefused("a --position needs the --group that holds it and the --topic it is on")
        if args.kind and not args.text:
            raise topicmap.MapRefused("a --kind needs the words the lead said")
        said, data = [], {}
        if args.position:
            data["position"] = topicmap.add_position(state, args.group, args.topic, args.position, args.reason,
                                                     args.basis)
            said.append(f"{args.group} on {args.topic}: {args.position}")
        elif args.group:
            group = topicmap.name_group(state, args.group)
            data["group"] = group
            said.append(f"group {group['name']} (named {group['named']})")
        if args.kind:
            data["note"] = topicmap.add_note(state, kinds, args.kind, args.text, args.topic)
            said.append(f"{args.kind}: {data['note']['text']}")
        elif args.topic and not args.position:
            topicmap.set_topic(state, args.topic)
            said.append(f"topic: {args.topic}")
        return [model_line("added " + "; ".join(said))], data, "", ""
    return run(args, out, change)


def cmd_open(args, out):
    def change(state, kinds):
        item = topicmap.open_item(state, kinds, args.item_type, args.text, args.kind, args.topic)
        lines = [model_line(f"#{item['n']} waiting ({item['type']})")]
        count = len(topicmap.waiting(state))
        if count >= topicmap.SUMMARIZE_AT:
            lines.append(model_line(f"{count} items wait: summarize before opening another thread (map next)."))
        return lines, {"item": item, "waiting": count}, "", ""
    return run(args, out, change)


def cmd_close(args, out):
    def change(state, kinds):
        item = topicmap.close_item(state, args.number, args.outcome, args.how)
        return [model_line(f"#{item['n']} {item['state']}")], {"item": item,
                                                               "waiting": len(topicmap.waiting(state))}, "", ""
    return run(args, out, change)


def cmd_next(args, out):
    def change(state, kinds):
        found = topicmap.moves(state, kinds)
        return ([model_line(f"{n}. [{m.move}] {m.text}") for n, m in enumerate(found, start=1)],
                {"moves": [m.as_json() for m in found], "waiting": len(topicmap.waiting(state))}, "", "")
    return run(args, out, change)


def cmd_show(args, out):
    def change(state, kinds):
        back = topicmap.readback(state, kinds)
        counts = topicmap.coverage(state, kinds)
        said = back.items()
        lines = [model_line("covered: " + ", ".join(f"{k} {counts[k]}" for k in back.covered)
                            + " | empty: " + ", ".join(back.empty))]
        lines += [say.Line(f"#{i['n']} [{i['type']}] {i['text']}", plain=plain) for i, plain in zip(back.waiting, said)]
        if back.unheard:
            lines.append(say.Line("never asked: " + ", ".join(back.unheard), plain=said[-1]))
        data = {"covered": {k: counts[k] for k in back.covered}, "empty": list(back.empty),
                "waiting": [*back.waiting], "unheard": [*back.unheard]}
        return lines, data, back.answer(), CLOSING if back.waiting else ""
    return run(args, out, change)
