"""The properties: what counts as a finding. Pure.

Static ones (F1, F2, F3, F3w, F4, F10, F12, F13) are judged on the flow trees and case tables; the builder calls them
at each step because only its walk knows the step's context. Explored ones (F5 to F9, F11) are judged on the state
graph in `judge_graph`, after `explore` has built it.
"""
import difflib

from planner import slices
from planner.flowcheck.findings import Finding

TIMEOUT, GAVE_UP = "timeout", "gave_up"
DELIVERIES = ("exactly-once", "at-least-once", "may-be-lost")


def words(key):
    return key.replace("_", " ")


# --- calls ----------------------------------------------------------------------------------------------------------

def provider_matches(b, index, where, node, table, provider_app):
    """A->>B must name B as the contract's provider, by an app title the vault knows."""
    name = node.parts[1]
    if provider_app is None:
        titles = sorted(a.title for a in b.cat.apps.values())
        b.report("F10", where, f"Participant {name} is no app the vault knows; the app titles are: {', '.join(titles)}.",
                 items=(table.id,))
        return False
    if provider_app.key != table.provider:
        owner = b.cat.apps.get(table.provider)
        b.report("F10", where, f"{table.id} is provided by {owner.title if owner else table.provider}, not {provider_app.title}. "
                 "Draw the call to the app that provides it, not a gateway or container.", items=(table.id,))
        return False
    return True


def outcomes(b, where, table, replies):
    """What the caller can see, in a stable order: the provider's cases (only the drawn replies, when its handling is
    drawn), then timeout; retried outcomes are replaced by gave_up (review 1.14)."""
    if replies is None:
        seen = [c.key for c in table.cases]
    else:
        seen = list(dict.fromkeys(key for key, _, _ in replies))
    if table.timeout:
        seen.append(TIMEOUT)
    if table.retries is not None:
        known = {c.key for c in table.cases} | ({TIMEOUT} if table.timeout else set())
        for key in table.retries.on:
            if key not in known:
                b.report("F10", where, f"{table.id} retries on '{key}', which is not one of its outcomes "
                         f"({', '.join(sorted(known))}).", items=(table.id,))
        seen = [k for k in seen if k not in table.retries.on] + [GAVE_UP]
    return tuple(seen)


def _nearest(key, choices):
    close = difflib.get_close_matches(key, list(choices), n=1, cutoff=0.5)
    if not close:
        lowered = {c.replace("_", "").lower(): c for c in choices}
        close = [lowered[key.replace("_", "").lower()]] if key.replace("_", "").lower() in lowered else []
    return f" Did you mean {close[0]}?" if close else ""


def check_branches(b, ctx, node, ins, table, visible):
    """F2 for a branch on a case the call cannot answer with; the set of keys the alt does handle."""
    flow = b.trees[ctx.flow][0]
    written = set()
    for branch in node.branches or ():
        for key in branch.keys:
            where = f"{flow.path}:{branch.line}"
            if key in written:
                b.report("F10", where, f"Case {key} has two branches on one call.", items=(table.id,))
            elif key not in visible:
                declared = [c.key for c in table.cases]
                why = ""
                if key == TIMEOUT and not table.timeout:
                    why = " The call cannot time out."
                elif table.retries is not None and key in table.retries.on:
                    why = f" {key} is retried, so the caller sees gave_up after the last attempt instead."
                elif key == GAVE_UP:
                    why = " The call has no retries."
                b.report("F2", where, f"{ins.actor} branches on {key}, which \"{table.title}\" does not answer with here "
                         f"(it can answer: {', '.join(visible)}).{why}{_nearest(key, declared + list(visible)) if not why else ''}",
                         items=(table.id,), owners=(ins.actor,), case=key, call_line=ins.where)
            written.add(key)
    return written


def check_decoration(b, flow, branch, reply, table):
    status, key = reply.parts[2], reply.parts[3]
    case = next((c for c in table.cases if c.key == key), None)
    where = f"{flow.path}:{reply.line}"
    if key not in branch.keys:
        b.report("F2", where, f"The branch for {', '.join(branch.keys)} opens with the answer {status} {key}.", items=(table.id,), case=key)
    elif case is None:
        b.report("F2", where, f"\"{table.title}\" declares no case {key}.{_nearest(key, [c.key for c in table.cases])}",
                 items=(table.id,), case=key)
    elif case.status != status:
        b.report("F2", where, f"Case {key} of \"{table.title}\" has status {case.status}, not {status}.", items=(table.id,), case=key)


def check_reply(b, where, node, table):
    status, key = node.parts[2], node.parts[3]
    case = next((c for c in table.cases if c.key == key), None)
    if case is None:
        b.report("F2", where, f"{b.cat.apps[table.provider].title} answers {key}, which \"{table.title}\" does not declare "
                 f"(it declares: {', '.join(c.key for c in table.cases)}).{_nearest(key, [c.key for c in table.cases])}",
                 items=(table.id,), case=key)
    elif case.status != status:
        b.report("F2", where, f"Case {key} of \"{table.title}\" has status {case.status}, not {status}.", items=(table.id,), case=key)


def report_unhandled(b, flow, node, ins, table, missing):
    """F1, one per missing outcome. An override covering one is applied with every other override, in `overrides`."""
    for key in missing:
        case = next((c for c in table.cases if c.key == key), None)
        if key == TIMEOUT:
            what = "the call times out"
        elif key == GAVE_UP:
            what = f"every one of its {table.retries.max} attempts fails"
        else:
            what = f"{ins.data['provider']} answers {words(key)} ({case.status})"
        summary = f"No branch for {key}: {ins.actor} does not say what happens when {what} on \"{table.title}\"."
        b.report("F1", ins.where, summary, items=(table.id,), owners=(ins.actor,), case=key, call_line=ins.where)


# --- events ---------------------------------------------------------------------------------------------------------

def event_usable(b, index, where, node):
    """The event an `A-)B` line publishes, after checking it is declared, A produces it and B subscribes to it."""
    sender, receiver, eid = node.parts[0], node.parts[1], node.parts[2]
    event = b.cat.events.get(eid)
    if event is None:
        b.report("F10", where, f"{eid} is declared by no AsyncAPI channel or event section.", items=(eid,))
        return None
    problems = []
    if event.delivery not in DELIVERIES:
        problems.append(f"{eid} has no delivery (x-vela-delivery: exactly-once, at-least-once or may-be-lost)")
    if not event.order or not (event.order in ("any", "per-producer") or str(event.order).startswith("per:")):
        problems.append(f"{eid} has no order (x-vela-order: any, per-producer or per:<field>)")
    elif str(event.order).startswith("per:") and order_entity(b, event) is None:
        problems.append(f"{eid} is ordered {event.order}, and that field is declared the key of no entity "
                        "(x-vela-key-of: ENT-nnn); payload values are not modeled, so the order cannot be read")
    sender_app, sub_app = b.app_of(index, sender), b.app_of(index, receiver)
    if sender_app is None or sender_app.key != event.producer:
        producer = b.cat.apps.get(event.producer)
        problems.append(f"{eid} is published by {producer.title if producer else 'no app'}, not {b.display(index, sender)}")
    if sub_app is None or sub_app.key not in dict(event.subscribers):
        problems.append(f"{b.display(index, receiver)} does not subscribe to {eid} (no receive operation or Subscriber row)")
    for text in problems:
        b.report("F10", where, text[0].upper() + text[1:] + ".", items=(eid,))
    return None if problems else event


def order_entity(b, event):
    if not str(event.order or "").startswith("per:"):
        return None
    entity = b.cat.entity(event.key_of) if event.key_of else None
    if entity is not None:
        b.entities[entity.slug] = entity
    return entity.slug if entity else None


def event_findings(b):
    """F3 and F3w for every event a case of a called contract emits; F12 for an in-slice subscriber whose handling
    of a published event is drawn nowhere and that does not await it."""
    out, seen = [], set()
    for ins in b.code:
        if ins.kind != "call":
            continue
        table = b.contracts[ins.data["contract"]]
        for case in table.cases:
            for eid in case.emits:
                if (eid, table.id) in seen:
                    continue
                seen.add((eid, table.id))
                event = b.cat.events.get(eid)
                if event is None:
                    out.append(Finding("F10", ins.where, f"Case {case.key} of \"{table.title}\" emits {eid}, which no channel declares.",
                                       items=(table.id, eid)))
                    continue
                if not event.subscribers:
                    out.append(Finding("F3", ins.where, f"\"{event.title}\", published when \"{table.title}\" answers {words(case.key)}, "
                                       "has no subscriber at all.", items=(table.id, eid), owners=(ins.data["provider"],),
                                       case=case.key, call_line=ins.where))
                    continue
                inside = [s for s, _ in event.subscribers if s in b.slice_apps]
                if not inside:
                    names = [b.cat.apps[s].title if s in b.cat.apps else s for s, _ in event.subscribers]
                    out.append(Finding("F3w", ins.where, f"\"{event.title}\" is consumed outside this slice, by {', '.join(names)}; "
                                       "its delivery has no effect here.", items=(eid,), case=case.key, call_line=ins.where))
                for sub in inside:
                    handled = any(t.item == eid and t.subscriber == sub and t.hid is not None for t in b.targets)
                    if not handled and (eid, sub) not in b.awaited:
                        out.append(Finding("F12", ins.where, f"{b.cat.apps[sub].title}'s handling of \"{event.title}\" is drawn in no "
                                           "flow of this slice, so its effects are not checked.", items=(eid,),
                                           owners=(b.cat.apps[sub].title,)))
    return out


def check_await(b, flow, node, ctx):
    where = f"{flow.path}:{node.line}"
    keys = [k for branch in node.branches or () for k in branch.keys]
    timer = b.timers[ctx.last_timer].name if ctx.last_timer is not None else None
    for key in keys:
        if key != "received" and key != timer:
            if timer is None:
                b.report("F10", where, f"This AWAIT branches on {key}, and no TIMER comes before it in this thread.", items=(node.parts[1],))
            else:
                b.report("F2", where, f"An AWAIT here can end received or {timer} (the timer before it), not {key}.",
                         items=(node.parts[1],), case=key)
    if keys and "received" not in keys:
        b.report("F1", where, f"No branch for received: the AWAIT does not say what happens when {node.parts[1]} arrives.",
                 items=(node.parts[1],), case="received")
    item = node.parts[1]
    if item.startswith("CON-") and item not in b.cat.contracts:
        b.report("F10", where, f"{item} has no case table.", items=(item,))
    if item.startswith("EVT-") and item not in b.cat.events:
        b.report("F10", where, f"{item} is declared by no channel.", items=(item,))


# --- across flows and slices ----------------------------------------------------------------------------------------

def unused_cases(catalog, trees):
    """F4, once per initiative: a declared case of a called contract that no flow anywhere branches on or replies.
    Only claimed once every flow that crosses the contract is drawn: while one is not, the case may be its to reach
    (Heron's "transcripts alone" refusal of Record consent, with the withdrawal flow still undrawn), and "reached by
    no flow" would be a claim nobody can back."""
    reached, called = set(), {}
    drawn = {flow.id for flow, _ in trees}
    for flow, tree in trees:
        for node in _walk(tree.nodes):
            if node.kind == "call":
                cid = node.parts[2]
                called.setdefault(cid, f"{flow.path}:{node.line}")
                for branch in node.branches or ():
                    reached |= {(cid, k) for k in branch.keys}
                table = catalog.contracts.get(cid)
                # No alt on a one-case contract continues with that case; a call an outside app makes is answered,
                # not branched on, so its cases are not the flow's to reach.
                if table is not None and ((node.branches is None and len(table.cases) == 1) or node.handler is not None):
                    reached |= {(cid, c.key) for c in table.cases}
            if node.kind == "call" and node.handling:
                reached |= {(node.parts[2], n.parts[3]) for n in _walk(node.handling) if n.kind == "reply"}
            if node.kind == "on":
                reached |= {("*", k) for k in node.parts[1]}
    out = []
    for cid in sorted(called):
        table = catalog.contracts.get(cid)
        if any(fid not in drawn for fid in catalog.crossing.get(cid, ())):
            continue
        for case in (table.cases if table else ()):
            if (cid, case.key) not in reached and ("*", case.key) not in reached:
                out.append(Finding("F4", table.source, f"Case {case.key} of \"{table.title}\" is reached by no flow.",
                                   items=(cid,), case=case.key))
    return out


def loose_ends(catalog, slice_index, flows):
    """F13: a GIVEN that no flow of this slice or one it comes after (its After, all the way back) leaves, and that is
    neither the entity's initial nor a final state. The join between slices, checked statically (review 1.9). A flow
    checked on its own outside any slice may start from anything any slice leaves."""
    left = set()
    earlier = catalog.slices
    if slice_index is not None and slice_index < len(catalog.slices):
        keys = slices.upstream(catalog.slices, catalog.slices[slice_index])
        earlier = [s for s in catalog.slices if s.key in keys]
    for found in earlier:
        for fid in found.flows:
            flow = catalog.flows.get(fid)
            for token in (flow.lines if flow else ()):
                if token.kind in ("finish", "on"):
                    left |= {(e, s) for e, s in token.parts[-1]}
    out = []
    for flow in flows:
        for token in flow.lines:
            if token.kind != "given":
                continue
            entity = catalog.entity(token.parts[1])
            state = token.parts[2]
            if entity is None or state in entity.final or state == entity.initial:
                continue
            if (token.parts[1], state) not in left and (entity.slug, state) not in left:
                out.append(Finding("F13", f"{flow.path}:{token.line}", f"{flow.id} starts from {entity.title} {words(state)}, "
                                   f"and no flow in this or an earlier slice ends leaving it {words(state)}.",
                                   items=(flow.id, entity.id)))
    return out


def _walk(nodes):
    for node in nodes:
        yield node
        yield from _walk(node.handling or ())
        yield from _walk(node.handler or ())
        for branch in node.branches or ():
            yield from _walk(branch.body)


# --- explored properties, on the state graph ------------------------------------------------------------------------

def label_key(label):
    """What two transitions have in common when they are the same step of the plan: kind, step, case and retry
    flag; not which journey took it or on which attempt. Findings that share it share a root cause."""
    return label[0], label[2], label[3] if label[0] not in ("set", "human", "arm", "end") else 0, label[5]


def judge_graph(g, sem, renderer, flow_paths):
    """F5, F6, F8, F9 for one explored run, one finding per root cause, shortest trace first. With a budget stop only
    what was actually reached is reported (F5, F8, F9, and stuck states), never a point of no return: unexplored
    states cannot be counted as able to finish (revision 2, item 16)."""
    from planner.flowcheck.explore import can_finish, shortest_onward
    out, seen = [], set()

    def steps(sid, tail=()):
        path = g.path(sid)
        chain, node = [], sid
        while node > 0:
            chain.append(node)
            node = g.parent[node]
        chain = [0] + list(reversed(chain))
        result = [(label, parity, g.states[a], g.states[b]) for (label, parity), a, b in zip(path, chain, chain[1:])]
        return result + list(tail)

    def add(key, finding):
        if key not in seen:
            seen.add(key)
            out.append(finding)

    def where_of(label, trail=()):
        """The step a finding sits on: its last transition's, or, when that was a message or a timer, the last
        flow step before it."""
        for candidate in [label] + [l for l, _, _, _ in reversed(trail)]:
            if candidate is not None and candidate[2] >= 0:
                return sem.p.code[candidate[2]].where
        return flow_paths[0]

    def pill(label):
        """The call step and case key a finding hangs on, for the dashboard's status pill (D8)."""
        if label is None or label[2] < 0:
            return "", ""
        ins = sem.p.code[label[2]]
        if label[0] in ("ans", "tmo") and ins.kind == "call":
            table = sem.p.contracts[ins.data["contract"]]
            return ins.where, (table.cases[label[3]].key if label[0] == "ans" else TIMEOUT)
        if label[0] in ("ptmo", "pcarry"):
            return ins.where, TIMEOUT
        if label[0] in ("reply", "rtmo", "late"):
            if label[0] == "rtmo":
                return sem.p.code[label[3]].where, TIMEOUT
            if ins.kind == "contract":
                return sem.p.code[label[3]].where, sem.p.contracts[ins.data["contract"]].cases[label[6]].key
            return sem.p.code[label[3]].where, ins.data["case"]
        return "", ""

    def ids(trail, *more):
        found = renderer.ids([(l, p) for l, p, _, _ in trail])
        return tuple(dict.fromkeys(found + [m for m in more if m]))

    for src, label, violation in g.violations:
        _, idx, current, to, cause, _ = violation
        key = ("F5", label_key(label))
        if key in seen:
            continue
        parity = g.parity(src)
        trail = steps(src, [(label, parity, g.states[src], _apply_view(g.states[src], idx, to, sem))])
        name = renderer.entity_name(idx, parity)
        slug = sem.instances[idx][0]
        entity = sem.p.entities[slug]
        because = " or ".join(cause_words(sem.p, c) for c in cause)
        if to is None:
            summary = f"{name} is {words(current)}, and {because} gives it nowhere to go from there."
        else:
            summary = f"{name} goes from {words(current)} to {words(to)}, which its state table does not allow for {because}."
        summary += _given_hint(sem, entity, current, to, cause, label)
        call_line, case = pill(label)
        add(key, Finding("F5", where_of(label), summary, items=ids(trail, entity.id),
                         owners=_owners(renderer.actor(label), renderer.owner_of(slug)),
                         trace=tuple(renderer.trace(trail)), case=case, call_line=call_line))

    for sid in sorted(g.cut):
        _, slug, text, journey = g.cut[sid]
        label = g.label[sid]
        trail = steps(sid)
        # One root cause: the same rule broken by the same answers, in whatever order they came. An answer that goes
        # nowhere (its caller has moved on) decides nothing, so it is no part of the cause (ledger C40).
        key = ("F9", text, frozenset(p for p in (pill(l) for l, _, _, _ in trail if l[0] != "late") if p[0]))
        if key in seen:
            continue
        entity = sem.p.entities[slug]
        call_line, case = _last_pill(trail, pill)
        named = [n for n in sorted(_atoms_of(next(e for t, _, e in entity.invariants if t == text))) if n in sem.p.entities]
        add(key, Finding("F9", where_of(label, trail), f"The invariant \"{text}\" of {entity.title} no longer holds.",
                         items=ids(trail, entity.id),
                         owners=_owners(renderer.actor(label) if label else "", renderer.owner_of(slug), *map(renderer.owner_of, named)),
                         trace=tuple(renderer.trace(trail)), case=case, call_line=call_line))

    finished, stuck = set(), set()
    for sid, count in g.succ_count.items():
        if not count:
            (finished if sem.finished(g.states[sid]) else stuck).add(sid)
    for sid in sorted(finished):
        label = g.label[sid]
        for idx, state in sem.not_final(g.states[sid]):
            slug = sem.instances[idx][0]
            entity = sem.p.entities[slug]
            key = ("F8", slug, state, label_key(label) if label else None)
            if key in seen:
                continue
            trail = steps(sid)
            call_line, case = _last_pill(trail, pill)
            add(key, Finding("F8", where_of(label, trail), f"{renderer.entity_name(idx, g.parity(sid))} is left {words(state)}, which is "
                             f"not one of its final states ({', '.join(words(f) for f in entity.final)}), and no END says the "
                             "journey leaves it so.", items=ids(trail, entity.id),
                             owners=_owners(renderer.actor(label) if label else "", renderer.owner_of(slug)),
                             trace=tuple(renderer.trace(trail)), case=case, call_line=call_line))

    if not g.complete:
        for sid in sorted(stuck):
            label = g.label[sid]
            trail = steps(sid)
            add(("F6", label_key(label) if label else None), _stuck_finding(sem, renderer, g, sid, trail, where_of(label, trail), None))
        return out

    # "Can't finish" (F6) at the frontier (revision 2, item 3): a state that can no longer finish whose BFS parent still
    # could. Its parent transition is the point of no return; every doomed state lies behind one. With bounded retries,
    # one duplicate and timers that fire once, the graph has no loops, so a state that cannot finish always reaches a
    # stuck one; "stuck" and "can't finish" are one finding seen from its two ends.
    finishing = can_finish(g, finished | set(g.cut) | {src for src, _, _ in g.violations})
    for v in range(len(g.states)):
        if v in finishing or (v > 0 and g.parent[v] not in finishing):
            continue
        label = g.label[v]
        key = ("F6", label_key(label) if label else None)
        if key in seen:
            continue
        onward = shortest_onward(g, v, stuck)
        if onward is None:
            add(key, Finding("F6", where_of(label), "From here the journey can no longer finish, though no step is blocked: "
                             "it runs on without end.", trace=tuple(renderer.trace(steps(v)))))
            continue
        tail, parity = [], g.parity(v)
        for a, b in zip(onward, onward[1:]):
            step_label, flip = _relabel(sem, g.states[a], g.states[b])
            tail.append((step_label, parity, g.states[a], g.states[b]))
            parity ^= flip
        point = len(steps(v))
        trail = steps(v, tail)
        add(key, _stuck_finding(sem, renderer, g, onward[-1], trail, where_of(None, trail[:point]), point, parity))
    return out


def _stuck_finding(sem, renderer, g, sid, trail, where, point, parity=None):
    """F6, can't finish: nothing can move and the journey has not finished. A thread awaits what cannot come, or a
    message waits for a receiver that will never be there. `point` is the step from which it could no longer finish."""
    state = g.states[sid]
    parity = g.parity(sid) if parity is None else parity
    reasons, owners = [], []
    for t in state[0]:
        if t[3] < 0:
            continue
        ins = sem.p.code[t[3]]
        prefix = renderer.prefix(t[0], parity)
        if ins.kind == "await":
            item = ins.data["item"]
            title = next((x.title for x in sem.p.targets if x.item == item), item)
            reasons.append(f"{prefix}{ins.actor} is still waiting for \"{title}\", which can no longer come.")
            owners.append(ins.actor)
        else:
            reasons.append(f"{prefix}{ins.actor} cannot take its next step ({ins.where}).")
    for _, items in state[3]:
        target = sem.p.targets[items[0][0]]
        reasons.append(f"\"{target.title}\" is still on its way to {target.subscriber_name}, and nothing will take it.")
        owners += [target.subscriber_name, target.producer]
    summary = " ".join(reasons) or "Nothing can move, and the journey has not finished."
    if point:
        summary += f" From step {point} on it could no longer finish."
        last = trail[point - 1][0]
        if last[0] in ("lost", "drop", "dlv", "dlv2"):
            target = sem.p.targets[last[3]]
            owners = [target.producer, target.subscriber_name] + owners
    return Finding("F6", where, summary, items=tuple(renderer.ids([(l, p) for l, p, _, _ in trail])),
                   owners=_owners(*owners), trace=tuple(renderer.trace(trail)))


def _atoms_of(expr):
    if expr[0] == "is":
        return {expr[1]}
    return set().union(*(_atoms_of(e) for e in expr[1:]))


def cause_words(program, cause):
    """What allowed (or failed to allow) a change, in words: "Confirm the booking" answering confirmed."""
    head, _, rest = cause.partition(" ")
    if head in program.contracts:
        title = program.contracts[head].title
        return f"\"{title}\" answering {words(rest)}" if rest else f"\"{title}\""
    target = next((t for t in program.targets if t.item == head), None)
    if target is not None:
        return f"{words(rest) or 'handling'} \"{target.title}\""
    flow = next((f for f, _, _ in program.flows if f.id == head), None)
    if flow is not None:
        return f"the steps of \"{flow.title}\" outside any case"
    if head == "timer":
        return f"the {words(rest)} timer firing" if rest else "a timer firing"
    return cause


def _last_pill(trail, pill):
    for label, _, _, _ in reversed(trail):
        call_line, case = pill(label)
        if call_line:
            return call_line, case
    return "", ""


def _apply_view(state, idx, to, sem):
    if to is None:
        return state
    ents = state[1][:idx] + (sem.codes[idx][to],) + state[1][idx + 1:]
    return (state[0], ents) + state[2:]


def _given_hint(sem, entity, current, to, cause, label):
    """Review 2.5: a flow that starts mid-lifecycle without GIVEN starts its entity at `initial`; say so."""
    if current != entity.initial or label is None or label[2] < 0:
        return ""
    if entity.slug in sem.p.flows[sem.p.code[label[2]].flow][2]:
        return ""
    starts = sorted({a for a, b, by in entity.table
                     if (to is None or b == to) and any(by == c or c.startswith(by + " ") for c in cause)})
    if not starts:
        return ""
    return (f" The flow has no GIVEN, so {entity.title} starts at its initial state, {words(entity.initial)}; "
            f"did you mean GIVEN {entity.slug} {starts[0]}?")


def _owners(*names):
    return tuple(n for n in dict.fromkeys(names) if n)


def _relabel(sem, before, after):
    for label, nxt, violation in sem.successors(before):
        if violation is None:
            canon, flip = sem.canonical(nxt)
            if canon == after:
                return label, flip
    raise AssertionError("an edge of the graph has no transition: the explorer and the semantics disagree")
