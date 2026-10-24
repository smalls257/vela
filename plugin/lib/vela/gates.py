"""Whether an item is ready to go on a Grill's agenda, computed once per item (overhaul Task 13). Pure.

The Violation this module exists to prevent is a Distributed Monolith between the grill skill and the check: the skill
told the model to search `11-unknowns-and-risks.md` for `**Blocks:**` itself to decide GATE-4, while E316 already does
that search in `rules.py`. Two copies of one rule drift, and the model's copy is the one nobody tests. So (Shield) the
conditions code can judge live here, read from the same functions the check rules read, and `vela check --gate grill
--item X --for-lead|--json` prints the verdict (Filter): "ready", or "not ready" with the plain reason and the one thing
that would make it ready.

What is judged, and why each rule is the grill skill's own (the why moves with the rule, plan 3.1):

- **GATE-1, the stage.** An app's item (the app page, its runtime page, a contract on its page) is grilled once the app
  is at `target` or later (`progress.in_grill_stage`): before then the app's parts are not read back, so a decision
  would be about a shape nobody confirmed. Initiative-level items pass.
- **GATE-2, a preferred option.** The item is at `assumption` with an `**Options considered:**` bullet, or an epic is at
  `draft` or `reopened`: a Grill decides between options Shape wrote down, it does not invent them. An item already
  `decided` (or a `fact`) is said so, since reopening is a change of mind the lead chooses. A concern page, a table row,
  an unknown or a risk carries no option bullet, so GATE-2 is left to the skill for those (a concern cell passes when the
  lead states what the initiative does for the app; code can't hear that).
- **GATE-4, open questions.** No open unknown's `**Blocks:**` holds the item, by `model.blockers`, which reads the same
  `model.blocked_units` E316 reads: a link to a page blocks every item on it, so linking the page cannot dodge the gate.
- **The case table.** A contract is not decided without its case table with an error case among its rows, or it is a
  Paper Tiger: decided while nobody said what happens when the call goes wrong (`cases.case_table`, as W380 and W385).
  A slice's joins need theirs too, because the flow check and the stubs read them.
- **The flow check.** A flow or a slice is not ready while its recorded flow check (`flowcheck.standing`) has a finding,
  is "not fully checked", or has not been run on it as it is now. Never a pass by default (R0), and no override covers
  "not fully checked": a check that did not finish proved nothing to set aside. Flow-check findings are set aside by the
  dated overrides the checker itself reads, which its standing already applies.

GATE-3 (the agenda's yes) and GATE-5 (the owner present) stay the skill's: code can't hear a yes.

The lead may override any rule. An `**Override:**` on the item naming the rule lets it through when `override.covers` it
today, and the verdict lists it, never hides it (Sensor): a standing rule's override past its `until` covers nothing, and
the fix says it ended. An owed question that blocks the item (W807) is a question to ask, not a gate, so it is listed
and never makes the item not ready; one the session record already answers (a capture whose words start with its copy
ID, or a wildcard over it, or a "waits on UNK-nnn:" capture naming it) is skipped, because close writes its ledger row
later. A "decided with <copy IDs> open (W807)" capture records a decision, not an answer.

`verdict(vault, record, item, today, flows=None)` is the interface Task 16's `decide` reads. `record` is the session
record's text or None; `flows` is {slice key or flow ID: standing.Standing} for the keys `flow_keys` names, read by the
shell from the checker's record. A flow or slice with no standing given is "not checked", never ready.
"""
import re
import shlex
from dataclasses import dataclass

from vela import cases, closegate, ladder, model, override, progress, questions, say, schema, slices
from vela.flowcheck import standing as flowstanding

FLOW_CHECK, CASE_TABLE = "flow check", "case table"
# The model's route when the lead lives with a finding: the command, never the Override bullet's grammar.
FLOW_OVERRIDE_ROUTE = ('If the lead lives with a finding, record it with vela apply (kind override, the slice page, rule '
                       '"flow check") with their reason and an end date; "not fully checked" takes none.')
CASE_TABLE_RULE = '"case table"'
OVERRIDE_NAMES = {"GATE-1": ("GATE-1",), "GATE-2": ("GATE-2",), "GATE-4": ("GATE-4", "E316"),
                  CASE_TABLE: (CASE_TABLE_RULE,)}
ROUTE_NAMES = {"GATE-1": "GATE-1", "GATE-2": "GATE-2", "GATE-4": "GATE-4", CASE_TABLE: CASE_TABLE_RULE}
NO_OPTION_KINDS = ("unknown", "risk", "party", "stored-value")
EPIC_OPEN = ("draft", "reopened")

_COPY = r"Q-[A-Z]{3}-\d{2}@(?:[A-Za-z0-9][A-Za-z0-9-]*\*?|\*)"
COPY_FIRST = re.compile(rf"^(?P<copy>{_COPY})")
COPY_ANY = re.compile(_COPY)
WAITS_ON = re.compile(r"^waits on UNK-\d+:\s*(?P<ids>.+)$")
DECIDED_WITH = re.compile(r"^decided with\b", re.I)
OWNER_NAME = re.compile(r"\(([^)]+)\)")


@dataclass(frozen=True)
class Reason:
    """One condition the item fails. `plain` and `fix` are for the lead (names, no IDs); `next` is the model's step."""
    rule: str  # "GATE-1", "GATE-2", "GATE-4", "case table" or "flow check"
    plain: str
    fix: str
    next: str = ""
    blocked_by: tuple = ()  # the open unknowns, for GATE-4

    def as_json(self):
        return {"rule": self.rule, "plain": self.plain, "fix": self.fix, "next": self.next,
                "blocked_by": list(self.blocked_by)}


@dataclass(frozen=True)
class Verdict:
    id: str
    name: str
    ready: bool
    reasons: tuple = ()
    overridden: tuple = ()  # Override.as_dict() of each override that let a rule through
    owed: tuple = ()  # copy IDs still owed on the item, not answered in the record
    questions: tuple = ()  # the owed copies' questions, in the same order
    route: str = ""  # the `vela decide` flags that would decide it anyway, "" when ready or when nothing can

    @property
    def fix(self):
        return self.reasons[0].fix if self.reasons else ""

    def as_json(self):
        return {"id": self.id, "name": self.name, "ready": self.ready, "reasons": [r.as_json() for r in self.reasons],
                "fix": self.fix, "override": self.route, "overridden": list(self.overridden), "owed": list(self.owed)}


# ------------------------------------------------------------------ where an item sits

@dataclass(frozen=True)
class Unit:
    id: str
    page: object
    item: object  # the heading Item, or None for a page or a table row
    scope: str  # the override scope: the item's ID, or "" for page level


def unit(vault, item_id):
    item = vault.item(item_id)
    if item is not None:
        return Unit(item_id, item.page, item, item_id)
    pages = vault.by_id.get(item_id)
    if pages:
        return Unit(item_id, pages[0], None, "")
    if item_id in vault.row_ids:
        return Unit(item_id, vault.row_ids[item_id][0], None, "")
    raise ValueError(f"{item_id} is not an ID in this vault")


UNDECIDED = ("inkling", "assumption", "draft")


def candidates(vault):
    """IDs a grill could decide: contracts and requirements whose State is not yet decided or fact, and pages whose own
    state is still a guess. `check --gate grill --all` gates every one on turn 1, so the grill can open with the ready
    one instead of reading the vault to find it (the reading spree is Computational Friction at the lead's expense)."""
    ids = [i.id for i in vault.contracts + vault.requirements if i.fact("State") in UNDECIDED]
    ids += [p.id for p in vault.pages if p.meta.get("state") in UNDECIDED and p.id]
    return sorted(set(ids))


def app_of(vault, found):
    """The app page whose item this is, or None for an initiative-level item."""
    page = found.page
    if page.type == "app-building-blocks":
        return page
    if page.type == "app-runtime" and page.name.endswith("-runtime"):
        app = vault.page(page.name[: -len("-runtime")] + "-building-blocks")
        return app if app is not None and app.type == "app-building-blocks" else None
    return None


def _say(vault, ident):
    return say.Resolver(vault).name(ident)


# ------------------------------------------------------------------ overrides

def _covering(vault, found, rule, today):
    """(covering overrides, ended overrides) on the item naming the rule."""
    names = OVERRIDE_NAMES[rule]
    mine = [o for o in override.valid_overrides(found.page, found.scope) if set(o.rules) & set(names)]
    return [o for o in mine if override.covers(o, today)], [o for o in mine if not override.covers(o, today)]


def _ended(fix, ended):
    if not ended:
        return fix
    last = max(o.until or "" for o in ended)
    return f"{fix} Your exception for this ended on {last}, so it doesn't cover it any more."


def route(vault, item_id, rules, today):
    """The `vela decide` flags that decide the item anyway, with a suggested end for a standing rule (offered, never
    written: the lead picks the date). Flags, not the Override bullet's grammar: a model that reads the bullet writes
    it by hand, and only `vela decide` and `vela apply` record an override with its receipts."""
    names = [ROUTE_NAMES[r] for r in rules if r in ROUTE_NAMES]
    if not names:
        return ""
    until = f" --until {override.suggest_until(item_id, vault, today)}" if any(map(override.is_standing, names)) else ""
    flags = " ".join(f"--override {shlex.quote(name)}" for name in names)
    return f"vela decide {item_id} ... {flags} --reason-from ^cR{until}"


# ------------------------------------------------------------------ the conditions

def stage_reason(vault, found, name):
    app = app_of(vault, found)
    if app is None or app.meta.get("change") not in schema.LADDERED_CHANGES or progress.in_grill_stage(vault, app):
        return None
    stage = ladder.stage(vault, app)
    app_name = _say(vault, app.id)
    return Reason("GATE-1", f"{app_name} is still at the {stage} stage, and a grill needs it at target or later.",
                  f"I'd run a Discover session on {app_name} first. Or I can decide {name} now and note it as "
                  "your call.", f"/vela:discover {app.id}")


def _state_and_options(found):
    if found.item is not None:
        return found.item.fact("State"), schema.OPTIONS_LABEL in found.item.facts
    return progress.text(found.page.meta.get("state")), bool(found.page.page_bullets(schema.OPTIONS_LABEL))


def option_reason(vault, found, name):
    if found.item is not None and found.item.kind in NO_OPTION_KINDS:
        return None
    if found.item is None and (found.page.id != found.id or found.page.type in ("concern", slices.PAGE_TYPE)):
        return None  # a table row or a concern page carries no option bullet; a slice is planned, not decided
    state, options = _state_and_options(found)
    reopen = "We can reopen it if you've changed your mind, and I'll note that you did."
    if state == "decided":
        return Reason("GATE-2", f"{name} is already decided.", reopen)
    if state == "fact":
        return Reason("GATE-2", f"{name} is already settled as a fact from a source.", reopen)
    if found.page.type == "epic" and found.item is None:
        if state in EPIC_OPEN:
            return None
        return Reason("GATE-2", f"{name} isn't written up as a draft yet, and an epic gets decided from a draft.",
                      f"I'd write {name} up as a draft first. Or I can decide it now and note it as your call.",
                      "/vela:epics")
    if state == "assumption" and options:
        return None
    said = "has no state yet" if not state else "is only an inkling" if state == "inkling" else \
        "has no options on the table yet, so there's nothing to pick from"
    return Reason("GATE-2", f"{name} {said}.", "I'd lay out the options first. Or I can decide it now and note it as "
                                               "your call.", f"/vela:shape {found.id}")


def unknown_reason(vault, found, name, today, blocked):
    blockers = blocked.get(found.id, [])
    if not blockers:
        return None, ()
    covering, ended = _covering(vault, found, "GATE-4", today)
    if covering:
        return None, tuple(covering)
    first = blockers[0]
    question = first.fact("Question") or first.name
    owner = OWNER_NAME.search(first.fact("Owner"))
    who = owner.group(1) if owner else first.fact("Owner")
    more = f" ({len(blockers) - 1} more open question{'' if len(blockers) == 2 else 's'} hold it up too.)" \
        if len(blockers) > 1 else ""
    waits = f"it waits for {who}" if who else "it waits until someone owns that question"
    fix = (f"Do you know the answer? If not, {waits}, or you can decide {name} anyway until a date you pick.")
    return Reason("GATE-4", f"{name} waits on an open question nobody has answered yet: {question}{more}",
                  _ended(fix, ended), "ask the lead; else the unknown's owner and ask-by date, or a research task",
                  tuple(u.id for u in blockers)), ()


def case_problem(vault, contract):
    """The plain sentence for a contract whose case table is missing or holds no error case, or ""."""
    table = cases.case_table(contract.page, contract)
    name = _say(vault, contract.id)
    if table is None:
        return f"Nobody has written down what {name} says back when a call goes wrong."
    if not any(c.is_error for c in table.cases):
        return f"{name}'s case table has no answer for when a call goes wrong."
    return ""


def case_reason(vault, found, name, today):
    if found.item is None or found.item.kind != "contract":
        return None, ()
    problem = case_problem(vault, found.item)
    if not problem:
        return None, ()
    covering, ended = _covering(vault, found, CASE_TABLE, today)
    if covering:
        return None, tuple(covering)
    return Reason(CASE_TABLE, problem, _ended("I'd go through what it sends back when things go wrong, one case at a "
                                              "time, here, or take it back to a boundary session.", ended),
                  f"/vela:boundary {found.id}"), ()


def slice_of(vault, item_id):
    return next((s for s in slices.read_slices(vault) if s.id == item_id), None)


def flow_keys(vault, item_id):
    """The flow-check record keys a verdict on this item reads: a slice's own key; a flow's own ID, then each slice
    that names it. Empty for anything else."""
    found = slice_of(vault, item_id)
    if found is not None:
        return [found.key]
    if item_id.startswith("FLO-") and any(p.type == "flow" for p in vault.by_id.get(item_id, ())):
        return [item_id] + [s.key for s in slices.read_slices(vault) if item_id in s.flows]
    return []


HOLDS = (flowstanding.PASSED, flowstanding.FINDINGS, flowstanding.NOT_FULLY)


def judged_standings(keys, flows):
    """The standings a flow's or slice's readiness rests on: the first key's when its record holds, else the others'
    that hold. Empty when nothing recorded holds."""
    got = [(k, flows.get(k)) for k in keys]
    own = got[0][1]
    if own is not None and own.state in HOLDS:
        return [got[0]]
    return [(k, s) for k, s in got[1:] if s is not None and s.state in HOLDS]


def flow_reason(vault, found, name, flows):
    keys = flow_keys(vault, found.id)
    if not keys:
        return None
    judged = judged_standings(keys, flows or {})
    command = f'vela check-slice "{keys[0]}"'
    if not judged:
        return Reason(FLOW_CHECK, f"The flow check hasn't been run on {name} as it stands now, so nothing shows it works.",
                      "Run the flow check on it, then read each finding out with its owners and settle it.", command)
    failing = [(k, s) for k, s in judged if not s.passed]
    if not failing:
        return None
    _, worst = failing[0]
    said = ("is not fully checked: the check did not finish, so it proved nothing yet" if worst.state == flowstanding.NOT_FULLY
            else f"has {worst.words}" + (f" ({', '.join(worst.open)})" if worst.open else ""))
    return Reason(FLOW_CHECK, f"The flow check of {name} {said}.",
                  "I'd read each finding out with its owners and settle it. If you're happy to live with one for "
                  "now, I'll note that with an end date; a check that didn't finish can't be waved through.",
                  f"{command}. {FLOW_OVERRIDE_ROUTE}")


def slice_reasons(vault, found, name, today):
    """A slice is planned, not decided: one already planned is said so, and every contract its flows call needs its case
    table with an error case."""
    if found.page.type != slices.PAGE_TYPE:
        return []
    got = slice_of(vault, found.id)
    if got is None:
        return []
    out = []
    if slices.rank(got.status) >= slices.rank("planned"):
        out.append(Reason("GATE-2", f"{name} is already {got.status}.", "Its later statuses are the team's to set."))
    for contract_id in got.joins:
        contract = vault.item(contract_id)
        problem = case_problem(vault, contract) if contract is not None else ""
        covering, _ = _covering(vault, unit(vault, contract_id), CASE_TABLE, today) if problem else ([], [])
        if problem and not covering:
            out.append(Reason(CASE_TABLE, problem, "I'd go through what it sends back when things go wrong first, one "
                                                   "case at a time.", f"/vela:boundary {contract_id}"))
    return out


# ------------------------------------------------------------------ the record

def answered(record):
    """The copy IDs and wildcards the session record answers: each capture whose words start with one, and each "waits
    on UNK-nnn:" capture's list. A "decided with ... open" capture is a decision, never an answer."""
    out = set()
    for capture in closegate.captures(record or "").values():
        words = capture.words.strip()
        if DECIDED_WITH.match(words):
            continue
        first = COPY_FIRST.match(words)
        if first:
            out.add(first.group("copy"))
        waits = WAITS_ON.match(words)
        if waits:
            out.update(COPY_ANY.findall(waits.group("ids")))
    return out


def is_answered(copy_id, patterns):
    for pattern in patterns:
        if pattern.endswith("*") and copy_id.startswith(pattern[:-1]):
            return True
        if copy_id == pattern:
            return True
    return False


# ------------------------------------------------------------------ the verdict

def verdict(vault, record, item, today, flows=None):
    """One item's Verdict. `today` is "YYYY-MM-DD"; nothing here reads a clock, the disk or git."""
    today = str(today)
    found = unit(vault, item)
    name = _say(vault, item)
    blocked = vault.cache.get("gate-blockers")
    if blocked is None:
        blocked = vault.cache["gate-blockers"] = model.blockers(vault)
    reasons, overridden = [], []
    for rule, judged in (("GATE-1", stage_reason(vault, found, name)), ("GATE-2", option_reason(vault, found, name))):
        if judged is None:
            continue
        covering, ended = _covering(vault, found, rule, today)
        if covering:
            overridden.extend(covering)
        else:
            reasons.append(Reason(judged.rule, judged.plain, _ended(judged.fix, ended), judged.next))
    for judged, covering in (unknown_reason(vault, found, name, today, blocked), case_reason(vault, found, name, today)):
        overridden.extend(covering)
        if judged is not None:
            reasons.append(judged)
    reasons.extend(slice_reasons(vault, found, name, today))
    flow = flow_reason(vault, found, name, flows)
    if flow is not None:
        reasons.append(flow)
    patterns = answered(record)
    owed = [d for d in questions.owed_on(vault, item) if not is_answered(d.copy.id, patterns)]
    unique = []
    for o in overridden:
        if o not in unique:
            unique.append(o)
    return Verdict(item, name, not reasons, tuple(reasons), tuple(o.as_dict() for o in unique),
                   tuple(d.copy.id for d in owed), tuple(d.copy.entry.question for d in owed),
                   route(vault, item, [r.rule for r in reasons], today) if reasons else "")


# ------------------------------------------------------------------ what the command says

def lines_for(found, resolver):
    """[say.Line] for one item: the text line carries IDs and rule names (for files and the skill), the plain one is
    what the lead hears, every ID said by its name."""
    plain = resolver.plain
    if found.ready:
        out = [say.Line(f"{found.id}: ready", plain=f"{found.name} is ready to decide.")]
    else:
        first = found.reasons[0]
        out = [say.Line(f"{found.id}: not ready ({first.rule}): {first.plain}",
                        plain=f"{found.name} isn't ready to decide yet. {plain(first.plain)} {plain(first.fix)}")]
        out += [say.Line(f"{found.id}: also ({r.rule}): {r.plain}", plain=f"Also: {plain(r.plain)}")
                for r in found.reasons[1:]]
    for o in found.overridden:
        until = f" until {o['until']}" if o.get("until") else ""
        out.append(say.Line(f"{found.id}: overridden: {', '.join(o['rules'])} by {o['by']} on {o['date']}{until}",
                            plain=f"{found.name} goes ahead because you made an exception{until}: "
                                  f"{plain(o['reason'])}"))
    out += [say.Line(f"{found.id}: owed {copy}", plain=f"Still to ask about {found.name}: {plain(question)}")
            for copy, question in zip(found.owed, found.questions)]
    return out


def report(vault, verdicts, notes=()):
    """The say.Result for `check --gate grill --item ... --for-lead|--json`: exit 0 when every item is ready, else 1."""
    resolver = say.Resolver(vault)
    ready = sum(1 for v in verdicts if v.ready)
    head = (f"All {len(verdicts)} items are ready to decide." if ready == len(verdicts) and len(verdicts) > 1
            else f"{ready} of {len(verdicts)} items {'is' if ready == 1 else 'are'} ready to decide.")
    verdicts = sorted(verdicts, key=lambda v: not v.ready)  # ready ones first: the grill leads with one
    lines = [say.Line(head, plain=head)] if len(verdicts) > 1 else []
    for found in verdicts:
        lines += lines_for(found, resolver)
    lines += [say.Line(n, plain=resolver.plain(n)) for n in notes]
    return say.Result("check --gate grill", exit=say.DONE if ready == len(verdicts) else say.REFUSED, lines=lines,
                      data={"ready": ready == len(verdicts), "items": [v.as_json() for v in verdicts]})
