"""`vela map`: the open session's running topic map, which Dump, Discover and Grill call as the lead talks.

    vela map add --kind K "what the lead said" [--topic T]           tag a thing to a kind
    vela map add --group G                                          a group the lead named, on the roster now
    vela map add --group G --topic T --position P [--reason R] [--basis stated|guess]
    vela map open --type gap|conflict|belief|fact "text" [--kind K] [--topic T]
    vela map close N [--as settled|recorded|set-aside] [--how "..."]
    vela map next                                                    what to raise next, best first
    vela map show --for-lead                                         the read-back, about four at a time

`vela record add --kind K --group G --topic T --position P` tags the capture onto the same map through `steer`
below and prints the first `next` move after the number: sessions call `record add` for nearly every lead answer and
rarely called `map` (probe batch A, 2026-10-16), so the map rides on the call that already happens.

The core is `vela/topicmap.py`; this module only finds the open record, reads and writes the map file, and prints
through `say`. The map lives in `.vela/map/<session>.json`, so it survives a long session and a restart and anyone can
open it; it is never only in the model's memory, and never staged (guard.py's tool-state rule). Exit codes: 0 done;
1 no open session, or input the map refuses (the model's to fix); 2 the map file or the catalog can't be read or
written; 3 several open sessions here (pick with `--record`).
"""
import pathlib
from dataclasses import dataclass

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


def session_of(root, args):
    """The open record's id, or Stop: exit 1 with none open, 3 with several."""
    try:
        _, record_id = record.open_record(root, sessiongit.read_json(root, sessiongit.STATE_FILE), args.record)
    except record.Stop as stop:
        if stop.result.exit == say.REFUSED:
            raise Stop(say.Result(name_of(args), exit=say.REFUSED, lines=[say.Line(NO_SESSION)])) from stop
        found = stop.result
        raise Stop(say.Result(name_of(args), exit=found.exit, needs_lead=found.needs_lead, lines=found.lines)) from stop
    return record_id


def map_path(session):
    return f"{topicmap.FOLDER}/{session}.json"


def load(root, session):
    path = root / map_path(session)
    if not path.is_file():
        return topicmap.new_state(session)
    return topicmap.parse(path.read_text(encoding="utf-8"))


def run(args, out, change):
    """Find the session, load its map, apply `change(state, kinds)` -> (lines, data, answer, closing) and write the
    map back when the change altered it. Every refusal and failure is said, never read as an empty map."""
    from vela import cli  # its ToolError; imported here as every command module does
    root = pathlib.Path(args.vault).resolve()
    name = name_of(args)
    try:
        session = session_of(root, args)
        kinds = catalog_kinds()
        state = load(root, session)
        before = topicmap.dumps(state)
        lines, data, answer, closing = change(state, kinds)
        wrote = []
        if topicmap.dumps(state) != before:
            wrote.append(sessiongit.write_text(root, map_path(session), topicmap.dumps(state)))
        result = say.Result(name, lines=lines, data={"map": map_path(session), **data}, wrote=wrote, answer=answer,
                            closing=closing)
    except Stop as stop:
        result = stop.result
    except topicmap.MapRefused as exc:
        result = say.Result(name, exit=say.REFUSED, refusals=[say.Refusal(
            "topic map", f"The map didn't take that: {exc}.", "fix that part and run it again",
            "nothing to override: the map only records", audience=say.MODEL)])
    except (topicmap.MapUnreadable, cli.ToolError, ValueError, OSError) as exc:
        result = say.Result(name, exit=say.FAILED, lines=[
            say.Line(f"vela: {exc}", plain="I couldn't read or save the session's topic map.")])
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
        said, tagged = topicmap.tag(state, kinds, args.text, [args.kind] if args.kind else [],
                                    [args.group] if args.group else [], args.topic, args.position, args.reason,
                                    args.basis)
        data = {k: v for k, v in (("position", tagged.get("position")), ("group", (tagged["groups"] or [None])[0]),
                                  ("note", (tagged["notes"] or [None])[0])) if v is not None}
        return [model_line("added " + "; ".join(said))], data, "", ""
    return run(args, out, change)


def catalog_kinds():
    from vela import cli  # imported here as every command module does
    kinds = cli.load_catalog().kinds
    if not kinds:
        raise cli.ToolError("the question catalog lists no kinds, so the topic map has nothing to tag to")
    return kinds


@dataclass
class Steer:
    """The map as one capture leaves it: loaded and tagged in memory before the capture is written, so a tag the map
    refuses stops the capture too (a half-tagged answer would look tagged), and saved after it."""
    session: str
    kinds: tuple
    state: dict
    before: str
    said: list
    tagged: bool

    def save(self, root):
        if topicmap.dumps(self.state) == self.before:
            return []
        return [sessiongit.write_text(root, map_path(self.session), topicmap.dumps(self.state))]

    def lines(self):
        """What the model reads after the capture's number: what went on the map or that nothing did, then the one
        next move. Model-only: the lead never hears map bookkeeping."""
        out = [model_line("map: added " + "; ".join(self.said))] if self.tagged else [model_line(
            f"{UNTAGGED} (kinds: {', '.join(k.name for k in self.kinds)})")]
        first = topicmap.moves(self.state, self.kinds)[:1]
        return out + [model_line(f"next: {m.text}") for m in first]

    def data(self):
        first = topicmap.moves(self.state, self.kinds)[:1]
        return {"map": map_path(self.session), "tagged": self.tagged, "next": first[0].as_json() if first else None}


UNTAGGED = "not tagged: the map can't steer from this answer"


def steer(root, session, text, kind_names, groups, topic, position):
    """Load the session's map and tag one answer onto it in memory (see Steer). Raises MapRefused for a tag the map
    won't take, and MapUnreadable, ToolError or OSError when the map or the catalog can't be read."""
    kinds = catalog_kinds()
    state = load(root, session)
    before = topicmap.dumps(state)
    said, _ = topicmap.tag(state, kinds, text, kind_names, groups, topic, position)
    return Steer(session, kinds, state, before, said, bool(kind_names or groups))


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
