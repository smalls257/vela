"""Counterexamples in plain words. Pure.

Each label already knows its source (the instruction it ran, the contract and case, the event, the timer), so a trace
renders with no parsing. Names go in the sentences; IDs go in the finding's IDs line. What an answer did to an entity
is read off the states either side of the step, so the sentence says what happened, not what was meant to.
"""
from vela.flowcheck.properties import words


def lower_first(text):
    return text[:1].lower() + text[1:] if text else text


class Renderer:
    def __init__(self, program, sem, apps):
        self.p, self.sem, self.apps = program, sem, apps

    def real(self, journey, parity):
        return 3 - journey if parity and self.sem.n == 2 else journey

    def prefix(self, journey, parity):
        return f"Journey {self.real(journey, parity)}: " if self.sem.n > 1 and journey else ""

    def entity_name(self, idx, parity):
        slug, journey = self.sem.instances[idx]
        title = self.p.entities[slug].title
        return title if journey == 0 else f"{title} {self.real(journey, parity)}"

    def owner_of(self, slug):
        owner = self.p.entities[slug].owner
        app = self.apps.get(str(owner))
        return app.title if app else str(owner)

    def trace(self, steps):
        """steps: [(label, parity, state before, state after)] -> sentences."""
        return [self.sentence(label, parity, before, after) for label, parity, before, after in steps]

    def changes(self, before, after, parity, skip=()):
        out = []
        for idx, (a, b) in enumerate(zip(before[1], after[1])):
            if a != b and idx not in skip:
                out.append(f"{self.entity_name(idx, parity)} is now {words(self.sem.names[idx][b])}")
        return out

    def sentence(self, label, parity, before, after):
        kind, journey, pc, x, attempt, flag = label[:6]
        head = self.prefix(journey, parity)
        text, skip = self.describe(kind, journey, pc, x, attempt, flag, parity, label[6] if len(label) > 6 else -1), ()
        if kind == "set":
            ins = self.p.code[pc]
            skip = (self.sem.entity_index(ins.data["entity"], journey),)
        extra = self.changes(before, after, parity, skip)
        if extra:
            text = text.rstrip(".") + "; " + ", ".join(extra) + "."
        return head + text[:1].upper() + text[1:]

    def describe(self, kind, journey, pc, x, attempt, flag, parity, case_index=-1):
        if kind in ("dlv", "dlv2", "dup", "lost", "drop"):
            t = self.p.targets[x]
            return {"dlv": f"{t.subscriber_name} receives \"{t.title}\".",
                    "dlv2": f"{t.subscriber_name} receives \"{t.title}\", and a duplicate is still on its way.",
                    "dup": f"{t.subscriber_name} receives \"{t.title}\" a second time.",
                    "lost": f"\"{t.title}\" is lost on its way to {t.subscriber_name}.",
                    "drop": f"The duplicate of \"{t.title}\" never arrives."}[kind]
        if kind == "timer":
            return f"The {words(self.p.timers[x].name)} timer fires."
        ins = self.p.code[pc]
        if kind in ("ans", "tmo", "enter"):
            table = self.p.contracts[ins.data["contract"]]
            caller, provider = ins.actor, ins.data["provider"]
            # The call line's own words read as a verb ("place a hold"); a contract's title is often a noun ("Consent check").
            said = ins.data.get("words")
            ask = f"{caller} asks {provider} to {lower_first(said)}" if said else f"{caller} asks {provider} for \"{table.title}\""
            if kind == "enter":
                return ask + "."
            if kind == "ans":
                case = table.cases[x]
                text = ask + (f", and {provider} answers {words(case.key)} ({case.status})" if not case.is_error
                              else f", and is refused: {words(case.key)} ({case.status})")
                emitted = [self.event_title(e) for e in case.emits if ins.data["emits"].get(case.key)]
                if emitted:
                    text += "; " + provider + " publishes " + ", ".join(f"\"{e}\"" for e in emitted)
            elif x < 0:
                text = ask + f", and the call times out before {provider} does anything"
            else:
                case = table.cases[x]
                text = ask + f", and the call times out, though {provider} had in fact answered {words(case.key)}"
                emitted = [self.event_title(e) for e in case.emits if ins.data["emits"].get(case.key)]
                if emitted:
                    text += " and published " + ", ".join(f"\"{e}\"" for e in emitted)
            return text + self.retry_words(caller, table, attempt, flag) + "."
        if kind in ("ptmo", "pcarry"):
            table = self.p.contracts[ins.data["contract"]]
            caller, provider = ins.actor, ins.data["provider"]
            what = (f"{provider} stops there, and what it has done so far stands" if kind == "ptmo"
                    else f"{provider} carries on with it alone")
            return (f"{caller} times out waiting for {provider} part-way through \"{table.title}\": {what}"
                    + self.retry_words(caller, table, attempt, flag) + ".")
        if kind == "late":
            call = self.p.code[x]
            table = self.p.contracts[call.data["contract"]]
            case = table.cases[case_index] if ins.kind == "contract" else next(c for c in table.cases if c.key == ins.data["case"])
            return f"{ins.actor} answers {call.actor}: {words(case.key)} ({case.status}), but {call.actor} has already moved on."
        if kind in ("reply", "rtmo"):
            call = self.p.code[x]
            table = self.p.contracts[call.data["contract"]]
            case = table.cases[case_index] if ins.kind == "contract" else next(c for c in table.cases if c.key == ins.data["case"])
            text = f"{ins.actor} answers {call.actor}: {words(case.key)} ({case.status})"
            if kind == "rtmo":
                text += f", but {call.actor} has already timed out"
            return text + self.retry_words(call.actor, table, attempt, flag) + "."
        if kind == "pub":
            t = self.p.targets[x]
            if ins.data.get("inbound"):
                return f"{t.producer} calls {t.subscriber_name}: \"{t.title}\"."
            return f"{t.producer} publishes \"{t.title}\" for {t.subscriber_name}."
        if kind == "set":
            idx = self.sem.entity_index(ins.data["entity"], journey)
            return f"{ins.actor} sets {self.entity_name(idx, parity)} to {words(ins.data['state'])}."
        if kind == "end":
            return self.end_words(ins, attempt, flag, journey, parity)
        if kind == "arm":
            timer = self.p.timers[x]
            return f"{ins.actor} starts the {words(timer.name)} timer ({timer.band})."
        if kind == "human":
            return ins.data["words"].rstrip(".") + "."
        return kind

    def retry_words(self, caller, table, attempt, flag):
        if flag == 1:
            return f"; {caller} tries again (attempt {attempt + 1} of {table.retries.max})"
        if flag == 2:
            return f"; {caller} gives up after {table.retries.max} attempts"
        return ""

    def end_words(self, ins, attempt, flag, journey, parity):
        outcome = words(ins.data["outcome"])
        thread = ins.data["thread"]
        if thread == "main":
            text = f"the journey ends: {outcome}"
            if ins.data["leaves"]:
                left = ", ".join(f"{self.entity_name(self.sem.entity_index(s, journey), parity)} {words(v)}"
                                 for s, v in sorted(ins.data["leaves"].items()))
                text += f", leaving {left}"
            return text + "."
        h = self.p.handlers[thread]
        if flag == 1:
            return f"{h.subscriber_name}'s handling of \"{h.title}\" ends {outcome}; it tries again (attempt {attempt + 1} of {h.retries.max})."
        if flag == 2:
            return f"{h.subscriber_name}'s handling of \"{h.title}\" ends {outcome}, and {h.subscriber_name} has no retries left."
        return f"{h.subscriber_name} finishes handling \"{h.title}\": {outcome}."

    def event_title(self, eid):
        for t in self.p.targets:
            if t.item == eid:
                return t.title
        return eid

    def ids(self, labels):
        """IDs along a trace, first seen first: contracts, events, entities changed."""
        out = []
        for label, _ in labels:
            kind, journey, pc, x = label[:4]
            found = []
            if kind in ("dlv", "dlv2", "dup", "lost", "drop", "pub"):
                found.append(self.p.targets[x if kind != "pub" else self.p.code[pc].data["target"]].item)
            elif kind in ("ans", "tmo", "enter", "ptmo", "pcarry"):
                found.append(self.p.code[pc].data["contract"])
            elif kind in ("reply", "rtmo", "late"):
                found.append(self.p.code[x].data["contract"])
            elif kind == "set":
                found.append(self.p.entities[self.p.code[pc].data["entity"]].id)
            out += [f for f in found if f and f not in out]
        return out

    def actor(self, label):
        kind, _, pc, x = label[:4]
        if kind in ("dlv", "dlv2", "dup", "lost", "drop"):
            return self.p.targets[x].subscriber_name
        if kind == "timer" or pc < 0:
            return ""
        ins = self.p.code[pc]
        if ins.kind == "end" and ins.data["thread"] != "main":
            return self.p.handlers[ins.data["thread"]].subscriber_name
        return ins.actor
