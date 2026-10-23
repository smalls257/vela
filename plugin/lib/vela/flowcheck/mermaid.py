"""The strict sequence-diagram subset: lines to tokens, tokens to a tree. Pure.

Only these lines are read; any other line is an unreadable-line problem (F10, R0):

    participant <Name> [as <App title>]
    A->>B: CON-nnn <words>                 a call; B must be CON-nnn's provider
    B-->>A: <status> <case_key>            an answer: B's drawn reply, or the first line of A's branch
    A-)B: EVT-nnn <words>                  an event published for subscriber B
    par [<words>] ... end                  right after an event line, a call an outside app makes, or a TIMER:
                                           the handler that runs when it arrives, or when the timer fires
    alt <case>[, <case>...] / else <case>[, <case>...] / end   branches on the call (or AWAIT) just before
    alt <words> / else <words> / end       as the first statement: the flow's starts, one per option, named in words.
                                           The check walks the first start only and says so (a Limit line).
    Note over X: SET <entity> <state>
    Note over X: END <outcome> [leaves <entity>=<state>[, ...]]
    Note over X: AWAIT EVT-nnn             block this thread until the event reaches X
    Note over X: TIMER <name> <band>       arm a timer (15m, 2d); it fires once per arming
    Note over X: ANSWERS FROM CONTRACT [: <case>, <case>]
                                           inside drawn handling: X answers its caller from its case table here
    Note over X: GIVEN <entity> <state>    a precondition; only before the flow's first step
    Note over X: HUMAN <words>             a person's step; changes nothing
    Note over X: ON <case>[, <case>...]: END <outcome> [leaves ...]   the same handling for every later call in this thread
    %% comment, and blank lines

A case may be written with its status ("503 unavailable"); the key is the last word.
"""
import re
from dataclasses import dataclass, field

from vela.flowcheck.tables import FlowLine, Problem

NAME = r"[A-Za-z_][\w]*"
LINE_PATTERNS = (
    ("participant", re.compile(rf"^participant\s+({NAME})(?:\s+as\s+(.+?))?\s*$")),
    ("answer", re.compile(rf"^({NAME})-->>({NAME}):\s*(\d{{3}}|ok|error)\s+(\w+)\s*$")),
    ("call", re.compile(rf"^({NAME})->>({NAME}):\s*(CON-\d+)\b\s*(.*)$")),
    ("event", re.compile(rf"^({NAME})-\)({NAME}):\s*(EVT-\d+)\b\s*(.*)$")),
    ("alt", re.compile(r"^alt\s+(.+?)\s*$")),
    ("else", re.compile(r"^else\s+(.+?)\s*$")),
    ("par", re.compile(r"^par\b\s*(.*)$")),
    ("end", re.compile(r"^end$")),
    ("note", re.compile(rf"^Note over ({NAME}):\s*(.*?)\s*$")),
)
OUTCOME = r"\w+(?:\s+(?!leaves\b)\w+)*"  # one or more words; "leaves" starts the leaves list
LEAVES = r"(?:\s+leaves\s+(\w+=\w+(?:\s*,\s*\w+=\w+)*))?"
NOTE_PATTERNS = (
    ("set", re.compile(r"^SET\s+(\S+)\s+(\w+)$")),
    ("finish", re.compile(rf"^END\s+({OUTCOME}){LEAVES}$")),
    ("await", re.compile(r"^AWAIT\s+((?:EVT|CON)-\d+)$")),
    ("timer", re.compile(r"^TIMER\s+([a-z][a-z0-9_]*)\s+(\d+\s?[a-z]+)$")),
    ("contract", re.compile(r"^ANSWERS FROM CONTRACT(?:\s*:\s*(.+))?$")),
    ("given", re.compile(r"^GIVEN\s+(\S+)\s+(\w+)$")),
    ("human", re.compile(r"^HUMAN\s+(.+)$")),
    ("on", re.compile(rf"^ON\s+(.+?):\s*END\s+({OUTCOME}){LEAVES}$")),
)


def case_keys(text):
    """("timeout", "unavailable") from "timeout, 503 unavailable". None when a part is not a key."""
    keys = []
    for part in text.split(","):
        words = part.split()
        if not words or not re.match(r"^\w+$", words[-1]) or (len(words) == 2 and not words[0].isdigit()) or len(words) > 2:
            return None
        keys.append(words[-1])
    return tuple(keys)


def _leaves(text):
    return tuple(tuple(pair.strip().split("=", 1)) for pair in text.split(",")) if text else ()


def tokenize(lines, first_line, path, item, problems):
    """FlowLines from the diagram's lines; `first_line` is the file line of lines[0] ("sequenceDiagram")."""
    out = []
    for n, raw in enumerate(lines, first_line):
        text = raw.strip()
        if not text or text.startswith("%%") or text == "sequenceDiagram":
            continue
        token = _token(text, n)
        if token is None:
            problems.append(Problem(f"{path}:{n}", f"Unreadable line, outside the checked subset: {text}", item))
        else:
            out.append(token)
    return out


def _token(text, n):
    for kind, pattern in LINE_PATTERNS:
        found = pattern.match(text)
        if not found:
            continue
        if kind in ("alt", "else"):
            # keys is None for an option written in words: only an opening alt may (the parser says so anywhere else)
            return FlowLine(n, kind, (case_keys(found.group(1)) or None, found.group(1)))
        if kind == "note":
            return _note(found.group(1), found.group(2), n)
        return FlowLine(n, kind, tuple(g if g is not None else "" for g in found.groups()))
    return None


def _note(actor, body, n):
    for kind, pattern in NOTE_PATTERNS:
        found = pattern.match(body)
        if not found:
            continue
        groups = found.groups()
        if kind == "finish":
            return FlowLine(n, kind, (actor, groups[0], _leaves(groups[1])))
        if kind == "on":
            keys = case_keys(groups[0])
            return FlowLine(n, kind, (actor, keys, groups[1], _leaves(groups[2]))) if keys else None
        if kind == "contract":
            keys = case_keys(groups[0]) if groups[0] else ()
            return FlowLine(n, kind, (actor, keys)) if keys is not None else None
        return FlowLine(n, kind, (actor,) + groups)
    return None


# --- the tree -------------------------------------------------------------------------------------------------------

@dataclass
class Branch:
    line: int
    keys: tuple
    body: list
    answer: object = None  # the decorating answer line, when the branch opens with one
    label: str = ""  # the option as written: the words of an opening alt's start


@dataclass
class Node:
    kind: str  # call | reply | contract | publish | set | finish | await | timer | given | human | on
    line: int
    actor: str
    parts: tuple
    handling: object = None  # call: the provider's drawn steps up to its reply (list), or None when not drawn
    branches: object = None  # call/await: [Branch], or None when no alt follows
    handler: object = None  # publish, a call an outside app makes, or a timer: the par block's steps (list), or None
    handler_line: int = 0


@dataclass
class Tree:
    nodes: list
    participants: dict = field(default_factory=dict)  # name -> (title, line)
    starts: list = field(default_factory=list)  # [Branch] of an opening alt written in words; `nodes` holds the first one's walk


def actor_of(token):
    if token.kind in ("call", "answer", "event"):
        return token.parts[0]
    if token.kind in ("set", "finish", "await", "timer", "given", "human", "on", "contract"):
        return token.parts[0]
    return None


class _Parser:
    def __init__(self, tokens, path, item, problems):
        self.tokens, self.i, self.path, self.item, self.problems = list(tokens), 0, path, item, problems
        self.participants = {}

    def problem(self, line, text):
        self.problems.append(Problem(f"{self.path}:{line}", text, self.item))

    def peek(self):
        return self.tokens[self.i] if self.i < len(self.tokens) else None

    def take(self):
        self.i += 1
        return self.tokens[self.i - 1]

    def opening_alt(self):
        """The branches of an alt written in words as the flow's first statement (after the participants), else []."""
        while self.peek() is not None and self.peek().kind == "participant":
            token = self.take()
            self.participants.setdefault(token.parts[0], (token.parts[1] or token.parts[0], token.line))
        token = self.peek()
        if token is None or token.kind != "alt" or token.parts[0] is not None:
            return []
        self.take()
        return self.alt_rest(token, words_allowed=True)

    def block(self, stop, opener=None):
        out = []
        while self.peek() is not None:
            token = self.peek()
            if token.kind in stop:
                return out
            if token.kind in ("else", "end"):
                self.take()
                self.problem(token.line, f"'{token.kind}' closes no alt or par.")
            elif token.kind == "alt":
                self.take()
                self.problem(token.line, "This alt follows no call or AWAIT, so there is nothing to branch on.")
                self.alt_rest(token)
            elif token.kind == "par":
                self.take()
                self.problem(token.line, "A par block opens a handler, so it goes right after an event line.")
                self.closed(token, self.block({"end"}, token))
            elif token.kind == "participant":
                self.take()
                name, title = token.parts
                self.participants.setdefault(name, (title or name, token.line))
            else:
                out += self.statement()
        if opener is not None:
            self.problem(opener.line, f"The {opener.kind} block opened here is never closed with end.")
        return out

    def closed(self, opener, body):
        token = self.peek()
        if token is not None and token.kind == "end":
            self.take()
        return body

    def words_only(self, token, allowed):
        """An option written in words names a start, so it belongs to the opening alt alone: anywhere else it is the
        unreadable line it always was."""
        if token.parts[0] is None and not allowed:
            self.problem(token.line, f"Unreadable line, outside the checked subset: {token.kind} {token.parts[1]}")

    def alt_rest(self, opener, words_allowed=False):
        """Branches from an alt token already taken to its end."""
        branches = [Branch(opener.line, opener.parts[0] or (), [], label=opener.parts[1])]
        self.words_only(opener, words_allowed)
        branches[0].body = self.block({"else", "end"}, opener)
        while self.peek() is not None and self.peek().kind == "else":
            token = self.take()
            self.words_only(token, words_allowed)
            branch = Branch(token.line, token.parts[0] or (), [], label=token.parts[1])
            branch.body = self.block({"else", "end"}, opener)
            branches.append(branch)
        if self.peek() is not None and self.peek().kind == "end":
            self.take()
        return branches

    def statement(self):
        token = self.take()
        node = Node(token.kind if token.kind not in ("answer", "event") else {"answer": "reply", "event": "publish"}[token.kind],
                    token.line, actor_of(token), token.parts)
        after = []
        if token.kind == "call":
            after = self.drawn_handling(node)
            if self.peek() is not None and self.peek().kind == "par":
                opener = self.take()
                node.handler, node.handler_line = self.closed(opener, self.block({"end"}, opener)), opener.line
        elif token.kind in ("event", "timer"):
            if self.peek() is not None and self.peek().kind == "par":
                opener = self.take()
                node.handler, node.handler_line = self.closed(opener, self.block({"end"}, opener)), opener.line
            if token.kind == "event" and self.peek() is not None and self.peek().kind == "alt":
                alt = self.take()
                self.problem(alt.line, "A branch on a handler's outcome cannot sit in the producer's thread: the producer "
                                       "cannot see it. If it needs to know, AWAIT an event the handler publishes.")
                self.alt_rest(alt)
        if token.kind in ("call", "await") and self.peek() is not None and self.peek().kind == "alt" and not after:
            node.branches = self.alt_rest(self.take())
        return [node] + after

    def drawn_handling(self, call):
        """The provider's steps after a call, up to its reply to the caller. They count as drawn handling only when a
        reply to the caller is among them; otherwise they are ordinary steps that follow the call, returned to the block."""
        caller, provider = call.parts[0], call.parts[1]
        body = []
        while self.peek() is not None:
            token = self.peek()
            if token.kind == "answer" and token.parts[0] == provider and token.parts[1] == caller:
                self.take()
                body.append(Node("reply", token.line, provider, token.parts))
                call.handling = body
                return []
            if token.kind == "contract" and token.parts[0] == provider:
                self.take()
                body.append(Node("contract", token.line, provider, token.parts))
                call.handling = body
                return []
            if token.kind in ("alt", "else", "end", "par", "participant") or actor_of(token) != provider:
                break
            body += self.statement()
        if _replies(body, provider, caller):
            call.handling = body
            return []
        return body


def _replies(nodes, provider, caller):
    for node in nodes:
        if (node.kind == "reply" and node.parts[0] == provider and node.parts[1] == caller) or \
                (node.kind == "contract" and node.parts[0] == provider):
            return True
        for branch in node.branches or ():
            if _replies(branch.body, provider, caller):
                return True
    return False


def parse_tree(flow, problems):
    parser = _Parser(flow.lines, flow.path, flow.id, problems)
    starts = parser.opening_alt()
    nodes = parser.block(set())
    if starts:
        nodes = starts[0].body + nodes  # the check walks the first start; the rest is the shared tail
    return Tree(nodes, parser.participants, starts)
