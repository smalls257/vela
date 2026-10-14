"""A finding, and the slice's result. Pure data.

`call_line` and `case` name the call step and the case key a finding is about, so the dashboard (D8) can mark the
status pill on that call without parsing the sentence.
"""
from dataclasses import dataclass, field

TITLES = {
    "F1": "Unhandled case", "F2": "Invented answer", "F3": "Unconsumed event", "F3w": "Consumed outside the slice",
    "F4": "Unused case", "F5": "Illegal transition", "F6": "Can't finish", "F8": "Not final",
    "F9": "Invariant broken", "F10": "Unreadable or undeclared", "F11": "Not fully checked",
    "F12": "Unmodeled handling", "F13": "Loose end",
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
        head = (f"planner check-slice: {self.name} ({', '.join(self.flows)}): {self.status}. {_count(errors, 'error')}, "
                f"{_count(warnings, 'warning')}" + (f", {covered} covered by overrides" if covered else "") +
                f". {self.states} states, {self.transitions} transitions, {self.seconds:.2f} s.")
        return "\n".join([head] + [f.format() for f in self.findings])


def _count(n, word):
    return f"{n} {word}{'' if n == 1 else 's'}"
