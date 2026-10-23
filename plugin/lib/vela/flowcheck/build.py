"""The model builder: a slice's flow trees and case tables in, a compiled Program and the static findings out. Pure.

Each flow compiles to instructions with jump targets, so a thread's position is one integer. Threads:
- the journey's main thread runs the flow's top level;
- a handler thread runs a `par` block after an event line (or after a call an outside app makes), started when the
  event is delivered;
- drawn provider handling runs on the caller's thread, on a call stack: the call pushes, the provider's reply pops.

The builder decides nothing about reachability; it only says what each step can do. Static properties (F1, F2, F3,
F10, F12) are judged in `properties` and reported from here because only the walk knows each step's context.
"""
import dataclasses
from dataclasses import dataclass, field

from vela.flowcheck import mermaid, properties
from vela.flowcheck.findings import Finding

TIMEOUT, GAVE_UP = "timeout", "gave_up"
DELIVERIES = ("exactly-once", "at-least-once", "may-be-lost")


@dataclass
class Ins:
    kind: str  # call reply publish set end await timer human goto done
    where: str
    flow: int
    actor: str = ""  # display name of who acts
    data: dict = field(default_factory=dict)


@dataclass
class Target:
    """Where a published message goes: one event (or inbound call) for one subscriber, run by one handler or awaited."""
    item: str  # EVT-nnn or CON-nnn
    title: str
    producer: str  # display name
    subscriber: str  # app key
    subscriber_name: str
    hid: object  # handler id, or None
    delivery: str
    order: str
    key_entity: object  # entity slug for per:<field> ordering


@dataclass
class Handler:
    hid: int
    item: str
    title: str
    subscriber_name: str
    body: int  # first pc
    retries: object
    where: str


@dataclass
class Timer:
    """A `TIMER <name> <band>` step: fires once per arming (revision 2, item 10); what firing does is the par block
    after it (a handler thread), the timer branch of an AWAIT racing it, or both."""
    name: str
    band: str
    where: str
    hid: object  # handler id of its par block, or None
    owner: str  # display name of who armed it


@dataclass
class Program:
    code: list
    flows: list  # [(Flow, start pc, givens {entity slug: state})]
    handlers: list
    targets: list
    timers: list  # [Timer]
    entities: dict  # slug -> Entity, the ones the slice touches
    contracts: dict
    awaited: set  # {(item, subscriber app key)}


class Context:
    """What a step inside a thread knows about where it sits."""

    def __init__(self, flow, thread, cause, actor_rules=None, stack=(), emits=None, in_handling=False):
        self.flow, self.thread, self.cause = flow, thread, cause
        self.rules = dict(actor_rules or {})  # actor name -> {case key: (outcome, leaves, where)}
        self.stack = stack  # ((provider name, caller name, call node), ...) for drawn handling
        self.emits = emits or {}  # event id -> provider name, for the branch of an undrawn case that emits it
        self.in_handling = in_handling
        self.last_timer = None
        self.branch_keys = ()  # ((call where, case key), ...): the undrawn case branch this step sits in

    def child(self, **changes):
        ctx = Context(self.flow, changes.get("thread", self.thread), changes.get("cause", self.cause),
                      {k: dict(v) for k, v in self.rules.items()}, changes.get("stack", self.stack),
                      changes.get("emits", self.emits), changes.get("in_handling", self.in_handling))
        ctx.last_timer = self.last_timer
        ctx.branch_keys = changes.get("branch_keys", self.branch_keys)
        return ctx


class Builder:
    def __init__(self, catalog, flow_ids, today):
        self.cat, self.today = catalog, today
        self.flow_ids = list(flow_ids)
        self.findings = []
        self.code, self.flows, self.handlers, self.targets, self.timers = [], [], [], [], []
        self.entities, self.contracts, self.awaited = {}, {}, set()
        self.pending_handlers = []
        self.participants = {}  # flow index -> {name: App or None}
        self.slice_apps = set()
        self.emit_requests = []  # (ins, case key, {event: hid}) resolved once every handler is known
        self.f12_seen = set()
        self.drawn_calls = set()  # (caller app key, contract id) for every call drawn in the slice's flows
        self.trees = {}

    # --- reporting ------------------------------------------------------------------------------------------------

    def report(self, code, where, summary, **extra):
        self.findings.append(Finding(code, where, summary, **extra))

    def where(self, flow, line):
        return f"{flow.path}:{line}"

    # --- the walk -------------------------------------------------------------------------------------------------

    def build(self):
        for problem in self.cat.problems:
            if not problem.item or problem.item in self.used_ids():
                self.report("F10", problem.where, problem.text, items=(problem.item,) if problem.item else ())
        for index, fid in enumerate(self.flow_ids):
            flow = self.cat.flows.get(fid)
            if flow is None:
                self.report("F10", "04b-releases.md", f"The slice names {fid}, and no flow page has that ID.", items=(fid,))
                continue
            if not flow.has_diagram:
                self.report("F10", flow.path, f"{fid} has no ```mermaid block starting sequenceDiagram, so nothing in it is checked.",
                            items=(fid,))
                continue
            problems = []
            tree = mermaid.parse_tree(flow, problems)
            for p in problems:
                self.report("F10", p.where, p.text, items=(fid,))
            self.trees[index] = (flow, tree)
            self.participants[index] = {name: self.cat.app_named(title) for name, (title, _) in tree.participants.items()}
        for index, (flow, tree) in sorted(self.trees.items()):
            for node in _walk(tree.all_nodes()):
                for name in _names(node):
                    app = self.app_of(index, name)
                    if app is not None:
                        self.slice_apps.add(app.key)
                caller = self.app_of(index, node.parts[0]) if node.kind == "call" else None
                if caller is not None:
                    self.drawn_calls.add((caller.key, node.parts[2]))
        for index, (flow, tree) in sorted(self.trees.items()):
            self.compile_flow(index, flow, tree)
        while self.pending_handlers:
            self.compile_handler(*self.pending_handlers.pop(0))
        self.resolve_emits()
        self.add_invariant_entities()
        self.findings += properties.event_findings(self)
        return Program(self.code, self.flows, self.handlers, self.targets, self.timers, self.entities, self.contracts,
                       self.awaited), self.findings

    def used_ids(self):
        ids = set(self.flow_ids)
        for fid in self.flow_ids:
            flow = self.cat.flows.get(fid)
            for token in (flow.lines if flow else ()):
                ids |= {p for p in token.parts if isinstance(p, str) and p[:4] in ("CON-", "EVT-")}
                if token.kind in ("set", "given", "timer"):
                    entity = self.cat.entity(token.parts[1])
                    if entity is not None:
                        ids |= {entity.id, entity.slug}
                if token.kind == "call" and token.parts[2] in self.cat.contracts:
                    for case in self.cat.contracts[token.parts[2]].cases:
                        ids |= set(case.emits)
                        for name in [s[0] for s in case.sets] + [w[0] for w in case.when]:
                            entity = self.cat.entity(name)
                            if entity is not None:
                                ids |= {entity.id, entity.slug}
        return ids

    def calls_not_drawn(self, app):
        """The contracts `app` calls (catalog.consumes) that no flow of this slice draws it calling. When every one is
        drawn somewhere in the slice, what it does with their answers is checked there, and an undrawn answer of its
        own adds nothing unchecked: the Rider app's Card check, answered from the card on file, while the bank
        sign-in it calls is drawn in Take payment's handling. Assumed, and said in the docs: the same call made
        inside the undrawn handling would be handled as it is where it is drawn."""
        return tuple(sorted(c for c in self.cat.consumes.get(app.key, ()) if (app.key, c) not in self.drawn_calls))

    def app_of(self, index, name):
        known = self.participants.get(index, {})
        if name in known:
            return known[name]
        return self.cat.app_named(name)

    def display(self, index, name):
        app = self.app_of(index, name)
        if app is not None:
            return app.title
        title = self.trees[index][1].participants.get(name, (name, 0))[0]
        return title

    def entity(self, flow, line, name, state=None, item=""):
        """The entity a step names, after checking it and the state exist; None (and an F10) when either does not."""
        found = self.cat.entity(name)
        where = self.where(flow, line)
        if found is None:
            self.report("F10", where, f"'{name}' is not an entity: no entity page has that ID, slug or title.",
                        items=(item,) if item else ())
            return None
        if state is not None and state not in found.states:
            self.report("F10", where, f"{found.title} has no state '{state}' (its states: {', '.join(sorted(found.states))}).",
                        items=(found.id,))
            return None
        self.entities[found.slug] = found
        return found

    def resolve_table(self, flow, line, table):
        """The case table with every entity its cases set or guard on named by slug, checked to exist. Kept once per
        contract, so every call of it in the slice shares one resolved table."""
        if table.id in self.contracts:
            return self.contracts[table.id]
        cases = []
        for case in table.cases:
            sets, when = [], []
            for name, target in case.sets:
                states = [target] if isinstance(target, str) else [s for pair in target for s in pair]
                entity = self.entity(flow, line, name, item=table.id)
                bad = [s for s in states if entity is not None and s not in entity.states]
                if entity is not None and not bad:
                    sets.append((entity.slug, target))
                elif bad:
                    self.report("F10", table.source, f"{table.id} case {case.key} sets {entity.title} to '{bad[0]}', "
                                f"which is not one of its states.", items=(table.id,))
            for name, op, states in case.when:
                entity = self.entity(flow, line, name, item=table.id)
                if entity is None:
                    continue
                bad = [s for s in states if s not in entity.states]
                if bad:
                    self.report("F10", table.source, f"{table.id} case {case.key} answers only when {entity.title} is "
                                f"'{bad[0]}', which is not one of its states.", items=(table.id,))
                    continue
                allowed = tuple(states) if op == "in" else tuple(sorted(entity.states - set(states)))
                when.append((entity.slug, allowed))
            cases.append(dataclasses.replace(case, sets=tuple(sets), when=tuple(when)))
        resolved = dataclasses.replace(table, cases=tuple(cases))
        self.contracts[table.id] = resolved
        return resolved

    def add_invariant_entities(self):
        """An invariant that names an entity the slice touches is judged even when it is written on, or names,
        an entity the slice never changes: that entity then sits at its initial state, which is what the model knows."""
        changed = True
        while changed:
            changed = False
            for entity in {e.slug: e for e in self.cat.entities.values()}.values():
                for _, _, expr in entity.invariants:
                    names = _invariant_atoms(expr) | {entity.slug}
                    found = [self.cat.entity(n) for n in names]
                    if any(f is not None and f.slug in self.entities for f in found):
                        for f in found:
                            if f is not None and f.slug not in self.entities:
                                self.entities[f.slug] = f
                                changed = True

    def emit(self, ins):
        self.code.append(ins)
        return len(self.code) - 1

    def compile_flow(self, index, flow, tree):
        forked = len(tree.starts) > 1
        givens, nodes = {}, list(tree.head if forked else tree.nodes)
        while nodes and nodes[0].kind in ("given", "human") and nodes[0].kind == "given":
            node = nodes.pop(0)
            entity = self.entity(flow, node.line, node.parts[1], node.parts[2])
            if entity is not None:
                givens[entity.slug] = node.parts[2]
        start = len(self.code)
        ctx = Context(index, "main", (flow.id,))
        if forked:
            self.fork(index, flow, tree, ctx)
        else:
            self.seq(nodes, ctx)
        self.emit(Ins("done", flow.path, index, data={"thread": "main"}))
        self.flows.append((flow, start, givens))

    def fork(self, index, flow, tree, ctx):
        """An opening alt names the flow's starts: one of them happens, so the walk forks once, takes each start's own steps,
        and every start goes on to the steps after the alt (the shared tail), compiled once."""
        where = self.where(flow, tree.starts[0].line)
        at = self.emit(Ins("fork", where, index, data={"targets": [], "labels": [b.label for b in tree.starts]}))
        gotos = []
        for branch in tree.starts:
            self.code[at].data["targets"].append(len(self.code))
            inner = ctx.child()
            self.seq(branch.body, inner)
            ctx.last_timer = inner.last_timer if inner.last_timer is not None else ctx.last_timer  # a timer a start armed is the one the shared steps await
            gotos.append(self.emit(Ins("goto", self.where(flow, branch.line), index)))
        for g in gotos:
            self.code[g].data["target"] = len(self.code)
        self.seq(tree.tail, ctx)

    def compile_handler(self, index, hid, node, item, title, subscriber_name, retries, cause_item):
        flow = self.trees[index][0]
        body = len(self.code)
        self.handlers[hid].body = body
        ctx = Context(index, hid, (cause_item if cause_item.startswith("timer ") else f"{cause_item} handled",))
        self.seq(node.handler, ctx)
        self.emit(Ins("done", flow.path, index, data={"thread": "handler"}))

    def seq(self, nodes, ctx):
        flow = self.trees[ctx.flow][0]
        replied = False
        for node in nodes:
            if replied:
                self.report("F10", self.where(flow, node.line), "A step after the provider's answer: the drawn handling ends at its answer.",
                            items=(flow.id,))
                break
            if node.kind == "given":
                self.report("F10", self.where(flow, node.line), "GIVEN sets where the flow starts, so it goes before the first step.",
                            items=(flow.id,))
            elif node.kind == "call":
                self.call(node, ctx)
            elif node.kind == "reply":
                replied = self.reply(node, ctx)
            elif node.kind == "contract":
                replied = self.answer_from_contract(node, ctx)
            elif node.kind == "publish":
                self.publish(node, ctx)
            elif node.kind == "set":
                entity = self.entity(flow, node.line, node.parts[1], node.parts[2])
                if entity is not None:
                    self.emit(Ins("set", self.where(flow, node.line), ctx.flow, self.display(ctx.flow, node.actor),
                                  {"entity": entity.slug, "state": node.parts[2], "cause": ctx.cause}))
            elif node.kind == "finish":
                self.finish(node, ctx)
            elif node.kind == "await":
                self.await_(node, ctx)
            elif node.kind == "timer":
                self.timer(node, ctx)
            elif node.kind == "human":
                self.emit(Ins("human", self.where(flow, node.line), ctx.flow, self.display(ctx.flow, node.actor),
                              {"words": node.parts[1]}))
            elif node.kind == "on":
                _, keys, outcome, leaves = node.parts
                rules = ctx.rules.setdefault(node.actor, {})
                for key in keys:
                    rules[key] = (outcome, leaves, self.where(flow, node.line))
        return replied

    # --- steps ----------------------------------------------------------------------------------------------------

    def call(self, node, ctx):
        flow = self.trees[ctx.flow][0]
        caller, provider_name, cid = node.parts[0], node.parts[1], node.parts[2]
        where = self.where(flow, node.line)
        table = self.cat.contracts.get(cid)
        if table is None:
            self.report("F10", where, f"{cid} has no case table: no spec operation or contract page declares its cases.", items=(cid,))
            return
        table = self.resolve_table(flow, node.line, table)
        provider_app = self.app_of(ctx.flow, provider_name)
        caller_app = self.app_of(ctx.flow, caller)
        if not properties.provider_matches(self, ctx.flow, where, node, table, provider_app):
            return
        if caller_app is not None and caller_app.outside:
            self.inbound_call(node, ctx, table)
            return
        if node.handler is not None:
            self.report("F10", self.where(flow, node.handler_line), "A par block after a call: only a call an outside app makes "
                        "starts a handler. Draw the provider's steps between the call and its answer instead.", items=(cid,))
        if table.timeout is None:
            self.report("F10", where, f"{cid} does not say whether it can time out: add '- **Can time out:** yes' or no under its heading (x-vela-timeout in a spec).", items=(cid,))
            return
        drawn = node.handling is not None
        if drawn and provider_app is not None and provider_app.outside:
            self.report("F10", where, f"{provider_app.title} is outside the vault, so it answers from its contract; its handling cannot be drawn.",
                        items=(cid,))
            return
        unseen = self.calls_not_drawn(provider_app) if not drawn and provider_app is not None and not provider_app.outside else ()
        if unseen:
            key = (flow.id, provider_app.key, cid)
            if key not in self.f12_seen:
                self.f12_seen.add(key)
                named = ", ".join(f"\"{self.cat.contracts[c].title}\"" if c in self.cat.contracts else c for c in unseen)
                self.report("F12", where, f"{provider_app.title} answers \"{table.title}\" from its contract alone in this flow, "
                            f"and it calls {named} itself, which no flow of this slice draws it calling; what it does with "
                            "the answers is not checked here.", items=(cid,) + tuple(unseen),
                            owners=(provider_app.title,), call_line=where)
        replies = _collect_replies(node.handling or (), provider_name, caller, table)
        outcomes = properties.outcomes(self, where, table, replies if drawn else None)
        ins = Ins("call", where, ctx.flow, self.display(ctx.flow, caller),
                  {"contract": cid, "provider": self.display(ctx.flow, provider_name), "drawn": None, "branches": {},
                   "visible": outcomes, "emits": {}, "words": node.parts[3].strip()})
        pc = self.emit(ins)
        if drawn:
            jump = self.emit(Ins("goto", where, ctx.flow))
            ins.data["drawn"] = len(self.code)
            inner = ctx.child(stack=ctx.stack + ((provider_name, caller, node),), cause=(cid,), in_handling=True, emits={})
            inner.rules = {}
            if not self.seq(node.handling, inner) and not _always_replies(node.handling, provider_name, caller):
                self.report("F10", where, f"A path through {ins.data['provider']}'s drawn handling of \"{table.title}\" never answers "
                            f"{ins.actor}.", items=(cid,))
            self.emit(Ins("done", where, ctx.flow, data={"thread": "noreply"}))
            self.code[jump].data["target"] = len(self.code)
        self.branches(node, ctx, ins, table, outcomes)

    def branches(self, node, ctx, ins, table, outcomes):
        flow = self.trees[ctx.flow][0]
        cid = table.id
        written = properties.check_branches(self, ctx, node, ins, table, outcomes)
        rules = ctx.rules.get(node.parts[0], {})
        gotos = []
        for branch in node.branches or ():
            body = list(branch.body)
            if body and body[0].kind == "reply" and body[0].parts[0] == node.parts[1] and body[0].parts[1] == node.parts[0]:
                properties.check_decoration(self, flow, branch, body.pop(0), table)
            keys = [k for k in branch.keys if k in outcomes]
            if not keys:
                continue
            start = len(self.code)
            for key in keys:
                ins.data["branches"][key] = start
            emits = {e: node.parts[1] for key in keys for e in _case_emits(table, key)} if ins.data["drawn"] is None else {}
            causes = tuple(f"{cid} {k}" for k in keys)
            if ctx.in_handling:
                # Inside a provider's drawn handling the change is also the provider's handling of its own call:
                # Consent and identity keeps a consent "in CON-005 signed_in" and "for CON-004". Either may allow it.
                causes += tuple(c for c in ctx.cause if c not in causes)
            inner = ctx.child(cause=causes, emits=emits,
                              branch_keys=tuple((ins.where, k) for k in keys) if ins.data["drawn"] is None else ())
            self.seq(body, inner)
            ctx.last_timer = inner.last_timer if inner.last_timer is not None else ctx.last_timer
            gotos.append(self.emit(Ins("goto", self.where(flow, branch.line), ctx.flow)))
        missing = [k for k in outcomes if k not in written]
        continuation = None
        for key in missing:
            if key in rules:
                outcome, leaves, rule_where = rules[key]
                ins.data["branches"][key] = len(self.code)
                self.emit(Ins("end", rule_where, ctx.flow, ins.actor, {"outcome": outcome, "leaves": self.leaves(flow, leaves, rule_where),
                                                                        "thread": ctx.thread, "uniform": True}))
        uncovered = [k for k in missing if k not in rules]
        if node.branches is None and len(uncovered) == 1:
            continuation = uncovered[0]
        elif uncovered:
            properties.report_unhandled(self, flow, node, ins, table, uncovered)
        after = len(self.code)
        for g in gotos:
            self.code[g].data["target"] = after
        if continuation is not None:
            ins.data["branches"][continuation] = after
            if ins.data["drawn"] is None:
                ctx.emits = {e: node.parts[1] for e in _case_emits(table, continuation)}
                ctx.branch_keys = ((ins.where, continuation),)
            ctx.cause = (f"{cid} {continuation}",)
        if ins.data["drawn"] is None:
            for case in table.cases:
                self.emit_requests.append((ins, case.key, {}))

    def reply(self, node, ctx):
        flow = self.trees[ctx.flow][0]
        where = self.where(flow, node.line)
        if not ctx.stack or (ctx.stack[-1][0], ctx.stack[-1][1]) != (node.parts[0], node.parts[1]):
            self.report("F10", where, f"This answer from {node.parts[0]} to {node.parts[1]} answers no call: an answer is the "
                        "provider's drawn reply, or the first line of the caller's branch.", items=(flow.id,))
            return False
        call_node = ctx.stack[-1][2]
        table = self.cat.contracts[call_node.parts[2]]
        properties.check_reply(self, where, node, table)
        self.emit(Ins("reply", where, ctx.flow, self.display(ctx.flow, node.parts[0]), {"case": node.parts[3]}))
        return True

    def answer_from_contract(self, node, ctx):
        """`ANSWERS FROM CONTRACT` inside drawn handling: the provider answers its caller with any case of its table
        (or the ones listed) whose When holds, its Sets and Emits included, as an undrawn provider would (item 8)."""
        flow = self.trees[ctx.flow][0]
        where = self.where(flow, node.line)
        if not ctx.stack or ctx.stack[-1][0] != node.parts[0]:
            self.report("F10", where, f"ANSWERS FROM CONTRACT over {node.parts[0]}, which is answering no call here: it goes "
                        "inside a provider's drawn handling, where its reply would be.", items=(flow.id,))
            return False
        call_node = ctx.stack[-1][2]
        table = self.resolve_table(flow, node.line, self.cat.contracts[call_node.parts[2]])
        keys = node.parts[1] or tuple(c.key for c in table.cases)
        for key in keys:
            if not any(c.key == key for c in table.cases):
                self.report("F2", where, f"{self.display(ctx.flow, node.parts[0])} answers {key} from its contract, which "
                            f"\"{table.title}\" does not declare (it declares: {', '.join(c.key for c in table.cases)}).",
                            items=(table.id,), case=key)
        ins = Ins("contract", where, ctx.flow, self.display(ctx.flow, node.parts[0]),
                  {"contract": table.id, "cases": tuple(n for n, c in enumerate(table.cases) if c.key in keys), "emits": {}})
        self.emit(ins)
        for key in keys:
            self.emit_requests.append((ins, key, {}))
        return True

    def timer(self, node, ctx):
        flow = self.trees[ctx.flow][0]
        where = self.where(flow, node.line)
        _, name, band = node.parts
        if any(t.name == name for t in self.timers):
            self.report("F10", where, f"A second timer called {name}: give each its own name.", items=(flow.id,))
            return
        hid = None
        if node.handler is not None:
            hid = len(self.handlers)
            owner = self.display(ctx.flow, node.actor)
            self.handlers.append(Handler(hid, f"timer {name}", f"the {name} timer", owner, -1, None, where))
            self.pending_handlers.append((ctx.flow, hid, node, f"timer {name}", f"the {name} timer", owner, None, f"timer {name}"))
        self.timers.append(Timer(name, band, where, hid, self.display(ctx.flow, node.actor)))
        ctx.last_timer = len(self.timers) - 1
        self.emit(Ins("timer", where, ctx.flow, self.display(ctx.flow, node.actor), {"timer": len(self.timers) - 1}))

    def publish(self, node, ctx):
        flow = self.trees[ctx.flow][0]
        where = self.where(flow, node.line)
        sender, receiver, eid = node.parts[0], node.parts[1], node.parts[2]
        event = properties.event_usable(self, ctx.flow, where, node)
        if event is None:
            return
        sub_app = self.app_of(ctx.flow, receiver)
        retries = dict(event.subscribers).get(sub_app.key)
        hid = self.handler_for(ctx.flow, node, eid, event.title, self.display(ctx.flow, receiver), retries, where)
        target = self.target(eid, event.title, self.display(ctx.flow, sender), sub_app, hid, event.delivery, event.order,
                             properties.order_entity(self, event))
        if eid in ctx.emits and ctx.emits[eid] == sender:
            for key in ctx.branch_keys:
                self.branch_targets.setdefault(key, {})[(eid, sub_app.key)] = target
            return
        self.emit(Ins("publish", where, ctx.flow, self.display(ctx.flow, sender), {"target": target}))

    def inbound_call(self, node, ctx, table):
        """A call an outside app makes (a webhook): modeled like an event the outside app publishes (review 1.5)."""
        flow = self.trees[ctx.flow][0]
        where = self.where(flow, node.line)
        if node.handler is None:
            self.report("F10", where, f"{table.id} is called by an outside app, so the receiver's handling goes in a par block after the line.",
                        items=(table.id,))
            return
        if table.delivery not in DELIVERIES or not table.order:
            self.report("F10", where, f"{table.id} is called by an outside app, so it needs a delivery and an order like an event's "
                        "(x-vela-delivery and x-vela-order, or Delivery and Order bullets).", items=(table.id,))
            return
        sub_app = self.app_of(ctx.flow, node.parts[1])
        hid = self.handler_for(ctx.flow, node, table.id, table.title, self.display(ctx.flow, node.parts[1]), None, where)
        target = self.target(table.id, table.title, self.display(ctx.flow, node.parts[0]), sub_app, hid, table.delivery, table.order, None)
        self.emit(Ins("publish", where, ctx.flow, self.display(ctx.flow, node.parts[0]), {"target": target, "inbound": True}))

    def handler_for(self, index, node, item, title, subscriber_name, retries, where):
        if node.handler is None:
            return None
        hid = len(self.handlers)
        self.handlers.append(Handler(hid, item, title, subscriber_name, -1, retries, where))
        self.pending_handlers.append((index, hid, node, item, title, subscriber_name, retries, item))
        return hid

    def target(self, item, title, producer, sub_app, hid, delivery, order, key_entity):
        self.targets.append(Target(item, title, producer, sub_app.key, sub_app.title, hid, delivery, order, key_entity))
        return len(self.targets) - 1

    def finish(self, node, ctx):
        flow = self.trees[ctx.flow][0]
        where = self.where(flow, node.line)
        if ctx.in_handling:
            self.report("F10", where, "END inside a provider's drawn handling: the provider answers its caller instead.", items=(flow.id,))
            return
        self.emit(Ins("end", where, ctx.flow, self.display(ctx.flow, node.actor),
                      {"outcome": node.parts[1], "leaves": self.leaves(flow, node.parts[2], where), "thread": ctx.thread}))

    def leaves(self, flow, pairs, where):
        out = {}
        for name, state in pairs:
            entity = self.entity(flow, int(where.rsplit(":", 1)[1]), name, state)
            if entity is not None:
                out[entity.slug] = state
        return out

    def await_(self, node, ctx):
        flow = self.trees[ctx.flow][0]
        where = self.where(flow, node.line)
        item = node.parts[1]
        app = self.app_of(ctx.flow, node.actor)
        if app is None:
            self.report("F10", where, f"AWAIT over {node.actor}, which is no app.", items=(item,))
            return
        self.awaited.add((item, app.key))
        ins = Ins("await", where, ctx.flow, app.title, {"item": item, "app": app.key, "received": None, "timer_branch": None,
                                                         "timer": ctx.last_timer})
        self.emit(ins)
        properties.check_await(self, flow, node, ctx)
        gotos = []
        for branch in node.branches or ():
            start = len(self.code)
            timer = self.timers[ctx.last_timer].name if ctx.last_timer is not None else None
            for key in branch.keys:
                ins.data["received" if key == "received" else "timer_branch"] = start
            self.seq(branch.body, ctx.child(cause=(f"{item} received",) if "received" in branch.keys else (f"timer {timer}",)))
            gotos.append(self.emit(Ins("goto", self.where(flow, branch.line), ctx.flow)))
        after = len(self.code)
        for g in gotos:
            self.code[g].data["target"] = after
        if ins.data["received"] is None:
            ins.data["received"] = after
            ctx.cause = (f"{item} received",)

    # --- events a case emits, published by the provider's answer ----------------------------------------------------

    branch_targets = None

    def resolve_emits(self):
        """For each undrawn call's case that emits events: the targets its answer publishes to, one per declared
        subscriber. A subscriber's handler is the par block drawn in that case's branch, else the first drawn for the
        same event and subscriber anywhere in the slice, else it is awaited, else delivery to it has no effect and is
        not modeled (warned in properties.event_findings)."""
        first = {}
        for t_index, target in enumerate(self.targets):
            if target.hid is not None:
                first.setdefault((target.item, target.subscriber), t_index)
        for ins, key, _ in self.emit_requests:
            table = self.contracts.get(ins.data["contract"]) or self.cat.contracts[ins.data["contract"]]
            case = next((c for c in table.cases if c.key == key), None)
            if case is None:
                continue
            local = (self.branch_targets or {}).get((ins.where, key), {})
            out = []
            for eid in case.emits:
                event = self.cat.events.get(eid)
                if event is None or event.delivery not in DELIVERIES:
                    continue
                for sub, _ in event.subscribers:
                    if (eid, sub) in local:
                        out.append(local[(eid, sub)])
                    elif (eid, sub) in first:
                        out.append(first[(eid, sub)])
                    elif (eid, sub) in self.awaited:
                        app = self.cat.apps.get(sub)
                        out.append(self.target(eid, event.title, ins.data["provider"], app, None, event.delivery, event.order,
                                               properties.order_entity(self, event)))
            ins.data["emits"][key] = tuple(out)


def _case_emits(table, key):
    case = next((c for c in table.cases if c.key == key), None)
    return case.emits if case else ()


def _invariant_atoms(expr):
    if expr[0] == "is":
        return {expr[1]}
    return set().union(*(_invariant_atoms(e) for e in expr[1:]))


def _collect_replies(nodes, provider, caller, table):
    """(case key, status, line) for every answer the drawn handling can give: its replies, and the cases an ANSWERS
    FROM CONTRACT step can answer with."""
    out = []
    for node in nodes:
        if node.kind == "reply" and node.parts[0] == provider and node.parts[1] == caller:
            out.append((node.parts[3], node.parts[2], node.line))
        if node.kind == "contract" and node.parts[0] == provider:
            keys = node.parts[1] or tuple(c.key for c in table.cases)
            out += [(c.key, c.status, node.line) for c in table.cases if c.key in keys]
        for branch in node.branches or ():
            out += _collect_replies(branch.body, provider, caller, table)
    return out


def _always_replies(nodes, provider, caller):
    for node in nodes:
        if (node.kind == "reply" and node.parts[0] == provider and node.parts[1] == caller) or \
                (node.kind == "contract" and node.parts[0] == provider):
            return True
    last = next((n for n in reversed(nodes) if n.kind in ("call", "await")), None)
    if last is None or not last.branches:
        return False
    return all(_always_replies(b.body, provider, caller) for b in last.branches)


def _walk(nodes):
    for node in nodes:
        yield node
        yield from _walk(node.handling or ())
        yield from _walk(node.handler or ())
        for branch in node.branches or ():
            yield from _walk(branch.body)


def _names(node):
    if node.kind in ("call", "publish", "reply"):
        return node.parts[:2]
    return (node.actor,)


def build(catalog, flow_ids, today):
    builder = Builder(catalog, flow_ids, today)
    builder.branch_targets = {}
    return builder.build()
