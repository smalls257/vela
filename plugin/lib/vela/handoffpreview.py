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
    return Preview(app.id, vault.named(app.id), vault.name_of(app.id), tuple(checklist(vault, app)),
                   tuple(g.sentence for g in handoffwarn.gaps(vault, app)), checks, record_warning)


def things(n):
    return f"{n} thing{'' if n == 1 else 's'}"


def lines(found):
    """The preview as `say.Line`s: the default text with IDs, the plain words beside each where the resolver alone
    would not say it the way a lead hears it."""
    if found.ready:
        out = [say.Line(f"vela handoff preview {found.app_id}: {found.named} meets the handoff checklist.",
                        plain=f"{found.name} meets the handoff checklist.")]
    else:
        out = [say.Line(f"vela handoff preview {found.app_id}: {found.named} doesn't meet the handoff checklist yet: "
                        f"{things(len(found.unmet))} not met.",
                        plain=f"{found.name} doesn't meet the handoff checklist yet; {things(len(found.unmet))} not met:")]
        out += [say.Line(f"- {gap}") for gap in found.unmet]
        out.append(say.Line('Handing it over anyway is the "handoff checklist" override.'))
    if found.not_settled:
        n = len(found.not_settled)
        out.append(say.Line(f"{things(n)} not settled at handoff: each is still a draft or not decided yet, has no case "
                            "table, or calls an app nobody has designed. Tell the app's team before they accept it:"))
        out += [say.Line(f"- {sentence}") for sentence in found.not_settled]
    if found.checks:
        out.append(say.Line("Flow checks, as recorded:"))
        out += [say.Line(f"- {c.label}: {c.standing.line()}", plain=f"- {c.name}: {c.standing.line()}") for c in found.checks]
    else:
        out.append(say.Line(f"{found.name} is on no slice, so there is no flow check to report."))
    if found.record_warning:
        out.append(say.Line(f"Warning: {found.record_warning}"))
    return out


def result(found):
    """The `say.Result`: exit 1 while the checklist is not met, else 0. The preview writes nothing either way."""
    return say.Result("handoff preview", exit=say.DONE if found.ready else say.REFUSED, lines=lines(found),
                      data=found.as_json())
