"""What handing an app over would leave unmet, before anyone hands it over (`vela handoff preview APP`, overhaul Task
21h). Pure: a built vault, the app, the slices it takes part in and their recorded flow-check standings in; a Preview
and its lines out. No disk, git or clock: the command module reads the record and passes the date.

The Violation this exists to prevent is a Leaky Narrative in the grill's handoff step: HANDOFF.md had the model work
out the handoff checklist from `vela ladder`, then pick out of `vela next` and `vela check` each item still a draft or
not decided yet, each contract with no case table and each provider nobody has designed. Three outputs read by hand
is where a line goes missing, and a missing line is what the senior accepts without a yes. Every part here comes from
the reader that already owns it, so the preview can't tell the lead less than the handoff record will:

- the checklist is `ladder.missing` for every stage up to and including the handoff, plus the epics stage's own
  entries (no concern cell left unexamined, every container settled), because CONVENTIONS "Handoff" lists those two
  on the handoff checklist. Epic pages are not on it: epics come after handoff, so they never hold one back;
- the not-settled list is `handoffwarn.gaps`, the same sentences `vela handoff` writes under "Not firm at handoff";
- each slice's flow check is `flowcheck.standing` as `vela handoff` records it, never a pass the record does not
  hold (a slice with no record reads "not checked").

Only an unmet checklist makes the preview exit 1: the not-settled items are what the lead tells the app's team, not a
block (the lead may hand over anyway; that is the "handoff checklist" override, recorded as START.md says).
"""
import re
from dataclasses import dataclass

from vela import handoffwarn, ladder, say, schema

# The stages whose entry lists make up the handoff checklist: every stage after baseline. "epics" is the stage's name,
# but its entry list is concern cells and containers, which CONVENTIONS "Handoff" puts on the checklist.
CHECKLIST_STAGES = schema.ENUMS["stage"][1:]


@dataclass(frozen=True)
class SliceCheck:
    key: str  # the slice's ID, or its release heading while it has no page
    label: str  # "SLC-003 Kiosks book ...": the default mode's words
    name: str  # the slice's own name, what the lead hears
    standing: object  # flowcheck.standing.Standing

    def as_json(self):
        s = self.standing
        return {"slice": self.key, "name": self.name, "state": s.state, "words": s.words, "checked": s.checked,
                "open": list(s.open), "line": s.line()}


@dataclass(frozen=True)
class Preview:
    app_id: str
    named: str  # "Shop (APP-shop)"
    name: str  # "Shop"
    unmet: tuple  # checklist sentences
    not_settled: tuple  # handoffwarn sentences
    checks: tuple  # SliceCheck, in slice order
    record_warning: str = ""
    gaps: tuple = ()  # the handoffwarn.Gap behind each not-settled sentence, so the lead hears them grouped

    @property
    def ready(self):
        return not self.unmet

    def as_json(self):
        return {"app": self.app_id, "ready": self.ready, "checklist_not_met": list(self.unmet),
                "not_settled": list(self.not_settled), "flow_checks": [c.as_json() for c in self.checks],
                "record_warning": self.record_warning}


def checklist(vault, app):
    """Each handoff checklist item the app's pages don't meet yet, in ladder order, each said once."""
    seen = []
    for stage in CHECKLIST_STAGES:
        for gap in ladder.missing(vault, app, stage):
            if gap not in seen:
                seen.append(gap)
    return seen


def preview(vault, app, taking_part, standings, record_warning=""):
    """The Preview of handing `app` over: `taking_part` is `slices.for_app`, `standings` {slice key: Standing}."""
    checks = tuple(SliceCheck(s.key, s.label, s.name, standings[s.key]) for s in taking_part if s.key in standings)
    found = handoffwarn.gaps(vault, app)
    return Preview(app.id, vault.named(app.id), vault.name_of(app.id), tuple(checklist(vault, app)),
                   tuple(g.sentence for g in found), checks, record_warning, tuple(found))


def things(n):
    return f"{n} thing{'' if n == 1 else 's'}"


def lines(found):
    """The preview as `say.Line`s for the default mode and `--json`: every checklist item and every not-settled
    sentence, with IDs. The lead's words are `lead_lines`, grouped (a default line says nothing to the lead)."""
    if found.ready:
        out = [say.Line(f"vela handoff preview {found.app_id}: {found.named} meets the handoff checklist.", plain="")]
    else:
        out = [say.Line(f"vela handoff preview {found.app_id}: {found.named} doesn't meet the handoff checklist yet: "
                        f"{things(len(found.unmet))} not met.", plain="")]
        out += [say.Line(f"- {gap}", plain="") for gap in found.unmet]
        out.append(say.Line('Handing it over anyway is the "handoff checklist" override.', plain=""))
    if found.not_settled:
        n = len(found.not_settled)
        out.append(say.Line(f"{things(n)} not settled at handoff: each is still a draft or not decided yet, has no case "
                            "table, or calls an app nobody has designed. Tell the app's team before they accept it:",
                            plain=""))
        out += [say.Line(f"- {sentence}", plain="") for sentence in found.not_settled]
    if found.checks:
        out.append(say.Line("Flow checks, as recorded:", plain=""))
        out += [say.Line(f"- {c.label}: {c.standing.line()}", plain="") for c in found.checks]
    else:
        out.append(say.Line(f"{found.name} is on no slice, so there is no flow check to report.", plain=""))
    if found.record_warning:
        out.append(say.Line(f"Warning: {found.record_warning}", plain=""))
    return out


# How the checklist's sentences group for the lead (ladder.missing's own words), so three contracts listed three
# times read as one thing: "three of its contracts aren't settled".
_CONTRACT = re.compile(r"^(?P<name>.+?), which it (?:offers|uses), (?P<phrase>.+)$")
_CONCERN = re.compile(r"^the concern (?P<name>.+?) hasn't been checked for this app$")
_QUESTION = re.compile(r"^the open question (?P<name>.+?) holds up (?P<held>.+)$")
_NO_YES = ": nobody has said yes to it."
_REQUIREMENT = re.compile(r"and the same goes for its acceptance criteria\.$")
_EPIC = re.compile(r"and the same goes for its \d+ acceptance criteria: nobody has agreed what finished looks like\.$")


def _grouped_checklist(unmet, plain):
    """(the parts of the answer, the checklist items said one by one)."""
    contracts, concerns, questions, others = [], [], [], []
    for gap in unmet:
        for pattern, bucket in ((_CONTRACT, contracts), (_CONCERN, concerns), (_QUESTION, questions)):
            m = pattern.match(gap)
            if m:
                name = plain(m["name"])
                if name not in bucket:
                    bucket.append(name)
                break
        else:
            others.append(plain(gap))
    parts = []
    if contracts:
        parts.append(f"{say.count_words(len(contracts))} of its contracts aren't settled"
                     + (f" ({say.names_said(contracts)})" if len(contracts) <= 3 else ""))
    if concerns:
        shown = say.names_said(concerns[:3]) + (f" and {say.count_words(len(concerns) - 3)} more" if len(concerns) > 3 else "")
        parts.append(f"nobody has looked at {shown} for it yet")
    if questions:
        parts.append(f"{say.count_words(len(questions))} open question{'s hold' if len(questions) != 1 else ' holds'} "
                     "up its contracts")
    if others:
        n = len(others)
        parts.append(f"{say.count_words(n)} {'other ' if parts else ''}thing{'s' if n != 1 else ''} on its checklist "
                     f"{'aren' if n != 1 else 'isn'}'t met yet")
    return parts, [o[0].upper() + o[1:] + "." for o in others]


def _grouped_not_settled(found, plain):
    """The not-settled gaps as a few lines: who hasn't said yes, which calls don't say what a failure returns, and the
    rest as written."""
    no_yes, no_cases, requirements, epics, rest = [], [], [], [], []
    for gap in found.gaps:
        if gap.kind == "unfirm" and gap.sentence.endswith(_NO_YES):
            no_yes.append(plain(gap.subject))
        elif gap.kind == "unfirm" and _REQUIREMENT.search(gap.sentence):
            requirements.append(plain(gap.subject))
        elif gap.kind == "unfirm" and _EPIC.search(gap.sentence):
            epics.append(plain(gap.subject))
        elif gap.kind == "no-case-table":
            no_cases.append(plain(gap.subject))
        else:
            rest.append(plain(gap.sentence))
    out = []
    if no_yes:
        out.append(f"Nobody has said yes to {say.names_said(no_yes)} yet.")
    if no_cases:
        one = len(no_cases) == 1
        out.append(f"{say.names_said(no_cases)} {'doesn' if one else 'don'}'t say what {'it returns' if one else 'they return'} "
                   "when a call fails.")
    if requirements:
        n = len(requirements)
        out.append(f"{say.count_words(n, capital=True)} requirement{'s' if n != 1 else ''} and {'their' if n != 1 else 'its'} "
                   f"criteria {'aren' if n != 1 else 'isn'}'t decided yet: {say.names_said(requirements)}.")
    if epics:
        n = len(epics)
        out.append(f"{say.count_words(n, capital=True)} epic{'s are' if n != 1 else ' is'} still {'drafts' if n != 1 else 'a draft'}, "
                   f"criteria and all, so nobody has agreed what finished looks like: {say.names_said(epics)}.")
    return out + rest


def lead_lines(found, plain):
    """What the lead hears: the answer, then the checklist one thing at a time, then what the team should hear."""
    if found.ready:
        answer = f"{found.name} meets the handoff checklist."
        items = []
    else:
        parts, items = _grouped_checklist(found.unmet, plain)
        answer = f"{found.name} isn't ready to hand over: {say.names_said(parts)}."
    settled = _grouped_not_settled(found, plain)
    if settled:
        items.append(f"The team should hear {'these' if len(settled) > 1 else 'this'} before they say yes:")
        items += settled
    if found.checks:
        items.append("Flow checks: " + "; ".join(f"{c.name}, {c.standing.line()}" for c in found.checks) + ".")
    if found.record_warning:
        items.append(plain(found.record_warning))
    return answer, items


def result(found, resolver=None):
    """The `say.Result`: exit 1 while the checklist is not met, else 0. The preview writes nothing either way."""
    plain = (resolver or say.Resolver()).plain
    answer, items = lead_lines(found, plain)
    return say.Result("handoff preview", exit=say.DONE if found.ready else say.REFUSED,
                      lines=lines(found) + [say.Line("", plain=i) for i in items], data=found.as_json(), answer=answer,
                      closing="" if found.ready else "You can still hand it over; I'll note that the team took it "
                                                     "with these open.")
