"""The transition system of one run: one or two journeys over a compiled Program. Pure.

A state is a tuple of plain tuples and ints, so it hashes cheaply and two runs build identical graphs:
    (threads, entity states, touched bitmask, messages, armed timers)
- a thread is (journey, handler id or -1 for main or -2 for a provider carrying on alone, spawn number, pc, call frames,
  attempt, applied, handler attempt); pc >= 0 runs, -1 ended by falling off its steps, -(p + 2) ended at the END
  instruction p;
- a call frame is (call pc, attempt, applied) for drawn provider handling in progress (the call stack); attempt 0 marks
  the frame of a call whose caller timed out and moved on, so its answer goes nowhere;
- an entity state is an index into that entity's sorted states; one per (entity, journey), one for a shared entity;
- messages are queues (key, items), item (target, journey, duplicate); `any` order and duplicates are unordered;
- an armed timer is (journey, timer id).

Successors are generated in a fixed order: threads by id, then messages by queue key, then timers.

Two reductions, both switchable for measurement:
- symmetry: two journeys of the same flow are interchangeable, so a state and its swap are one state (review 1.8);
- local steps: a step that touches only its own thread (a call to a contract with no guards, effects or emits, a
  drawn call's entry, a reply, a HUMAN step, arming a timer) commutes with every other step and changes nothing the
  properties observe, so when one is enabled it alone is explored. Sound here because the graph is acyclic.
"""
from vela.flowcheck.build import GAVE_UP, TIMEOUT

ENDED = -1
DETACHED = -2  # the handler id of a provider carrying on with a call its caller has timed out on
GONE = 0  # the attempt of a frame whose caller has moved on
SYMMETRY, LOCAL_STEPS = "symmetry", "local-steps"
ALL_REDUCTIONS = frozenset({SYMMETRY, LOCAL_STEPS})


def ended_at(pc):
    return -pc - 2 if pc <= -2 else None


class Semantics:
    def __init__(self, program, journeys, reductions=ALL_REDUCTIONS):
        self.p = program
        self.code = program.code
        self.journeys = tuple(journeys)  # flow index per journey; journey numbers are 1..n
        self.n = len(self.journeys)
        unknown = set(reductions) - ALL_REDUCTIONS
        if unknown:
            raise ValueError(f"unknown reductions: {sorted(unknown)}")
        self.symmetric = SYMMETRY in reductions and self.n == 2 and self.journeys[0] == self.journeys[1]
        self.reduce = LOCAL_STEPS in reductions
        flows = set(self.journeys)
        used = set()
        for ins in self.code:
            if ins.flow in flows:
                used |= _entities_of(ins, program)
        for index in flows:
            used |= set(program.flows[index][2])
        grown = True
        while grown:  # entities an invariant ties to the ones this run touches (see Builder.add_invariant_entities)
            grown = False
            for slug in sorted(program.entities):
                for _, _, expr in program.entities[slug].invariants:
                    names = {n for n in _atoms(expr) | {slug} if n in program.entities}
                    if names & used and not names <= used:
                        used |= names
                        grown = True
        self.instances = []
        for slug in sorted(used):
            entity = program.entities[slug]
            if entity.shared:
                self.instances.append((slug, 0))
            else:
                self.instances += [(slug, j) for j in range(1, self.n + 1)]
        self.index = {key: i for i, key in enumerate(self.instances)}
        self.names = [sorted(program.entities[slug].states) for slug, _ in self.instances]
        self.codes = [{s: c for c, s in enumerate(names)} for names in self.names]
        self.swap_entities = [self.index.get((slug, 3 - j) if j else (slug, 0), i) for i, (slug, j) in enumerate(self.instances)]
        self.local = [self._is_local(ins) for ins in self.code]
        self.invariants = [(slug, text, expr) for slug in sorted(used) for text, _, expr in program.entities[slug].invariants
                           if _atoms(expr) <= used]
        self.has_shared = any(j == 0 for _, j in self.instances)

    # --- the start ------------------------------------------------------------------------------------------------

    def initial(self):
        ents = []
        for slug, j in self.instances:
            entity = self.p.entities[slug]
            state = entity.initial
            for journey, flow_index in enumerate(self.journeys, 1):
                givens = self.p.flows[flow_index][2]
                if slug in givens and (j == 0 or j == journey):
                    state = givens[slug]
                    break
            ents.append(self.codes[self.index[(slug, j)]][state])
        threads = tuple((j, -1, 0, self.settle(self.p.flows[f][1]), (), 1, 0, 1) for j, f in enumerate(self.journeys, 1))
        return (threads, tuple(ents), 0, (), ())

    def settle(self, pc):
        while True:
            ins = self.code[pc]
            if ins.kind == "goto":
                pc = ins.data["target"]
            elif ins.kind == "done":
                return ENDED
            else:
                return pc

    def entity_index(self, slug, journey):
        found = self.index.get((slug, 0))
        return found if found is not None else self.index[(slug, journey)]

    # --- the step relation ----------------------------------------------------------------------------------------

    def successors(self, state):
        """[(label, next state, violation or None)]. A label is (kind, journey, pc, x, attempt, flag)."""
        threads = state[0]
        if self.reduce:
            for i, t in enumerate(threads):
                if t[3] >= 0 and self.local[t[3]]:
                    return self.thread_steps(state, i)
        out = []
        for i, t in enumerate(threads):
            if t[3] >= 0:
                out += self.thread_steps(state, i)
        out += self.message_steps(state)
        out += self.timer_steps(state)
        return out

    def thread_steps(self, state, i):
        """Thread i's own steps, and, inside drawn handling, its callers timing out part-way through (ledger C40).
        Each touches thread i alone, so the local-steps reduction may take them together."""
        out = self.step(state, i)
        if state[0][i][4]:
            out += self.part_way(state, i)
        return out

    def step(self, state, i):
        t = state[0][i]
        ins = self.code[t[3]]
        kind = ins.kind
        if kind == "call":
            return self.call_steps(state, i, ins)
        if kind == "reply":
            return self.reply_steps(state, i, ins)
        if kind == "contract":
            return self.contract_steps(state, i, ins)
        if kind == "publish":
            msgs = self.publish(state[3], ins.data["target"], t[0])
            return [(("pub", t[0], t[3], ins.data["target"], 0, 0), self.with_thread(state, i, self.advance(t), msgs=msgs), None)]
        if kind == "set":
            ents, touched, viol = self.apply(state[1], state[2], t[0], ((ins.data["entity"], ins.data["state"]),), ins.data["cause"], t[3])
            nxt = self.with_thread((state[0], ents, touched, state[3], state[4]), i, self.advance(t))
            return [(("set", t[0], t[3], 0, 0, 0), nxt, viol)]
        if kind == "end":
            return [self.end_step(state, i, ins)]
        if kind == "timer":
            armed = tuple(sorted(set(state[4]) | {(t[0], ins.data["timer"])}))
            return [(("arm", t[0], t[3], ins.data["timer"], 0, 0), self.with_thread(state, i, self.advance(t), timers=armed), None)]
        if kind == "human":
            return [(("human", t[0], t[3], 0, 0, 0), self.with_thread(state, i, self.advance(t)), None)]
        return []  # await: woken by a delivery or a timer

    def advance(self, t, pc=None):
        nxt = self.settle(t[3] + 1 if pc is None else pc)
        return (t[0], t[1], t[2], nxt, t[4], 1, 0, t[7])

    def with_thread(self, state, i, thread, msgs=None, timers=None):
        threads = state[0][:i] + (thread,) + state[0][i + 1:]
        return (threads, state[1], state[2], state[3] if msgs is None else msgs, state[4] if timers is None else timers)

    def call_steps(self, state, i, ins):
        t = state[0][i]
        table = self.p.contracts[ins.data["contract"]]
        journey, attempt, applied = t[0], t[5], t[6]
        out = []
        if ins.data["drawn"] is not None:
            frames = t[4] + ((t[3], attempt, applied),)
            entered = (t[0], t[1], t[2], self.settle(ins.data["drawn"]), frames, 1, 0, t[7])
            out.append((("enter", journey, t[3], -1, attempt, 0), self.with_thread(state, i, entered), None))
            if table.timeout:
                out += self.observe(state, i, t, ins, table, TIMEOUT, attempt, applied, ("tmo", -1), state)
            return out
        ents = state[1]
        enabled = [(n, c) for n, c in enumerate(table.cases) if self.guard(ents, journey, c)]
        for n, case in enabled:
            after, viol = self.effects(state, journey, ins, table, case, applied)
            out += self.observe(after, i, t, ins, table, case.key, attempt, 1 if table.idempotent else 0, ("ans", n), state, viol)
        if table.timeout:
            out += self.observe(state, i, t, ins, table, TIMEOUT, attempt, applied, ("tmo", -1), state)
            if not (table.idempotent and applied):
                for n, case in enabled:
                    after, viol = self.effects(state, journey, ins, table, case, applied)
                    out += self.observe(after, i, t, ins, table, TIMEOUT, attempt, 1 if table.idempotent else 0, ("tmo", n), state, viol)
        return out

    def effects(self, state, journey, ins, table, case, applied):
        """The state after the provider applied `case` (its sets and emits); an idempotent call applies them once."""
        if table.idempotent and applied:
            return state, None
        ents, touched, viol = self.apply(state[1], state[2], journey, case.sets, (f"{table.id} {case.key}",), None)
        msgs = state[3]
        for target in ins.data["emits"].get(case.key, ()):
            msgs = self.publish(msgs, target, journey)
        return (state[0], ents, touched, msgs, state[4]), viol

    def observe(self, after, i, t, ins, table, key, attempt, applied, label, before, viol=None):
        """The caller sees `key`: retried, given up on, or its branch taken. `after` already holds the provider's effects."""
        kind, x = label
        retries = table.retries
        if retries is not None and key in retries.on:
            if attempt < retries.max:
                thread = (t[0], t[1], t[2], t[3], t[4], attempt + 1, applied, t[7])
                return [((kind, t[0], t[3], x, attempt, 1), self.with_thread(after, i, thread), viol)]
            key, flag = GAVE_UP, 2
        else:
            flag = 0
        target = ins.data["branches"].get(key)
        if target is None:
            return []  # no branch: F1 is reported statically, or an override covers it
        return [((kind, t[0], t[3], x, attempt, flag), self.with_thread(after, i, self.advance(t, target)), viol)]

    def contract_steps(self, state, i, ins):
        """ANSWERS FROM CONTRACT: the provider answers with any listed case whose When holds, applying its effects, and
        the answer goes back to the caller as a drawn reply would (it may still find the caller timed out)."""
        t = state[0][i]
        table = self.p.contracts[ins.data["contract"]]
        out = []
        for n in ins.data["cases"]:
            case = table.cases[n]
            if not self.guard(state[1], t[0], case):
                continue
            ents, touched, viol = self.apply(state[1], state[2], t[0], case.sets, (f"{table.id} {case.key}",), t[3])
            msgs = state[3]
            for target in ins.data["emits"].get(case.key, ()):
                msgs = self.publish(msgs, target, t[0])
            after = (state[0], ents, touched, msgs, state[4])
            for label, nxt, _ in self.reply_steps(after, i, ins, case.key, n):
                out.append((label, nxt, viol))
        return out

    def reply_steps(self, state, i, ins, case_key=None, case_index=-1):
        t = state[0][i]
        call_pc, attempt, applied = t[4][-1]
        if attempt == GONE:  # the caller timed out and moved on: the answer goes nowhere, and the provider is done
            done = (t[0], t[1], t[2], ENDED, (), 1, 0, t[7])
            return [(("late", t[0], t[3], call_pc, 0, 0, case_index), self.with_thread(state, i, done), None)]
        call = self.code[call_pc]
        table = self.p.contracts[call.data["contract"]]
        caller = (t[0], t[1], t[2], call_pc, t[4][:-1], attempt, applied, t[7])
        out = []
        case_key = ins.data["case"] if case_key is None else case_key
        for key, kind in ((case_key, "reply"), (TIMEOUT, "rtmo")):
            if kind == "rtmo" and not table.timeout:
                continue
            retries = table.retries
            if retries is not None and key in retries.on and attempt < retries.max:
                frames = t[4][:-1] + ((call_pc, attempt + 1, applied),)
                again = (t[0], t[1], t[2], self.settle(call.data["drawn"]), frames, 1, 0, t[7])
                out.append(((kind, t[0], t[3], call_pc, attempt, 1, case_index), self.with_thread(state, i, again), None))
                continue
            seen = GAVE_UP if retries is not None and key in retries.on else key
            target = call.data["branches"].get(seen)
            if target is None:
                continue
            out.append(((kind, t[0], t[3], call_pc, attempt, 2 if seen == GAVE_UP else 0, case_index),
                        self.with_thread(state, i, self.advance(caller, target)), None))
        return out

    def part_way(self, state, i):
        """A caller of drawn handling times out while its provider is part-way through it (ledger C40): what the
        provider has done so far stands, and the caller takes its timeout branch (or tries again). The provider then
        either stops where it is ("ptmo") or carries on alone ("pcarry"), and its answer goes nowhere. Before its first
        step this is the request arriving late; after its last, the answer arriving late (as "rtmo"). Each frame of the
        call stack whose call can time out is a caller that can give up, the innermost one included."""
        t = state[0][i]
        frames = t[4]
        out = []
        for k, (call_pc, attempt, applied) in enumerate(frames):
            call = self.code[call_pc]
            table = self.p.contracts[call.data["contract"]]
            if attempt == GONE or not table.timeout:
                continue
            retries = table.retries
            below = frames[:k]
            if retries is not None and TIMEOUT in retries.on and attempt < retries.max:
                caller = (t[0], t[1], t[2], self.settle(call.data["drawn"]), below + ((call_pc, attempt + 1, applied),), 1, 0, t[7])
                flag = 1
            else:
                seen = GAVE_UP if retries is not None and TIMEOUT in retries.on else TIMEOUT
                target = call.data["branches"].get(seen)
                if target is None:
                    continue  # no branch: F1 is reported statically, or an override covers it
                caller = self.advance((t[0], t[1], t[2], call_pc, below, attempt, applied, t[7]), target)
                flag = 2 if seen == GAVE_UP else 0
            out.append((("ptmo", t[0], call_pc, t[3], attempt, flag), self.with_thread(state, i, caller), None))
            spawn = 1 + max((th[2] for th in state[0] if th[0] == t[0] and th[1] == DETACHED), default=-1)
            alone = (t[0], DETACHED, spawn, t[3], ((call_pc, GONE, 0),) + frames[k + 1:], t[5], t[6], 1)
            threads = state[0][:i] + (caller,) + state[0][i + 1:]
            out.append((("pcarry", t[0], call_pc, t[3], attempt, flag),
                        (tuple(sorted(threads + (alone,))),) + state[1:], None))
        return out

    def end_step(self, state, i, ins):
        t = state[0][i]
        thread = ins.data["thread"]
        done = (t[0], t[1], t[2], -t[3] - 2, (), 1, 0, t[7])
        if thread != "main":
            handler = self.p.handlers[thread]
            retries = handler.retries
            if retries is not None and ins.data["outcome"] in retries.on:
                if t[7] < retries.max:
                    again = (t[0], t[1], t[2], self.settle(handler.body), (), 1, 0, t[7] + 1)
                    return (("end", t[0], t[3], 0, t[7], 1), self.with_thread(state, i, again), None)
                return (("end", t[0], t[3], 0, t[7], 2), self.with_thread(state, i, done), None)
        return (("end", t[0], t[3], 0, t[7], 0), self.with_thread(state, i, done), None)

    # --- entities -------------------------------------------------------------------------------------------------

    def guard(self, ents, journey, case):
        for slug, states in case.when:
            idx = self.entity_index(slug, journey)
            if self.names[idx][ents[idx]] not in states:
                return False
        return True

    def apply(self, ents, touched, journey, sets, cause, pc):
        """(entities, touched, violation): each change must be a row of the entity's table allowed by `cause`."""
        viol = None
        for slug, target in sets:
            idx = self.entity_index(slug, journey)
            current = self.names[idx][ents[idx]]
            to = target if isinstance(target, str) else dict(target).get(current)
            if to is None:
                viol = viol or ("F5", idx, current, None, cause, pc)
                continue
            if to == current:
                continue
            if not _allowed(self.p.entities[slug].table, current, to, cause):
                viol = viol or ("F5", idx, current, to, cause, pc)
            ents = ents[:idx] + (self.codes[idx][to],) + ents[idx + 1:]
            touched |= 1 << idx
        return ents, touched, viol

    # --- messages and timers --------------------------------------------------------------------------------------

    def queue_key(self, target, journey):
        t = self.p.targets[target]
        if t.order == "per-producer":
            return (1, t.producer, t.subscriber, 0)
        if str(t.order).startswith("per:"):
            return (2, self.entity_index(t.key_entity, journey), t.subscriber, 0)
        return (0, target, journey, 0)

    def has_effect(self, target):
        t = self.p.targets[target]
        return t.hid is not None or (t.item, t.subscriber) in self.p.awaited

    def publish(self, msgs, target, journey, duplicate=0):
        """Messages with one more item. A delivery with no effect (an outside subscriber, or handling drawn nowhere)
        is not put in flight: it can change nothing the properties observe."""
        if not self.has_effect(target):
            return msgs
        key = self.queue_key(target, journey) if not duplicate else (3, target, journey, 0)
        item = (target, journey, duplicate)
        out, placed = [], False
        for qkey, items in msgs:
            if qkey == key:
                out.append((qkey, items + (item,)))
                placed = True
            else:
                out.append((qkey, items))
        if not placed:
            out.append((key, (item,)))
            out.sort()
        return tuple(out)

    def message_steps(self, state):
        out = []
        for q, (qkey, items) in enumerate(state[3]):
            target, journey, duplicate = items[0]
            rest = state[3][:q] + (((qkey, items[1:]),) if len(items) > 1 else ()) + state[3][q + 1:]
            t = self.p.targets[target]
            delivered = self.deliver(state, target, journey)
            if delivered is not None:
                threads, ents, touched, _, timers = delivered
                if t.delivery == "at-least-once" and not duplicate:
                    out.append((("dlv", journey, -1, target, 0, 0), (threads, ents, touched, rest, timers), None))
                    again = self.publish(rest, target, journey, duplicate=1)
                    out.append((("dlv2", journey, -1, target, 0, 0), (threads, ents, touched, again, timers), None))
                else:
                    out.append((("dup" if duplicate else "dlv", journey, -1, target, 0, 0), (threads, ents, touched, rest, timers), None))
            if t.delivery == "may-be-lost" and not duplicate:
                out.append((("lost", journey, -1, target, 0, 0), (state[0], state[1], state[2], rest, state[4]), None))
            if duplicate:
                out.append((("drop", journey, -1, target, 0, 0), (state[0], state[1], state[2], rest, state[4]), None))
        return out

    def deliver(self, state, target, journey):
        """The state after delivering one message, its queue untouched; None when nothing can take it yet. A thread
        awaiting it takes it first; else its handler starts; else it waits for an awaiter."""
        t = self.p.targets[target]
        threads = state[0]
        for i, th in enumerate(threads):
            if th[0] != journey or th[3] < 0:
                continue
            ins = self.code[th[3]]
            if ins.kind == "await" and ins.data["item"] == t.item and ins.data["app"] == t.subscriber:
                woken = (th[0], th[1], th[2], self.settle(ins.data["received"]), th[4], 1, 0, th[7])
                timers = state[4]
                if ins.data["timer_branch"] is not None:
                    # An AWAIT with a timer branch is a race; whichever ends the wait cancels the other.
                    timers = tuple(a for a in timers if a != (journey, ins.data["timer"]))
                return self.with_thread(state, i, woken, timers=timers)
        if t.hid is None:
            return None
        spawn = 1 + max((th[2] for th in threads if th[0] == journey and th[1] == t.hid), default=-1)
        handler = self.p.handlers[t.hid]
        new = (journey, t.hid, spawn, self.settle(handler.body), (), 1, 0, 1)
        return (tuple(sorted(threads + (new,))), state[1], state[2], state[3], state[4])

    def timer_steps(self, state):
        """An armed timer fires, once (revision 2, item 10). It wakes an AWAIT racing it into the AWAIT's timer branch,
        and starts its par block's handler; whichever of the event and the timer comes first cancels the other."""
        out = []
        for armed in state[4]:
            journey, timer = armed
            timers = tuple(a for a in state[4] if a != armed)
            threads = state[0]
            for i, th in enumerate(threads):
                ins = self.code[th[3]] if th[3] >= 0 else None
                if th[0] == journey and ins is not None and ins.kind == "await" and ins.data["timer_branch"] is not None \
                        and ins.data["timer"] == timer:
                    threads = threads[:i] + ((th[0], th[1], th[2], self.settle(ins.data["timer_branch"]), th[4], 1, 0, th[7]),) + threads[i + 1:]
                    break
            hid = self.p.timers[timer].hid
            if hid is not None:
                spawn = 1 + max((th[2] for th in threads if th[0] == journey and th[1] == hid), default=-1)
                new = (journey, hid, spawn, self.settle(self.p.handlers[hid].body), (), 1, 0, 1)
                threads = tuple(sorted(threads + (new,)))
            out.append((("timer", journey, -1, timer, 0, 0), (threads, state[1], state[2], state[3], timers), None))
        return out

    # --- judging a state ------------------------------------------------------------------------------------------

    def finished(self, state):
        return all(t[3] < 0 for t in state[0]) and not state[3]

    def invariant_broken(self, state):
        for slug, text, expr in self.invariants:
            for journey in range(1, self.n + 1):
                if not self.holds(expr, state[1], journey):
                    return ("F9", slug, text, journey)
        return None

    def holds(self, expr, ents, journey):
        op = expr[0]
        if op == "is":
            if (expr[1], 0) not in self.index and (expr[1], journey) not in self.index:
                return True
            idx = self.entity_index(expr[1], journey)
            return self.names[idx][ents[idx]] == expr[2]
        if op == "not":
            return not self.holds(expr[1], ents, journey)
        if op == "and":
            return self.holds(expr[1], ents, journey) and self.holds(expr[2], ents, journey)
        if op == "or":
            return self.holds(expr[1], ents, journey) or self.holds(expr[2], ents, journey)
        return (not self.holds(expr[1], ents, journey)) or self.holds(expr[2], ents, journey)

    def not_final(self, state):
        """[(entity instance, state)] touched and left neither final nor where its journey's END says it leaves it."""
        out = []
        for idx, (slug, j) in enumerate(self.instances):
            if not state[2] >> idx & 1:
                continue
            name = self.names[idx][state[1][idx]]
            if name in self.p.entities[slug].final:
                continue
            accepted = False
            for t in state[0]:
                at = ended_at(t[3])
                if t[1] == -1 and at is not None and (j == 0 or t[0] == j):
                    if self.code[at].data["leaves"].get(slug) == name:
                        accepted = True
            if not accepted:
                out.append((idx, name))
        return out

    # --- symmetry -------------------------------------------------------------------------------------------------

    def canonical(self, state):
        if not self.symmetric:
            return state, 0
        swapped = self.swap(state)
        return (swapped, 1) if swapped < state else (state, 0)

    def swap(self, state):
        threads, ents, touched, msgs, timers = state
        threads = tuple(sorted((3 - t[0],) + t[1:] for t in threads))
        perm = self.swap_entities
        new_ents = [0] * len(ents)
        new_touched = 0
        for i, value in enumerate(ents):
            new_ents[perm[i]] = value
            if touched >> i & 1:
                new_touched |= 1 << perm[i]
        queues = []
        for (kind, a, b, c), items in msgs:
            if kind in (0, 3):
                key = (kind, a, 3 - b, c)
            elif kind == 2:
                key = (kind, perm[a], b, c)
            else:
                key = (kind, a, b, c)
            queues.append((key, tuple((tg, 3 - j, d) for tg, j, d in items)))
        timers = tuple(sorted((3 - j, tm) for j, tm in timers))
        return (threads, tuple(new_ents), new_touched, tuple(sorted(queues)), timers)

    # --- reduction ------------------------------------------------------------------------------------------------

    def _is_local(self, ins):
        if ins.kind in ("human", "timer", "reply"):
            return True
        if ins.kind != "call":
            return False
        if ins.data["drawn"] is not None:
            return True
        table = self.p.contracts[ins.data["contract"]]
        return not any(c.sets or c.when or ins.data["emits"].get(c.key) for c in table.cases)


def _allowed(table, current, to, causes):
    for start, end, by in table:
        if start == current and end == to and any(by == c or c.startswith(by + " ") for c in causes):
            return True
    return False


def _atoms(expr):
    if expr[0] == "is":
        return {expr[1]}
    return set().union(*(_atoms(e) for e in expr[1:]))


def _entities_of(ins, program):
    data = ins.data
    if ins.kind == "set":
        return {data["entity"]}
    if ins.kind == "end":
        return set(data["leaves"])
    if ins.kind in ("call", "contract"):
        table = program.contracts[data["contract"]]
        return {slug for c in table.cases for slug, _ in c.sets + c.when}
    if ins.kind == "publish":
        target = program.targets[data["target"]]
        return {target.key_entity} if target.key_entity else set()
    return set()
