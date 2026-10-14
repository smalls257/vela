"""Each flow's error cases, for the branch picker on the Flows view (design 19, decision D8). Pure: a vault in, data out.

The happy path shows by default; a picker above the diagram swaps in one branch at a time, one option per answer a
call can give (success, not found, times out, refused, gives up), grouped by the call it branches at. Every option
carries the flow check's word on it: "finding" when a finding is about that answer at that call, "not fully checked"
when the check did not get to the end. Nothing is shown as passed unless the check ran to the end and passed (R0).

What it exists to prevent: a Paper Tiger diagram that shows only the success path, and so says nothing about what the
teams must build when a call goes wrong; and a second reading of the diagram that drifts from the checker's (a
Leaky Narrative between the two). So the diagram is read once, by the flow checker's own readers
(`flowcheck.readers.read_catalog`, `flowcheck.mermaid.parse_tree`); the answers' words come from the contract's case
table through `cases.case_table`; and the markers from `flowcheck.check_catalog`, the run `check-slice` makes.
Nothing here parses mermaid.

A branch's steps are one path through the diagram: the call, the provider's drawn handling if any, the branch for the
chosen answer, and every later step that follows from it, with every other choice on the happy path. The walk is
depth-first and tries the happy answer first, so the path found is the one closest to the happy path. Flows with no
strict diagram, or one with no alt, keep the played view as it is and get one line saying their error cases are not
drawn yet.
"""
from dataclasses import dataclass

from planner import cases, flowcheck
from planner.flowcheck import mermaid, readers
from planner.flowcheck.findings import TITLES

# The budget the dashboard's slice check uses (slices_data.CHECK_STATES): the same run, so the same verdict.
CHECK_STATES = 20_000
# Paths walked while looking for one branch's path; past it the branch says it could not be drawn, never a guess.
PATH_BUDGET = 5_000
SYNTHETIC_WORDS = {"timeout": "Times out", "gave_up": "Gives up after its retries"}
NOT_DRAWN_NOTE = "Error cases aren't drawn yet: this flow has no checked sequence diagram with alt branches."


def case_words(key):
    """"Not found" from not_found; the checker's own answers in the words a person says."""
    return SYNTHETIC_WORDS.get(key) or key.replace("_", " ").capitalize()


@dataclass(frozen=True, eq=False)
class Path:
    steps: tuple = ()
    ended: bool = False
    replies: tuple = ()  # (from, to or None, keys): answers drawn on this path, read by the call whose handling it is
    choices: frozenset = frozenset()  # (call line, answer key)

    def then(self, other):
        return Path(self.steps + other.steps, other.ended, self.replies + other.replies, self.choices | other.choices)


EMPTY = Path()


def step(kind, line, text, **more):
    out = {"kind": kind, "line": line, "text": text, "alt": False}
    out.update(more)
    return out


def flagged(path):
    """The same path with every step marked as off the happy path."""
    return Path(tuple(dict(s, alt=True) for s in path.steps), path.ended, path.replies, path.choices)


def lines_within(nodes):
    found = set()
    for node in nodes or ():
        found.add(node.line)
        found |= lines_within(node.handling)
        found |= lines_within(node.handler)
        for branch in node.branches or ():
            found |= lines_within(branch.body)
    return found


def keys_words(keys):
    words = [case_words(k).lower() for k in keys]
    return words[0] if len(words) == 1 else ", ".join(words[:-1]) + " or " + words[-1]


class Walker:
    """Walks one parsed diagram into paths. In a search, `target` is the (call line, answer) wanted on the path: at its
    call the target is tried first, and before it the answers whose branch can still reach it."""

    def __init__(self, tree, catalog, entity_keys):
        self.tree, self.catalog, self.entity_keys = tree, catalog, entity_keys
        self.target = None
        self.points = {}  # call line -> {"item", "keys": every answer it can give, "happy"}
        self.unhandled = set()  # (line, key): an answer the call can give that no branch and no ON rule takes

    def title(self, name):
        return self.tree.participants.get(name, (name, 0))[0]

    def table(self, item):
        return self.catalog.contracts.get(item) if item else None

    def case(self, item, key):
        table = self.table(item)
        return next((c for c in table.cases if c.key == key), None) if table else None

    def error(self, item, key):
        found = self.case(item, key)
        return key in SYNTHETIC_WORDS or bool(found and found.is_error)

    def entity_title(self, name):
        found = self.catalog.entity(name)
        return found.title if found else name

    # --- the walk --------------------------------------------------------------------------------------------------
    def block(self, nodes, rules=()):
        if not nodes:
            yield EMPTY
            return
        head, rest = nodes[0], nodes[1:]
        later = rules + ((head,) if head.kind == "on" else ())
        for first in self.node(head, rules):
            if first.ended:
                yield first
                continue
            for after in self.block(rest, later):
                yield first.then(after)

    def node(self, node, rules):
        kind, actor, parts, line = node.kind, node.actor, node.parts, node.line
        if kind == "call":
            yield from self.call(node, rules)
        elif kind == "await":
            head = Path((step("note", line, f"Waits for {parts[1]}", over=[actor], tag="wait", item=parts[1]),))
            keys = list(dict.fromkeys(k for b in node.branches or () for k in b.keys))
            yield from self.choose(node, rules, parts[1], None, [(k, EMPTY) for k in keys], head)
        elif kind == "reply":
            frm, to, status, key = parts
            yield Path((step("reply", line, f"{status} {case_words(key).lower()}", **{"from": frm, "to": to, "case": key}),),
                       replies=((frm, to, (key,)),))
        elif kind == "publish":
            frm, to, evt, words = parts
            arrow = Path((step("event", line, f"{evt} {words}".strip(), **{"from": frm, "to": to, "item": evt}),))
            yield from self.with_handler(arrow, node, f"When {evt} reaches {self.title(to)}", to)
        elif kind == "timer":
            yield from self.with_handler(Path((step("note", line, f"Timer {parts[1]}, {parts[2]}", over=[actor], tag="timer"),)),
                                         node, f"When the {parts[1]} timer fires", actor)
        elif kind == "contract":
            keys = tuple(parts[1] or ())
            said = "Answers from its contract" + (f": {keys_words(keys)}" if keys else "")
            yield Path((step("note", line, said, over=[actor], tag="contract"),), replies=((actor, None, keys),))
        elif kind in ("set", "given"):
            words = f"{self.entity_title(parts[1])}: {parts[2].replace('_', ' ')}"
            yield Path((step("note", line, words if kind == "set" else f"Starts with {words}", over=[actor], tag=kind,
                             key=self.entity_keys.get(parts[1], ""), entity=self.entity_title(parts[1]),
                             entity_name=parts[1], state=parts[2]),))
        elif kind == "human":
            yield Path((step("note", line, parts[1], over=[actor], tag="person"),))
        elif kind == "finish":
            yield Path((self.end_step(line, actor, parts[1], parts[2]),), ended=True)
        elif kind == "on":
            yield Path((step("note", line, f"If a later call {keys_words(parts[1])}: ends, {parts[2].replace('_', ' ')}",
                             over=[actor], tag="rule"),))

    def end_step(self, line, actor, outcome, leaves):
        left = "".join(f"; leaves {self.entity_title(e)} {s.replace('_', ' ')}" for e, s in leaves)
        return step("note", line, f"Ends: {outcome.replace('_', ' ')}{left}", over=[actor], tag="end", outcome=outcome.replace("_", " "),
                    outcome_key=outcome, leaves=[tuple(pair) for pair in leaves])

    def with_handler(self, head, node, words, who):
        if node.handler is None:
            yield head
            return
        opener = Path((step("note", node.handler_line, words, over=[who], tag="handler"),))
        for inner in self.block(node.handler):  # a thread of its own: its END ends the handler, not the flow
            steps = tuple(dict(s, tag="handler_end") if s.get("tag") == "end" else s for s in inner.steps)
            yield head.then(opener).then(Path(steps, False, (), inner.choices))

    def call(self, node, rules):
        caller, provider, con, words = node.parts
        table = self.table(con)
        head = Path((step("call", node.line, words.strip() or con, **{"from": caller, "to": provider, "item": con}),))
        retried = table.retries.on if table and table.retries else ()
        synthetic = [k for k, on in (("timeout", bool(table and table.timeout) and "timeout" not in retried),
                                      ("gave_up", bool(table and table.retries and table.retries.max > 1))) if on]
        if node.handling is not None:
            # a drawn provider answers as its drawing says: each path through its handling gives the answer it replies
            answers = []
            for n, inner in enumerate(self.block(node.handling)):
                if n >= PATH_BUDGET:
                    break
                handled = Path(inner.steps, False, (), inner.choices)
                answers += [(key, handled) for key in self.reply_keys(inner, provider, caller, con)]
            answers += [(key, EMPTY) for key in synthetic]
        else:
            keys = [c.key for c in table.cases if c.key not in retried] if table else []
            keys += [k for k in synthetic if k not in keys]
            keys += [k for b in node.branches or () for k in b.keys if k not in keys]
            answers = [(key, EMPTY) for key in keys]
        yield from self.choose(node, rules, con, provider, answers, head)

    def reply_keys(self, path, provider, caller, con):
        """The answers a drawn provider's handling gives its caller on this path: its last drawn reply, or, where it
        answers from its contract, each answer it names (all its cases when it names none)."""
        for frm, to, keys in reversed(path.replies):
            if frm == provider and to in (caller, None):
                if to is None and not keys:
                    table = self.table(con)
                    return [c.key for c in table.cases] if table else []
                return list(keys)
        return []

    def answer(self, line, actor, provider, item, key):
        """An answer the branch does not draw itself: a dashed reply from the provider, or, for one that is not a reply
        (a timeout, giving up, an awaited event), a note over the one waiting."""
        found = self.case(item, key)
        if provider and found:
            return step("reply", line, f"{found.status} {case_words(key).lower()}", **{"from": provider, "to": actor, "case": key})
        return step("note", line, case_words(key), over=[actor], case=key, tag="timeout" if key in SYNTHETIC_WORDS else "answer")

    def choose(self, node, rules, item, provider, answers, head):
        """Every way the step at `node` can go: one alternative per answer, in the order `ordered` gives."""
        line, actor, branches = node.line, node.actor, node.branches or []
        if not branches and not any(self.on_rule(rules, actor, k) for k, _ in answers):
            # nothing branches here: the step goes on as drawn, through each path of a drawn provider's handling
            pres = []
            for _, pre in answers:
                if pre.steps and not any(p is pre for p in pres):
                    pres.append(pre)
            for pre in pres or [EMPTY]:
                yield head.then(pre)
            return
        for key, pre in self.ordered(line, item, answers, branches, rules, actor):
            off = key != self.points[line]["happy"]
            choice = Path(choices=frozenset({(line, key)}))
            branch = next((b for b in branches if key in b.keys), None)
            mark = flagged if off else (lambda p: p)
            # a drawn provider's handling keeps its own marks: its steps are off the happy path only where it chose so
            lead = pre if pre.steps else mark(Path((self.answer(line, actor, provider, item, key),)))
            first = branch.body[0] if branch is not None and branch.body else None
            if not pre.steps and first is not None and first.kind == "reply" and first.parts[:2] == (provider, actor):
                lead = EMPTY  # the branch draws the provider's answer on its own first line
            if branch is not None:
                for body in self.block(branch.body, rules):
                    yield head.then(lead).then(choice).then(mark(body))
            else:
                rule = self.on_rule(rules, actor, key)
                if rule is None:  # no alt here: the flow goes on after the call
                    yield head.then(lead).then(choice)
                    continue
                yield head.then(lead).then(choice).then(mark(Path((self.end_step(rule.line, actor, rule.parts[2], rule.parts[3]),), ended=True)))

    @staticmethod
    def on_rule(rules, actor, key):
        """The latest ON rule of this thread that takes `key` for calls `actor` makes (revision 2, item 14)."""
        return next((r for r in reversed(rules) if r.actor == actor and key in (r.parts[1] or ())), None)

    def ordered(self, line, item, answers, branches, rules, actor):
        """The drawable answers, happy first (the first that is not an error), then the rest as written. In a search,
        the target first at its own call, and before it the answers whose branch can still reach it. An answer no
        branch and no ON rule takes is recorded as not drawn."""
        def drawable(key):  # with no alt, an answer no ON rule takes goes on to the next step as drawn
            return not branches or any(key in b.keys for b in branches) or self.on_rule(rules, actor, key) is not None
        usable = [a for a in answers if drawable(a[0])]
        self.unhandled |= {(line, k) for k, _ in answers if not drawable(k)}
        happy = next((i for i, (k, _) in enumerate(usable) if not self.error(item, k)), 0)
        order = ([usable[happy]] + [a for i, a in enumerate(usable) if i != happy]) if usable else []
        point = self.points.setdefault(line, {"item": item, "keys": [], "happy": order[0][0] if order else ""})
        point["keys"] += [k for k in dict.fromkeys(k for k, _ in answers) if k not in point["keys"]]
        if self.target is None:
            return order
        want_line, want_key = self.target
        if want_line == line:
            return sorted(order, key=lambda a: a[0] != want_key)

        def reaches(answer):
            key, pre = answer
            branch = next((b for b in branches if key in b.keys), None)
            return want_line in (lines_within(branch.body) if branch else set()) or any(c[0] == want_line for c in pre.choices)
        return sorted(order, key=lambda a: not reaches(a))

    def survey(self):
        """Walk every path once, up to the budget, so every call that branches is known, even inside other branches.
        False when the budget ran out first."""
        for n, _ in enumerate(self.block(self.tree.nodes)):
            if n >= PATH_BUDGET:
                return False
        return True

    def search(self, target=None):
        """The first path, in happy-first order, that takes `target` (call line, answer); the happy path for None.
        None when the budget runs out first."""
        self.target = target
        try:
            for n, path in enumerate(self.block(self.tree.nodes)):
                if n >= PATH_BUDGET:
                    return None
                if target is None or target in path.choices:
                    return path
            return None
        finally:
            self.target = None


# --- the vault side: words, keys, the check ------------------------------------------------------------------------

def answers_of(vault):
    """{contract id: {answer key: (status, answer)}} from each contract's case table, through cases.case_table."""
    out = {}
    for contract in vault.contracts:
        table = cases.case_table(contract.page, contract)
        if table is not None:
            out[contract.id] = {c.key: (c.status, c.answer) for c in table.cases}
    return out


def participant_keys(tree, catalog, vault, keys):
    """{participant name: explorer key} for the apps the vault has a page for; the page finds the rest by title."""
    by_app = {readers._app_key(p.id): keys.page(p) for p in vault.apps}
    out = {}
    for name, (title, _) in tree.participants.items():
        app = catalog.app_named(title)
        if app is not None and app.key in by_app:
            out[name] = by_app[app.key]
    return out


def entity_keys(catalog, vault, keys):
    by_path = {p.path: keys.page(p) for p in vault.pages}
    return {name: by_path[str(e.where).split(":", 1)[0]] for name, e in catalog.entities.items()
            if str(e.where).split(":", 1)[0] in by_path}



# --- the played view: one diagram, so a branch is drawn as the flow's own steps, in plain words ---------------------

QUIET_TAGS = ("set", "given", "rule", "handler", "handler_end", "contract")  # the checker's bookkeeping, not steps a person reads
NO_ENDING = "This branch doesn't say what happens next."


def answer_words(item, key, answers):
    """"Agreed: calendar entries only" from the case table's Answer; the checker's own answers in words."""
    if key == "timeout":
        return "no answer in time"
    if key == "gave_up":
        return "no answer after the retries"
    said = answers.get(item, {}).get(key, ("", ""))[1]
    return said or case_words(key).lower()


def sentence_part(text):
    """A cell's words as the tail of "It ends here: ...": no closing full stop, and a lower-case first letter unless
    the word is a name or an acronym ("Heron", "API")."""
    said = text.strip().rstrip(".").strip()
    if len(said) > 1 and said[0].isupper() and said[1].islower() and said.split()[0].lower() in COMMON_OPENERS:
        said = said[0].lower() + said[1:]
    return said


# Opening words that are not names, so "The agent tells..." reads "It ends here: the agent tells...".
COMMON_OPENERS = {"the", "a", "an", "no", "nothing", "it", "they", "there", "this", "that", "their", "his", "her", "its"}


def joined(parts):
    return parts[0] if len(parts) == 1 else ", ".join(parts[:-1]) + " and " + parts[-1]


def ending_words(end, outcomes, words, settled):
    """What an ending means, in the plan's own words: the flow page's `| Outcome | What the person sees |` row for it;
    else the meanings of the states the journey ends in (the states its END leaves, then those set just before it,
    from the entity pages' `| State | Means |` tables), when every one has its words; else its outcome name. The
    outcome name is the last resort, never a guess at a sentence."""
    row = (outcomes or {}).get(end.get("outcome_key", ""))
    if row:
        return sentence_part(row)
    pairs = list(dict.fromkeys([tuple(p) for p in end.get("leaves") or ()] + list(settled)))
    meanings = [(words or {}).get(entity, {}).get(state, ("", ""))[0] for entity, state in pairs]
    if pairs and all(meanings):
        return joined([sentence_part(m) for m in dict.fromkeys(meanings)])
    return end["outcome"]


def outcome_words(page):
    """{END outcome: what the person sees} from a flow page's optional `| Outcome | What the person sees |` table."""
    found = {}
    for table in page.tables if page is not None else ():
        head = [c.strip().lower() for c in table.header or ()]
        if head[:2] != ["outcome", "what the person sees"]:
            continue
        for row in table.rows:
            cells = [c.strip() for c in row] + ["", ""]
            if cells[0].strip("`") and cells[1]:
                found[cells[0].strip("`")] = cells[1]
    return found


def played(steps, names, answers, contract_titles, ended=True, outcomes=None, words=None):
    """The path as the played view's steps: a call and its answer are one step ("Desktop agent asks Consent and
    identity to record the person's consent. Answer: kept."), an answer that comes later is its own step, a person's
    step stays, and the checker's bookkeeping (states set, ON rules) is left out. The journey's ending is the last
    step, a band in plain words ("It ends here: the agent tells the person Heron isn't on."), from `ending_words`
    with the flow page's outcome rows (`outcomes`) and the entities' state words (`words`); a path the diagram leaves
    without an ending says so instead, which is a finding of its own for the reader. Each step says whether it leaves
    the happy path (`differs`). No status codes and no state names."""
    out, open_calls, i = [], [], 0
    settled = []  # (entity, state) set since the last step a person reads: the states the journey ends in
    steps = list(steps)
    while i < len(steps):
        s = steps[i]
        if s.get("tag") in ("set", "given") and s.get("entity_name"):
            settled.append((s["entity_name"], s["state"]))
        if s.get("tag") in QUIET_TAGS:
            i += 1
            continue
        who = lambda n: names.get(n, n)  # noqa: E731
        if s.get("tag") == "end":
            said = ending_words(s, outcomes, words, settled)
            out.append({"kind": "end", "over": s.get("over", []), "differs": s["alt"], "short": f"It ends here: {said}."})
            settled = []
            i += 1
            continue
        settled = []
        if s["kind"] == "call":
            nxt = steps[i + 1] if i + 1 < len(steps) else None
            ask = f"{who(s['from'])} asks {who(s['to'])} to {s['text']}"
            if nxt and nxt["kind"] == "reply" and (nxt["from"], nxt["to"]) == (s["to"], s["from"]):
                said = answer_words(s.get("item"), nxt.get("case"), answers)
                out.append({"kind": "request", "from": s["from"], "to": s["to"], "item": s.get("item"), "differs": s["alt"] or nxt["alt"],
                            "short": f"{ask}. Answer: {said}.", "answer": said})
                i += 2
                continue
            if nxt and nxt["kind"] == "note" and nxt.get("tag") == "timeout" and nxt.get("over") == [s["from"]]:
                said = answer_words(s.get("item"), nxt.get("case"), answers)
                out.append({"kind": "send", "from": s["from"], "to": s["to"], "item": s.get("item"), "differs": s["alt"] or nxt["alt"],
                            "short": f"{ask}: {said}.", "answer": said})
                i += 2
                continue
            open_calls.append((s["from"], s["to"], s.get("item")))
            out.append({"kind": "send", "from": s["from"], "to": s["to"], "item": s.get("item"), "differs": s["alt"], "short": f"{ask}."})
        elif s["kind"] == "reply":
            item = next((c for f, to, c in reversed(open_calls) if (to, f) == (s["from"], s["to"])), None)
            open_calls = [c for c in open_calls if c[2] != item] if item else open_calls
            said = answer_words(item, s.get("case"), answers)
            title = contract_titles.get(item, "")
            out.append({"kind": "answer", "from": s["from"], "to": s["to"], "item": item, "differs": s["alt"],
                        "short": f"{who(s['from'])} answers {who(s['to'])}{' on ' + title.lower() if title else ''}: {said}.", "answer": said})
        elif s["kind"] == "event":
            out.append({"kind": "send", "from": s["from"], "to": s["to"], "item": s.get("item"), "differs": s["alt"],
                        "short": f"{who(s['from'])} tells {who(s['to'])}: {s['text']}."})
        else:
            words = s["text"] if s.get("tag") != "timeout" else f"{s['text']}"
            out.append({"kind": "note", "over": s.get("over", []), "differs": s["alt"], "short": words.rstrip(".") + "."})
        i += 1
    if not ended or not out or out[-1]["kind"] != "end":
        out.append({"kind": "end", "over": [], "differs": True, "short": NO_ENDING, "open": True})
    for n, step in enumerate(out, 1):
        step["n"] = n
    return out


def state_words(vault, catalog):
    """{entity name: {state: (what it means, what it means not to be in it)}} from each entity page's optional
    `| State | Means | Not in it |` table, under every name the checker finds the entity by."""
    pages = {p.path: p for p in vault.pages}
    out = {}
    for name, entity in catalog.entities.items():
        page = pages.get(str(entity.where).split(":", 1)[0])
        if page is None:
            continue
        found = {}
        for table in page.tables:
            head = [c.strip().lower() for c in table.header or ()]
            if head[:2] != ["state", "means"]:
                continue
            for row in table.rows:
                cells = [c.strip() for c in row] + ["", ""]
                if cells[0]:
                    found[cells[0].strip("`")] = (cells[1], cells[2] if len(head) > 2 else "")
        if found:
            out[name] = found
    return out


def labeled_invariant(text, words):
    """The broken invariant as a sentence of the entities' own words ("The agent says consent wasn't kept, while
    Consent and identity has kept it (calendar only)."), or None when a state it needs has no words written."""
    expr, problem = readers.parse_invariant(text)
    if expr is None or problem:
        return None

    def said(e, positive):
        if e[0] == "not":
            return said(e[1], not positive)
        if e[0] == "is":
            pair = words.get(e[1], {}).get(e[2])
            return (pair[0] if positive else pair[1]) or None if pair else None
        if e[0] in ("and", "or"):
            a, b = said(e[1], positive), said(e[2], positive)
            joiner = "and" if (e[0] == "and") == positive else "or"
            return a and b and f"{a} {joiner} {b}"
        return None

    if expr[0] == "implies":
        a, b = said(expr[1], True), said(expr[2], False)
    elif expr[0] == "not" and expr[1][0] == "and":
        a, b = said(expr[1][1], True), said(expr[1][2], True)
    else:
        a, b = said(expr, False), ""
    if not a or b is None:
        return None
    sentence = f"{a}, while {b}" if b else a
    return sentence[0].upper() + sentence[1:] + "."


def plain_invariant(text, catalog):
    """A broken invariant in words a person reads, from its entities' titles and its states:
    "This flow can reach a moment when Transcripts read is at “read” while Consent is not at “calendar and
    transcripts”." None when the expression is not one of the shapes worded here."""
    expr, problem = readers.parse_invariant(text)
    if expr is None or problem:
        return None

    def title(name):
        found = catalog.entity(name)
        return found.title if found else name.replace("_", " ")

    def pos(e):
        if e[0] == "is":
            return f"{title(e[1])} is at “{e[2].replace('_', ' ')}”"
        if e[0] == "not" and e[1][0] == "is":
            return neg(e[1])
        if e[0] == "and":
            a, b = pos(e[1]), pos(e[2])
            return a and b and f"{a} and {b}"
        if e[0] == "or":
            a, b = pos(e[1]), pos(e[2])
            return a and b and f"{a} or {b}"
        if e[0] == "not":
            return neg(e[1])
        return None

    def neg(e):
        if e[0] == "is":
            return f"{title(e[1])} is not at “{e[2].replace('_', ' ')}”"
        if e[0] == "not":
            return pos(e[1])
        if e[0] == "or":
            a, b = neg(e[1]), neg(e[2])
            return a and b and f"{a} and {b}"
        return None

    if expr[0] == "implies":
        a, b = pos(expr[1]), neg(expr[2])
        said = a and b and f"{a} while {b}"
    elif expr[0] == "not" and expr[1][0] == "and":
        a, b = pos(expr[1][1]), pos(expr[1][2])
        said = a and b and f"{a} while {b}"
    else:
        said = neg(expr)
    return f"This flow can reach a moment when {said}." if said else None


INVARIANT = __import__("re").compile(r'^The invariant "(?P<text>.+?)" of .+? no longer holds\.')


def plain_summary(f, catalog, words=None):
    """(sentence, expression or ""): the finding in plain words, and the checker's own expression for a disclosure
    when the sentence had to be written around it."""
    found = INVARIANT.match(f.summary)
    if not found:
        return f.summary, ""
    said = labeled_invariant(found.group("text"), words or {}) or plain_invariant(found.group("text"), catalog)
    return (said or "This flow can break a rule the plan says must always hold."), f.summary


def finding_record(f, catalog, words=None):
    plain, expression = plain_summary(f, catalog, words)
    return {"code": f.code, "title": TITLES.get(f.code, f.code), "summary": plain, "expression": expression, "trace": list(f.trace),
            "owners": list(f.owners), "items": list(f.items), "where": f.where, "case": f.case,
            "severity": f.severity, "covered": f.covered}


def _line(where):
    tail = str(where).rsplit(":", 1)[-1]
    return int(tail) if tail.isdigit() else 0


def limits_for(path, walker, stated, shared):
    """Which of the checker's stated limits a branch's own path runs into: a timer when it arms one, a shared entity
    when a step changes it or starts from it, or calls a contract whose cases set it or answer by it, and a budget
    stop always (what was not explored is not claimed)."""
    steps = path.steps if path is not None else ()
    timers = any(s.get("tag") == "timer" for s in steps)
    touched = {s.get("entity") for s in steps if s.get("entity")}
    for s in steps:
        table = walker.table(s.get("item")) if s.get("kind") == "call" else None
        for case in table.cases if table else ():
            touched |= {walker.entity_title(e) for e, _ in case.sets} | {walker.entity_title(w[0]) for w in case.when}
    touched &= set(shared)
    out = []
    for i, text in enumerate(stated):
        if text.startswith("A timer"):
            if timers:
                out.append(i)
        elif text.startswith("Not explored"):
            out.append(i)
        elif any(text.startswith(name) or f", {name}" in text or f" and {name}" in text for name in touched):
            out.append(i)
    return out


def marks_of(findings, not_checked):
    """The flow check's words on one option: a finding (or a warning), and "not fully checked" whenever the check did
    not reach the end, so an option is never read as passed when it was not checked."""
    marks = []
    if any(f["severity"] == "error" for f in findings):
        marks.append("finding")
    elif any(f["severity"] == "warning" for f in findings):
        marks.append("warning")
    if not_checked:
        marks.append("not fully checked")
    return marks


def flow_branches(flow, catalog, vault, keys, answers, today):
    """The branch picker's data for one flow, or a one-line note when its error cases are not drawn."""
    if flow is None or not flow.has_diagram:
        return {"state": "none", "note": NOT_DRAWN_NOTE}
    tree = mermaid.parse_tree(flow, [])
    walker = Walker(tree, catalog, entity_keys(catalog, vault, keys))
    surveyed = walker.survey()
    happy = walker.search()
    if happy is None or not walker.points:
        return {"state": "none", "note": NOT_DRAWN_NOTE}
    # the run check-slice makes for the first slice that proves this flow (so the marks match it), else the flow alone
    home = next((s for s in catalog.slices if flow.id in s.flows), None)
    result = flowcheck.check_catalog(catalog, (home.id or home.name) if home else flow.id, today, CHECK_STATES)
    stated = list(result.limits)  # the checker's own sentences on what its result rests on (ledger C39)
    shared = sorted({e.title for e in catalog.entities.values() if e.shared})
    not_checked = "not fully checked" in result.status
    mine = [f for f in result.findings if f.where.startswith(flow.path + ":") or f.call_line.startswith(flow.path + ":")]
    words = state_words(vault, catalog)
    outcomes = outcome_words(next((p for p in vault.pages if p.path == flow.path), None))
    found = [finding_record(f, catalog, words) for f in mine]
    at = {}
    for i, f in enumerate(mine):
        if f.case and f.call_line:
            at.setdefault((_line(f.call_line), f.case), []).append(i)
    groups, ids, seen_titles, used = [], set(), {}, []
    names = {name: title for name, (title, _) in tree.participants.items()}
    titles_of = {cid: table.title for cid, table in catalog.contracts.items()}

    def use(steps):
        for s in steps:
            for who in [s.get("from"), s.get("to"), *s.get("over", [])]:
                if who and who not in used:
                    used.append(who)
    use(happy.steps)
    for line, point in sorted(walker.points.items()):
        item = point["item"]
        table = catalog.contracts.get(item)
        name = table.title if table else item
        seen_titles[name] = seen_titles.get(name, 0) + 1
        options = []
        for key in point["keys"]:
            if (line, key) in happy.choices:
                continue
            ident = f"{item}.{key}" if f"{item}.{key}" not in ids else f"{item}.{key}.{line}"
            ids.add(ident)
            status, says = answers.get(item, {}).get(key, ("", ""))
            hits = at.get((line, key), [])
            marks = marks_of([found[i] for i in hits], not_checked)
            path = None if (line, key) in walker.unhandled else walker.search((line, key))
            if (line, key) in walker.unhandled:
                marks = ["not drawn"] + marks
            elif path is None:
                marks = ["too many paths to draw"] + marks
            steps = played(path.steps, names, answers, titles_of, path.ended, outcomes, words) if path else []
            use(steps)
            options.append({"id": ident, "label": f"{name}: {case_words(key)}", "case": key, "line": line, "status": status,
                            "says": says, "findings": hits, "marks": marks, "drawn": path is not None, "steps": steps,
                            "limits": limits_for(path, walker, stated, shared)})
        if options:
            label = name + (f", call {seen_titles[name]}" if seen_titles[name] > 1 else "")
            groups.append({"label": label, "item": item, "line": line, "options": options})
    happy_hits = sorted({i for choice in happy.choices for i in at.get(choice, [])})
    on_options = {i for g in groups for o in g["options"] for i in o["findings"]} | set(happy_hits)
    people = participant_keys(tree, catalog, vault, keys)
    order = list(tree.participants) + [u for u in used if u not in tree.participants]
    options = [o for g in groups for o in g["options"]]
    return {
        "state": "drawn",
        "participants": [{"id": n, "title": names.get(n, n), "key": people.get(n, "")} for n in order if n in used],
        "happy": {"id": "happy", "label": "Happy path", "steps": played(happy.steps, names, answers, titles_of, happy.ended, outcomes, words), "findings": happy_hits,
                  "marks": marks_of([found[i] for i in happy_hits], not_checked), "limits": limits_for(happy, walker, stated, shared)},
        "limits": stated,
        "groups": groups, "findings": found,
        "flowWide": [i for i in range(len(found)) if i not in on_options],  # findings about no one answer at one call
        "check": {"status": result.status, "states": result.states, "notChecked": not_checked, "surveyed": surveyed},
        "counts": {"branches": sum(1 for o in options if o["drawn"]), "notDrawn": sum(1 for o in options if not o["drawn"]),
                   "withFindings": sum(1 for o in options + [{"marks": marks_of([found[i] for i in happy_hits], False)}]
                                       if {"finding", "warning"} & set(o["marks"])),
                   "notChecked": (1 + len(options)) if not_checked else 0},
    }


def extract(vault, keys, today, specs=None):
    """{flow key: branch data} for every flow page."""
    catalog = readers.read_catalog(vault, specs or {})
    answers = answers_of(vault)
    return {keys.page(page): flow_branches(catalog.flows.get(page.id), catalog, vault, keys, answers, today)
            for page in sorted(vault.of_type("flow"), key=lambda p: p.id)}


__all__ = ["extract", "flow_branches", "case_words", "Walker", "NOT_DRAWN_NOTE"]
