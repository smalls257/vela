"""A finding, and the slice's result. Pure data.

`call_line` and `case` name the call step and the case key a finding is about, so the dashboard (D8) can mark the
status pill on that call without parsing the sentence.
"""
from dataclasses import dataclass, field

# Each title is said the way a reader would say it: the dashboard's error-case notes and the slices' check line show
# them, so model-checker words ("invariant broken", "illegal transition") don't belong here (label sweep, 2026-10-16).
TITLES = {
    "F1": "An answer nobody handles", "F2": "An answer the contract doesn't give", "F3": "A message nobody picks up",
    "F3w": "Picked up outside the slice", "F4": "An answer nobody uses", "F5": "A change the plan doesn't allow",
    "F6": "Can't finish", "F8": "Stops halfway", "F9": "Breaks a rule that must always hold",
    "F10": "Unreadable or undeclared", "F11": "Not fully checked", "F12": "Handling the diagram doesn't show",
    "F13": "Loose end",
}
WARNINGS = {"F3w", "F4", "F12"}
NOT_CHECKED = {"F10", "F11"}


@dataclass(frozen=True)
class Finding:
    code: str
    where: str  # "06-runtime/flows/FLO-001-buy.md:14"
    summary: str  # one sentence in plain words, names not IDs
    items: tuple = ()  # the IDs it is about, for the reader who wants them
    owners: tuple = ()  # app titles that own the decision
    trace: tuple = ()  # sentences, start to the bad state
    case: str = ""  # the case key the finding is about, when it is about one
    call_line: str = ""  # the call step it is about, "path:line"
    covered: str = ""  # the override that covers it, when one does and has not expired

    @property
    def severity(self):
        if self.covered:
            return "covered"
        return "warning" if self.code in WARNINGS else "error"

    def format(self):
        head = f"{self.code} {TITLES.get(self.code, '')}: {self.where}: {self.summary}"
        if self.covered:
            head += f" Covered by an override until {self.covered}."
        lines = [head]
        lines += [f"  {n}. {sentence}" for n, sentence in enumerate(self.trace, 1)]
        if self.owners:
            lines.append(f"  {'Owner' if len(self.owners) == 1 else 'Owners'} of the decision: {', '.join(self.owners)}.")
        if self.items:
            lines.append(f"  IDs: {', '.join(self.items)}.")
        return "\n".join(lines)


@dataclass
class SliceResult:
    name: str
    flows: tuple
    findings: list = field(default_factory=list)
    states: int = 0
    transitions: int = 0
    seconds: float = 0.0
    runs: list = field(default_factory=list)  # [(journeys, states, transitions, complete)]
    skipped: list = field(default_factory=list)  # [flow ids] of runs a budget stop left unexplored
    limits: list = field(default_factory=list)  # sentences: what the result rests on and does not claim
    journeys: int = 2  # journeys at once over a shared entity: 2, or 3 on request

    @property
    def status(self):
        """passes, fails, or not fully checked. Never passes with a budget stop or an unreadable line (R0)."""
        codes = {f.code for f in self.findings if f.severity == "error"}
        if codes & NOT_CHECKED:
            return "fails, and is not fully checked" if codes - NOT_CHECKED else "not fully checked"
        return "fails" if codes else "passes"

    def format(self):
        errors = sum(1 for f in self.findings if f.severity == "error")
        warnings = sum(1 for f in self.findings if f.severity == "warning")
        covered = sum(1 for f in self.findings if f.severity == "covered")
        head = (f"vela check-slice: {self.name} ({', '.join(self.flows)}): {self.status}. {_count(errors, 'error')}, "
                f"{_count(warnings, 'warning')}" + (f", {covered} covered by overrides" if covered else "") +
                f". {self.states} states, {self.transitions} transitions, {self.seconds:.2f} s.")
        return "\n".join([head] + [f"Limit: {limit}" for limit in self.limits] + [f.format() for f in self.findings])

    @property
    def open(self):
        """The findings that block the slice: errors no unexpired override covers."""
        return [f for f in self.findings if f.severity == "error"]

    def lead_line(self, name):
        """What the lead hears about this slice, by its name: whether it runs end to end, and if not, the first thing
        that breaks it. No counters, timings, codes or paths (`check-slice --for-lead`; the 14 October voice audit)."""
        status = self.status
        if status == "passes":
            covered = any(f.severity == "covered" for f in self.findings)
            return f"{name} runs end to end." + (" A few cases go through on exceptions you set." if covered else "")
        unread = [f for f in self.open if f.code == "F10"]
        if status == "not fully checked":
            if any(f.code == "F11" for f in self.open):
                return f"{name} isn't fully checked: the check ran out of time before it finished, so it isn't proven yet."
            return f"{name} isn't checked yet: {_unread_words(unread[0])}" if unread else f"{name} isn't checked yet."
        broken = [f for f in self.open if f.code not in NOT_CHECKED]
        more = len(broken) - 1
        said = f"{name} breaks: {broken[0].summary}" if broken else f"{name} breaks."
        return said + (f" There {'is' if more == 1 else 'are'} {more} more problem{'' if more == 1 else 's'} like it."
                       if more > 0 else "")


def _unread_words(finding):
    """An unreadable line in plain words: a flow with no sequence drawn is said as that, not as its markup."""
    if "mermaid" in finding.summary or "sequenceDiagram" in finding.summary:
        return "its steps aren't drawn as a sequence yet, so there's nothing to check."
    return finding.summary


def _count(n, word):
    return f"{n} {word}{'' if n == 1 else 's'}"
